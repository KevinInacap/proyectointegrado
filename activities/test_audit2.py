import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from metrics.models import AttentionType, SubAttention
from organization.models import Delegation, Role, UserProfile
from .models import Activity, ServiceCatalog


class AttentionAuditTests(TestCase):
    def setUp(self):
        self.delegation = Delegation.objects.create(name='Audit', scope='Audit')
        self.user = get_user_model().objects.create_user(username='attention-audit')
        self.profile = UserProfile.objects.create(user=self.user, rut='22222222-2',
            full_name='Audit', email='attention@example.com', delegation=self.delegation)
        self.role = Role.objects.create(name='Audit writer', permissions_data=['lectura', 'edicion'])
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
