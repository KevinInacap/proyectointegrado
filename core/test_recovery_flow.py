import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from organization.models import UserProfile


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordRecoveryFlowTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username='persona', email='persona@example.com', password='ClaveAnterior123!',
        )
        UserProfile.objects.create(
            user=user, rut='12.345.678-5', full_name='Persona Prueba',
            email='persona@example.com', status='Activo',
        )

    def test_code_is_mailed_used_once_and_new_password_works(self):
        requested = self.client.post('/recuperar-clave/', {
            'action': 'request_code', 'identifier': 'persona@example.com',
        })
        self.assertEqual(requested.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn('10 minutos', message.body)
        self.assertEqual(len(message.alternatives), 1)
        html_body = message.alternatives[0][0]
        self.assertNotIn('cid:', html_body)
        self.assertIn('Vuelve a la página de recuperación', html_body)
        self.assertIn('Persona Prueba', html_body)
        self.assertIn('doble clic', html_body)
        self.assertFalse(message.attachments)
        code = re.search(r'\b\d{6}\b', message.body).group()
        self.assertRegex(html_body, r'letter-spacing:8px[^>]*>\d{6}</span>')

        verified = self.client.post('/recuperar-clave/', {
            'action': 'verify_code', 'code': code,
        })
        self.assertEqual(verified.status_code, 200)
        self.assertContains(verified, 'Nueva contraseña')

        changed = self.client.post('/recuperar-clave/', {
            'action': 'reset_password', 'new_password': 'NuevaClaveSegura123!',
            'confirm_password': 'NuevaClaveSegura123!',
        })
        self.assertEqual(changed.status_code, 200)
        self.assertFalse(self.client.login(username='persona', password='ClaveAnterior123!'))
        self.assertTrue(self.client.login(username='persona', password='NuevaClaveSegura123!'))

        reused = self.client.post('/recuperar-clave/', {'action': 'verify_code', 'code': code})
        self.assertEqual(reused.status_code, 400)

    def test_recovery_accepts_rut_without_formatting(self):
        requested = self.client.post('/recuperar-clave/', {
            'action': 'request_code', 'identifier': '123456785',
        })

        self.assertEqual(requested.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('persona@example.com', mail.outbox[0].to)
