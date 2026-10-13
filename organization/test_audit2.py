from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase
from django.utils import timezone

from core.models import AuditLog, PasswordRecoveryCode
from core.test_audit2 import WEAK_PASSWORDS, STRONG_PASSWORD
from organization.models import Delegation, Position, Role, UserProfile


class Audit2OrganizationTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user('audit_admin', password=STRONG_PASSWORD)
        self.admin_profile = UserProfile.objects.create(
            user=self.admin, rut='11.111.111-1', full_name='Admin Audit', email='admin@example.test',
        )
        self.admin_profile.roles.add(Role.objects.get(name='Administrador'))
        self.target = get_user_model().objects.create_user('audit_target', password=STRONG_PASSWORD)
        self.target_profile = UserProfile.objects.create(
            user=self.target, rut='12.345.678-5', full_name='Target Audit', email='target@example.test',
        )
        self.client.force_login(self.admin)

    def post(self, path, data):
        return self.client.post(path, data=data, content_type='application/json')

    def payload(self, **changes):
        return dict(username='audit_new', full_name='Persona Nueva', email='new@example.test',
                    rut='9.876.543-3', password=STRONG_PASSWORD, **changes)

    def test_delete_user_is_soft_and_prevents_future_login(self):
        response = self.post(f'/api/users/{self.target_profile.pk}/delete/', {})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(UserProfile.objects.filter(pk=self.target_profile.pk).exists())
        self.assertFalse(get_user_model().objects.filter(pk=self.target.pk).exists())
        self.assertTrue(AuditLog.objects.filter(
            affected_table='usuario', affected_record_id=str(self.target_profile.pk), action='DELETE',
        ).exists())
        self.assertNotEqual(Client().post('/', {
            'username': self.target_profile.email, 'password': STRONG_PASSWORD,
        }).status_code, 302)

    def test_delete_user_rejects_self_and_principal_admin(self):
        self.assertEqual(self.post(f'/api/users/{self.admin_profile.pk}/delete/', {}).status_code, 400)
        principal = get_user_model().objects.create_user('admin', password=STRONG_PASSWORD)
        profile = UserProfile.objects.create(
            user=principal, rut='13.456.789-2', full_name='Admin principal', email='principal@example.test',
        )
        self.assertEqual(self.post(f'/api/users/{profile.pk}/delete/', {}).status_code, 400)
        principal.refresh_from_db()
        self.assertTrue(principal.is_active)

    def test_all_password_endpoints_reject_missing_components(self):
        for password in WEAK_PASSWORDS:
            for path, data in (
                ('/api/users/create/', {**self.payload(), 'password': password}),
                (f'/api/users/{self.target_profile.pk}/update/', {'password': password}),
                (f'/api/users/{self.target_profile.pk}/reset-password/', {'password': password}),
            ):
                with self.subTest(path=path, password=password):
                    self.assertEqual(self.post(path, data).status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username='audit_new').exists())
        self.target.refresh_from_db()
        self.assertTrue(self.target.check_password(STRONG_PASSWORD))

    def test_password_is_not_trimmed_and_html_specials_are_allowed(self):
        password = '  Viento49<>  '
        response = self.post('/api/users/create/', {**self.payload(), 'password': password})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(get_user_model().objects.get(username='audit_new').check_password(password))

    def test_functional_admin_cannot_grant_technical_privileges(self):
        for flag in ('is_superuser', 'is_staff'):
            with self.subTest(flag=flag):
                self.assertEqual(self.post('/api/users/create/', self.payload(**{flag: True})).status_code, 403)
                self.assertEqual(self.post(f'/api/users/{self.target_profile.pk}/update/', {flag: True}).status_code, 403)

    def test_functional_admin_cannot_take_over_superuser(self):
        self.target.is_superuser = True
        self.target.save()
        for operation in ('update', 'reset-password', 'delete', 'toggle-status'):
            with self.subTest(operation=operation):
                self.assertEqual(self.post(f'/api/users/{self.target_profile.pk}/{operation}/', {'password': 'OtraClave57!'}).status_code, 403)

    def test_administrative_password_changes_revoke_recovery(self):
        for operation in ('update', 'reset-password'):
            record = PasswordRecoveryCode.objects.create(
                user=self.target, code_hash=make_password('123456'), expires_at=timezone.now() + timedelta(minutes=10),
            )
            self.assertEqual(self.post(f'/api/users/{self.target_profile.pk}/{operation}/', {'password': 'OtraClave57!'}).status_code, 200)
            record.refresh_from_db()
            self.assertIsNotNone(record.used_at)

    def test_admin_reset_password_can_login_using_rut_and_registered_email(self):
        role, _ = Role.objects.get_or_create(name='Gestor Territorial')
        self.target_profile.roles.add(role)
        self.target_profile.position, _ = Position.objects.get_or_create(name='Gestor Territorial')
        self.target_profile.save(update_fields=['position', 'updated_at'])
        new_password = 'NuevaClavePrueba2026!'
        response = self.post(f'/api/users/{self.target_profile.pk}/reset-password/', {'password': new_password})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()['is_active'])
        self.assertEqual(response.json()['account_status'], 'Activo')
        self.assertTrue(response.json()['has_active_role'])
        self.target.refresh_from_db()
        self.assertTrue(self.target.check_password(new_password))

        for identifier in (self.target_profile.rut, self.target_profile.email):
            with self.subTest(identifier=identifier):
                login_client = Client()
                logged_in = login_client.post('/', {'username': identifier, 'password': new_password})
                self.assertEqual(logged_in.status_code, 302)
                self.assertTrue('_auth_user_id' in login_client.session)

    def test_admin_can_reassign_user_role_delegation_and_position(self):
        from django.urls import reverse

        old_delegation = Delegation.objects.create(name='Delegación anterior', scope='Centro')
        delegation = Delegation.objects.create(name='Delegación de prueba', scope='Sur')
        old_position, _ = Position.objects.get_or_create(name='Gestor Territorial')
        position, _ = Position.objects.get_or_create(name='Verificador Técnico')
        old_role = Role.objects.create(name='Rol anterior de prueba', permissions_data=[])
        role = Role.objects.create(name='Rol de prueba', permissions_data=['lectura'])
        self.target_profile.delegation = old_delegation
        self.target_profile.position = old_position
        self.target_profile.save(update_fields=['delegation', 'position', 'updated_at'])
        self.target_profile.roles.add(old_role)

        target_client = Client()
        logged_in = target_client.post('/', {
            'username': self.target_profile.email,
            'password': STRONG_PASSWORD,
        })
        self.assertEqual(logged_in.status_code, 302)
        self.assertTrue(target_client.session.get('_auth_user_id'))
        self.assertEqual(target_client.get(reverse('activities:dashboard')).url,
                         reverse('activities:dashboard_gestor'))

        response = self.post(f'/api/users/{self.target_profile.pk}/update/', {
            'full_name': self.target_profile.full_name,
            'email': self.target_profile.email,
            'rut': self.target_profile.rut,
            'delegation_id': delegation.pk,
            'position_id': position.pk,
            'role_ids': [role.pk],
        })
        self.assertEqual(response.status_code, 200, response.content)
        self.target_profile.refresh_from_db()
        self.assertEqual(self.target_profile.delegation_id, delegation.pk)
        self.assertEqual(self.target_profile.position_id, position.pk)
        self.assertEqual(list(self.target_profile.roles.values_list('id', flat=True)), [role.pk])

        # El panel vuelve a leer el perfil persistido: no muestra el rol o sede antiguos de la sesión.
        dashboard = target_client.get(reverse('activities:dashboard'), follow=True)
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.redirect_chain[-1][0], reverse('activities:dashboard_verificador'))
        self.assertContains(dashboard, 'Delegación de prueba')
        self.assertContains(dashboard, 'Rol de prueba')
        self.assertNotContains(dashboard, 'Delegación anterior')
        self.assertNotContains(dashboard, 'Rol anterior de prueba')

        # Una cuenta común no puede usar la API administrativa para cambiarse su asignación.
        denied = target_client.post(
            f'/api/users/{self.target_profile.pk}/update/',
            data='{"delegation_id": null}', content_type='application/json',
        )
        self.assertEqual(denied.status_code, 403)

    def test_plain_text_fields_reject_stored_html(self):
        payload = '<img src=x onerror=alert(1)>'
        for path, data in (
            ('/api/users/create/', {**self.payload(), 'full_name': payload}),
            (f'/api/users/{self.target_profile.pk}/update/', {'full_name': payload}),
            ('/api/roles/create/', {'name': payload}),
            ('/api/positions/', {'name': payload}),
            ('/api/roles/permissions/add-custom/', {'module_id': 'audit', 'code': 'audit.read', 'name': payload}),
            ('/api/delegations/', {'name': 'Delegacion Audit', 'scope': 'Zona', 'photo_url': 'javascript:alert(1)'}),
            ('/api/delegations/', {'name': 'Delegacion Audit', 'scope': 'Zona', 'photo_url': 'data:image/svg+xml,<svg onload=alert(1)>'}),
        ):
            with self.subTest(path=path):
                self.assertEqual(self.post(path, data).status_code, 400)

    def test_role_permissions_authorize_only_the_matching_crud_operation(self):
        delegation = Delegation.objects.create(name='Centro de permisos', scope='Centro')
        self.admin_profile.delegation = delegation
        self.admin_profile.save(update_fields=['delegation', 'updated_at'])
        self.target_profile.delegation = delegation
        self.target_profile.save(update_fields=['delegation', 'updated_at'])
        self.admin_profile.roles.clear()
        role = Role.objects.create(name='Gestor de cuentas', permissions_data=['usuarios.view', 'usuarios.create'])
        self.admin_profile.roles.add(role)
        self.assertEqual(self.client.get('/api/users/').status_code, 200)
        self.assertEqual(self.client.get('/api/roles/').status_code, 403)
        create = self.post('/api/users/create/', self.payload(position_id=None, role_ids=[], delegation_id=delegation.pk))
        self.assertEqual(create.status_code, 200, create.content)
        self.assertTrue(get_user_model().objects.filter(username='audit_new').exists())
        self.assertEqual(self.post(f'/api/users/{self.target_profile.pk}/toggle-status/', {}).status_code, 403)
        role.permissions_data.append('usuarios.toggle_status')
        role.save(update_fields=['permissions_data', 'updated_at'])
        toggled = self.post(f'/api/users/{self.target_profile.pk}/toggle-status/', {})
        self.assertEqual(toggled.status_code, 200, toggled.content)
        self.target_profile.refresh_from_db()
        self.assertEqual(self.target_profile.status, 'Inactivo')

    def test_user_management_is_limited_to_delegation_and_cannot_grant_global_admin(self):
        from organization.models import Role

        own = Delegation.objects.create(name='Delegación propia', scope='Centro')
        other = Delegation.objects.create(name='Delegación ajena', scope='Norte')
        self.admin_profile.delegation = own
        self.admin_profile.save(update_fields=['delegation', 'updated_at'])
        self.target_profile.delegation = own
        self.target_profile.save(update_fields=['delegation', 'updated_at'])
        manager_role = Role.objects.create(name='Gestor acotado', permissions_data=[
            'usuarios.view', 'usuarios.create', 'usuarios.edit', 'usuarios.toggle_status',
        ])
        self.admin_profile.roles.clear()
        self.admin_profile.roles.add(manager_role)

        listed = self.client.get('/api/users/').json()['users']
        self.assertEqual({item['id'] for item in listed}, {self.admin_profile.pk, self.target_profile.pk})
        created = self.post('/api/users/create/', self.payload(
            delegation_id=other.pk, role_ids=[],
        ))
        self.assertEqual(created.status_code, 403)
        self.assertEqual(self.post(f'/api/users/{self.target_profile.pk}/update/', {
            'delegation_id': other.pk,
        }).status_code, 403)

        global_admin = Role.objects.get(name='Administrador')
        elevated = self.post(f'/api/users/{self.target_profile.pk}/update/', {
            'role_ids': [global_admin.pk],
        })
        self.assertEqual(elevated.status_code, 403)

    def test_position_permission_catalog_covers_the_existing_position_crud(self):
        from organization.views import SYSTEM_PERMISSIONS_CATALOG, _all_system_perm_codes
        module = next(item for item in SYSTEM_PERMISSIONS_CATALOG if item['module_id'] == 'cargos')
        self.assertEqual({item['code'] for item in module['permissions']}, {
            'cargos.view', 'cargos.create', 'cargos.edit', 'cargos.delete',
        })
        self.assertTrue({'cargos.view', 'cargos.create', 'cargos.edit', 'cargos.delete'}.issubset(_all_system_perm_codes()))

    def test_delegation_code_is_stable_unique_and_exposed_by_crud(self):
        created = self.post('/api/delegations/', {'name': 'Sede Norte', 'scope': 'Zona norte', 'commune': 'La Serena'})
        self.assertEqual(created.status_code, 200, created.content)
        item = Delegation.objects.get(pk=created.json()['id'])
        self.assertEqual(item.code, f'DEL-{item.pk:03d}')
        self.assertEqual(item.commune, 'La Serena')
        self.assertEqual(created.json()['code'], item.code)
        self.assertTrue(any(row['code'] == item.code and row['commune'] == 'La Serena' for row in self.client.get('/api/delegations/').json()['delegations']))
        changed = self.post(f'/organization/delegations/{item.pk}/update/', {'name': 'Sede Norte Nueva'})
        self.assertEqual(changed.status_code, 200, changed.content)
        item.refresh_from_db()
        self.assertEqual(item.code, created.json()['code'])
        self.assertEqual(self.post(f'/organization/delegations/{item.pk}/update/', {'commune': 'Coquimbo'}).status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.commune, 'Coquimbo')
        self.assertEqual(self.post(f'/organization/delegations/{item.pk}/update/', {'commune': ''}).status_code, 400)
        self.assertEqual(self.post('/api/delegations/', {
            'name': 'Sede Duplicada', 'scope': 'Zona', 'code': item.code.lower(),
        }).status_code, 400)

    def test_position_cards_follow_current_role_permissions(self):
        from django.urls import reverse

        delegation = Delegation.objects.create(name='Sede de prueba', scope='Zona')
        position, _ = Position.objects.get_or_create(name='Gestor Territorial')
        role = Role.objects.create(name='Rol de panel', permissions_data=['lectura', 'derivacion'])
        self.target_profile.delegation = delegation
        self.target_profile.position = position
        self.target_profile.save(update_fields=['delegation', 'position', 'updated_at'])
        self.target_profile.roles.add(role)
        client = Client()
        client.force_login(self.target)
        url = reverse('activities:dashboard_gestor')
        page = client.get(url)
        self.assertContains(page, delegation.code)
        self.assertContains(page, 'Mi trabajo')
        self.assertContains(page, 'Seguimiento')
        self.assertNotContains(page, 'Aquí se consultarán los registros de atención.')
        role.permissions_data = ['edicion']
        role.save(update_fields=['permissions_data', 'updated_at'])
        page = client.get(url)
        self.assertContains(page, 'Aquí se consultarán los registros de atención.')
        self.assertNotContains(page, 'Aquí se revisará el estado de las solicitudes.')
        self.assertNotContains(page, 'Aquí se mostrarán las tareas asignadas.')

    def test_non_admin_cannot_read_or_change_other_delegations(self):
        own = Delegation.objects.create(name='Sede propia', scope='Centro')
        other = Delegation.objects.create(name='Sede ajena', scope='Sur')
        self.admin_profile.delegation = own
        self.admin_profile.save(update_fields=['delegation', 'updated_at'])
        self.target_profile.delegation = other
        self.target_profile.save(update_fields=['delegation', 'updated_at'])
        shared = Role.objects.create(name='Rol compartido', permissions_data=[])
        self.admin_profile.roles.clear()
        self.admin_profile.roles.add(shared)
        self.target_profile.roles.add(shared)
        limited = Role.objects.create(name='Permisos territoriales', permissions_data=[
            'delegaciones.view', 'delegaciones.create', 'delegaciones.edit',
            'delegaciones.delete', 'usuarios.view', 'roles.view',
        ])
        self.admin_profile.roles.add(limited)

        listed = self.client.get('/api/delegations/')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([row['id'] for row in listed.json()['delegations']], [own.pk])
        users = self.client.get('/api/users/').json()
        self.assertEqual([row['id'] for row in users['delegations']], [own.pk])
        self.assertEqual([row['id'] for row in users['users']], [self.admin_profile.pk])
        role = next(row for row in self.client.get('/api/roles/').json()['roles'] if row['id'] == shared.pk)
        self.assertEqual(role['users_count'], 1)
        self.assertEqual(role['users_sample'], [self.admin_profile.full_name])

        self.assertEqual(self.post('/api/delegations/', {'name': 'Otra sede', 'scope': 'Nueva'}).status_code, 403)
        self.assertEqual(self.post(f'/api/delegations/{other.pk}/update/', {'name': 'Intrusión'}).status_code, 404)
        self.assertEqual(self.post(f'/api/delegations/{other.pk}/toggle-status/', {}).status_code, 404)
        self.assertEqual(self.post(f'/api/delegations/{own.pk}/update/', {'scope': 'Centro actualizado'}).status_code, 200)
        other.refresh_from_db()
        self.assertEqual(other.name, 'Sede ajena')

    def test_role_configuration_requires_an_administrator_even_with_granular_grants(self):
        self.admin_profile.roles.clear()
        limited = Role.objects.create(name='Editor limitado', permissions_data=[
            'roles.create', 'roles.edit', 'roles.delete', 'roles.manage_features',
        ])
        target_role = Role.objects.create(name='Rol objetivo', permissions_data=['lectura'])
        self.admin_profile.roles.add(limited)
        cases = (
            ('/api/roles/create/', {'name': 'Rol escalado', 'permissions': ['usuarios.edit']}),
            (f'/api/roles/{target_role.pk}/update/', {'permissions': ['usuarios.edit']}),
            (f'/api/roles/{target_role.pk}/delete/', {}),
            (f'/api/roles/{target_role.pk}/duplicate/', {'name': 'Copia escalada'}),
            ('/api/roles/permissions/add-custom/', {'module_id': 'prueba', 'code': 'prueba.edit', 'name': 'Nuevo permiso'}),
        )
        for path, data in cases:
            with self.subTest(path=path):
                self.assertEqual(self.post(path, data).status_code, 403)
        target_role.refresh_from_db()
        self.assertEqual(target_role.permissions_data, ['lectura'])
        self.assertFalse(Role.objects.filter(name='Rol escalado').exists())

    def test_administrator_name_is_reserved_for_system_role(self):
        self.assertEqual(self.post('/api/roles/create/', {
            'name': 'Administrador General', 'permissions': [],
        }).status_code, 400)
        self.assertFalse(Role.objects.filter(name='Administrador General').exists())
        custom = Role.objects.create(name='Rol de prueba', permissions_data=[])
        self.assertEqual(self.post(f'/api/roles/{custom.pk}/update/', {
            'name': 'Administrador General', 'permissions': [],
        }).status_code, 400)
        self.assertEqual(self.post(f'/api/roles/{custom.pk}/duplicate/', {
            'name': 'Administrador General',
        }).status_code, 400)
        custom.refresh_from_db()
        self.assertEqual(custom.name, 'Rol de prueba')

    def test_delete_position_without_users_succeeds_and_is_audited(self):
        pos = Position.objects.create(name='Cargo Vacío Para Borrar', description='Prueba')
        response = self.post(f'/api/positions/{pos.pk}/delete/', {})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(Position.objects.filter(pk=pos.pk).exists())
        self.assertTrue(AuditLog.objects.filter(
            affected_table='cargo', affected_record_id=str(pos.pk), action='DELETE'
        ).exists())

    def test_delete_position_with_assigned_users_is_blocked(self):
        pos = Position.objects.create(name='Cargo Con Funcionario', description='Prueba')
        self.target_profile.position = pos
        self.target_profile.save(update_fields=['position', 'updated_at'])
        response = self.post(f'/api/positions/{pos.pk}/delete/', {})
        self.assertEqual(response.status_code, 400, response.content)
        self.assertTrue(Position.objects.filter(pk=pos.pk).exists())
