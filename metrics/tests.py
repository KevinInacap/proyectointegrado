import json
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, override_settings
from core.models import AuditLog
from organization.models import Position, Role, UserProfile
from .models import AttentionType, MeasurementItem, MeasurementPeriod, SubAttention


@override_settings(ROOT_URLCONF='metrics.urls')
class CatalogAPITests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.admin = users.objects.create_user(username='catalog_admin', password='test', is_staff=True, is_superuser=True)
        self.regular = users.objects.create_user(username='regular', password='test')
        self.staff = users.objects.create_user(username='other_staff', password='test', is_staff=True)

    def send(self, method, path, payload):
        return getattr(self.client, method)(path, data=json.dumps(payload), content_type='application/json')

    def test_admin_required_for_read_and_write(self):
        self.assertEqual(self.client.get('/items/').status_code, 403)
        self.client.force_login(self.regular)
        self.assertEqual(self.client.get('/items/').status_code, 403)
        self.assertEqual(self.send('post', '/items/', {'code': 'X', 'name': 'X'}).status_code, 403)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get('/items/').status_code, 403)

    def test_application_administrator_can_use_all_catalogs_without_django_staff(self):
        account = get_user_model().objects.create_user('app_catalog_admin', password='ClaveSegura92!')
        profile = UserProfile.objects.create(
            user=account, rut='13.714.021-0', full_name='Admin Catálogos', email='catalogos@example.test',
        )
        profile.roles.add(Role.objects.get(name='Administrador'))
        self.client.force_login(account)
        for path in ('/items/', '/goals/', '/attention-types/', '/subattentions/', '/management-types/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(self.send('post', '/attention-types/', {'code': 'PR-1', 'name': 'Prueba de catálogo'}).status_code, 201)

    def test_period_reference_is_authorized_and_read_only(self):
        period = MeasurementPeriod.objects.create(
            name='Semestre 2026', start_date='2026-01-01', end_date='2026-06-30',
        )
        self.assertEqual(self.client.get('/periods/').status_code, 403)
        self.client.force_login(self.admin)
        response = self.client.get('/periods/')
        self.assertEqual(response.status_code, 200)
        self.assertIn({'id': period.pk, 'name': 'Semestre 2026', 'status': 'Abierto'}, response.json()['results'])
        self.assertEqual(self.client.post('/periods/').status_code, 405)

    def test_management_types_persist_and_require_admin(self):
        self.assertEqual(self.client.get('/management-types/').status_code, 403)
        self.client.force_login(self.admin)
        payload = {'code': 'G-01', 'name': 'Derivación', 'description': 'Asignar unidad responsable'}
        created = self.send('post', '/management-types/', payload)
        self.assertEqual(created.status_code, 201)
        pk = created.json()['id']
        self.assertEqual(self.client.get(f'/management-types/{pk}/').json()['name'], 'Derivación')
        self.assertEqual(self.send('patch', f'/management-types/{pk}/', {'status': 'Inactivo'}).status_code, 200)
        self.assertEqual(self.client.get('/management-types/?status=Inactivo').json()['count'], 1)
        self.assertEqual(self.send('post', '/management-types/', payload).status_code, 400)
        self.assertEqual(self.client.delete(f'/management-types/{pk}/').status_code, 204)
        self.client.force_login(self.regular)
        self.assertEqual(self.client.get('/management-types/').status_code, 403)
        self.assertEqual(self.send('post', '/management-types/', payload).status_code, 403)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get('/management-types/').status_code, 403)

    def test_item_crud_search_pagination_and_duplicate(self):
        self.client.force_login(self.admin)
        payload = {'code': 'IT-01', 'name': 'Atenciones RSH', 'item_type': 'Cuantitativo', 'status': 'Activo'}
        created = self.send('post', '/items/', payload)
        self.assertEqual(created.status_code, 201)
        pk = created.json()['id']
        self.assertEqual(self.send('post', '/items/', {**payload, 'code': 'it-01'}).status_code, 400)
        self.assertEqual(self.client.get('/items/?search=RSH&page_size=1').json()['count'], 1)
        self.assertEqual(self.send('patch', f'/items/{pk}/', {'status': 'Inactivo'}).json()['status'], 'Inactivo')
        self.assertEqual(self.client.delete(f'/items/{pk}/').status_code, 204)
        self.assertEqual(self.client.get(f'/items/{pk}/').status_code, 404)

    def test_catalog_changes_are_audited_with_persisted_values(self):
        self.client.force_login(self.admin)
        created = self.send('post', '/items/', {'code': 'IT-AUDIT', 'name': 'Ítem de auditoría'})
        self.assertEqual(created.status_code, 201, created.content)
        pk = created.json()['id']
        changed = self.send('patch', f'/items/{pk}/', {'name': 'Nombre corregido'})
        self.assertEqual(changed.status_code, 200, changed.content)
        deleted = self.client.delete(f'/items/{pk}/')
        self.assertEqual(deleted.status_code, 204)
        logs = list(AuditLog.objects.filter(affected_table='catalogo_measurementitem', affected_record_id=str(pk)).order_by('pk'))
        self.assertEqual([log.action for log in logs], ['CREATE', 'UPDATE', 'DELETE'])
        self.assertEqual(logs[1].previous_value['name'], 'Ítem de auditoría')
        self.assertEqual(logs[1].new_value['name'], 'Nombre corregido')
        self.assertEqual(logs[2].previous_value['name'], 'Nombre corregido')

    def test_catalog_integrity_error_does_not_leak_database_details(self):
        self.client.force_login(self.admin)
        with patch.object(MeasurementItem, 'save', side_effect=IntegrityError('detalles privados')):
            response = self.send('post', '/items/', {'code': 'IT-RACE', 'name': 'Ítem nuevo'})
        self.assertEqual(response.status_code, 409)
        self.assertNotIn('detalles privados', response.content.decode())
        self.assertFalse(MeasurementItem.objects.filter(code='IT-RACE').exists())

    def test_catalog_save_rolls_back_when_audit_fails(self):
        self.client.force_login(self.admin)
        with patch('metrics.views.AuditLog.objects.create', side_effect=RuntimeError('auditoría caída')):
            with self.assertRaises(RuntimeError):
                self.send('post', '/items/', {'code': 'IT-ROLLBACK', 'name': 'Ítem nuevo'})
        self.assertFalse(MeasurementItem.objects.filter(code='IT-ROLLBACK').exists())

    def test_catalog_search_covers_descriptions_and_combines_filters(self):
        self.client.force_login(self.admin)
        MeasurementItem.objects.create(
            code='IT-DESC', name='Ítem archivado', description='Orientación vecinal', status='Inactivo',
        )
        active = MeasurementItem.objects.create(
            code='IT-ACT', name='Orientación activa', description='Atención social', status='Activo',
        )
        self.assertEqual(
            self.client.get('/items/?search=VECINAL&status=Inactivo&page_size=1').json()['count'], 1,
        )
        self.assertEqual(
            self.client.get('/items/?search=orientaci%C3%B3n&status=Activo').json()['results'][0]['id'], active.pk,
        )
        kind = AttentionType.objects.create(
            code='AT-SEARCH', name='Apoyo Comunitario', description='Orientación y acompañamiento',
        )
        other_kind = AttentionType.objects.create(code='AT-OTHER', name='Salud')
        SubAttention.objects.create(
            code='SA-SEARCH', name='Derivación', description='Orientación especializada', attention_type=kind,
        )
        SubAttention.objects.create(
            code='SA-OTHER', name='Control', attention_type=other_kind,
        )
        filtered = self.client.get(
            f'/subattentions/?search=acompa%C3%B1amiento&attention_type={kind.pk}&status=Activo'
        ).json()
        self.assertEqual(filtered['count'], 1)

    def test_type_subattention_relation_and_conflict(self):
        self.client.force_login(self.admin)
        type_id = self.send('post', '/attention-types/', {'code': 'SOC', 'name': 'Social'}).json()['id']
        self.assertEqual(self.send('post', '/subattentions/', {'code': 'BAD', 'name': 'RSH', 'attention_type': 999}).status_code, 400)
        sub = self.send('post', '/subattentions/', {'code': 'RSH', 'name': 'RSH', 'attention_type': type_id})
        self.assertEqual(sub.status_code, 201)
        self.assertEqual(self.send('post', '/subattentions/', {'code': 'RSH2', 'name': 'rsh', 'attention_type': type_id}).status_code, 400)
        self.assertEqual(self.client.get(f'/subattentions/?attention_type={type_id}').json()['count'], 1)
        self.assertEqual(self.client.delete(f'/attention-types/{type_id}/').status_code, 409)
        self.assertEqual(self.client.delete(f"/subattentions/{sub.json()['id']}/").status_code, 204)
        self.assertEqual(self.client.delete(f'/attention-types/{type_id}/').status_code, 204)

    def test_goal_relations_and_unique_triple(self):
        self.client.force_login(self.admin)
        period = MeasurementPeriod.objects.create(name='T1', start_date='2026-01-01', end_date='2026-03-31')
        position = Position.objects.create(name='Gestor', description='')
        item = MeasurementItem.objects.create(code='IT-1', name='Atenciones')
        data = {'code': 'GO-1', 'period': period.pk, 'position': position.pk, 'item': item.pk,
                'target_value': '10.00', 'weight': '50.00', 'unit_of_measure': 'Atenciones'}
        self.assertEqual(self.send('post', '/goals/', {**data, 'item': 999}).status_code, 400)
        self.assertEqual(self.send('post', '/goals/', {**data, 'weight': '101.00'}).status_code, 400)
        self.assertEqual(self.send('post', '/goals/', data).status_code, 201)
        self.assertEqual(self.send('post', '/goals/', {**data, 'code': 'GO-2'}).status_code, 400)
        self.assertEqual(self.client.get('/goals/?search=Atenciones').json()['count'], 1)
