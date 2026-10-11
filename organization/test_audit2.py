from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase
from django.utils import timezone

from core.models import PasswordRecoveryCode
from core.test_audit2 import WEAK_PASSWORDS, STRONG_PASSWORD
from organization.models import Delegation, Position, Role, UserProfile


class Audit2OrganizationTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user('audit_admin', password=STRONG_PASSWORD)
        self.admin_profile = UserProfile.objects.create(
            user=self.admin, rut='11.111.111-1', full_name='Admin Audit', email='admin@example.test',
        )
        self.admin_profile.roles.add(Role.objects.get(name='Administrador General'))
        self.target = get_user_model().objects.create_user('audit_target', password=STRONG_PASSWORD)
        self.target_profile = UserProfile.objects.create(
            user=self.target, rut='12.345.678-5', full_name='Target Audit', email='target@example.test',
        )
        self.client.force_login(self.admin)

    def post(self, path, data):
        return self.client.post(path, data=data, content_type='application/json')

    def payload(self, **changes):
        return dict(username='audit_new', full_name='Persona Nueva', email='new@example.test',
                    rut='9.876.543-3', password=STRONG_PASSWORD, **changes)

    def test_all_password_endpoints_reject_missing_components(self):
        for password in WEAK_PASSWORDS:
            for path, data in (
                ('/api/users/create/', {**self.payload(), 'password': password}),
                (f'/api/users/{self.target_profile.pk}/update/', {'password': password}),
                (f'/api/users/{self.target_profile.pk}/reset-password/', {'password': password}),
            ):
                with self.subTest(path=path, password=password):
                    self.assertEqual(self.post(path, data).status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username='audit_new').exists())
        self.target.refresh_from_db()
        self.assertTrue(self.target.check_password(STRONG_PASSWORD))

    def test_password_is_not_trimmed_and_html_specials_are_allowed(self):
        password = '  Viento49<>  '
        response = self.post('/api/users/create/', {**self.payload(), 'password': password})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(get_user_model().objects.get(username='audit_new').check_password(password))

    def test_functional_admin_cannot_grant_technical_privileges(self):
        for flag in ('is_superuser', 'is_staff'):
            with self.subTest(flag=flag):
                self.assertEqual(self.post('/api/users/create/', self.payload(**{flag: True})).status_code, 403)
                self.assertEqual(self.post(f'/api/users/{self.target_profile.pk}/update/', {flag: True}).status_code, 403)

    def test_functional_admin_cannot_take_over_superuser(self):
        self.target.is_superuser = True
        self.target.save()
        for operation in ('update', 'reset-password', 'delete', 'toggle-status'):
            with self.subTest(operation=operation):
                self.assertEqual(self.post(f'/api/users/{self.target_profile.pk}/{operation}/', {'password': 'OtraClave57!'}).status_code, 403)

    def test_administrative_password_changes_revoke_recovery(self):
        for operation in ('update', 'reset-password'):
            record = PasswordRecoveryCode.objects.create(
                user=self.target, code_hash=make_password('123456'), expires_at=timezone.now() + timedelta(minutes=10),
            )
            self.assertEqual(self.post(f'/api/users/{self.target_profile.pk}/{operation}/', {'password': 'OtraClave57!'}).status_code, 200)
            record.refresh_from_db()
            self.assertIsNotNone(record.used_at)

    def test_admin_reset_password_can_login_using_rut_and_registered_email(self):
        role, _ = Role.objects.get_or_create(name='Gestor Territorial')
        self.target_profile.roles.add(role)
        new_password = 'NuevaClavePrueba2026!'
        response = self.post(f'/api/users/{self.target_profile.pk}/reset-password/', {'password': new_password})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()['is_active'])
        self.assertEqual(response.json()['account_status'], 'Activo')
        self.assertTrue(response.json()['has_active_role'])
        self.target.refresh_from_db()
        self.assertTrue(self.target.check_password(new_password))

        for identifier in (self.target_profile.rut, self.target_profile.email):
            with self.subTest(identifier=identifier):
                login_client = Client()
                logged_in = login_client.post('/', {'username': identifier, 'password': new_password})
                self.assertEqual(logged_in.status_code, 302)
                self.assertTrue('_auth_user_id' in login_client.session)

    def test_admin_can_reassign_user_role_delegation_and_position(self):
        delegation = Delegation.objects.create(name='Delegación de prueba', scope='Centro')
        position = Position.objects.create(name='Cargo de prueba')
        role = Role.objects.create(name='Rol de prueba', permissions_data=['lectura'])
        response = self.post(f'/api/users/{self.target_profile.pk}/update/', {
            'full_name': self.target_profile.full_name,
            'email': self.target_profile.email,
            'rut': self.target_profile.rut,
            'delegation_id': delegation.pk,
            'position_id': position.pk,
            'role_ids': [role.pk],
        })
        self.assertEqual(response.status_code, 200, response.content)
        self.target_profile.refresh_from_db()
        self.assertEqual(self.target_profile.delegation_id, delegation.pk)
        self.assertEqual(self.target_profile.position_id, position.pk)
        self.assertEqual(list(self.target_profile.roles.values_list('id', flat=True)), [role.pk])

    def test_plain_text_fields_reject_stored_html(self):
        payload = '<img src=x onerror=alert(1)>'
        for path, data in (
            ('/api/users/create/', {**self.payload(), 'full_name': payload}),
            (f'/api/users/{self.target_profile.pk}/update/', {'full_name': payload}),
            ('/api/roles/create/', {'name': payload}),
            ('/api/positions/', {'name': payload}),
            ('/api/roles/permissions/add-custom/', {'module_id': 'audit', 'code': 'audit.read', 'name': payload}),
            ('/api/delegations/', {'name': 'Delegacion Audit', 'scope': 'Zona', 'photo_url': 'javascript:alert(1)'}),
            ('/api/delegations/', {'name': 'Delegacion Audit', 'scope': 'Zona', 'photo_url': 'data:image/svg+xml,<svg onload=alert(1)>'}),
        ):
            with self.subTest(path=path):
                self.assertEqual(self.post(path, data).status_code, 400)
