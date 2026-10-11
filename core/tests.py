"""Pruebas unitarias de acceso sin base de datos real."""
from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase
from django.utils import timezone

from . import views


def fake_render(_request, _template, context=None, status=200):
    return SimpleNamespace(context_data=context or {}, status_code=status)


class AuthenticationTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def request(self, path='/', data=None, session=None):
        request = self.factory.post(path, data) if data is not None else self.factory.get(path)
        request.session = session if session is not None else {}
        return request

    @patch.object(views, 'render', side_effect=fake_render)
    def test_demo_get_cannot_create_role(self, _render):
        session = {'user_role': 'Administrador General', 'user_name': 'Demo'}
        response = views.login_view(self.request('/?rol=admin', session=session))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('user_role', session)
        self.assertNotIn('user_name', session)

    @patch.object(views, 'render', side_effect=fake_render)
    @patch.object(views, 'authenticate', return_value=None)
    @patch.object(views, '_find_profile_for_login', return_value=None)
    @patch.object(views.messages, 'error')
    def test_invalid_login_is_generic(self, _messages, _profile, _auth, _render):
        response = views.login_view(self.request(data={'username': 'nadie', 'password': 'secreto'}))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(_messages.call_args.args[1], 'Usuario o contraseña incorrectos.')

    @patch.object(views, 'render', side_effect=fake_render)
    @patch.object(views, 'authenticate')
    @patch.object(views.messages, 'error')
    def test_inactive_profile_cannot_login(self, _messages, auth, _render):
        auth.return_value = SimpleNamespace(is_active=True, profile=SimpleNamespace(status='Bloqueado'))
        response = views.login_view(self.request(data={'username': 'usuario', 'password': 'clave'}))
        self.assertEqual(response.status_code, 401)

    @patch.object(views, 'render', side_effect=fake_render)
    @patch.object(views.UserProfile.objects, 'select_related')
    @patch.object(views.PasswordRecoveryCode.objects, 'filter')
    @patch.object(views, '_send_password_recovery_email')
    def test_unknown_recovery_is_generic(self, send, codes, profiles, _render):
        profiles.return_value.filter.return_value.first.return_value = None
        response = views.password_recovery_view(self.request(data={'action': 'request_code', 'identifier': 'nadie@example.com'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['step'], 'verify')
        self.assertIn('Si existe', response.context_data['notice'])
        send.assert_not_called()
        codes.assert_not_called()

    @patch.object(views, 'render', side_effect=fake_render)
    @patch.object(views.UserProfile.objects, 'select_related')
    @patch.object(views, '_send_password_recovery_email')
    def test_session_limit_skips_lookup_and_preserves_current_code(self, send, profiles, _render):
        session = {'recovery_last_request_at': timezone.now().timestamp(), 'recovery_user_id': 3,
                   'recovery_verified_code_id': 7}
        response = views.password_recovery_view(self.request(data={'action': 'request_code', 'identifier': 'a@example.com'}, session=session))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(session['recovery_user_id'], 3)
        self.assertEqual(session['recovery_verified_code_id'], 7)
        profiles.assert_not_called()
        send.assert_not_called()

    @patch.object(views, 'render', side_effect=fake_render)
    @patch.object(views.transaction, 'atomic', return_value=nullcontext())
    @patch.object(views.UserProfile.objects, 'select_related')
    @patch.object(views.PasswordRecoveryCode.objects, 'filter')
    @patch.object(views, '_send_password_recovery_email')
    def test_account_limit_blocks_new_session_resend(self, send, codes, profiles, _atomic, _render):
        profile = SimpleNamespace(user=get_user_model()(pk=3, is_active=True), user_id=3,
                                  email='a@example.com', full_name='Ana', status='Activo')
        profiles.return_value.filter.return_value.first.return_value = profile
        codes.return_value.order_by.return_value.first.return_value = SimpleNamespace(created_at=timezone.now())
        with patch.object(get_user_model().objects, 'select_for_update'):
            response = views.password_recovery_view(self.request(data={'action': 'request_code', 'identifier': 'a@example.com'}))
        self.assertEqual(response.status_code, 200)
        send.assert_not_called()
        codes.return_value.update.assert_not_called()

    @patch.object(views, 'render', side_effect=fake_render)
    @patch.object(views.transaction, 'atomic', return_value=nullcontext())
    @patch.object(views.UserProfile.objects, 'select_related')
    @patch.object(views.PasswordRecoveryCode.objects, 'filter')
    @patch.object(views.PasswordRecoveryCode.objects, 'create')
    @patch.object(views, '_send_password_recovery_email', side_effect=RuntimeError('offline'))
    def test_smtp_failure_keeps_uniform_response_and_old_code(self, send, create, codes, profiles, _atomic, _render):
        profile = SimpleNamespace(user=get_user_model()(pk=3, is_active=True), user_id=3,
                                  email='a@example.com', full_name='Ana', status='Activo')
        profiles.return_value.filter.return_value.first.return_value = profile
        codes.return_value.order_by.return_value.first.return_value = None
        with patch.object(get_user_model().objects, 'select_for_update'):
            response = views.password_recovery_view(self.request(data={'action': 'request_code', 'identifier': 'a@example.com'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['step'], 'verify')
        self.assertIn('Si existe', response.context_data['notice'])
        codes.return_value.update.assert_not_called()
        create.assert_not_called()

    @patch.object(views, 'render', side_effect=fake_render)
    @patch.object(views.transaction, 'atomic', return_value=nullcontext())
    @patch.object(views.UserProfile.objects, 'select_related')
    @patch.object(views.PasswordRecoveryCode.objects, 'filter')
    @patch.object(views.PasswordRecoveryCode.objects, 'create')
    @patch.object(views, '_send_password_recovery_email')
    def test_resend_invalidates_old_code_and_verification(self, send, create, codes, profiles, _atomic, _render):
        profile = SimpleNamespace(user=get_user_model()(pk=3, is_active=True), user_id=3, email='a@example.com', full_name='Ana', status='Activo')
        profiles.return_value.filter.return_value.first.return_value = profile
        codes.return_value.order_by.return_value.first.return_value = None
        send.return_value = 1
        session = {'recovery_verified_code_id': 7, 'recovery_user_id': 3}
        with patch.object(get_user_model().objects, 'select_for_update'):
            response = views.password_recovery_view(self.request(data={'action': 'request_code', 'identifier': 'a@example.com'}, session=session))
        self.assertEqual(response.context_data['step'], 'verify')
        self.assertNotIn('recovery_verified_code_id', session)
        self.assertTrue(any(call[0] == 'update' for call in codes.return_value.mock_calls))
        create.assert_called_once()
        send.assert_called_once()

    @patch.object(views, 'render', side_effect=fake_render)
    def test_password_form_requires_verified_code(self, _render):
        response = views.password_recovery_view(self.request(data={'action': 'reset_password', 'new_password': 'NuevaClave123!'}, session={'recovery_user_id': 1}))
        self.assertEqual(response.status_code, 400)
        self.assertNotEqual(response.context_data['step'], 'new_password')

    @patch.object(views, 'render', side_effect=fake_render)
    @patch.object(views.PasswordRecoveryCode.objects, 'filter')
    def test_get_password_form_requires_still_valid_code(self, codes, _render):
        session = {'recovery_user_id': 3, 'recovery_verified_code_id': 7, 'recovery_pending': True}
        codes.return_value.first.return_value = SimpleNamespace(is_valid=False)
        response = views.password_recovery_view(self.request(session=session))
        self.assertEqual(response.context_data['step'], 'verify')
        self.assertNotIn('recovery_verified_code_id', session)
        session['recovery_verified_code_id'] = 8
        codes.return_value.first.return_value = SimpleNamespace(is_valid=True)
        response = views.password_recovery_view(self.request(session=session))
        self.assertEqual(response.context_data['step'], 'new_password')

    @patch.object(views, 'render', side_effect=fake_render)
    def test_unknown_code_has_same_error_as_wrong_code(self, _render):
        session = {'recovery_pending': True}
        response = views.password_recovery_view(self.request(data={'action': 'verify_code', 'code': '000000'}, session=session))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.context_data['step'], 'verify')
        self.assertEqual(response.context_data['error'], 'El código no es válido o expiró. Solicita uno nuevo si es necesario.')

    def test_code_expiration_reuse_and_attempt_limit(self):
        code = views.PasswordRecoveryCode(code_hash='hash', expires_at=timezone.now() + timedelta(minutes=1))
        self.assertTrue(code.is_valid)
        code.used_at = timezone.now()
        self.assertFalse(code.is_valid)
        code.used_at = None
        code.expires_at = timezone.now() - timedelta(seconds=1)
        self.assertFalse(code.is_valid)
        code.expires_at = timezone.now() + timedelta(minutes=1)
        code.attempts = 5
        self.assertFalse(code.is_valid)

    @patch.object(views, 'render', side_effect=fake_render)
    @patch.object(views.transaction, 'atomic', return_value=nullcontext())
    @patch.object(views.PasswordRecoveryCode.objects, 'select_for_update')
    @patch.object(views, 'check_password', return_value=True)
    def test_valid_code_unlocks_password_form(self, _check, locked, _atomic, _render):
        locked.return_value.filter.return_value.first.return_value = SimpleNamespace(pk=7, is_valid=True, code_hash='hash')
        session = {'recovery_user_id': 3, 'recovery_pending': True}
        response = views.password_recovery_view(self.request(data={'action': 'verify_code', 'code': '123456'}, session=session))
        self.assertEqual(response.context_data['step'], 'new_password')
        self.assertEqual(session['recovery_verified_code_id'], 7)

    @patch.object(views, 'render', side_effect=fake_render)
    @patch.object(views.transaction, 'atomic', return_value=nullcontext())
    @patch.object(views.PasswordRecoveryCode.objects, 'select_for_update')
    @patch.object(views, 'check_password', return_value=False)
    def test_wrong_code_counts_attempt(self, _check, locked, _atomic, _render):
        code = SimpleNamespace(is_valid=True, code_hash='hash', attempts=4, save=MagicMock())
        locked.return_value.filter.return_value.first.return_value = code
        response = views.password_recovery_view(self.request(data={'action': 'verify_code', 'code': '000000'}, session={'recovery_user_id': 3}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(code.attempts, 5)
        code.save.assert_called_once()

    @patch.object(views, 'render', side_effect=fake_render)
    @patch.object(views.transaction, 'atomic', return_value=nullcontext())
    @patch.object(views.PasswordRecoveryCode.objects, 'select_for_update')
    @patch.object(views, 'validate_password', side_effect=views.ValidationError('Clave débil'))
    def test_weak_password_keeps_code_unused(self, _validate, locked, _atomic, _render):
        user = MagicMock()
        locked.return_value.filter.return_value.first.return_value = SimpleNamespace(is_valid=True, user=user)
        session = {'recovery_user_id': 3, 'recovery_verified_code_id': 7}
        response = views.password_recovery_view(self.request(data={'action': 'reset_password', 'new_password': '12345678', 'confirm_password': '12345678'}, session=session))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.context_data['step'], 'new_password')
        user.set_password.assert_not_called()

    @patch.object(views, 'render', side_effect=fake_render)
    @patch.object(views.transaction, 'atomic', return_value=nullcontext())
    @patch.object(views.PasswordRecoveryCode.objects, 'select_for_update')
    @patch.object(views.PasswordRecoveryCode.objects, 'filter')
    @patch.object(views, 'validate_password')
    def test_successful_reset_consumes_code_and_session(self, validate, codes, locked, _atomic, _render):
        user = MagicMock()
        locked.return_value.filter.return_value.first.return_value = SimpleNamespace(is_valid=True, user=user)
        session = {'recovery_user_id': 3, 'recovery_verified_code_id': 7, 'recovery_pending': True}
        response = views.password_recovery_view(self.request(data={'action': 'reset_password', 'new_password': 'ClaveSegura123!', 'confirm_password': 'ClaveSegura123!'}, session=session))
        self.assertEqual(response.status_code, 200)
        self.assertIn('success', response.context_data)
        validate.assert_called_once()
        user.set_password.assert_called_once_with('ClaveSegura123!')
        codes.return_value.update.assert_called_once()
        self.assertNotIn('recovery_verified_code_id', session)
        self.assertNotIn('recovery_user_id', session)
