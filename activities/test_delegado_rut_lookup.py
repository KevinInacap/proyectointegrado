import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import AuditLog
from metrics.models import AttentionType, SubAttention
from organization.models import Delegation, Position, Role, UserProfile

from .models import Activity, Vecino


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class DelegadoRutLookupTests(TestCase):
    def setUp(self):
        self.delegation = Delegation.objects.create(name='Sede consulta RUT', scope='Prueba')
        self.other = Delegation.objects.create(name='Otra sede consulta RUT', scope='Prueba')
        self.user = get_user_model().objects.create_user(username='delegado-consulta-rut')
        self.profile = UserProfile.objects.create(
            user=self.user, rut='20.000.000-0', full_name='Delegado consulta RUT',
            email='delegado-rut@example.test', delegation=self.delegation,
            position=Position.objects.get(name='Delegado Municipal'),
        )
        self.profile.roles.add(Role.objects.get(name='Delegado Municipal'))
        self.client.force_login(self.user)
        self.api = reverse('activities:api_vecinos')

    def neighbor(self, **changes):
        return Vecino.objects.create(**dict({
            'nombre': 'Vecina registrada', 'rut': '12.345.678-5',
            'direccion': 'Dirección de prueba 123', 'telefono': '912345678',
            'territorio': self.delegation.name, 'estado': 'Activo',
        }, **changes))

    def test_exact_lookup_accepts_formatted_and_unformatted_rut_without_name_matches(self):
        neighbor = self.neighbor()
        self.neighbor(nombre='Nombre con 12.345.678-5', rut='11.111.111-1')
        for rut in ('12.345.678-5', '12345678-5', '123456785', ' 12.345.678-5 '):
            with self.subTest(rut=rut):
                response = self.client.get(self.api, {'rut': rut, 'q': 'sin coincidencia'})
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data['found'])
                self.assertEqual([item['id'] for item in data['vecinos']], [neighbor.pk])
                self.assertEqual(data['paginated_vecinos'], data['vecinos'])
                self.assertEqual(data['pagination']['total_count'], 1)
        self.assertEqual(Activity.objects.count(), 0)
        self.assertFalse(AuditLog.objects.exists())

    def test_missing_or_invalid_rut_is_rejected_without_returning_any_neighbors(self):
        self.neighbor()
        for rut in ('', '12345678-9', 'texto123456785', '12345678', '1' * 100):
            with self.subTest(rut=rut):
                response = self.client.get(self.api, {'rut': rut})
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json()['success'])
                self.assertFalse(response.json()['found'])
                self.assertNotIn('Vecina registrada', response.content.decode())
        self.assertEqual(Vecino.objects.count(), 1)
        self.assertFalse(Activity.objects.exists())

    def test_exact_lookup_includes_inactive_local_record_even_with_active_filter(self):
        neighbor = self.neighbor(estado='Inactivo')
        response = self.client.get(self.api, {'rut': '123456785', 'estado': 'Activo'})
        data = response.json()
        self.assertTrue(data['found'])
        self.assertEqual(data['vecinos'][0]['id'], neighbor.pk)
        self.assertEqual(data['vecinos'][0]['estado'], 'Inactivo')
        self.assertEqual(Vecino.objects.count(), 1)

    def test_foreign_and_deleted_records_are_not_disclosed_or_replaced(self):
        for changes in ({'territorio': self.other.name}, {'deleted_at': timezone.now()}):
            with self.subTest(changes=changes):
                neighbor = self.neighbor(**changes)
                response = self.client.get(self.api, {'rut': '123456785'})
                data = response.json()
                self.assertEqual(response.status_code, 200)
                self.assertFalse(data['found'])
                self.assertEqual(data['vecinos'], [])
                self.assertEqual(data['paginated_vecinos'], [])
                self.assertEqual(data['pagination']['total_count'], 0)
                self.assertEqual(Vecino.objects.count(), 1)
                neighbor.delete()

    def attention_payload(self):
        kind = AttentionType.objects.create(code='RUT-T', name='Consulta de RUT')
        subtype = SubAttention.objects.create(code='RUT-S', name='Orientación', attention_type=kind)
        return {
            'activity_code': 'RUT-NUEVA-ATENCION', 'activity_date': timezone.localdate().isoformat(),
            'attention_type_id': kind.pk, 'subattention_id': subtype.pk,
            'problem_description': 'Solicitud de orientación', 'executed_action': 'Orientación entregada',
            'new_neighbor': {'nombre': 'Solicitante nuevo', 'rut': '9876543-3',
                             'direccion': 'Dirección de prueba 456', 'telefono': '912345678',
                             'email': 'solicitante-rut@example.test', 'territorio': self.other.name},
        }

    def test_unregistered_rut_can_register_neighbor_and_attention_together_once(self):
        self.assertFalse(self.client.get(self.api, {'rut': '9876543-3'}).json()['found'])
        self.assertFalse(Vecino.objects.exists())
        payload = self.attention_payload()
        api = reverse('activities:api_atenciones')
        response = self.client.post(api, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        neighbor = Vecino.objects.get()
        attention = Activity.objects.get()
        self.assertEqual(neighbor.rut, '9.876.543-3')
        self.assertEqual(neighbor.territorio, self.delegation.name)
        self.assertEqual(attention.neighbor_id, neighbor.pk)
        self.assertEqual(attention.contact_name, neighbor.nombre)
        self.assertEqual(attention.contact_phone, neighbor.telefono)
        found = self.client.get(self.api, {'rut': '98765433'}).json()
        self.assertTrue(found['found'])
        self.assertEqual(found['vecinos'][0]['id'], neighbor.pk)
        self.assertEqual(self.client.post(api, json.dumps(payload), content_type='application/json').status_code, 200)
        self.assertEqual(Vecino.objects.count(), 1)
        self.assertEqual(Activity.objects.count(), 1)

    def test_invalid_attention_or_registration_does_not_create_partial_neighbor(self):
        payload = self.attention_payload()
        api = reverse('activities:api_atenciones')
        for changes in ({'subattention_id': 999999}, {'activity_date': '2999-01-01'},
                        {'new_neighbor': dict(payload['new_neighbor'], direccion='')},
                        {'new_neighbor': dict(payload['new_neighbor'], rut='9876543-9')}):
            with self.subTest(changes=changes):
                response = self.client.post(api, json.dumps(dict(payload, **changes)), content_type='application/json')
                self.assertEqual(response.status_code, 400)
                self.assertFalse(Vecino.objects.exists())
                self.assertFalse(Activity.objects.exists())
                self.assertFalse(AuditLog.objects.exists())

    def test_lookup_requires_read_permission(self):
        self.neighbor()
        self.profile.roles.clear()
        response = self.client.get(self.api, {'rut': '123456785'})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('Vecina registrada', response.content.decode())

    def attention(self, code, neighbor, **changes):
        return Activity.objects.create(**dict({
            'activity_code': code, 'activity_date': timezone.localdate(),
            'contact_name': neighbor.nombre, 'neighbor': neighbor,
            'problem_description': 'Solicitud de orientación', 'executed_action': 'Orientación entregada',
            'delegation': self.delegation, 'user': self.user, 'validation_status': 'Pending',
        }, **changes))

    def test_attention_search_by_full_rut_preserves_status_counts_and_pagination(self):
        neighbor = self.neighbor()
        for index in range(9):
            self.attention(f'RUT-PENDIENTE-{index}', neighbor)
        self.attention('RUT-APROBADA', neighbor, validation_status='Approved')
        other = self.neighbor(nombre='Otra vecina', rut='11.111.111-1')
        self.attention('OTRA-PENDIENTE', other)
        listing = reverse('activities:dashboard_delegado_section', args=['atenciones'])
        for rut in ('12.345.678-5', '12345678-5', '123456785'):
            with self.subTest(rut=rut):
                params = {'q': rut, 'estado': 'Pending'}
                first = self.client.get(listing, params)
                second = self.client.get(listing, {**params, 'page': 2})
                self.assertEqual(first.context['page'].paginator.count, 9)
                self.assertEqual(len(first.context['page']), 8)
                self.assertEqual(len(second.context['page']), 1)
                self.assertEqual(first.context['attention_scope_counts'], {
                    'total': 10, 'followup': 9, 'approved': 1,
                })
                self.assertTrue(all(item.neighbor_id == neighbor.pk for item in first.context['page']))
                self.assertContains(first, f'q={rut}&amp;estado=Pending&amp;page=2')
                approved = self.client.get(listing, {'q': rut, 'estado': 'Approved'})
                self.assertEqual(approved.context['page'].paginator.count, 1)
                self.assertEqual(approved.context['attention_scope_counts'], first.context['attention_scope_counts'])

    def test_attention_rut_search_excludes_foreign_deleted_and_nonmatching_records(self):
        neighbor = self.neighbor()
        visible = self.attention('RUT-LOCAL-VISIBLE', neighbor)
        self.attention('RUT-ATENCION-AJENA', neighbor, delegation=self.other)
        self.attention('RUT-ATENCION-ELIMINADA', neighbor, deleted_at=timezone.now())
        foreign = self.neighbor(nombre='Ficha ajena', rut='12345678-5', territorio=self.other.name)
        self.attention('RUT-FICHA-AJENA', foreign)
        deleted = self.neighbor(nombre='Ficha dada de baja', rut='123456785', deleted_at=timezone.now())
        self.attention('RUT-FICHA-ELIMINADA', deleted)
        listing = reverse('activities:dashboard_delegado_section', args=['atenciones'])
        response = self.client.get(listing, {'q': '123456785'})
        self.assertEqual([item.pk for item in response.context['page']], [visible.pk])
        self.assertEqual(response.context['attention_scope_counts'], {
            'total': 1, 'followup': 1, 'approved': 0,
        })
        absent = self.client.get(listing, {'q': '98765433'})
        self.assertEqual(absent.context['page'].paginator.count, 0)
        self.assertEqual(absent.context['attention_scope_counts'], {
            'total': 0, 'followup': 0, 'approved': 0,
        })

