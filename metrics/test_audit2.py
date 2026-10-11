import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from activities.models import Activity
from organization.models import Position, Role, UserProfile
from .models import AttentionType, Goal, MeasurementItem, MeasurementPeriod, SubAttention


@override_settings(ROOT_URLCONF='metrics.urls')
class CatalogAuditTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='audit', is_superuser=True)
        self.client.force_login(self.user)
        self.kind = AttentionType.objects.create(code='TYPE', name='Tipo')
        self.sub = SubAttention.objects.create(code='SUB', name='Sub', attention_type=self.kind)
        self.item = MeasurementItem.objects.create(code='ITEM', name='Item')
        self.period = MeasurementPeriod.objects.create(name='T1', start_date='2026-01-01', end_date='2026-03-31')
        self.position = Position.objects.create(name='Cargo')
        self.goal = dict(code='GOAL', period=self.period.pk, position=self.position.pk,
                         item=self.item.pk, target_value='10', weight='50')

    def send(self, method, path, data):
        return getattr(self.client, method)(path, json.dumps(data), content_type='application/json')

    def test_malformed_fields_are_400_without_writes(self):
        for field in ('code', 'name', 'description', 'item_type', 'status'):
            for value in ([], {}, True, 23):
                with self.subTest(field=field, value=value):
                    response = self.send('post', '/items/', {'code': 'NEW', 'name': 'Nuevo', field: value})
                    self.assertEqual(response.status_code, 400)
        self.assertEqual(MeasurementItem.objects.count(), 1)

    def test_bad_foreign_keys_and_decimals_are_400(self):
        for field in ('period', 'position', 'item', 'weight', 'target_value'):
            for value in ([], {}, True, 'NaN', 'Infinity', float('inf'), 1e100):
                with self.subTest(field=field, value=value):
                    self.assertEqual(self.send('post', '/goals/', {**self.goal, field: value}).status_code, 400)

    def test_non_object_and_invalid_json(self):
        for value in ([], None, True, 'text'):
            self.assertEqual(self.send('post', '/items/', value).status_code, 400)
        self.assertEqual(self.client.post('/items/', b'\xff', content_type='application/json').status_code, 400)

    def test_patch_malformed_field_does_not_change_record(self):
        self.assertEqual(self.send('patch', f'/subattentions/{self.sub.pk}/', {'attention_type': {}}).status_code, 400)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.attention_type_id, self.kind.pk)

    def test_deleted_goal_relations_are_rejected(self):
        for obj in (self.period, self.position, self.item):
            obj.deleted_at = timezone.now()
            obj.save()
            self.assertEqual(self.send('post', '/goals/', self.goal).status_code, 400)
            obj.deleted_at = None
            obj.save()

    def test_deleted_parent_type_is_rejected(self):
        self.kind.deleted_at = timezone.now()
        self.kind.save()
        self.assertEqual(self.send('post', '/subattentions/', dict(code='NEW', name='Nuevo', attention_type=self.kind.pk)).status_code, 400)

    def activity(self, **fields):
        return Activity.objects.create(activity_code='A', activity_date='2026-01-01',
                                       problem_description='P', executed_action='A', **fields)

    def test_related_deletes_return_conflict_and_preserve_history(self):
        activity = self.activity(attention_type=self.kind, subattention=self.sub, item=self.item, deleted_at=timezone.now())
        for catalog, obj in (('attention-types', self.kind), ('subattentions', self.sub), ('items', self.item)):
            self.assertEqual(self.client.delete(f'/{catalog}/{obj.pk}/').status_code, 409)
            self.assertTrue(type(obj).objects.filter(pk=obj.pk).exists())
        activity.refresh_from_db()
        self.assertEqual(activity.subattention_id, self.sub.pk)

    def test_type_without_subattention_still_protected_by_activity(self):
        self.sub.delete()
        self.activity(attention_type=self.kind)
        self.assertEqual(self.client.delete(f'/attention-types/{self.kind.pk}/').status_code, 409)

    def test_reparent_used_subattention_is_rejected(self):
        self.activity(attention_type=self.kind, subattention=self.sub)
        other = AttentionType.objects.create(code='OTHER', name='Otro')
        self.assertEqual(self.send('patch', f'/subattentions/{self.sub.pk}/', {'attention_type': other.pk}).status_code, 400)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.attention_type_id, self.kind.pk)

    def test_live_admin_role_revocation_and_profile_status(self):
        self.user.is_superuser = False
        self.user.save()
        profile = UserProfile.objects.create(user=self.user, rut='11111111-1', full_name='Audit', email='audit@example.com')
        role, _ = Role.objects.get_or_create(name='Administrador General')
        profile.roles.add(role)
        self.assertEqual(self.client.get('/items/').status_code, 200)
        role.deleted_at = timezone.now()
        role.save()
        self.assertEqual(self.client.get('/items/').status_code, 403)
        role.deleted_at = None
        role.save()
        profile.status = 'Bloqueado'
        profile.save()
        self.assertEqual(self.client.get('/items/').status_code, 403)

    def test_forged_session_and_staff_do_not_grant_access(self):
        self.user.is_superuser = False
        self.user.is_staff = True
        self.user.save()
        session = self.client.session
        session['user_role'] = 'Administrador General'
        session.save()
        for catalog in ('items', 'goals', 'attention-types', 'subattentions'):
            self.assertEqual(self.client.get(f'/{catalog}/').status_code, 403)
            self.assertEqual(self.send('post', f'/{catalog}/', {}).status_code, 403)
        self.assertEqual(self.client.delete(f'/items/{self.item.pk}/').status_code, 403)

    def test_pagination_reports_the_page_actually_returned(self):
        response = self.client.get('/items/?page=999')
        self.assertEqual(response.json()['page'], 1)

    def test_invalid_status_filter_is_rejected(self):
        self.assertEqual(self.client.get('/items/?status=Unknown').status_code, 400)

    @override_settings(ROOT_URLCONF='config.urls')
    def test_public_catalog_routes_are_mounted(self):
        for catalog in ('items', 'goals', 'attention-types', 'subattentions'):
            response = self.client.get(f'/api/catalogs/{catalog}/')
            self.assertEqual(response.status_code, 200)
            self.assertIn('results', response.json())

    def test_goal_put_delete_and_related_item_protection(self):
        response = self.send('post', '/goals/', self.goal)
        self.assertEqual(response.status_code, 201)
        path = f"/goals/{response.json()['id']}/"
        self.assertEqual(self.client.delete(f'/items/{self.item.pk}/').status_code, 409)
        self.assertEqual(self.send('put', path, {**self.goal, 'target_value': '20.00'}).json()['target_value'], '20.00')
        self.assertEqual(self.send('put', path, {'code': 'MISSING'}).status_code, 400)
        self.assertEqual(self.client.get(path).json()['code'], 'GOAL')
        self.assertEqual(self.client.delete(path).status_code, 204)
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_invalid_query_ids_are_400(self):
        for value in ('1.5', '-1', '0', 'Infinity', '9' * 100):
            self.assertEqual(self.client.get('/subattentions/', {'attention_type': value}).status_code, 400)
