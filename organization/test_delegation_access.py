import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from activities.models import Activity
from core.models import AuditLog
from .models import Delegation, Position, Role, UserProfile


class OrganizationDelegationAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.north = Delegation.objects.create(name='Auditoría Norte', scope='Norte')
        cls.south = Delegation.objects.create(name='Auditoría Sur', scope='Sur')
        cls.local_position = Position.objects.create(name='Cargo local de auditoría')
        cls.shared_position = Position.objects.create(name='Cargo de otra sede')
        cls.permission_role = Role.objects.create(
            name='Catálogos y auditoría territorial',
            permissions_data=['auditoria.view', 'cargos.create', 'cargos.edit', 'cargos.delete'],
        )
        cls.operator = get_user_model().objects.create_user(username='auditor-local')
        cls.foreign_user = get_user_model().objects.create_user(username='funcionario-ajeno')
        cls.admin = get_user_model().objects.create_user(username='administracion-auditoria')
        cls.profile = UserProfile.objects.create(
            user=cls.operator, full_name='Auditor local', rut='18.100.000-1',
            email='auditor-local@example.test', delegation=cls.north,
            position=cls.local_position,
        )
        cls.profile.roles.add(cls.permission_role)
        UserProfile.objects.create(
            user=cls.foreign_user, full_name='Funcionario de otra sede', rut='18.100.000-2',
            email='funcionario-ajeno@example.test', delegation=cls.south,
            position=cls.shared_position,
        )
        admin_profile = UserProfile.objects.create(
            user=cls.admin, full_name='Administración de prueba', rut='18.100.000-3',
            email='administracion-auditoria@example.test', delegation=cls.north,
            position=Position.objects.get(name='Administrador General'),
        )
        admin_profile.roles.add(Role.objects.get(name='Administrador'))
        cls.local_activity = Activity.objects.create(
            activity_code='AUDIT-LOCAL', activity_date='2026-01-02',
            contact_name='Vecino local', problem_description='Consulta local',
            executed_action='Atención registrada', delegation=cls.north,
        )
        cls.foreign_activity = Activity.objects.create(
            activity_code='AUDIT-FOREIGN', activity_date='2026-01-02',
            contact_name='Vecino ajeno', problem_description='Consulta ajena',
            executed_action='Atención ajena', delegation=cls.south,
        )
        cls.local_log = AuditLog.objects.create(
            user=cls.operator, affected_table='actividad',
            affected_record_id=str(cls.local_activity.pk), action='CREATE',
            new_value={'code': 'ACTIVIDAD-LOCAL'},
        )
        cls.foreign_log = AuditLog.objects.create(
            user=cls.foreign_user, affected_table='actividad',
            affected_record_id=str(cls.foreign_activity.pk), action='CREATE',
            new_value={'code': 'SECRETO-DE-OTRA-SEDE'},
        )
        cls.admin_foreign_log = AuditLog.objects.create(
            user=cls.admin, affected_table='actividad',
            affected_record_id=str(cls.foreign_activity.pk), action='CREATE',
            new_value={'code': 'ADMIN-CAMBIO-OTRO-TERRITORIO'},
        )
        cls.global_log = AuditLog.objects.create(
            user=cls.operator, affected_table='rol',
            affected_record_id=str(cls.permission_role.pk), action='UPDATE',
            new_value={'name': 'CATÁLOGO-GLOBAL'},
        )
        cls.deleted_log = AuditLog.objects.create(
            user=cls.operator, affected_table='actividad',
            affected_record_id=str(cls.local_activity.pk), action='CREATE',
            new_value={'code': 'TRAZA-ELIMINADA'}, deleted_at=timezone.now(),
        )

    def setUp(self):
        self.client.force_login(self.operator)

    def update_position(self, position, **changes):
        return self.client.put(
            reverse('organization:api_position_update', args=[position.pk]),
            data=json.dumps(changes), content_type='application/json',
        )

    def test_catalog_permission_cannot_promote_a_cargo_to_administrator(self):
        for name in ('Ádministrador General', 'Super Administrador'):
            with self.subTest(name=name):
                response = self.update_position(self.local_position, name=name)
                self.assertEqual(response.status_code, 403)
                self.local_position.refresh_from_db()
                self.assertEqual(self.local_position.name, 'Cargo local de auditoría')
                self.assertFalse(self.profile.roles.filter(name='Administrador').exists())
                self.assertFalse(self.profile.roles.filter(name='SuperAdministrador').exists())

    def test_non_admin_cannot_change_an_existing_administrative_cargo(self):
        position = Position.objects.get(name='Administrador General')
        response = self.update_position(position, name='Cargo renombrado sin autoridad')
        self.assertEqual(response.status_code, 403)
        position.refresh_from_db()
        self.assertEqual(position.name, 'Administrador General')

    def test_non_admin_cannot_create_an_administrative_cargo_alias(self):
        response = self.client.post(
            reverse('organization:api_positions'),
            data=json.dumps({'name': 'Ádministrador General', 'description': ''}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Position.objects.filter(name='Ádministrador General').exists())

    def test_catalog_edit_cannot_change_a_cargo_used_by_another_delegation(self):
        response = self.update_position(self.shared_position, description='Cambio ajeno')
        self.assertEqual(response.status_code, 403)
        self.shared_position.refresh_from_db()
        self.assertEqual(self.shared_position.description, '')
        toggle = self.client.post(reverse(
            'organization:api_position_toggle', args=[self.shared_position.pk],
        ))
        self.assertEqual(toggle.status_code, 403)

    def test_scoped_catalog_edit_remains_available_for_a_local_cargo(self):
        response = self.update_position(self.local_position, description='Descripción local')
        self.assertEqual(response.status_code, 200, response.content)
        self.local_position.refresh_from_db()
        self.assertEqual(self.local_position.description, 'Descripción local')

    def test_administrator_keeps_cross_delegation_catalog_management(self):
        self.client.force_login(self.admin)
        response = self.update_position(self.shared_position, description='Gestión central')
        self.assertEqual(response.status_code, 200, response.content)
        self.shared_position.refresh_from_db()
        self.assertEqual(self.shared_position.description, 'Gestión central')

    def test_audit_api_only_returns_verifiable_local_events(self):
        response = self.client.get(reverse('organization:api_audit_logs'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([log['id'] for log in response.json()['logs']], [self.local_log.pk])
        self.assertNotContains(response, 'SECRETO-DE-OTRA-SEDE')
        self.assertNotContains(response, 'ADMIN-CAMBIO-OTRO-TERRITORIO')
        self.assertNotContains(response, 'CATÁLOGO-GLOBAL')
        self.assertNotContains(response, 'TRAZA-ELIMINADA')

    def test_audit_api_does_not_use_querystring_to_expand_territory(self):
        response = self.client.get(reverse('organization:api_audit_logs'), {
            'delegation_id': self.south.pk, 'delegation': self.south.name,
        })
        self.assertEqual([log['id'] for log in response.json()['logs']], [self.local_log.pk])

    def test_missing_inactive_or_deleted_delegation_has_no_audit_data(self):
        for state in ('missing', 'inactive', 'deleted'):
            with self.subTest(state=state):
                self.north.status = 'Inactivo' if state == 'inactive' else 'Activo'
                self.north.deleted_at = timezone.now() if state == 'deleted' else None
                self.north.save(update_fields=['status', 'deleted_at', 'updated_at'])
                self.profile.delegation = None if state == 'missing' else self.north
                self.profile.save(update_fields=['delegation', 'updated_at'])
                response = self.client.get(reverse('organization:api_audit_logs'))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['logs'], [])

    def test_transfer_does_not_expose_the_previous_territorys_events(self):
        self.profile.delegation = self.south
        self.profile.save(update_fields=['delegation', 'updated_at'])
        response = self.client.get(reverse('organization:api_audit_logs'))
        self.assertEqual(
            [log['id'] for log in response.json()['logs']], [self.foreign_log.pk],
        )

    def test_administrator_retains_global_audit_without_deleted_logs(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('organization:api_audit_logs'))
        identifiers = {log['id'] for log in response.json()['logs']}
        self.assertEqual(identifiers, {
            self.local_log.pk, self.foreign_log.pk,
            self.admin_foreign_log.pk, self.global_log.pk,
        })

    def test_revoked_audit_permission_denies_direct_api_access(self):
        self.permission_role.permissions_data = []
        self.permission_role.save(update_fields=['permissions_data', 'updated_at'])
        self.assertEqual(
            self.client.get(reverse('organization:api_audit_logs')).status_code, 403,
        )

    def test_audit_read_permission_cannot_be_bypassed_by_changing_http_method(self):
        self.permission_role.permissions_data = []
        self.permission_role.save(update_fields=['permissions_data', 'updated_at'])
        endpoint = reverse('organization:api_audit_logs')
        for method in ('post', 'put', 'delete'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(endpoint)
                self.assertEqual(response.status_code, 405)
                self.assertNotIn('logs', response.json())

    def test_missing_inactive_or_deleted_cargo_denies_direct_organization_access(self):
        for state in ('missing', 'inactive', 'deleted'):
            with self.subTest(state=state):
                self.local_position.status = 'Inactivo' if state == 'inactive' else 'Activo'
                self.local_position.deleted_at = timezone.now() if state == 'deleted' else None
                self.local_position.save(update_fields=['status', 'deleted_at', 'updated_at'])
                self.profile.position = None if state == 'missing' else self.local_position
                self.profile.save(update_fields=['position', 'updated_at'])
                self.assertEqual(
                    self.client.get(reverse('organization:api_audit_logs')).status_code, 403,
                )
                self.assertEqual(
                    self.update_position(self.local_position, description='Sin autoridad').status_code,
                    403,
                )

    def test_auditor_dashboard_and_api_use_the_same_territorial_scope(self):
        self.profile.position = Position.objects.get(name='Auditor Municipal')
        self.profile.save(update_fields=['position', 'updated_at'])
        self.permission_role.permissions_data.append('lectura')
        self.permission_role.save(update_fields=['permissions_data', 'updated_at'])
        response = self.client.get(reverse('activities:dashboard_auditor'))
        self.assertEqual(response.status_code, 200)
        rows = response.context['dashboard_audit_rows']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['table'], 'actividad')
        self.assertEqual(rows[0]['record_id'], str(self.local_activity.pk))
        self.assertEqual(response.context['dashboard_work_kpis'][0]['value'], 1)

    def test_position_counts_respect_delegation_and_admin_exception(self):
        self.permission_role.permissions_data.append('cargos.view')
        self.permission_role.save(update_fields=['permissions_data', 'updated_at'])
        endpoint = reverse('organization:api_positions')
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        local = {item['id']: item['users_count'] for item in response.json()['positions']}
        self.assertEqual(local[self.local_position.pk], 1)
        self.assertEqual(local[self.shared_position.pk], 0)
        self.client.force_login(self.admin)
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        global_counts = {item['id']: item['users_count'] for item in response.json()['positions']}
        self.assertEqual(global_counts[self.shared_position.pk], 1)

