import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organization.models import Delegation, Role, UserProfile
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

    def test_session_role_does_not_grant_admin_dashboard(self):
        session = self.client.session
        session['user_role'] = 'Administrador General'
        session.save()
        self.assertNotEqual(self.client.get(reverse('activities:dashboard_admin')).status_code, 200)

    def test_readonly_role_landing_is_distinct_and_restricted(self):
        for role_name, route in (
            ('Coordinador del Sistema', 'dashboard_coordinador'),
            ('Delegado Municipal', 'dashboard_delegado'),
            ('Usuario de Consulta', 'dashboard_consulta'),
        ):
            self.profile.roles.clear()
            role, _ = Role.objects.get_or_create(name=role_name)
            self.profile.roles.add(role)
            response = self.client.get(reverse('activities:' + route))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Módulos habilitados para')
            for other in {'dashboard_coordinador', 'dashboard_delegado', 'dashboard_consulta'} - {route}:
                self.assertNotEqual(self.client.get(reverse('activities:' + other)).status_code, 200)

    def test_role_modules_are_distinct_and_direct_urls_are_restricted(self):
        cases = (
            ('Coordinador del Sistema', 'dashboard_coordinador', 'metas', 'equipo'),
            ('Delegado Municipal', 'dashboard_delegado', 'equipo', 'metas'),
            ('Usuario de Consulta', 'dashboard_consulta', 'indicadores', 'equipo'),
        )
        for role_name, route, allowed_module, forbidden_module in cases:
            self.profile.roles.clear()
            role, _ = Role.objects.get_or_create(name=role_name)
            if not role.permissions_data:
                role.permissions_data = ['lectura']
                role.save(update_fields=['permissions_data', 'updated_at'])
            self.profile.roles.add(role)
            url = reverse('activities:' + route)
            self.assertEqual(self.client.get(f'{url}?module={allowed_module}').status_code, 200)
            self.assertEqual(self.client.get(f'{url}?module={forbidden_module}').status_code, 404)

    def test_operational_dashboards_use_profile_identity_without_mock_records(self):
        for role_name, route in (
            ('Gestor Territorial', 'dashboard_gestor'),
            ('Verificador Técnico', 'dashboard_verificador'),
        ):
            self.profile.roles.clear()
            role, _ = Role.objects.get_or_create(name=role_name)
            self.profile.roles.add(role)
            response = self.client.get(reverse('activities:' + route))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Usuario Rol')
            self.assertContains(response, 'Centro de prueba')
            self.assertNotContains(response, 'Panel demostrativo')
            self.assertNotContains(response, 'Kevin Encina')
            self.assertNotContains(response, 'ACT-2026-0839')

    def test_admin_dashboard_get_does_not_seed_activities(self):
        role, _ = Role.objects.get_or_create(name='Administrador General')
        self.profile.roles.add(role)
        before = Activity.objects.count()
        response = self.client.get(reverse('activities:dashboard_admin'))
        self.assertContains(response, 'Usuario Rol')
        self.assertContains(response, 'Administrador General')
        self.assertNotContains(response, 'Panel demostrativo')
        self.assertContains(response, 'id="mapaDelegacionesReal"')
        self.assertEqual(Activity.objects.count(), before)

    def test_coordinator_and_delegate_aliases_route_to_their_own_landing(self):
        for role_name, route in (
            ('Coordinador', 'dashboard_coordinador'),
            ('Coordinador del Sistema', 'dashboard_coordinador'),
            ('Delegado', 'dashboard_delegado'),
            ('Delegado Municipal', 'dashboard_delegado'),
        ):
            self.profile.roles.clear()
            role, _ = Role.objects.get_or_create(name=role_name)
            self.profile.roles.add(role)
            self.assertRedirects(
                self.client.get(reverse('activities:dashboard')),
                reverse('activities:' + route),
                fetch_redirect_response=False,
            )
            self.assertEqual(self.client.get(reverse('activities:' + route)).status_code, 200)


class RolePermissionToggleApiTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username='admin-role-toggle', password='test-pass')
        self.admin_profile = UserProfile.objects.create(
            user=self.admin, rut='11223344-5', full_name='Admin de prueba',
            email='admin-role-toggle@example.test',
        )
        self.admin_role, _ = Role.objects.get_or_create(
            name='Administrador General', defaults={'is_system': True}
        )
        self.admin_profile.roles.add(self.admin_role)
        self.target_role, _ = Role.objects.get_or_create(
            name='Coordinador', defaults={'permissions_data': ['lectura', 'atenciones.view']}
        )
        self.target_role.permissions_data = ['lectura', 'atenciones.view']
        self.target_role.save(update_fields=['permissions_data', 'updated_at'])
        self.client.force_login(self.admin)
        self.url = '/api/roles/toggle-permiso/'

    def toggle(self, permission, enabled):
        import json
        return self.client.post(
            self.url,
            data=json.dumps({'rol_name': self.target_role.name, 'permiso': permission, 'enabled': enabled}),
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
        self.assertEqual(self.target_role.permissions_data, ['lectura', 'atenciones.view'])

        regular = get_user_model().objects.create_user(username='regular-role-toggle', password='test-pass')
        UserProfile.objects.create(
            user=regular, rut='22334455-6', full_name='Usuario de prueba',
            email='regular-role-toggle@example.test',
        )
        self.client.force_login(regular)
        denied = self.toggle('lectura', False)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(self.target_role.permissions_data, ['lectura', 'atenciones.view'])


class ActivityCreatePageTests(TestCase):
    def setUp(self):
        from metrics.models import AttentionType, SubAttention

        self.delegation = Delegation.objects.create(name='Centro', scope='Centro', status='Activo')
        self.other_delegation = Delegation.objects.create(name='Sur', scope='Sur', status='Activo')
        self.user = get_user_model().objects.create_user(username='gestor-form', password='test-pass')
        self.profile = UserProfile.objects.create(
            user=self.user, rut='13579246-0', full_name='Gestor de Formulario',
            email='gestor-form@example.test', delegation=self.delegation,
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

    def test_form_shows_active_catalogs_and_only_assigned_delegation(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Registrar una atención')
        self.assertContains(response, 'Registro Social de Hogares')
        self.assertContains(response, 'value="{}"'.format(self.delegation.pk))
        self.assertNotContains(response, 'value="{}"'.format(self.other_delegation.pk))
        dashboard = self.client.get(reverse('activities:dashboard_gestor'))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, 'id="caseAttentionType"')
        self.assertContains(dashboard, 'Registro Social de Hogares')
        from django.utils import timezone
        expected_date = timezone.localdate().isoformat()
        self.assertContains(dashboard, f'value="{expected_date}" max="{expected_date}"')

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
