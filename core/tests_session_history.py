from django.conf import settings
from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.sessions.models import Session
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from organization.models import Delegation, Position, Role, UserProfile
from .middleware import PrivateResponseMiddleware


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class SessionHistoryTests(TestCase):
    def setUp(self):
        self.delegation = Delegation.objects.create(name='Sede de prueba de sesión', scope='Pruebas')
        self.admin = self.create_account('history-admin', 'Administrador General', 'Administrador', '11.111.111-1', True)
        self.social = self.create_account('history-social', 'Asistente Social', 'Asistente Social', '12.345.678-5')

    def create_account(self, username, position_name, role_name, rut, administrator=False):
        user = get_user_model().objects.create_user(username=username, password='PruebaSesion2026!', is_staff=administrator, is_superuser=administrator)
        position, _ = Position.objects.get_or_create(name=position_name)
        role, _ = Role.objects.get_or_create(name=role_name, defaults={'permissions_data': ['lectura', 'edicion']})
        profile = UserProfile.objects.create(user=user, rut=rut, full_name=username, email=username + '@example.test', delegation=self.delegation, position=position)
        profile.roles.add(role)
        return user

    def sign_in(self, user, remember=False):
        data = {'username': user.username, 'password': 'PruebaSesion2026!'}
        if remember:
            data['remember_me'] = 'on'
        response = self.client.post(reverse('core:login'), data)
        self.assertEqual(response.status_code, 302)
        return response

    def assert_private_no_store(self, response):
        policy = response['Cache-Control']
        for value in ('private', 'no-store', 'no-cache', 'must-revalidate', 'max-age=0'):
            self.assertIn(value, policy)
        self.assertIn('Cookie', response['Vary'])
        self.assertEqual(response['Pragma'], 'no-cache')

    def test_logout_invalidates_old_cookie_and_another_account_cannot_reopen_admin(self):
        self.sign_in(self.admin)
        old_key = self.client.session.session_key
        admin_page = self.client.get(reverse('activities:dashboard_admin'))
        self.assertEqual(admin_page.status_code, 200)
        self.assertContains(admin_page, 'js/session-guard.js')
        self.assert_private_no_store(admin_page)

        self.assert_private_no_store(self.client.get(reverse('core:logout')))
        self.assertFalse(Session.objects.filter(session_key=old_key).exists())
        old_browser = Client()
        old_browser.cookies[settings.SESSION_COOKIE_NAME] = old_key
        self.assertNotEqual(old_browser.get(reverse('activities:dashboard_admin')).status_code, 200)

        self.sign_in(self.social)
        self.assertNotEqual(self.client.session.session_key, old_key)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.social.pk))
        response = self.client.get(reverse('activities:dashboard_admin'), follow=True)
        self.assertEqual(response.redirect_chain[-1][0], reverse('activities:dashboard_asistente'))
        self.assertNotContains(response, 'Usuarios y Dotación Municipal')
        self.assert_private_no_store(response)
        self.assertEqual(self.client.get('/api/users/').status_code, 403)

    def test_authenticated_login_get_or_historical_post_keeps_current_account(self):
        self.sign_in(self.social)
        original_key = self.client.session.session_key
        for response in (
            self.client.get(reverse('core:login')),
            self.client.post(reverse('core:login'), {'username': self.admin.username, 'password': 'PruebaSesion2026!'}),
        ):
            self.assertEqual(response.url, reverse('activities:dashboard_asistente'))
            self.assert_private_no_store(response)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.social.pk))
        self.assertEqual(self.client.session.session_key, original_key)

    def test_login_and_session_state_responses_are_not_cached(self):
        login = self.client.get(reverse('core:login'))
        self.assertContains(login, 'js/session-guard.js')
        self.assert_private_no_store(login)
        anonymous = self.client.get(reverse('core:session_state'))
        self.assertEqual(anonymous.json(), {'fingerprint': '', 'redirect_url': reverse('core:login')})
        self.assert_private_no_store(anonymous)
        self.assert_private_no_store(self.sign_in(self.admin))
        state = self.client.get(reverse('core:session_state'))
        self.assert_private_no_store(state)
        self.assertEqual(state.json()['redirect_url'], reverse('activities:dashboard_admin'))
        self.assertNotIn(self.client.session.session_key, state.content.decode())
        self.assertNotIn('PruebaSesion2026!', state.content.decode())

    def test_fingerprint_changes_when_account_or_persisted_permissions_change(self):
        self.sign_in(self.social)
        initial = self.client.get(reverse('core:session_state')).json()['fingerprint']
        self.assertTrue(initial)
        self.assertEqual(initial, self.client.get(reverse('core:session_state')).json()['fingerprint'])
        role = self.social.profile.roles.get(name='Asistente Social')
        role.permissions_data = ['lectura']
        role.save(update_fields=['permissions_data', 'updated_at'])
        revised = self.client.get(reverse('core:session_state')).json()['fingerprint']
        self.assertNotEqual(initial, revised)
        self.client.get(reverse('core:logout'))
        self.assertEqual(self.client.get(reverse('core:session_state')).json()['fingerprint'], '')
        self.sign_in(self.admin)
        self.assertNotEqual(revised, self.client.get(reverse('core:session_state')).json()['fingerprint'])

    def test_invalidated_profile_is_not_presented_as_a_valid_session(self):
        self.sign_in(self.social)
        UserProfile.objects.filter(user=self.social).update(status='Inactivo')
        self.assertEqual(self.client.get(reverse('core:session_state')).json()['fingerprint'], '')
        response = self.client.get(reverse('core:login'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_fingerprint_detects_technical_privileges_revoked_outside_profile(self):
        self.sign_in(self.admin)
        initial = self.client.get(reverse('core:session_state')).json()['fingerprint']
        get_user_model().objects.filter(pk=self.admin.pk).update(is_superuser=False, is_staff=False)
        changed = self.client.get(reverse('core:session_state')).json()['fingerprint']
        self.assertNotEqual(initial, changed)

    def test_remember_checkbox_controls_cookie_lifetime_without_saving_credentials(self):
        self.sign_in(self.social)
        self.assertTrue(self.client.session.get_expire_at_browser_close())
        self.assertNotIn('password', self.client.session)
        self.client.get(reverse('core:logout'))
        self.sign_in(self.social, remember=True)
        self.assertFalse(self.client.session.get_expire_at_browser_close())
        self.assertLessEqual(self.client.session.get_expiry_age(), settings.SESSION_COOKIE_AGE)

    def test_static_assets_keep_their_own_cache_policy(self):
        response = PrivateResponseMiddleware(lambda request: HttpResponse('body {}', content_type='text/css'))(
            RequestFactory().get(settings.STATIC_URL + 'css/example.css'))
        self.assertNotIn('Cache-Control', response)
