import json
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organization.models import Delegation, Position, Role, UserProfile
from core.models import AuditLog
from .models import Activity, ServiceCatalog, Validation, Vecino


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
            if position_name == 'Delegado Municipal':
                self.assertContains(response, 'Panel de tu delegación')
                self.assertContains(response, 'Atenciones de mi delegación')
                self.assertContains(response, 'Nueva atención')
            elif position_name == 'Asistente Social':
                self.assertContains(response, 'Panel de Gestión Social Territorial')
                self.assertContains(response, 'Casos Sociales Únicos')
            else:
                self.assertContains(response, 'Accesos de ' + position_name)
                self.assertContains(response, 'Información conectada al sistema')
            self.assertContains(response, 'Usuario Rol')
            self.assertContains(response, 'Centro de prueba')
            for other in {'dashboard_coordinador', 'dashboard_delegado', 'dashboard_asistente'} - {route}:
                self.assertNotEqual(self.client.get(reverse('activities:' + other)).status_code, 200)

    def test_coordinator_panel_reads_live_data_with_territorial_scope(self):
        for position_name, route in (('Coordinador del Sistema', 'dashboard_coordinador'),):
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
            self.assertContains(response, 'Información conectada al sistema')

    def test_delegado_dashboard_filters_only_assigned_delegation_and_obeys_role(self):
        self.set_position('Delegado Municipal')
        role = Role.objects.create(name='Operación local', permissions_data=['lectura', 'edicion'])
        self.profile.roles.add(role)
        other_delegation = Delegation.objects.create(name='Otra sede', scope='Sur')
        own = Activity.objects.create(
            activity_code='ACT-LOCAL-1', activity_date='2026-01-02', contact_name='Vecina Local',
            problem_description='Alumbrado de prueba', executed_action='Recepción',
            delegation=self.delegation, validation_status='Pending',
        )
        Activity.objects.create(
            activity_code='ACT-AJENA-1', activity_date='2026-01-02', contact_name='Vecina Ajena',
            problem_description='Otro asunto', executed_action='Recepción',
            delegation=other_delegation,
        )
        url = reverse('activities:dashboard_delegado')
        response = self.client.get(url)
        self.assertContains(response, own.activity_code)
        self.assertNotContains(response, 'ACT-AJENA-1')
        self.assertContains(response, 'Nueva atención')
        self.assertNotContains(response, 'Dar de baja')
        self.assertEqual(self.client.get(f'{url}?q=alumbrado&estado=followup').context['page'].paginator.count, 1)
        self.assertEqual(self.client.get(f'{url}?q=sin-coincidencia').context['page'].paginator.count, 0)
        role.permissions_data = ['lectura', 'cierre']
        role.save(update_fields=['permissions_data', 'updated_at'])
        response = self.client.get(url)
        self.assertNotContains(response, 'Nueva atención')
        self.assertContains(response, 'Dar de baja')
        role.permissions_data = []
        role.save(update_fields=['permissions_data', 'updated_at'])
        response = self.client.get(url)
        self.assertContains(response, 'Tu rol no tiene accesos habilitados')
        self.assertNotContains(response, own.activity_code)

    def test_delegado_attention_crud_updates_dashboard_and_paginates(self):
        from metrics.models import AttentionType, SubAttention
        self.set_position('Delegado Municipal')
        role = Role.objects.create(name='Delegado con cierre', permissions_data=['lectura', 'edicion', 'cierre'])
        self.profile.roles.add(role)
        attention_type = AttentionType.objects.create(code='DEL-T-1', name='Atención vecinal')
        subattention = SubAttention.objects.create(code='DEL-S-1', name='Orientación', attention_type=attention_type)
        api = reverse('activities:api_atenciones')
        payload = {
            'delegation': self.delegation.pk, 'contact_name': 'Vecino de prueba',
            'activity_date': '2026-01-02', 'problem_description': 'Consulta de alumbrado',
            'executed_action': 'Se registró la solicitud',
            'attention_type_id': attention_type.pk, 'subattention_id': subattention.pk,
            'is_collective_agenda': False,
        }
        response = self.client.post(api, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        pk = response.json()['id']
        dashboard = reverse('activities:dashboard_delegado')
        self.assertContains(self.client.get(dashboard), 'Consulta de alumbrado')
        detail = reverse('activities:api_atencion_detail', args=[pk])
        self.assertEqual(self.client.put(detail, json.dumps({'problem_description': 'Consulta editada'}), content_type='application/json').status_code, 200)
        self.assertContains(self.client.get(dashboard), 'Consulta editada')
        for index in range(9):
            Activity.objects.create(
                activity_code=f'DEL-PAGE-{index}', activity_date='2026-01-01',
                contact_name='Vecino', problem_description=f'Caso {index}',
                executed_action='Registro', delegation=self.delegation,
            )
        first = self.client.get(dashboard)
        second = self.client.get(f'{dashboard}?page=2')
        self.assertEqual(len(first.context['page']), 8)
        self.assertEqual(len(second.context['page']), 2)
        self.assertEqual(self.client.delete(detail).status_code, 200)
        self.assertNotContains(self.client.get(dashboard), 'Consulta editada')

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
                self.assertContains(response, 'Acceso según permisos vigentes')
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

    def test_admin_sections_and_report_tabs_have_reloadable_urls(self):
        self.set_position('Administrador General')
        role, _ = Role.objects.get_or_create(name='Administrador')
        self.profile.roles.add(role)
        for section in ('delegaciones', 'cargos', 'usuarios', 'roles', 'metas',
                        'tipo-atencion', 'sub-atencion', 'atenciones', 'tipo-gestion',
                        'vecinos', 'solicitudes-sociales', 'reportes'):
            with self.subTest(section=section):
                url = reverse('activities:dashboard_admin_section', args=[section])
                self.assertEqual(self.client.get(url).status_code, 200)
        for tab in ('general', '1vs1', 'multi'):
            with self.subTest(tab=tab):
                url = reverse('activities:dashboard_admin_report', args=[tab])
                self.assertEqual(self.client.get(url).status_code, 200)
        base = reverse('activities:dashboard_admin')
        self.assertContains(self.client.get(base), f'data-admin-base="{base}"')
        self.assertEqual(self.client.get('/activities/dashboard/admin/desconocido/').status_code, 404)
        self.assertEqual(self.client.get('/activities/dashboard/admin/reportes/desconocido/').status_code, 404)

    def test_admin_section_requires_admin_position(self):
        self.set_position('Delegado Municipal')
        role, _ = Role.objects.get_or_create(name='Administrador')
        self.profile.roles.add(role)
        url = reverse('activities:dashboard_admin_section', args=['usuarios'])
        self.assertNotEqual(self.client.get(url).status_code, 200)

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

    def test_asistente_social_operational_dashboard(self):
        self.set_position('Asistente Social')
        self.profile.roles.clear()
        role = Role.objects.get(name='Asistente Social')
        self.profile.roles.add(role)
        response = self.client.get(reverse('activities:dashboard_asistente'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Panel de Gestión Social Territorial')
        self.assertContains(response, 'Semáforo SGR')
        self.assertContains(response, 'RN-012')
        self.assertContains(response, 'Evaluación y Diagnóstico')
        self.assertContains(response, 'Gestión de Beneficios')
        self.assertContains(response, 'Informes Sociales')
        self.assertContains(response, 'Atención de Emergencias')
        self.assertContains(response, 'Articulación de Redes')


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

    def test_create_form_keeps_catalogs_and_dashboard_is_database_connected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Registrar una atención')
        self.assertContains(response, 'Registro Social de Hogares')
        self.assertContains(response, 'name="delegation" value="{}"'.format(self.delegation.pk))
        self.assertNotContains(response, 'name="delegation" value="{}"'.format(self.other_delegation.pk))
        dashboard = self.client.get(reverse('activities:dashboard_gestor'))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, 'Mis atenciones')
        self.assertContains(dashboard, 'Registrar atención')
        self.assertNotContains(dashboard, 'Disponible más adelante')
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


class VerifierWorkflowTests(TestCase):
    def setUp(self):
        self.delegation = Delegation.objects.create(name='Sede de Verificación', scope='Sector Norte')
        self.other_delegation = Delegation.objects.create(name='Sede Restringida', scope='Sector Sur')
        self.verifier = get_user_model().objects.create_user(username='verificador-prueba', password='Safe!Verifier2026')
        self.verifier_position, _ = Position.objects.get_or_create(name='Verificador Técnico')
        self.verifier_profile = UserProfile.objects.create(
            user=self.verifier, rut='16.111.111-2', full_name='Verificador de Prueba',
            email='verificador-prueba@example.test', delegation=self.delegation,
            position=self.verifier_position,
        )
        self.role = Role.objects.get(name='Verificador Técnico')
        self.verifier_profile.roles.add(self.role)
        self.author = get_user_model().objects.create_user(username='gestor-autor', password='Safe!Author2026')
        self.author_profile = UserProfile.objects.create(
            user=self.author, rut='16.222.222-0', full_name='Gestor Autor',
            email='gestor-autor@example.test', delegation=self.delegation,
            position=Position.objects.get(name='Gestor Territorial'),
        )
        self.client.force_login(self.verifier)
        self.own_activity = Activity.objects.create(
            activity_code='ACT-VERIFY-OWN', activity_date='2026-10-20',
            contact_name='Persona Solicitante', problem_description='Solicitud vecinal de prueba',
            executed_action='Se registró la recepción del requerimiento.',
            delegation=self.delegation, user=self.author, validation_status='Pending',
        )
        self.other_activity = Activity.objects.create(
            activity_code='ACT-VERIFY-OTHER', activity_date='2026-10-20',
            contact_name='Persona de otra sede', problem_description='Registro fuera de jurisdicción',
            executed_action='No debe aparecer en este panel.',
            delegation=self.other_delegation, user=self.author, validation_status='Pending',
        )

    def validate(self, activity, payload):
        return self.client.post(
            reverse('activities:api_validar_atencion', args=[activity.pk]),
            data=json.dumps(payload), content_type='application/json',
        )

    def test_verifier_dashboard_lists_only_pending_work_in_assigned_delegation(self):
        response = self.client.get(reverse('activities:dashboard_verificador'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.own_activity.activity_code)
        self.assertNotContains(response, self.other_activity.activity_code)
        self.assertContains(response, 'Cola de validación')
        self.assertContains(response, 'Resolver')

    def test_correction_decision_requires_reason_and_persists_validation_and_audit(self):
        missing_note = self.validate(self.own_activity, {'decision': 'Requires correction', 'observations': ''})
        self.assertEqual(missing_note.status_code, 400)

        response = self.validate(self.own_activity, {
            'decision': 'Requires correction', 'observations': 'Adjuntar respaldo de la visita realizada.',
        })
        self.assertEqual(response.status_code, 200, response.content)
        self.own_activity.refresh_from_db()
        self.assertEqual(self.own_activity.validation_status, 'Requires correction')
        validation = Validation.objects.get(activity=self.own_activity)
        self.assertEqual(validation.verifier_id, self.verifier.pk)
        self.assertEqual(validation.decision, 'Requires correction')
        self.assertTrue(AuditLog.objects.filter(
            affected_table='actividad', affected_record_id=str(self.own_activity.pk), action='VALIDATE',
        ).exists())

    def test_verifier_cannot_decide_own_or_other_delegation_activity(self):
        self.own_activity.user = self.verifier
        self.own_activity.save(update_fields=['user', 'updated_at'])
        own_denied = self.validate(self.own_activity, {'decision': 'Approved', 'observations': ''})
        self.assertEqual(own_denied.status_code, 403)
        outside_denied = self.validate(self.other_activity, {'decision': 'Approved', 'observations': ''})
        self.assertEqual(outside_denied.status_code, 404)

    def test_decision_is_one_way_after_resolution_and_permission_is_required(self):
        approved = self.validate(self.own_activity, {'decision': 'Approved', 'observations': 'Antecedentes revisados.'})
        self.assertEqual(approved.status_code, 200)
        repeated = self.validate(self.own_activity, {'decision': 'Rejected', 'observations': 'Rechazo por inconsistencia.'})
        self.assertEqual(repeated.status_code, 409)

        permission = self.role.permission_definitions.get(code='validar_evidencia')
        self.role.permission_definitions.remove(permission)
        self.role.permissions_data = [code for code in self.role.permissions_data if code != 'validar_evidencia']
        self.role.save(update_fields=['permissions_data', 'updated_at'])
        another_activity = Activity.objects.create(
            activity_code='ACT-VERIFY-PERMISSION', activity_date='2026-10-21',
            contact_name='Otra persona', problem_description='Caso de permiso',
            executed_action='Acción registrada.', delegation=self.delegation,
            user=self.author, validation_status='Pending',
        )
        denied = self.validate(another_activity, {'decision': 'Approved', 'observations': ''})
        self.assertEqual(denied.status_code, 403)


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


class VecinoApiValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='admin-vecinos', password='test-pass')
        self.profile = UserProfile.objects.create(
            user=self.user, rut='11223344-5', full_name='Admin Vecinos', email='admin-vecinos@example.test',
        )
        role, _ = Role.objects.get_or_create(name='Administrador', defaults={'is_system': True})
        self.profile.roles.add(role)
        self.client.force_login(self.user)
        self.url = reverse('activities:api_vecinos')
        self.payload = {
            'nombre': 'Vecino de prueba', 'rut': '12.345.678-5', 'email': 'vecino@example.test',
            'direccion': 'Calle de prueba 123', 'telefono': '', 'territorio': 'Centro', 'estado': 'Activo',
        }

    def post(self, payload=None):
        return self.client.post(self.url, json.dumps(payload or self.payload), content_type='application/json')

    def put(self, vecino, payload):
        return self.client.put(f'{self.url}{vecino.pk}/', json.dumps(payload), content_type='application/json')

    def test_existing_legacy_invalid_rut_can_be_edited_if_unchanged(self):
        vecino = Vecino.objects.create(nombre='Vecino antiguo', rut='16.241.879-2', direccion='Calle 1')
        payload = {'nombre': 'Vecino antiguo actualizado', 'rut': vecino.rut, 'direccion': 'Calle 2'}
        response = self.put(vecino, payload)
        self.assertEqual(response.status_code, 200)
        vecino.refresh_from_db()
        self.assertEqual(vecino.nombre, payload['nombre'])
        self.assertEqual(vecino.rut, '16.241.879-2')

    def test_changing_rut_requires_valid_check_digit(self):
        vecino = Vecino.objects.create(nombre='Vecino antiguo', rut='16.241.879-2', direccion='Calle 1')
        response = self.put(vecino, {'nombre': vecino.nombre, 'rut': '12.345.678-9', 'direccion': vecino.direccion})
        self.assertEqual(response.status_code, 400)
        vecino.refresh_from_db()
        self.assertEqual(vecino.rut, '16.241.879-2')

    def test_rut_and_email_are_unique_case_insensitively_and_across_formats(self):
        first = self.post()
        self.assertEqual(first.status_code, 200)
        existing = Vecino.objects.get(rut='12.345.678-5')
        duplicate_rut = dict(self.payload, email='otro@example.test', rut='123456785')
        self.assertEqual(self.post(duplicate_rut).status_code, 400)
        duplicate_email = dict(self.payload, nombre='Otra persona', rut='11.111.111-1', email='VECINO@EXAMPLE.TEST')
        self.assertEqual(self.post(duplicate_email).status_code, 400)
        self.assertEqual(Vecino.objects.count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.email, 'vecino@example.test')

    def test_asistente_social_delegation_scoping_strictly_enforced(self):
        del_sur = Delegation.objects.create(name='Delegación Sur Test', scope='Sur')
        del_norte = Delegation.objects.create(name='Delegación Norte Test', scope='Norte')
        pos_asistente, _ = Position.objects.get_or_create(name='Asistente Social')
        user_asistente = get_user_model().objects.create_user(username='asistente-eval', password='password')
        prof_asistente = UserProfile.objects.create(
            user=user_asistente, rut='19.822.450-3', full_name='Asistente Social Test',
            email='asistente@test.com', delegation=del_sur, position=pos_asistente, status='Activo'
        )
        role = Role.objects.create(name='Rol Asistente Test', permissions_data=['lectura', 'edicion', 'cierre'])
        prof_asistente.roles.add(role)
        self.client.force_login(user_asistente)

        vecino_sur = Vecino.objects.create(nombre='Vecino Sur', rut='14.892.314-0', territorio='Delegación Sur Test', direccion='Calle Sur')
        vecino_norte = Vecino.objects.create(nombre='Vecino Norte', rut='16.241.879-2', territorio='Delegación Norte Test', direccion='Calle Norte')

        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        nombres = [v['nombre'] for v in resp.json()['vecinos']]
        # Solo debe ver vecinos de su propia delegación
        self.assertIn('Vecino Sur', nombres)
        self.assertNotIn('Vecino Norte', nombres)

        # Al registrar un nuevo vecino, queda estrictamente ligado a su delegación asignada
        payload = {
            'nombre': 'Nuevo Vecino Sur',
            'rut': '18.390.412-4',
            'email': 'sur@test.com',
            'direccion': 'Avda Sur 100',
            'telefono': '+56911223344',
            'territorio': 'Delegación Sur Test',
            'estado': 'Activo'
        }
        create_resp = self.client.post(self.url, json.dumps(payload), content_type='application/json')
        self.assertEqual(create_resp.status_code, 200)
        self.assertTrue(Vecino.objects.filter(rut='18.390.412-4', territorio='Delegación Sur Test').exists())

        # No debe poder acceder ni editar datos de otra delegación
        detail_norte = self.client.get(reverse('activities:api_vecino_detail', args=[vecino_norte.pk]))
        self.assertEqual(detail_norte.status_code, 404)
