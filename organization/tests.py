import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from . import views


class AdminApiIsolatedTests(SimpleTestCase):
    """Pruebas de vistas sin crear ni consultar una base de datos."""

    def setUp(self):
        self.factory = RequestFactory()

    def request(self, method='get', payload=None):
        if method == 'get':
            request = self.factory.get('/organization/roles/')
        else:
            request = getattr(self.factory, method)(
                '/organization/roles/',
                data=json.dumps(payload or {}),
                content_type='application/json',
            )
        request.session = {'user_role': 'Administrador General'}
        return request

    def test_session_role_does_not_authenticate(self):
        request = self.request()
        request.user = SimpleNamespace(is_authenticated=False, is_active=True, is_superuser=False)
        self.assertEqual(views.api_roles_list(request).status_code, 403)

    def test_inactive_account_is_denied(self):
        request = self.request()
        request.user = SimpleNamespace(is_authenticated=True, is_active=False, is_superuser=True)
        self.assertEqual(views.api_roles_list(request).status_code, 403)

    @patch.object(views.UserProfile.objects, 'filter')
    def test_active_account_without_database_role_is_denied(self, profiles):
        profiles.return_value.exists.return_value = False
        request = self.request()
        request.user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=False)
        self.assertEqual(views.api_roles_list(request).status_code, 403)
        self.assertEqual(profiles.call_args.kwargs['status'], 'Activo')

    def test_json_array_is_not_accepted_as_object(self):
        request = self.factory.post('/organization/roles/', data='[]', content_type='application/json')
        self.assertEqual(views._get_request_data(request), {})

    def test_rut_validation_requires_actual_format(self):
        self.assertTrue(views._is_valid_chilean_rut('12.345.678-5'))
        self.assertFalse(views._is_valid_chilean_rut('abc12345678-5'))

    def test_invalid_permission_shape(self):
        self.assertIsNone(views._validated_permissions('usuarios.view'))
        self.assertIsNone(views._validated_permissions([123]))

    def test_unsafe_delegation_url(self):
        self.assertIsNotNone(views._validate_delegation_details({
            'photo_url': '/static/../secret.png',
        }))

    def test_invalid_role_payload_rejected_before_database_write(self):
        request = self.request('post', {'name': 'Prueba', 'permissions': 'usuarios.view'})
        request.user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=True)
        response = views.api_role_create(request)
        self.assertEqual(response.status_code, 400)

    def test_invalid_user_status_rejected_before_database_write(self):
        request = self.request('post', {
            'username': 'prueba', 'full_name': 'Prueba Usuario',
            'email': 'prueba@example.com', 'rut': '12345678-5',
            'password': 'clave-segura', 'status': 'Desconocido',
        })
        request.user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=True)
        self.assertEqual(views.api_user_create(request).status_code, 400)
