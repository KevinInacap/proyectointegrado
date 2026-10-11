import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from metrics.models import AttentionType, SubAttention
from organization.models import Delegation, Role, UserProfile
from core.models import AuditLog
from .models import Activity, ServiceCatalog


class AttentionAuditTests(TestCase):
    def setUp(self):
        self.delegation = Delegation.objects.create(name='Audit', scope='Audit')
        self.user = get_user_model().objects.create_user(username='attention-audit')
        self.profile = UserProfile.objects.create(user=self.user, rut='22222222-2',
            full_name='Audit', email='attention@example.com', delegation=self.delegation)
        self.role = Role.objects.create(name='Audit writer', permissions_data=['lectura', 'edicion', 'cierre'])
        self.profile.roles.add(self.role)
        self.client.force_login(self.user)
        self.kind = AttentionType.objects.create(code='TYPE', name='Social')
        self.sub = SubAttention.objects.create(code='SUB', name='Orientación', attention_type=self.kind)
        self.other = SubAttention.objects.create(code='OTHER', name='Registro', attention_type=self.kind)
        self.payload = dict(contact_name='Solicitante', contact_phone='123', title='Problema',
                            description='Acción', attention_type_id=self.kind.pk, subattention_id=self.sub.pk)
        self.url = reverse('activities:api_atenciones')

    def post(self, **changes):
        return self.client.post(self.url, json.dumps({**self.payload, **changes}), content_type='application/json')

    def test_typed_names_are_serialized_in_list_and_detail(self):
        response = self.post()
        self.assertEqual(response.status_code, 201)
        detail = reverse('activities:api_atencion_detail', args=[response.json()['id']])
        for record in (self.client.get(self.url).json()['atenciones'][0], self.client.get(detail).json()['atencion']):
            self.assertEqual(record['attention_type'], self.kind.name)
            self.assertEqual(record['subattention_type'], self.sub.name)

    def test_changed_subattention_is_not_deduplicated(self):
        first = self.post()
        repeat = self.post()
        other = self.post(subattention_id=self.other.pk)
        self.assertEqual(repeat.status_code, 200)
        self.assertEqual(first.json()['id'], repeat.json()['id'])
        self.assertEqual(other.status_code, 201)
        self.assertNotEqual(first.json()['id'], other.json()['id'])

    def test_code_reuse_with_changed_fields_conflicts(self):
        self.assertEqual(self.post(activity_code='RETRY').status_code, 201)
        self.assertEqual(self.post(activity_code='RETRY').status_code, 200)
        for changes in ({'subattention_id': self.other.pk}, {'contact_phone': '456'}, {'is_collective_agenda': True}):
            self.assertEqual(self.post(activity_code='RETRY', **changes).status_code, 409)
        self.assertEqual(Activity.objects.count(), 1)

    def test_malformed_ids_are_400_and_do_not_create(self):
        for key in ('attention_type_id', 'subattention_id', 'catalog_id'):
            for value in (True, 1.5, float('inf'), {}, [], 10**100):
                with self.subTest(key=key, value=value):
                    self.assertEqual(self.post(**{key: value}).status_code, 400)
        self.assertFalse(Activity.objects.exists())

    def test_deleted_delegation_cannot_read_or_write(self):
        self.post()
        self.delegation.deleted_at = timezone.now()
        self.delegation.save()
        self.assertEqual(self.post().status_code, 403)
        self.assertEqual(self.client.get(self.url).json()['atenciones'], [])

    def test_typed_names_take_precedence_over_legacy_catalog(self):
        catalog = ServiceCatalog.objects.create(area='Area', service='Servicio', attention_type='Legacy', subattention_type='Old')
        self.assertEqual(self.post(catalog_id=catalog.pk).status_code, 201)
        record = self.client.get(self.url).json()['atenciones'][0]
        self.assertEqual(record['attention_type'], self.kind.name)
        self.assertEqual(record['subattention_type'], self.sub.name)
        self.assertEqual(record['service'], 'Servicio')

    def test_admin_crud_for_activity_is_audited_and_cannot_change_verification(self):
        created = self.post()
        self.assertEqual(created.status_code, 201, created.content)
        activity = Activity.objects.get(pk=created.json()['id'])
        detail = reverse('activities:api_atencion_detail', args=[activity.pk])

        updated = self.client.put(detail, json.dumps({
            'contact_name': 'Nombre corregido',
            'problem_description': 'Solicitud corregida',
            'executed_action': 'Derivación registrada',
            'activity_date': '2026-09-18',
            'attention_type_id': self.kind.pk,
            'subattention_id': self.other.pk,
        }), content_type='application/json')
        self.assertEqual(updated.status_code, 200, updated.content)
        activity.refresh_from_db()
        self.assertEqual(activity.contact_name, 'Nombre corregido')
        self.assertEqual(activity.subattention_id, self.other.pk)
        self.assertEqual(activity.activity_date.isoformat(), '2026-09-18')
        self.assertTrue(AuditLog.objects.filter(affected_table='actividad', affected_record_id=str(activity.pk), action='UPDATE').exists())

        rejected = self.client.put(detail, json.dumps({'status': 'Approved'}), content_type='application/json')
        self.assertEqual(rejected.status_code, 403)
        activity.refresh_from_db()
        self.assertEqual(activity.validation_status, 'Pending')

        deleted = self.client.delete(detail)
        self.assertEqual(deleted.status_code, 200, deleted.content)
        activity.refresh_from_db()
        self.assertIsNotNone(activity.deleted_at)
        self.assertTrue(AuditLog.objects.filter(affected_table='actividad', affected_record_id=str(activity.pk), action='DELETE').exists())
