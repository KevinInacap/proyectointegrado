import json
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from .models import Delegation, Position, Role, UserProfile
from .access import role_name_for_position

from . import views


class CargoRoleNameTests(SimpleTestCase):
    def test_administrative_cargos_map_to_their_distinct_roles(self):
        self.assertEqual(role_name_for_position('Administrador General'), 'Administrador')
        self.assertEqual(role_name_for_position('SuperAdministrador'), 'SuperAdministrador')

    def test_regular_cargo_maps_to_same_named_role(self):
        self.assertEqual(role_name_for_position('Asistente Social'), 'Asistente Social')


class AdminApiIsolatedTests(SimpleTestCase):
    """Pruebas de vistas sin crear ni consultar una base de datos."""

    def setUp(self):
        self.factory = RequestFactory()

    def request(self, method='get', payload=None):
        if method == 'get':
            request = self.factory.get('/organization/roles/')
        else:
            request = getattr(self.factory, method)(
                '/organization/roles/',
                data=json.dumps(payload or {}),
                content_type='application/json',
            )
        request.session = {'user_role': 'Administrador General'}
        return request

    def test_session_role_does_not_authenticate(self):
        request = self.request()
        request.user = SimpleNamespace(is_authenticated=False, is_active=True, is_superuser=False)
        self.assertEqual(views.api_roles_list(request).status_code, 403)

    def test_inactive_account_is_denied(self):
        request = self.request()
        request.user = SimpleNamespace(is_authenticated=True, is_active=False, is_superuser=True)
        self.assertEqual(views.api_roles_list(request).status_code, 403)

    @patch.object(views.UserProfile.objects, 'filter')
    def test_active_account_without_database_role_is_denied(self, profiles):
        profiles.return_value.exists.return_value = False
        request = self.request()
        request.user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=False)
        self.assertEqual(views.api_roles_list(request).status_code, 403)
        self.assertEqual(profiles.call_args.kwargs['status'], 'Activo')

    def test_json_array_is_not_accepted_as_object(self):
        request = self.factory.post('/organization/roles/', data='[]', content_type='application/json')
        self.assertEqual(views._get_request_data(request), {})

    def test_rut_validation_requires_actual_format(self):
        self.assertTrue(views._is_valid_chilean_rut('12.345.678-5'))
        self.assertFalse(views._is_valid_chilean_rut('abc12345678-5'))

    def test_invalid_permission_shape(self):
        self.assertIsNone(views._validated_permissions('usuarios.view'))
        self.assertIsNone(views._validated_permissions([123]))

    def test_unsafe_delegation_url(self):
        self.assertIsNotNone(views._validate_delegation_details({
            'photo_url': '/static/../secret.png',
        }))

    def test_invalid_role_payload_rejected_before_database_write(self):
        request = self.request('post', {'name': 'Prueba', 'permissions': 'usuarios.view'})
        request.user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=True)
        response = views.api_role_create(request)
        self.assertEqual(response.status_code, 400)

    def test_invalid_user_status_rejected_before_database_write(self):
        request = self.request('post', {
            'username': 'prueba', 'full_name': 'Prueba Usuario',
            'email': 'prueba@example.com', 'rut': '12345678-5',
            'password': 'clave-segura', 'status': 'Desconocido',
        })
        request.user = SimpleNamespace(is_authenticated=True, is_active=True, is_superuser=True)
        self.assertEqual(views.api_user_create(request).status_code, 400)


class TerritorialAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.north = Delegation.objects.create(name='Sede Norte RBAC', scope='Norte')
        self.south = Delegation.objects.create(name='Sede Sur RBAC', scope='Sur')
        local_reader = Role.objects.create(
            name='Consulta territorial RBAC',
            permissions_data=['delegaciones.view', 'usuarios.view', 'roles.create'],
        )
        self.assistant = User.objects.create_user(
            username='assistant-rbac', password='Safe!TestPass2026', is_staff=True,
        )
        self.delegate = User.objects.create_user(
            username='delegate-rbac', password='Safe!TestPass2026',
        )
        self.admin = User.objects.create_user(
            username='admin-rbac', password='Safe!TestPass2026',
        )
        for user, rut, position, delegation, base_role in (
            (self.assistant, '12.345.678-5', 'Asistente Social', self.north, 'Asistente Social'),
            (self.delegate, '11.111.111-1', 'Delegado Municipal', self.south, 'Delegado Municipal'),
            (self.admin, '10.000.000-8', 'Administrador General', self.north, 'Administrador'),
        ):
            profile = UserProfile.objects.create(
                user=user, rut=rut, full_name=user.username,
                email=f'{user.username}@example.test', delegation=delegation,
                position=Position.objects.get(name=position),
            )
            profile.roles.add(Role.objects.get(name=base_role))
            if user != self.admin:
                profile.roles.add(local_reader)

    def test_assistant_and_delegate_only_list_their_assigned_delegation(self):
        for user, expected in ((self.assistant, self.north), (self.delegate, self.south)):
            self.client.force_login(user)
            delegations = self.client.get(reverse('organization:api_delegations'))
            self.assertEqual(delegations.status_code, 200)
            self.assertEqual(
                [item['id'] for item in delegations.json()['delegations']], [expected.pk],
            )
            users = self.client.get(reverse('organization:api_users_list'))
            self.assertEqual(users.status_code, 200)
            self.assertEqual(
                {item['delegation_id'] for item in users.json()['users']}, {expected.pk},
            )

    def test_administrator_role_lists_both_delegations_despite_local_assignment(self):
        self.client.force_login(self.admin)
        delegations = self.client.get(reverse('organization:api_delegations'))
        self.assertEqual(delegations.status_code, 200)
        self.assertTrue(
            {self.north.pk, self.south.pk}.issubset(
                {item['id'] for item in delegations.json()['delegations']}
            )
        )
        users = self.client.get(reverse('organization:api_users_list'))
        self.assertEqual(users.status_code, 200)
        self.assertEqual(
            {self.assistant.username, self.delegate.username, self.admin.username},
            {item['username'] for item in users.json()['users']},
        )

    def test_staff_flag_and_assistant_cargo_do_not_grant_admin_only_actions(self):
        self.client.force_login(self.assistant)
        response = self.client.post(
            reverse('organization:api_role_create'),
            data=json.dumps({'name': 'Rol no autorizado', 'permissions': []}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Role.objects.filter(name='Rol no autorizado').exists())


class UserCargoRoleSyncTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username='cargo-role-admin', email='cargo-role-admin@example.test', password='Admin!Safe2026Pass',
        )
        self.client.force_login(self.admin)
        self.delegation = Delegation.objects.create(name='Sede de prueba', scope='Sector de prueba')
        self.assistant_position = Position.objects.get(name='Asistente Social')
        self.delegado_position = Position.objects.get(name='Delegado Municipal')

    def test_every_active_position_has_a_persisted_base_role(self):
        for position in Position.objects.filter(status='Activo', deleted_at__isnull=True):
            base_name = role_name_for_position(position.name)
            self.assertTrue(
                Role.objects.filter(name__iexact=base_name, deleted_at__isnull=True).exists(),
                f"Falta el rol base '{base_name}' para el cargo '{position.name}'.",
            )

    def test_create_user_adds_matching_role_even_if_form_role_list_is_empty(self):
        response = self.client.post(reverse('organization:api_user_create'), data=json.dumps({
            'username': 'asistente-prueba',
            'full_name': 'Asistente de Prueba',
            'email': 'asistente-prueba@example.test',
            'rut': '12.345.678-5',
            'password': 'L3tra!Segura-de-Universidad2026',
            'status': 'Activo',
            'delegation_id': self.delegation.pk,
            'position_id': self.assistant_position.pk,
            'role_ids': [],
        }), content_type='application/json')

        self.assertEqual(response.status_code, 200, response.content)
        profile = UserProfile.objects.get(pk=response.json()['user_id'])
        self.assertEqual(list(profile.roles.values_list('name', flat=True)), ['Asistente Social'])
        self.assertIn('lectura', profile.roles.get().permissions_data)

    def test_changing_cargo_replaces_only_old_base_role_and_keeps_extra_roles(self):
        User = get_user_model()
        user = User.objects.create_user(username='cambio-cargo', password='L3tra!Segura-de-Universidad2026')
        profile = UserProfile.objects.create(
            user=user, rut='11.111.111-1', full_name='Cambio de Cargo',
            email='cambio-cargo@example.test', delegation=self.delegation,
            position=self.assistant_position,
        )
        assistant_role = Role.objects.get(name='Asistente Social')
        extra_role = Role.objects.create(name='Permiso complementario', permissions_data=['reportes.view'])
        profile.roles.set([assistant_role, extra_role])

        response = self.client.post(reverse('organization:api_user_update', args=[profile.pk]), data=json.dumps({
            'full_name': profile.full_name,
            'email': profile.email,
            'rut': profile.rut,
            'status': profile.status,
            'delegation_id': self.delegation.pk,
            'position_id': self.delegado_position.pk,
            'role_ids': [extra_role.pk],
        }), content_type='application/json')

        self.assertEqual(response.status_code, 200, response.content)
        profile.refresh_from_db()
        self.assertEqual(profile.position_id, self.delegado_position.pk)
        self.assertSetEqual(set(profile.roles.values_list('name', flat=True)), {
            'Delegado Municipal', 'Permiso complementario',
        })

    def test_changing_cargo_without_role_ids_still_syncs_base_role(self):
        User = get_user_model()
        user = User.objects.create_user(username='cambio-sin-roles', password='L3tra!Segura-de-Universidad2026')
        profile = UserProfile.objects.create(
            user=user, rut='10.111.111-3', full_name='Cambio Sin Roles',
            email='cambio-sin-roles@example.test', delegation=self.delegation,
            position=self.assistant_position,
        )
        profile.roles.add(Role.objects.get(name='Asistente Social'))

        response = self.client.post(reverse('organization:api_user_update', args=[profile.pk]), data=json.dumps({
            'full_name': profile.full_name,
            'email': profile.email,
            'rut': profile.rut,
            'status': profile.status,
            'position_id': self.delegado_position.pk,
        }), content_type='application/json')

        self.assertEqual(response.status_code, 200, response.content)
        profile.refresh_from_db()
        self.assertSetEqual(set(profile.roles.values_list('name', flat=True)), {'Delegado Municipal'})

    def test_creating_cargo_also_creates_its_base_role(self):
        response = self.client.post(reverse('organization:api_positions'), data=json.dumps({
            'name': 'Orientador Comunitario',
            'description': 'Orienta a vecinos en trámites municipales.',
            'status': 'Activo',
        }), content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['base_role'], 'Orientador Comunitario')
        role = Role.objects.get(name='Orientador Comunitario')
        self.assertTrue(role.is_system)

    def test_renaming_cargo_keeps_assigned_users_and_base_role_in_sync(self):
        position = Position.objects.create(name='Encargado de Prueba', description='Cargo temporal')
        role = Role.objects.create(name='Encargado de Prueba', is_system=True, permissions_data=['lectura'])
        User = get_user_model()
        user = User.objects.create_user(username='encargado-prueba', password='Safe!TestPass2026')
        profile = UserProfile.objects.create(
            user=user, rut='10.222.333-4', full_name='Encargado de Prueba',
            email='encargado-prueba@example.test', delegation=self.delegation, position=position,
        )
        profile.roles.add(role)

        response = self.client.post(reverse('organization:api_position_update', args=[position.pk]), data=json.dumps({
            'name': 'Encargado Territorial', 'description': 'Cargo actualizado.', 'status': 'Activo',
        }), content_type='application/json')

        self.assertEqual(response.status_code, 200, response.content)
        profile.refresh_from_db()
        role.refresh_from_db()
        self.assertEqual(role.name, 'Encargado Territorial')
        self.assertEqual(list(profile.roles.values_list('name', flat=True)), ['Encargado Territorial'])


class UserIdentityEditingTests(TestCase):
    """Regresiones de identidad y privilegios al editar la dotación existente."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_superuser(
            username='identity-admin', email='identity-admin@example.test', password='Safe!TestPass2026',
        )
        cls.delegation = Delegation.objects.create(name='Identidad territorial', scope='Sector de prueba')
        cls.assistant_position = Position.objects.get(name='Asistente Social')
        cls.delegate_position = Position.objects.get(name='Delegado Municipal')
        cls.super_position, _ = Position.objects.get_or_create(name='SuperAdministrador')
        cls.extra_role = Role.objects.create(name='Apoyo identidad', permissions_data=['reportes.view'])
        cls.user = User.objects.create_user(username='legacy-person', is_staff=True)
        cls.profile = UserProfile.objects.create(
            user=cls.user, rut='12.345.678-9', full_name='Persona Histórica',
            email='legacy-person@example.test', delegation=cls.delegation,
            position=cls.assistant_position,
        )
        cls.profile.roles.add(Role.objects.get(name='Asistente Social'))

    def setUp(self):
        self.client.force_login(self.admin)

    def update(self, payload):
        return self.client.post(
            reverse('organization:api_user_update', args=[self.profile.pk]),
            data=json.dumps(payload), content_type='application/json',
        )

    def create(self, **overrides):
        payload = {
            'username': 'new-identity', 'full_name': 'Nueva Persona',
            'email': 'new-identity@example.test', 'rut': '10000013-k',
            'password': 'Safe!TestPass2026', 'delegation_id': self.delegation.pk,
            'position_id': self.assistant_position.pk,
        }
        payload.update(overrides)
        return self.client.post(
            reverse('organization:api_user_create'), data=json.dumps(payload), content_type='application/json',
        )

    def test_cargo_can_change_without_resubmitting_historical_rut(self):
        response = self.update({'position_id': self.delegate_position.pk})
        self.assertEqual(response.status_code, 200, response.content)
        self.profile.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.profile.rut, '12.345.678-9')
        self.assertEqual(self.profile.position_id, self.delegate_position.pk)
        self.assertSetEqual(set(self.profile.roles.values_list('name', flat=True)), {'Delegado Municipal'})
        self.assertTrue(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_unchanged_historical_rut_allows_role_change_even_when_reformatted(self):
        response = self.update({'rut': '12345678-9', 'role_ids': [self.extra_role.pk]})
        self.assertEqual(response.status_code, 200, response.content)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.rut, '12.345.678-9')
        self.assertSetEqual(set(self.profile.roles.values_list('name', flat=True)), {'Asistente Social', 'Apoyo identidad'})

    def test_changed_invalid_rut_does_not_partially_update_cargo_or_roles(self):
        from core.models import AuditLog
        audit_count = AuditLog.objects.count()
        for rut in ('12.345.678-0', '', 'abc12345678-5', '0-0'):
            with self.subTest(rut=rut):
                response = self.update({'rut': rut, 'position_id': self.delegate_position.pk, 'role_ids': [self.extra_role.pk]})
                self.assertEqual(response.status_code, 400, response.content)
                self.profile.refresh_from_db()
                self.assertEqual(self.profile.rut, '12.345.678-9')
                self.assertEqual(self.profile.position_id, self.assistant_position.pk)
                self.assertSetEqual(set(self.profile.roles.values_list('name', flat=True)), {'Asistente Social'})
        self.assertEqual(AuditLog.objects.count(), audit_count)

    def test_new_rut_requires_valid_dv(self):
        response = self.create(rut='12.345.678-9')
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(get_user_model().objects.filter(username='new-identity').exists())

    def test_new_and_changed_valid_rut_store_canonical_format_and_uppercase_k(self):
        response = self.create()
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(UserProfile.objects.get(pk=response.json()['user_id']).rut, '10.000.013-K')
        response = self.update({'rut': '12345678-5'})
        self.assertEqual(response.status_code, 200, response.content)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.rut, '12.345.678-5')

    def test_duplicate_identity_is_rejected_for_create_and_update_across_formats(self):
        other = get_user_model().objects.create_user(username='other-identity')
        UserProfile.objects.create(user=other, rut='10000013-k', full_name='Otra Persona', email='other-identity@example.test')
        response = self.create(rut='10.000.013-K')
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn('ya se encuentra registrado', response.json()['message'])
        response = self.update({'rut': '10.000.013-K', 'position_id': self.delegate_position.pk})
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn('pertenece a otro funcionario', response.json()['message'])
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.rut, '12.345.678-9')
        self.assertEqual(self.profile.position_id, self.assistant_position.pk)

    def test_super_administrator_cargo_cannot_bypass_reserved_role_on_create(self):
        response = self.create(position_id=self.super_position.pk, role_ids=[])
        self.assertEqual(response.status_code, 403, response.content)
        self.assertFalse(get_user_model().objects.filter(username='new-identity').exists())

    def test_super_administrator_cargo_cannot_bypass_reserved_role_on_update(self):
        from core.models import AuditLog
        for roles in (None, []):
            payload = {'position_id': self.super_position.pk}
            if roles is not None:
                payload['role_ids'] = roles
            response = self.update(payload)
            self.assertEqual(response.status_code, 403, response.content)
            self.profile.refresh_from_db()
            self.assertEqual(self.profile.position_id, self.assistant_position.pk)
            self.assertSetEqual(set(self.profile.roles.values_list('name', flat=True)), {'Asistente Social'})
        self.assertFalse(AuditLog.objects.filter(affected_record_id=str(self.profile.pk), action='UPDATE').exists())
