"""Regresiones del recorrido de recuperación con correo y base de prueba."""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import PasswordRecoveryCode
from organization.models import UserProfile


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
)
class PasswordRecoveryFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='recuperacion-prueba', email='vecino@example.test', password='ClaveAnterior!42',
        )
        UserProfile.objects.create(
            user=self.user, rut='12.345.678-5', full_name='Persona de Prueba',
            email='vecino@example.test', status='Activo',
        )
        self.url = reverse('core:password_recovery')

    def request_code(self, client=None):
        with patch('core.views.secrets.randbelow', return_value=123456):
            return (client or self.client).post(self.url, {
                'action': 'request_code', 'identifier': 'vecino@example.test',
            })

    def test_complete_recovery_sends_one_code_and_prevents_reuse(self):
        response = self.request_code()
        self.assertContains(response, 'Paso 2 de 3')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['vecino@example.test'])
        self.assertIn('123456', mail.outbox[0].body)
        recovery = PasswordRecoveryCode.objects.get(user=self.user)
        self.assertNotEqual(recovery.code_hash, '123456')

        response = self.client.post(self.url, {'action': 'verify_code', 'code': '123456'})
        self.assertContains(response, 'Paso 3 de 3')
        response = self.client.post(self.url, {
            'action': 'reset_password', 'new_password': 'NuevaClave!829',
            'confirm_password': 'NuevaClave!829',
        })
        self.assertContains(response, 'Contraseña actualizada')
        self.user.refresh_from_db()
        recovery.refresh_from_db()
        self.assertTrue(self.user.check_password('NuevaClave!829'))
        self.assertIsNotNone(recovery.used_at)
        self.assertEqual(self.client.post(self.url, {'action': 'verify_code', 'code': '123456'}).status_code, 400)

    def test_expired_code_does_not_change_password(self):
        self.request_code()
        PasswordRecoveryCode.objects.filter(user=self.user).update(expires_at=timezone.now() - timedelta(seconds=1))
        response = self.client.post(self.url, {'action': 'verify_code', 'code': '123456'})
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('ClaveAnterior!42'))

    def test_five_incorrect_attempts_lock_code(self):
        self.request_code()
        for _ in range(5):
            self.assertEqual(self.client.post(self.url, {'action': 'verify_code', 'code': '000000'}).status_code, 400)
        recovery = PasswordRecoveryCode.objects.get(user=self.user)
        self.assertEqual(recovery.attempts, 5)
        self.assertEqual(self.client.post(self.url, {'action': 'verify_code', 'code': '123456'}).status_code, 400)

    def test_unknown_account_receives_same_public_response(self):
        known = self.request_code()
        unknown = Client().post(self.url, {'action': 'request_code', 'identifier': 'ausente@example.test'})
        self.assertEqual(known.status_code, unknown.status_code)
        notice = 'Si existe una cuenta activa con esos datos, enviamos un código al correo registrado.'
        self.assertContains(known, notice)
        self.assertContains(unknown, notice)
        self.assertEqual(len(mail.outbox), 1)

    def test_code_requires_initiating_recovery_in_this_session(self):
        self.request_code()
        second_client = Client()
        self.assertEqual(second_client.post(self.url, {'action': 'verify_code', 'code': '123456'}).status_code, 400)
        response = second_client.get(self.url)
        self.assertContains(response, 'inicia la recuperación en este navegador')
        self.assertNotContains(response, '¿Ya tienes un código en tu correo?')
        response = self.request_code(second_client)
        self.assertContains(response, 'Paso 2 de 3')
        self.assertContains(second_client.post(self.url, {'action': 'verify_code', 'code': '123456'}), 'Paso 3 de 3')
