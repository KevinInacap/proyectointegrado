import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organization.models import Delegation, Role, UserProfile
from .models import Activity, ServiceCatalog, Vecino


class AttentionApiSecurityTests(TestCase):
    def setUp(self):
        self.north = Delegation.objects.create(name='Norte', scope='Norte', status='Activo')
        self.south = Delegation.objects.create(name='Sur', scope='Sur', status='Activo')
        self.role = Role.objects.create(name='Gestor de prueba', permissions_data=['lectura', 'edicion'])
        self.user = get_user_model().objects.create_user(username='gestor-prueba', password='test-pass')
        self.profile = UserProfile.objects.create(
            user=self.user, rut='12345678-5', full_name='Gestor Prueba',
            email='gestor-prueba@example.com', delegation=self.north, status='Activo',
        )
        self.profile.roles.add(self.role)
        self.client.force_login(self.user)
        self.url = reverse('activities:api_atenciones')
        self.catalog = ServiceCatalog.objects.create(
            area='Social', service='Orientación', attention_type='Social',
            subattention_type='RSH', status='Activo',
        )
        self.payload = {
            'contact_name': 'Solicitante Real', 'contact_phone': '123456',
            'title': 'Problema', 'description': 'Acción',
            'delegation': self.north.name, 'catalog_id': self.catalog.pk,
            'attention_type': 'Social', 'subattention_type': 'RSH',
            'status': 'Approved',
        }

    def post(self, data=None):
        return self.client.post(self.url, json.dumps(data or self.payload), content_type='application/json')

    def test_session_role_alone_grants_nothing(self):
        self.client.logout()
        session = self.client.session
        session['user_role'] = 'Administrador General'
        session.save()
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.post().status_code, 403)

    def test_other_delegation_is_rejected_and_not_listed(self):
        response = self.post(dict(self.payload, delegation=self.south.name))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Activity.objects.exists())
        other = Activity.objects.create(
            activity_code='OTHER-1', activity_date='2026-01-01',
            problem_description='Secreto', executed_action='Acción',
            delegation=self.south,
        )
        self.assertEqual(self.client.get(self.url).json()['atenciones'], [])
        self.assertEqual(
            self.client.get(reverse('activities:api_atencion_detail', args=[other.pk])).status_code, 404
        )

    def test_catalog_pair_and_requester_are_validated(self):
        self.assertEqual(self.post(dict(self.payload, subattention_type='Otro')).status_code, 400)
        self.assertEqual(self.post(dict(self.payload, contact_name='')).status_code, 400)
        self.assertFalse(Activity.objects.exists())

    def test_status_is_server_controlled_and_duplicate_retry_is_idempotent(self):
        first = self.post()
        self.assertEqual(first.status_code, 201)
        second = self.post()
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()['id'], second.json()['id'])
        self.assertEqual(Activity.objects.count(), 1)
        activity = Activity.objects.get()
        self.assertEqual(activity.validation_status, 'Pending')
        self.assertEqual(activity.user_id, self.user.pk)
        self.assertEqual(activity.catalog_id, self.catalog.pk)

    def test_invalid_json_and_method(self):
        self.assertEqual(self.client.post(self.url, '{', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.delete(self.url).status_code, 405)

    def test_vecinos_scoped_to_territory(self):
        Vecino.objects.create(nombre='Norte', rut='12345678-5', territorio='Norte')
        Vecino.objects.create(nombre='Sur', rut='23456789-6', territorio='Sur')
        response = self.client.get(reverse('activities:api_vecinos'))
        self.assertEqual([v['nombre'] for v in response.json()['vecinos']], ['Norte'])

    def test_permission_revocation_takes_effect(self):
        self.role.permissions_data = []
        self.role.save()
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.post().status_code, 403)


class DashboardAccessTests(TestCase):
    def setUp(self):
        self.delegation = Delegation.objects.create(name='Centro de prueba', scope='Centro')
        self.user = get_user_model().objects.create_user(username='rol-prueba', password='test-pass')
        self.profile = UserProfile.objects.create(
            user=self.user, rut='87654321-K', full_name='Usuario Rol',
            email='rol-prueba@example.com', delegation=self.delegation,
        )
        self.client.force_login(self.user)

    def test_session_role_does_not_grant_admin_dashboard(self):
        session = self.client.session
        session['user_role'] = 'Administrador General'
        session.save()
        self.assertNotEqual(self.client.get(reverse('activities:dashboard_admin')).status_code, 200)

    def test_readonly_role_landing_is_distinct_and_restricted(self):
        for role_name, route in (
            ('Coordinador del Sistema', 'dashboard_coordinador'),
            ('Delegado Municipal', 'dashboard_delegado'),
            ('Usuario de Consulta', 'dashboard_consulta'),
        ):
            self.profile.roles.clear()
            self.profile.roles.add(Role.objects.create(name=role_name))
            response = self.client.get(reverse('activities:' + route))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Atenciones visibles')
            for other in {'dashboard_coordinador', 'dashboard_delegado', 'dashboard_consulta'} - {route}:
                self.assertNotEqual(self.client.get(reverse('activities:' + other)).status_code, 200)

    def test_admin_dashboard_get_does_not_seed_activities(self):
        self.profile.roles.add(Role.objects.create(name='Administrador General'))
        before = Activity.objects.count()
        self.client.get(reverse('activities:dashboard_admin'))
        self.assertEqual(Activity.objects.count(), before)
