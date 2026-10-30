import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import AuditLog
from metrics.models import AttentionType, SubAttention
from organization.models import Delegation, Position, Role, UserProfile
from .models import Activity, Vecino


class DelegadoRegistryTests(TestCase):
    def setUp(self):
        self.delegation = Delegation.objects.create(name='Padrón local', scope='Centro')
        self.other = Delegation.objects.create(name='Padrón ajeno', scope='Sur')
        self.user = get_user_model().objects.create_user(username='delegado-padron', password='test-pass')
        self.role = Role.objects.create(name='Operación de padrón', permissions_data=['lectura', 'edicion', 'cierre'])
        self.profile = UserProfile.objects.create(
            user=self.user, rut='11111111-1', full_name='Delegado de revisión',
            email='delegado@example.com', position=Position.objects.get(name='Delegado Municipal'),
            delegation=self.delegation,
        )
        self.profile.roles.add(self.role)
        self.client.force_login(self.user)
        kind = AttentionType.objects.create(code='REG-T', name='Consulta vecinal')
        sub = SubAttention.objects.create(code='REG-S', name='Orientación', attention_type=kind)
        self.api = reverse('activities:api_atenciones')
        self.payload = {
            'activity_code': 'REG-TEST-1', 'activity_date': '2026-01-02',
            'attention_type_id': kind.pk, 'subattention_id': sub.pk,
            'problem_description': 'Solicitud de orientación', 'executed_action': 'Orientación entregada',
        }
        self.registration = {'nombre': 'Vecina del padrón', 'rut': '12345678-5',
                             'direccion': 'Dirección de prueba 123', 'telefono': '912345678',
                             'email': 'vecina@example.com'}

    def post(self, **kwargs):
        return self.client.post(self.api, json.dumps(dict(self.payload, **kwargs)), content_type='application/json')

    def neighbor(self, **kwargs):
        return Vecino.objects.create(**dict(self.registration, rut='12.345.678-5',
                                           territorio=self.delegation.name, **kwargs))

    def test_inline_registration_creates_neighbor_and_linked_attention_once(self):
        response = self.post(new_neighbor=dict(self.registration, territorio=self.other.name, estado='Inactivo'))
        self.assertEqual(response.status_code, 201)
        neighbor = Vecino.objects.get()
        attention = Activity.objects.get()
        self.assertEqual(attention.neighbor_id, neighbor.pk)
        self.assertEqual(attention.contact_name, neighbor.nombre)
        self.assertEqual(attention.contact_phone, neighbor.telefono)
        self.assertEqual(neighbor.rut, '12.345.678-5')
        self.assertEqual(neighbor.territorio, self.delegation.name)
        self.assertEqual(neighbor.estado, 'Activo')
        self.assertEqual(self.post(new_neighbor=self.registration).status_code, 200)
        self.assertEqual(self.post(new_neighbor=dict(self.registration, direccion='Otra dirección')).status_code, 409)
        self.assertEqual(Vecino.objects.count(), 1)
        self.assertEqual(Activity.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action='CREATE', affected_table='vecino').count(), 1)
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_inline_retry_without_client_code_does_not_duplicate_either_record(self):
        self.payload.pop('activity_code')
        self.assertEqual(self.post(new_neighbor=self.registration).status_code, 201)
        self.assertEqual(self.post(new_neighbor=self.registration).status_code, 200)
        self.assertEqual(Vecino.objects.count(), 1)
        self.assertEqual(Activity.objects.count(), 1)

    def test_invalid_attention_or_neighbor_never_creates_a_registry_entry(self):
        for patch_data in ({'rut': '12345678-9'}, {'direccion': ''}, {'email': 'incorrecto'}, {'nombre': ['texto']},
                           {'nombre': '<script>alert(1)</script>'}, {'telefono': '123'},
                           {'direccion': '<img src=x>'}, {'rut': '12345678-5ABC'}):
            response = self.post(new_neighbor=dict(self.registration, **patch_data))
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.post(new_neighbor=self.registration, subattention_id=999999).status_code, 400)
        self.assertEqual(self.post(new_neighbor=self.registration, activity_date='2999-01-01').status_code, 400)
        self.assertEqual(Vecino.objects.count(), 0)
        self.assertEqual(Activity.objects.count(), 0)

    def test_neighbor_create_and_update_reject_invalid_fields_without_mutation(self):
        url = reverse('activities:api_vecinos')
        for changes in ({'nombre': '<script>'}, {'telefono': '123'}, {'email': 'bad@'},
                        {'direccion': '<img>'}, {'rut': '12345678-5ABC'}):
            with self.subTest(changes=changes):
                response = self.client.post(url, json.dumps(dict(self.registration, **changes)), content_type='application/json')
                self.assertEqual(response.status_code, 400)
                self.assertFalse(Vecino.objects.exists())
        response = self.client.post(url, json.dumps(self.registration), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        neighbor = Vecino.objects.get()
        detail = reverse('activities:api_vecino_detail', args=[neighbor.pk])
        for changes in ({'estado': 'inventado'}, {'telefono': '123'}, {'nombre': '<script>'}):
            with self.subTest(changes=changes):
                response = self.client.put(detail, json.dumps(dict(self.registration, **changes)), content_type='application/json')
                self.assertEqual(response.status_code, 400)
                neighbor.refresh_from_db()
                self.assertEqual(neighbor.nombre, self.registration['nombre'])
                self.assertEqual(neighbor.estado, 'Activo')

    def test_neighbor_create_and_update_are_atomic_with_audit(self):
        url = reverse('activities:api_vecinos')
        with patch('activities.views.AuditLog.objects.create', side_effect=RuntimeError('auditoría caída')):
            with self.assertRaises(RuntimeError):
                self.client.post(url, json.dumps(self.registration), content_type='application/json')
        self.assertFalse(Vecino.objects.exists())
        neighbor = self.neighbor()
        detail = reverse('activities:api_vecino_detail', args=[neighbor.pk])
        payload = dict(self.registration, direccion='Dirección cambiada')
        with patch('activities.views.AuditLog.objects.create', side_effect=RuntimeError('auditoría caída')):
            with self.assertRaises(RuntimeError):
                self.client.put(detail, json.dumps(payload), content_type='application/json')
        neighbor.refresh_from_db()
        self.assertEqual(neighbor.direccion, self.registration['direccion'])

    def test_partial_neighbor_edit_preserves_unsent_values(self):
        neighbor = self.neighbor(estado='Inactivo', telefono='912345678')
        detail = reverse('activities:api_vecino_detail', args=[neighbor.pk])
        response = self.client.put(detail, json.dumps({'direccion': 'Nueva dirección 10'}), content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        neighbor.refresh_from_db()
        self.assertEqual(neighbor.direccion, 'Nueva dirección 10')
        self.assertEqual(neighbor.telefono, '912345678')
        self.assertEqual(neighbor.estado, 'Inactivo')
        self.assertEqual(neighbor.nombre, self.registration['nombre'])

    def test_neighbor_collision_is_reported_without_database_details(self):
        url = reverse('activities:api_vecinos')
        with patch('activities.views.Vecino.objects.create', side_effect=IntegrityError('detalles privados')):
            response = self.client.post(url, json.dumps(self.registration), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('detalles privados', response.content.decode())
        self.assertFalse(Vecino.objects.exists())

    def test_attention_failure_rolls_back_neighbor_and_both_audits(self):
        with patch('activities.views.Activity.objects.create', side_effect=RuntimeError('Fallo simulado')):
            with self.assertRaises(RuntimeError):
                self.post(new_neighbor=self.registration)
        self.assertEqual(Vecino.objects.count(), 0)
        self.assertEqual(Activity.objects.count(), 0)
        self.assertEqual(AuditLog.objects.filter(action='CREATE').count(), 0)

    def test_existing_neighbor_is_reused_and_cannot_be_renamed_from_attention(self):
        neighbor = self.neighbor()
        response = self.post(neighbor_id=neighbor.pk, contact_name='Nombre manipulado', contact_phone='000')
        self.assertEqual(response.status_code, 201)
        attention = Activity.objects.get()
        self.assertEqual(attention.contact_name, neighbor.nombre)
        url = reverse('activities:api_atencion_detail', args=[attention.pk])
        edited = self.client.put(url, json.dumps({'contact_name': 'Otro nombre', 'contact_phone': '999'}), content_type='application/json')
        self.assertEqual(edited.status_code, 200)
        neighbor.refresh_from_db()
        attention.refresh_from_db()
        self.assertEqual(neighbor.nombre, self.registration['nombre'])
        self.assertEqual(neighbor.telefono, self.registration['telefono'])
        self.assertEqual(attention.contact_name, neighbor.nombre)
        self.assertEqual(attention.contact_phone, neighbor.telefono)
        self.assertEqual(Vecino.objects.count(), 1)

    def test_duplicate_rut_and_two_simultaneous_registration_modes_are_rejected(self):
        neighbor = self.neighbor()
        self.assertEqual(self.post(new_neighbor=self.registration).status_code, 400)
        self.assertEqual(self.post(new_neighbor=self.registration, neighbor_id=neighbor.pk).status_code, 400)
        self.assertEqual(Activity.objects.count(), 0)
        self.assertEqual(Vecino.objects.count(), 1)

    def test_foreign_inactive_deleted_or_malformed_neighbor_cannot_be_selected(self):
        neighbor = self.neighbor()
        for fields in ({'territorio': self.other.name}, {'estado': 'Inactivo'}, {'deleted_at': timezone.now()}):
            Vecino.objects.filter(pk=neighbor.pk).update(territorio=self.delegation.name, estado='Activo', deleted_at=None)
            Vecino.objects.filter(pk=neighbor.pk).update(**fields)
            self.assertIn(self.post(neighbor_id=neighbor.pk).status_code, {400, 404})
        for value in (True, -1, '9' * 50, {}, 1.2):
            self.assertEqual(self.post(neighbor_id=value).status_code, 400)
        self.assertEqual(Activity.objects.count(), 0)

    def test_inline_registration_requires_permission_and_active_assigned_delegation(self):
        self.role.permissions_data = ['lectura']
        self.role.save()
        self.assertEqual(self.post(new_neighbor=self.registration).status_code, 403)
        self.role.permissions_data = ['lectura', 'edicion']
        self.role.save()
        self.profile.delegation = None
        self.profile.save()
        self.assertEqual(self.post(new_neighbor=self.registration).status_code, 403)
        self.assertEqual(Vecino.objects.count(), 0)

    def test_historic_contact_can_be_linked_explicitly_without_guessing_identity(self):
        old = Activity.objects.create(activity_code='ANTERIOR', activity_date='2026-01-02',
                                      contact_name='Contacto anterior', problem_description='Consulta',
                                      executed_action='Registro', delegation=self.delegation)
        self.assertEqual(Vecino.objects.count(), 0)
        url = reverse('activities:api_atencion_detail', args=[old.pk])
        response = self.client.put(url, json.dumps({'new_neighbor': self.registration}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        old.refresh_from_db()
        self.assertEqual(old.neighbor, Vecino.objects.get())
        self.assertEqual(old.contact_name, self.registration['nombre'])

    def test_profile_history_and_index_filter_exclude_foreign_and_deleted_attentions(self):
        neighbor = self.neighbor()
        own = self.post(neighbor_id=neighbor.pk)
        Activity.objects.create(activity_code='AJENA-PRIVADA', activity_date='2026-01-02', neighbor=neighbor,
                                delegation=self.other, problem_description='Dato ajeno', executed_action='Registro')
        Activity.objects.create(activity_code='ELIMINADA', activity_date='2026-01-02', neighbor=neighbor,
                                delegation=self.delegation, deleted_at=timezone.now(), problem_description='Borrada', executed_action='Registro')
        detail = self.client.get(reverse('activities:api_vecino_detail', args=[neighbor.pk])).json()
        self.assertEqual(detail['attention_count'], 1)
        self.assertEqual(detail['followup_count'], 1)
        self.assertEqual([row['id'] for row in detail['recent_attentions']], [own.json()['id']])
        url = reverse('activities:dashboard_delegado_section', args=['atenciones'])
        response = self.client.get(url, {'vecino': neighbor.pk, 'estado': 'followup'})
        self.assertEqual(response.context['page'].paginator.count, 1)
        self.assertContains(response, f'name="vecino" value="{neighbor.pk}"')
        self.assertNotContains(response, 'Dato ajeno')
        self.assertEqual(self.client.get(url, {'vecino': 'incorrecto'}).status_code, 404)

    def test_identical_contacts_with_distinct_registry_ids_remain_distinct_attentions(self):
        first = self.neighbor()
        second = Vecino.objects.create(nombre=first.nombre, rut='11.111.111-1', telefono=first.telefono,
                                       direccion=first.direccion, territorio=self.delegation.name)
        self.payload.pop('activity_code')
        self.assertEqual(self.post(neighbor_id=first.pk).status_code, 201)
        self.assertEqual(self.post(neighbor_id=second.pk).status_code, 201)
        self.assertEqual(Activity.objects.count(), 2)

    def test_registry_search_accepts_formatted_and_unformatted_rut(self):
        neighbor = self.neighbor()
        api = reverse('activities:api_vecinos')
        page = reverse('activities:dashboard_delegado_section', args=['vecinos'])
        for query in ('12345678-5', '12.345.678-5', '123456785'):
            self.assertEqual([item['id'] for item in self.client.get(api, {'q': query}).json()['vecinos']], [neighbor.pk])
            self.assertEqual(list(self.client.get(page, {'q': query}).context['page']), [neighbor])

    def test_team_work_counts_are_local_and_exclude_deleted_attentions(self):
        self.post(new_neighbor=self.registration)
        Activity.objects.create(activity_code='FOREIGN-TEAM', activity_date='2026-01-02', user=self.user,
                                delegation=self.other, problem_description='Fuera', executed_action='Registro')
        Activity.objects.create(activity_code='DELETED-TEAM', activity_date='2026-01-02', user=self.user,
                                delegation=self.delegation, deleted_at=timezone.now(), problem_description='Borrada', executed_action='Registro')
        response = self.client.get(reverse('activities:dashboard_delegado_section', args=['equipo']))
        member = next(member for member in response.context['page'] if member.pk == self.profile.pk)
        self.assertEqual(member.attention_count, 1)
        self.assertEqual(member.followup_count, 1)
