import datetime
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from organization.models import Delegation, Position, Role, UserProfile
from .models import Activity, Validation, Vecino


class DelegationBoundaryRegressionTests(TestCase):
    """Los permisos de operación nunca sustituyen el ámbito territorial vigente."""

    def setUp(self):
        self.north = Delegation.objects.create(name='Norte aislamiento', scope='Norte')
        self.south = Delegation.objects.create(name='Sur aislamiento', scope='Sur')
        self.user = get_user_model().objects.create_user(
            username='operador-aislamiento', password='Safe!Isolation2026',
        )
        self.position = Position.objects.create(name='Cargo operativo aislamiento')
        self.profile = UserProfile.objects.create(
            user=self.user, rut='18.111.111-1', full_name='Operador de aislamiento',
            email='operador-aislamiento@example.test', delegation=self.north,
            position=self.position,
        )
        self.role = Role.objects.create(
            name='Operación aislamiento', permissions_data=['lectura', 'edicion', 'cierre'],
        )
        self.profile.roles.add(self.role)
        self.client.force_login(self.user)
        self.own = Activity.objects.create(
            activity_code='ISOLATION-NORTH', activity_date='2026-01-02',
            contact_name='Solicitante local', problem_description='Consulta local',
            executed_action='Registro de la solicitud', delegation=self.north,
        )
        self.foreign = Activity.objects.create(
            activity_code='ISOLATION-SOUTH', activity_date='2026-01-02',
            contact_name='Solicitante ajeno', problem_description='Consulta ajena',
            executed_action='Registro de otra delegación', delegation=self.south,
        )
        self.activities_url = reverse('activities:api_atenciones')
        self.neighbors_url = reverse('activities:api_vecinos')
        self.neighbor_payload = {
            'nombre': 'Vecina nueva', 'rut': '12.345.678-5',
            'email': 'vecina-aislamiento@example.test', 'direccion': 'Calle de prueba 12',
            'territorio': self.south.name,
        }

    def neighbor_post(self):
        return self.client.post(
            self.neighbors_url, data=json.dumps(self.neighbor_payload),
            content_type='application/json',
        )

    def test_missing_inactive_or_deleted_delegation_cannot_create_neighbors(self):
        for state in ('missing', 'inactive', 'deleted'):
            with self.subTest(state=state):
                self.north.status = 'Inactivo' if state == 'inactive' else 'Activo'
                self.north.deleted_at = timezone.now() if state == 'deleted' else None
                self.north.save(update_fields=['status', 'deleted_at', 'updated_at'])
                self.profile.delegation = None if state == 'missing' else self.north
                self.profile.save(update_fields=['delegation', 'updated_at'])
                self.assertEqual(self.neighbor_post().status_code, 403)
                self.assertFalse(Vecino.objects.exists())

    def test_local_creation_uses_authenticated_delegation_despite_foreign_payload(self):
        response = self.neighbor_post()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Vecino.objects.get().territorio, self.north.name)

    def test_soft_deleted_delegation_hides_activity_and_prevents_changes(self):
        self.north.deleted_at = timezone.now()
        self.north.save(update_fields=['deleted_at', 'updated_at'])
        self.assertEqual(self.client.get(self.activities_url).json()['atenciones'], [])
        detail = reverse('activities:api_atencion_detail', args=[self.own.pk])
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.assertEqual(self.client.put(
            detail, data=json.dumps({'contact_name': 'Cambio no autorizado'}),
            content_type='application/json',
        ).status_code, 404)
        self.own.refresh_from_db()
        self.assertEqual(self.own.contact_name, 'Solicitante local')

    def test_foreign_attention_cannot_be_read_edited_or_deleted_through_either_route(self):
        for route in ('api_atencion_detail', 'api_atencion_detail_prefixed'):
            endpoint = reverse('activities:' + route, args=[self.foreign.pk])
            with self.subTest(route=route):
                self.assertEqual(self.client.get(endpoint).status_code, 404)
                self.assertEqual(self.client.put(
                    endpoint, data=json.dumps({'contact_name': 'Cambio ajeno'}),
                    content_type='application/json',
                ).status_code, 404)
                self.assertEqual(self.client.delete(endpoint).status_code, 404)
        self.foreign.refresh_from_db()
        self.assertEqual(self.foreign.contact_name, 'Solicitante ajeno')
        self.assertIsNone(self.foreign.deleted_at)

    def test_local_attention_cannot_be_moved_to_foreign_delegation(self):
        endpoint = reverse('activities:api_atencion_detail', args=[self.own.pk])
        response = self.client.put(
            endpoint, data=json.dumps({'delegation': self.south.pk}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.own.refresh_from_db()
        self.assertEqual(self.own.delegation_id, self.north.pk)

    def test_deactivated_profile_loses_direct_api_access(self):
        for state in ('Inactivo', 'Bloqueado'):
            with self.subTest(state=state):
                self.profile.status = state
                self.profile.save(update_fields=['status', 'updated_at'])
                self.assertEqual(self.client.get(self.activities_url).status_code, 403)
                self.assertEqual(self.neighbor_post().status_code, 403)

    def test_missing_inactive_or_deleted_position_loses_direct_api_access(self):
        for state in ('missing', 'inactive', 'deleted'):
            with self.subTest(state=state):
                self.position.status = 'Inactivo' if state == 'inactive' else 'Activo'
                self.position.deleted_at = timezone.now() if state == 'deleted' else None
                self.position.save(update_fields=['status', 'deleted_at', 'updated_at'])
                self.profile.position = None if state == 'missing' else self.position
                self.profile.save(update_fields=['position', 'updated_at'])
                self.assertEqual(self.client.get(self.activities_url).status_code, 403)
                self.assertEqual(self.neighbor_post().status_code, 403)
                self.assertEqual(self.client.get(self.neighbors_url).status_code, 403)

    def test_edit_rejects_future_activity_date_without_modifying_record(self):
        endpoint = reverse('activities:api_atencion_detail', args=[self.own.pk])
        tomorrow = timezone.localdate() + datetime.timedelta(days=1)
        response = self.client.put(
            endpoint, data=json.dumps({'activity_date': tomorrow.isoformat()}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.own.refresh_from_db()
        self.assertEqual(self.own.activity_date, datetime.date(2026, 1, 2))

    def test_verifier_history_respects_current_delegation_and_read_permission(self):
        self.profile.position = Position.objects.get(name='Verificador Técnico')
        self.profile.save(update_fields=['position', 'updated_at'])
        self.role.permissions_data = ['lectura', 'validar_evidencia']
        self.role.save(update_fields=['permissions_data', 'updated_at'])
        own_review = Validation.objects.create(
            activity=self.own, verifier=self.user, decision='Approved',
        )
        foreign_review = Validation.objects.create(
            activity=self.foreign, verifier=self.user, decision='Approved',
        )
        deleted_activity = Activity.objects.create(
            activity_code='ISOLATION-DELETED', activity_date='2026-01-02',
            problem_description='Registro dado de baja', executed_action='Registro',
            delegation=self.north, deleted_at=timezone.now(),
        )
        Validation.objects.create(
            activity=deleted_activity, verifier=self.user, decision='Approved',
        )
        endpoint = reverse('activities:dashboard_verificador')
        response = self.client.get(endpoint)
        self.assertEqual(
            [item.pk for item in response.context['dashboard_validations']], [own_review.pk],
        )
        self.assertEqual(response.context['dashboard_work_kpis'][1]['value'], 1)

        self.profile.delegation = self.south
        self.profile.save(update_fields=['delegation', 'updated_at'])
        response = self.client.get(endpoint)
        self.assertEqual(
            [item.pk for item in response.context['dashboard_validations']], [foreign_review.pk],
        )
        self.role.permissions_data = ['validar_evidencia']
        self.role.save(update_fields=['permissions_data', 'updated_at'])
        response = self.client.get(endpoint)
        self.assertEqual(list(response.context['dashboard_validations']), [])
        self.assertEqual(response.context['dashboard_work_kpis'], [])

    def test_neighbor_writes_reject_non_object_json_before_any_mutation(self):
        response = self.neighbor_post()
        self.assertEqual(response.status_code, 200, response.content)
        neighbor = Vecino.objects.get()
        detail = reverse('activities:api_vecino_detail', args=[neighbor.pk])
        for method, endpoint in (('post', self.neighbors_url), ('put', detail)):
            for value in ([], None, 'texto'):
                with self.subTest(method=method, value=value):
                    response = getattr(self.client, method)(
                        endpoint, data=json.dumps(value), content_type='application/json',
                    )
                    self.assertEqual(response.status_code, 400)
                    neighbor.refresh_from_db()
                    self.assertEqual(neighbor.nombre, 'Vecina nueva')
                    self.assertEqual(neighbor.territorio, self.north.name)
                    self.assertEqual(Vecino.objects.count(), 1)

    def test_collective_agenda_can_be_enabled_and_disabled_when_editing(self):
        endpoint = reverse('activities:api_atencion_detail', args=[self.own.pk])
        for enabled, expected_stage in ((True, 2), (False, 1)):
            with self.subTest(enabled=enabled):
                response = self.client.put(
                    endpoint, data=json.dumps({'is_collective_agenda': enabled}),
                    content_type='application/json',
                )
                self.assertEqual(response.status_code, 200, response.content)
                self.own.refresh_from_db()
                self.assertIs(self.own.is_collective_agenda, enabled)
                self.assertEqual(self.client.get(endpoint).json()['atencion']['stage'], expected_stage)

    def test_collective_agenda_rejects_non_boolean_values_without_partial_changes(self):
        endpoint = reverse('activities:api_atencion_detail', args=[self.own.pk])
        for value in ('false', 'true', 0, 1, None, [], {}, ''):
            with self.subTest(value=value):
                response = self.client.put(
                    endpoint, data=json.dumps({
                        'is_collective_agenda': value, 'contact_name': 'Cambio que no debe guardarse',
                    }), content_type='application/json',
                )
                self.assertEqual(response.status_code, 400)
                self.own.refresh_from_db()
                self.assertFalse(self.own.is_collective_agenda)
                self.assertEqual(self.own.contact_name, 'Solicitante local')

    def test_enabling_collective_agenda_requires_contact_for_legacy_attention(self):
        self.own.contact_name = ''
        self.own.save(update_fields=['contact_name', 'updated_at'])
        endpoint = reverse('activities:api_atencion_detail', args=[self.own.pk])
        response = self.client.put(
            endpoint, data=json.dumps({'is_collective_agenda': True}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.own.refresh_from_db()
        self.assertFalse(self.own.is_collective_agenda)
        response = self.client.put(
            endpoint, data=json.dumps({'is_collective_agenda': True, 'contact_name': 'Nombre corregido'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.own.refresh_from_db()
        self.assertTrue(self.own.is_collective_agenda)
        self.assertEqual(self.own.contact_name, 'Nombre corregido')

    def test_create_accepts_boolean_collective_agenda_and_rejects_string_flag(self):
        payload = {
            'contact_name': 'Nuevo solicitante de agenda', 'delegation': self.north.pk,
            'title': 'Atención de agenda colectiva', 'description': 'Se registra el compromiso',
            'activity_date': timezone.localdate().isoformat(), 'is_collective_agenda': True,
        }
        response = self.client.post(
            self.activities_url, data=json.dumps(payload), content_type='application/json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(Activity.objects.get(pk=response.json()['id']).is_collective_agenda)
        payload['is_collective_agenda'] = 'false'
        self.assertEqual(self.client.post(
            self.activities_url, data=json.dumps(payload), content_type='application/json',
        ).status_code, 400)
        self.assertEqual(Activity.objects.filter(contact_name=payload['contact_name']).count(), 1)

