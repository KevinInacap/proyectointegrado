"""Regresiones de auditoría: ejecutar únicamente con la BD aislada indicada."""
import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from core.models import PasswordRecoveryCode
from organization.models import Role, UserProfile


WEAK_PASSWORDS = ('Ab1!xyz', 'abcdefgh9!', 'ABCDEFGH9!', 'Abcdefghi!', 'Abcdefghi9', 'Abcdefghi9 ')
STRONG_PASSWORD = 'VientoNorte49!'


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class Audit2AuthTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('audit_person', password='Anterior49!')
        self.profile = UserProfile.objects.create(
            user=self.user, rut='12.345.678-5', full_name='Persona Auditoria',
            email='audit@example.test', status='Activo',
        )
        self.role = Role.objects.get(name='Administrador')
        self.profile.roles.add(self.role)

    def request_code(self, client=None):
        client = client or self.client
        response = client.post('/recuperar-clave/', {'identifier': self.profile.email})
        self.assertEqual(response.status_code, 200)
        return re.search(r'\b\d{6}\b', mail.outbox[-1].body).group()

    def verify(self, code, client=None):
        return (client or self.client).post('/recuperar-clave/', {'action': 'verify_code', 'code': code})

    def reset(self, password):
        return self.client.post('/recuperar-clave/', {
            'action': 'reset_password', 'new_password': password, 'confirm_password': password,
        })

    def test_policy_requires_each_component(self):
        for password in WEAK_PASSWORDS:
            with self.subTest(password=password), self.assertRaises(ValidationError):
                validate_password(password)
        validate_password('Az7!qwer')

    def test_recovery_checks_policy_and_consumes_code(self):
        code = self.request_code()
        record = PasswordRecoveryCode.objects.get(user=self.user)
        self.assertTrue(check_password(code, record.code_hash))
        self.assertNotEqual(code, record.code_hash)
        self.assertAlmostEqual((record.expires_at - record.created_at).total_seconds(), 600, delta=3)
        self.assertEqual(self.verify(code).status_code, 200)
        for password in WEAK_PASSWORDS:
            with self.subTest(password=password):
                self.assertEqual(self.reset(password).status_code, 400)
                record.refresh_from_db()
                self.assertIsNone(record.used_at)
        self.assertEqual(self.reset(STRONG_PASSWORD).status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(STRONG_PASSWORD))
        self.assertEqual(self.verify(code).status_code, 400)

    def test_expired_code_and_attempt_budget(self):
        code = self.request_code()
        wrong = '000000' if code != '000000' else '999999'
        for _ in range(5):
            self.assertEqual(self.verify(wrong).status_code, 400)
        self.assertEqual(self.verify(code).status_code, 400)
        record = PasswordRecoveryCode.objects.get(user=self.user)
        self.assertEqual(record.attempts, 5)
        record.attempts = 0
        record.expires_at = timezone.now() - timedelta(seconds=1)
        record.save()
        session = self.client.session
        session['recovery_user_id'] = self.user.pk
        session.save()
        self.assertEqual(self.verify(code).status_code, 400)

    def test_resend_wait_is_per_account_and_replaces_old_code(self):
        code = self.request_code()
        self.request_code(Client())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(PasswordRecoveryCode.objects.filter(user=self.user).count(), 1)
        record = PasswordRecoveryCode.objects.get(user=self.user)
        PasswordRecoveryCode.objects.filter(pk=record.pk).update(created_at=timezone.now() - timedelta(seconds=46))
        other = Client()
        self.request_code(other)
        self.assertEqual(len(mail.outbox), 2)
        record.refresh_from_db()
        self.assertIsNotNone(record.used_at)
        # A verified session must not accept a replaced record.
        session = self.client.session
        session['recovery_verified_code_id'] = record.pk
        session.save()
        self.assertEqual(self.reset(STRONG_PASSWORD).status_code, 400)

    def test_deleted_profile_cannot_login_or_recover(self):
        self.profile.deleted_at = timezone.now()
        self.profile.save()
        self.assertEqual(self.client.post('/', {'username': self.user.username, 'password': 'Anterior49!'}).status_code, 401)
        self.client.post('/recuperar-clave/', {'identifier': self.profile.email})
        self.assertEqual(len(mail.outbox), 0)

    def test_revocation_between_verification_and_reset(self):
        self.assertEqual(self.verify(self.request_code()).status_code, 200)
        self.profile.status = 'Bloqueado'
        self.profile.save()
        self.assertEqual(self.reset(STRONG_PASSWORD).status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Anterior49!'))

    def test_live_roles_override_stale_session_and_soft_deleted_role(self):
        self.client.force_login(self.user)
        session = self.client.session
        session['user_role'] = 'Administrador General'
        session.save()
        self.assertEqual(self.client.get('/api/users/').status_code, 200)
        self.profile.roles.clear()
        self.assertEqual(self.client.get('/api/users/').status_code, 403)
        self.profile.roles.add(self.role)
        self.role.deleted_at = timezone.now()
        self.role.save()
        self.assertEqual(self.client.get('/api/users/').status_code, 403)

    def test_login_does_not_claim_success_before_authentication(self):
        response = self.client.post('/', {'username': 'audit_missing', 'password': 'not-a-password'})
        self.assertContains(response, 'Usuario o contraseña incorrectos.', status_code=401)
        self.assertNotContains(response, 'Autenticación exitosa', status_code=401)
        self.assertNotContains(response, 'Redirigiendo al panel', status_code=401)

    def test_mail_failure_has_same_public_response_as_unknown_account(self):
        with patch('core.views._send_password_recovery_email', side_effect=RuntimeError('offline')):
            failed = self.client.post('/recuperar-clave/', {'identifier': self.profile.email})
        unknown = Client().post('/recuperar-clave/', {'identifier': 'unknown@example.test'})
        self.assertEqual(failed.status_code, unknown.status_code)
        self.assertEqual(failed.context['notice'], unknown.context['notice'])
        self.assertFalse(PasswordRecoveryCode.objects.filter(user=self.user).exists())
