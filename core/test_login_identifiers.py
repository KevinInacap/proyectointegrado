from django.contrib.auth import get_user_model
from django.test import TestCase

from organization.models import Position, Role, UserProfile


class EmailAndRutLoginTests(TestCase):
    def setUp(self):
        self.role, _ = Role.objects.get_or_create(name='Administrador')
        user = get_user_model().objects.create_user(
            username='login-prueba', password='ClavePruebaSegura2026!'
        )
        profile = UserProfile.objects.create(
            user=user,
            rut='215714047',
            full_name='Cuenta de Prueba',
            email='Persona.Prueba@example.com',
            status='Activo',
            position=Position.objects.get_or_create(name='Administrador General')[0],
        )
        profile.roles.add(self.role)

    def test_login_accepts_registered_email_case_insensitively(self):
        response = self.client.post('/', {
            'username': 'persona.prueba@EXAMPLE.com',
            'password': 'ClavePruebaSegura2026!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/activities/dashboard/admin/'))

    def test_login_accepts_registered_rut(self):
        response = self.client.post('/', {
            'username': '21.571.404-7',
            'password': 'ClavePruebaSegura2026!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/activities/dashboard/admin/'))

    def test_unknown_email_is_rejected(self):
        response = self.client.post('/', {
            'username': 'otra@example.com',
            'password': 'ClavePruebaSegura2026!',
        })
        self.assertEqual(response.status_code, 401)

    def test_login_accepts_exact_username(self):
        response = self.client.post('/', {
            'username': 'LOGIN-PRUEBA', 'password': 'ClavePruebaSegura2026!',
        })
        self.assertRedirects(response, '/activities/dashboard/admin/', fetch_redirect_response=False)

    def test_text_containing_a_rut_is_not_a_rut_identity(self):
        response = self.client.post('/', {
            'username': 'intruso215714047', 'password': 'ClavePruebaSegura2026!',
        })
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('_auth_user_id', self.client.session)
