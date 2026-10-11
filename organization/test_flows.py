import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Delegation, Role, UserProfile


class AdminPersistenceFlowTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username='test_admin', password='ClaveSegura123!', is_superuser=True,
        )
        self.client.force_login(self.admin)

    def post_json(self, path, data):
        return self.client.post(path, data=json.dumps(data), content_type='application/json')

    def test_role_delegation_and_user_are_persisted(self):
        role_response = self.post_json('/api/roles/create/', {
            'name': 'Operador de prueba', 'description': 'Cuenta temporal', 'permissions': [],
        })
        self.assertEqual(role_response.status_code, 200, role_response.content)
        role = Role.objects.get(name='Operador de prueba')

        delegation_response = self.post_json('/organization/delegations/', {
            'name': 'Delegación de prueba', 'scope': 'Sector de prueba',
        })
        self.assertEqual(delegation_response.status_code, 200, delegation_response.content)
        delegation = Delegation.objects.get(name='Delegación de prueba')

        user_response = self.post_json('/api/users/create/', {
            'username': 'persona_prueba', 'full_name': 'Persona Prueba',
            'email': 'persona@example.com', 'rut': '12.345.678-5',
            'password': 'ClaveSegura123!', 'delegation_id': delegation.id,
            'role_ids': [role.id], 'status': 'Activo',
        })
        self.assertEqual(user_response.status_code, 200, user_response.content)
        profile = UserProfile.objects.get(user__username='persona_prueba')
        self.assertTrue(profile.user.check_password('ClaveSegura123!'))
        self.assertEqual(profile.delegation_id, delegation.id)
        self.assertEqual(list(profile.roles.values_list('id', flat=True)), [role.id])

        self.assertEqual(self.client.get('/api/users/').status_code, 200)
