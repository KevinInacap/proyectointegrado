import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organization.models import Delegation, Position, Role, UserProfile
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

    def test_type_subtype_ids_must_exist_be_active_and_belong_together(self):
        from metrics.models import AttentionType, SubAttention
        first = AttentionType.objects.create(code='AT-TEST-1', name='Tipo uno')
        second = AttentionType.objects.create(code='AT-TEST-2', name='Tipo dos')
        subtype = SubAttention.objects.create(
            code='SA-TEST-1', name='Subtipo uno', attention_type=first
        )
        typed = dict(self.payload, attention_type_id=second.pk, subattention_id=subtype.pk)
        self.assertEqual(self.post(typed).status_code, 400)
        typed['attention_type_id'] = first.pk
        subtype.status = 'Inactivo'
        subtype.save()
        self.assertEqual(self.post(typed).status_code, 400)
        subtype.status = 'Activo'
        subtype.save()
        self.assertEqual(
            self.post(typed).status_code,
            201 if {'attention_type', 'subattention'}.issubset(
                {field.name for field in Activity._meta.fields}
            ) else 503,
        )

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

    def set_position(self, name):
        self.profile.position, _ = Position.objects.get_or_create(name=name)
        self.profile.save(update_fields=['position', 'updated_at'])

    def test_session_role_does_not_grant_admin_dashboard(self):
        session = self.client.session
        session['user_role'] = 'Administrador General'
        session.save()
        self.assertNotEqual(self.client.get(reverse('activities:dashboard_admin')).status_code, 200)

    def test_cargo_dashboard_is_simple_personalized_and_route_restricted(self):
        for position_name, role_name, route in (
            ('Coordinador del Sistema', 'Gestor de prueba', 'dashboard_coordinador'),
            ('Delegado Municipal', 'Gestor de prueba', 'dashboard_delegado'),
            ('Asistente Social', 'Gestor de prueba', 'dashboard_asistente'),
        ):
            self.set_position(position_name)
            self.profile.roles.clear()
            role, _ = Role.objects.get_or_create(name=role_name)
            if not role.permissions_data:
                role.permissions_data = ['lectura', 'edicion']
                role.save(update_fields=['permissions_data', 'updated_at'])
            self.profile.roles.add(role)
            response = self.client.get(reverse('activities:' + route))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Accesos de ' + position_name)
            self.assertContains(response, 'Usuario Rol')
            self.assertContains(response, 'Centro de prueba')
            self.assertContains(response, 'Disponible más adelante')
            self.assertNotContains(response, 'Registrar atención')
            for other in {'dashboard_coordinador', 'dashboard_delegado', 'dashboard_asistente'} - {route}:
                self.assertNotEqual(self.client.get(reverse('activities:' + other)).status_code, 200)

    def test_cargo_panels_are_presentational_not_operational(self):
        for position_name, route in (
            ('Coordinador del Sistema', 'dashboard_coordinador'),
            ('Delegado Municipal', 'dashboard_delegado'),
        ):
            self.set_position(position_name)
            self.profile.roles.clear()
            role, _ = Role.objects.get_or_create(name=position_name)
            if not role.permissions_data:
                role.permissions_data = ['lectura']
                role.save(update_fields=['permissions_data', 'updated_at'])
            self.profile.roles.add(role)
            url = reverse('activities:' + route)
            response = self.client.get(f'{url}?module=atenciones&q=prueba')
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'name="q"')
            self.assertNotContains(response, '?module=')

    def test_operational_dashboards_use_profile_identity_without_mock_records(self):
        for role_name, route in (
            ('Gestor Territorial', 'dashboard_gestor'),
            ('Verificador Técnico', 'dashboard_verificador'),
        ):
            self.set_position(role_name)
            self.profile.roles.clear()
            role, _ = Role.objects.get_or_create(name=role_name)
            self.profile.roles.add(role)
            response = self.client.get(reverse('activities:' + route))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Usuario Rol')
            self.assertContains(response, 'Centro de prueba')
            self.assertContains(response, 'Faro Monumental de La Serena')
            if any(code in role.permissions_data for code in ('lectura', 'edicion', 'derivacion', 'cierre')):
                self.assertContains(response, 'Disponible más adelante')
            else:
                self.assertContains(response, 'Tu rol no tiene accesos habilitados')
            self.assertNotContains(response, 'Panel demostrativo')
            self.assertNotContains(response, 'Kevin Encina')
            self.assertNotContains(response, 'ACT-2026-0839')

    def test_admin_dashboard_get_does_not_seed_activities(self):
        self.set_position('Administrador General')
        role, _ = Role.objects.get_or_create(name='Administrador')
        self.profile.roles.add(role)
        before = Activity.objects.count()
        response = self.client.get(reverse('activities:dashboard_admin'))
        self.assertContains(response, 'Usuario Rol')
        self.assertContains(response, 'Administrador General')
        self.assertNotContains(response, 'Panel demostrativo')
        self.assertContains(response, 'id="mapaDelegacionesReal"')
        self.assertEqual(Activity.objects.count(), before)

    def test_position_selects_dashboard_independently_of_role(self):
        for position_name, role_name, route in (
            ('Coordinador del Sistema', 'Verificador Técnico', 'dashboard_coordinador'),
            ('Delegado Municipal', 'Usuario de Consulta', 'dashboard_delegado'),
            ('Auditor Municipal', 'Gestor Territorial', 'dashboard_auditor'),
        ):
            self.set_position(position_name)
            self.profile.roles.clear()
            role, _ = Role.objects.get_or_create(name=role_name)
            self.profile.roles.add(role)
            self.assertRedirects(
                self.client.get(reverse('activities:dashboard')),
                reverse('activities:' + route),
                fetch_redirect_response=False,
            )
            self.assertEqual(self.client.get(reverse('activities:' + route)).status_code, 200)

    def test_every_builtin_position_opens_its_assigned_dashboard(self):
        routes = {
            'Administrador General': 'dashboard_admin',
            'Asistente Social': 'dashboard_asistente',
            'Auditor Municipal': 'dashboard_auditor',
            'Coordinador del Sistema': 'dashboard_coordinador',
            'Delegado Municipal': 'dashboard_delegado',
            'Gestor Territorial': 'dashboard_gestor',
            'Verificador Técnico': 'dashboard_verificador',
        }
        for position_name, route in routes.items():
            with self.subTest(position=position_name):
                self.set_position(position_name)
                self.profile.roles.clear()
                role_name = 'Administrador' if position_name == 'Administrador General' else 'Perfil de prueba'
                role, _ = Role.objects.get_or_create(name=role_name)
                self.profile.roles.add(role)
                response = self.client.get(reverse('activities:dashboard'), follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.redirect_chain[-1][0], reverse('activities:' + route))
                if position_name != 'Administrador General':
                    self.assertContains(response, position_name)
                    self.assertContains(response, 'Tu rol no tiene accesos habilitados')

    def test_admin_cargo_selects_panel_without_granting_admin_apis(self):
        self.set_position('Administrador General')
        role, _ = Role.objects.get_or_create(name='Verificador Técnico', defaults={'permissions_data': ['lectura']})
        role.permissions_data = ['lectura']
        role.save(update_fields=['permissions_data', 'updated_at'])
        self.profile.roles.add(role)
        self.assertEqual(self.client.get(reverse('activities:dashboard')).url, reverse('activities:dashboard_admin'))
        self.assertEqual(self.client.get('/organization/users/').status_code, 403)

    def test_administrator_role_grants_management_without_changing_cargo_panel(self):
        from django.urls import reverse

        other = Activity.objects.create(
            activity_code='GLOBAL-ADMIN-1', activity_date='2026-01-02',
            problem_description='Registro de otra delegación', executed_action='Prueba',
            delegation=Delegation.objects.create(name='Compañías de prueba', scope='Norte'),
        )
        self.set_position('Delegado Municipal')
        self.profile.roles.clear()
        self.profile.roles.add(Role.objects.get(name='Administrador'))

        self.assertRedirects(
            self.client.get(reverse('activities:dashboard')),
            reverse('activities:dashboard_delegado'),
            fetch_redirect_response=False,
        )
        self.assertNotEqual(self.client.get(reverse('activities:dashboard_admin')).status_code, 200)
        self.assertEqual(self.client.get('/organization/users/').status_code, 200)
        self.assertIn(
            other.activity_code,
            [item['activity_code'] for item in self.client.get(reverse('activities:api_atenciones')).json()['atenciones']],
        )

    def test_new_custom_cargo_gets_a_role_limited_dashboard(self):
        self.set_position('Cargo Especializado')
        role = Role.objects.create(name='Consulta de usuarios', permissions_data=['usuarios.view'])
        self.profile.roles.add(role)
        self.assertEqual(self.client.get(reverse('activities:dashboard')).url, reverse('activities:dashboard_cargo'))
        response = self.client.get(reverse('activities:dashboard_cargo'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cargo Especializado')
        self.assertContains(response, 'Panel de trabajo')
        self.assertContains(response, 'Tu rol no tiene accesos habilitados')
        self.assertNotContains(response, 'Gestión de Usuarios y Personal')
        self.assertNotContains(response, 'Registrar atención')


class RolePermissionToggleApiTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username='admin-role-toggle', password='test-pass')
        self.admin_profile = UserProfile.objects.create(
            user=self.admin, rut='11223344-5', full_name='Admin de prueba',
            email='admin-role-toggle@example.test',
        )
        self.admin_role, _ = Role.objects.get_or_create(
            name='Administrador', defaults={'is_system': True}
        )
        self.admin_profile.roles.add(self.admin_role)
        self.target_role, _ = Role.objects.get_or_create(
            name='Coordinador', defaults={'permissions_data': ['lectura', 'atenciones.view']}
        )
        from organization.access import set_role_permission_codes
        set_role_permission_codes(self.target_role, ['lectura', 'atenciones.view'])
        self.client.force_login(self.admin)
        self.url = '/api/roles/toggle-permiso/'

    def toggle(self, permission, enabled, role_name=None):
        import json
        return self.client.post(
            self.url,
            data=json.dumps({'rol_name': role_name or self.target_role.name, 'permiso': permission, 'enabled': enabled}),
            content_type='application/json',
        )

    def test_permission_switch_persists_and_audits_both_states(self):
        from core.models import AuditLog

        disabled = self.toggle('lectura', False)
        self.assertEqual(disabled.status_code, 200)
        self.target_role.refresh_from_db()
        self.assertEqual(self.target_role.permissions_data, ['atenciones.view'])

        enabled = self.toggle('cierre', True)
        self.assertEqual(enabled.status_code, 200)
        self.target_role.refresh_from_db()
        self.assertEqual(self.target_role.permissions_data, ['atenciones.view', 'cierre'])
        self.assertEqual(AuditLog.objects.filter(affected_table='rol', affected_record_id=str(self.target_role.pk)).count(), 2)

    def test_switch_requires_admin_and_boolean_state(self):
        import json

        response = self.client.post(
            self.url,
            data=json.dumps({'rol_name': 'Coordinador', 'permiso': 'lectura', 'enabled': 'false'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.target_role.permissions_data, ['atenciones.view', 'lectura'])

    def test_administrator_role_is_full_and_its_switches_cannot_claim_to_revoke_access(self):
        from organization.access import role_permission_codes
        from organization.views import _all_system_perm_codes

        expected = set(_all_system_perm_codes())
        self.assertTrue(expected.issubset(role_permission_codes(self.admin_role)))
        self.assertEqual(self.toggle('lectura', False, role_name=self.admin_role.name).status_code, 403)
        self.admin_role.refresh_from_db()
        self.assertTrue(expected.issubset(role_permission_codes(self.admin_role)))

    def test_role_grants_are_stored_in_both_the_json_compatibility_field_and_relation(self):
        from organization.models import PermissionDefinition
        from organization.access import set_role_permission_codes

        permission = PermissionDefinition.objects.get(code='atenciones.view')
        set_role_permission_codes(self.target_role, ['atenciones.view', 'cargos.view'])
        self.assertEqual(set(self.target_role.permissions_data), {'atenciones.view', 'cargos.view'})
        self.assertEqual(
            set(self.target_role.permission_definitions.values_list('code', flat=True)),
            {'atenciones.view', 'cargos.view'},
        )
        self.assertTrue(permission.is_system)

        regular = get_user_model().objects.create_user(username='regular-role-toggle', password='test-pass')
        UserProfile.objects.create(
            user=regular, rut='22334455-6', full_name='Usuario de prueba',
            email='regular-role-toggle@example.test',
        )
        self.client.force_login(regular)
        denied = self.toggle('lectura', False)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(self.target_role.permissions_data, ['atenciones.view', 'cargos.view'])


class ActivityCreatePageTests(TestCase):
    def setUp(self):
        from metrics.models import AttentionType, SubAttention

        self.delegation = Delegation.objects.create(name='Centro', scope='Centro', status='Activo')
        self.other_delegation = Delegation.objects.create(name='Sur', scope='Sur', status='Activo')
        self.user = get_user_model().objects.create_user(username='gestor-form', password='test-pass')
        self.profile = UserProfile.objects.create(
            user=self.user, rut='13579246-0', full_name='Gestor de Formulario',
            email='gestor-form@example.test', delegation=self.delegation,
            position=Position.objects.get_or_create(name='Gestor Territorial')[0],
        )
        role, _ = Role.objects.get_or_create(
            name='Gestor Territorial', defaults={'permissions_data': ['lectura', 'edicion']},
        )
        role.permissions_data = ['lectura', 'edicion']
        role.save(update_fields=['permissions_data', 'updated_at'])
        self.profile.roles.add(role)
        self.kind = AttentionType.objects.create(code='AT-FORM', name='Orientación Social')
        self.sub = SubAttention.objects.create(
            code='SA-FORM', name='Registro Social de Hogares', attention_type=self.kind,
        )
        self.client.force_login(self.user)
        self.url = reverse('activities:activity_create')

    def payload(self, **changes):
        from django.utils import timezone

        data = {
            'contact_name': 'Solicitante de prueba',
            'contact_phone': '+56 9 1234 5678',
            'attention_type_id': str(self.kind.pk),
            'subattention_id': str(self.sub.pk),
            'delegation': str(self.delegation.pk),
            'activity_date': timezone.localdate().isoformat(),
            'problem_description': 'Solicita orientación municipal.',
            'executed_action': 'Se entrega orientación y se registra la atención.',
        }
        data.update(changes)
        return data

    def test_create_form_keeps_catalogs_and_dashboard_stays_presentational(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Registrar una atención')
        self.assertContains(response, 'Registro Social de Hogares')
        self.assertContains(response, 'name="delegation" value="{}"'.format(self.delegation.pk))
        self.assertNotContains(response, 'name="delegation" value="{}"'.format(self.other_delegation.pk))
        dashboard = self.client.get(reverse('activities:dashboard_gestor'))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, 'Trabajo territorial')
        self.assertContains(dashboard, 'Disponible más adelante')
        self.assertNotContains(dashboard, 'id="caseAttentionType"')

    def test_valid_form_persists_type_subtype_responsible_and_delegation(self):
        response = self.client.post(self.url, self.payload())
        self.assertRedirects(response, reverse('activities:dashboard'), fetch_redirect_response=False)
        record = Activity.objects.get()
        self.assertEqual(record.user_id, self.user.pk)
        self.assertEqual(record.delegation_id, self.delegation.pk)
        self.assertEqual(record.attention_type_id, self.kind.pk)
        self.assertEqual(record.subattention_id, self.sub.pk)

    def test_form_rejects_missing_type_subtype_and_other_delegation(self):
        missing_type = self.client.post(self.url, self.payload(attention_type_id=''))
        self.assertEqual(missing_type.status_code, 400)
        self.assertFalse(Activity.objects.exists())
        unauthorized = self.client.post(self.url, self.payload(delegation=str(self.other_delegation.pk)))
        self.assertEqual(unauthorized.status_code, 403)
        self.assertFalse(Activity.objects.exists())


class AttentionSelectionUnitTests(TestCase):
    def test_type_and_subtype_ids_must_match(self):
        from types import SimpleNamespace
        from unittest.mock import Mock, patch
        import metrics.models as metric_models
        from .views import _typed_attention_selection

        attention_type = SimpleNamespace(pk=11, status='Activo')
        valid_sub = SimpleNamespace(pk=22, status='Activo', attention_type_id=11)
        invalid_sub = SimpleNamespace(pk=23, status='Activo', attention_type_id=99)
        type_model = Mock()
        type_model.objects.filter.return_value.first.return_value = attention_type
        sub_model = Mock()
        with patch.object(metric_models, 'AttentionType', type_model, create=True), patch.object(
            metric_models, 'SubAttention', sub_model, create=True
        ):
            sub_model.objects.filter.return_value.first.return_value = valid_sub
            self.assertIsNone(_typed_attention_selection({
                'attention_type_id': 11, 'subattention_id': 22
            })[2])
            sub_model.objects.filter.return_value.first.return_value = invalid_sub
            self.assertIsNotNone(_typed_attention_selection({
                'attention_type_id': 11, 'subattention_id': 23
            })[2])
            self.assertIsNotNone(_typed_attention_selection({
                'attention_type_id': 11
            })[2])
