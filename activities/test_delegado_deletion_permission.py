import importlib
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import AuditLog
from organization.access import role_permission_codes
from organization.models import Delegation, PermissionDefinition, Position, Role, UserProfile

from .models import Activity


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class DelegadoDeletionPermissionTests(TestCase):
    def setUp(self):
        self.delegation = Delegation.objects.create(name='Sede CRUD local', scope='Prueba')
        self.role = Role.objects.get(name='Delegado Municipal')
        self.user = get_user_model().objects.create_user(username='delegado-crud-estandar')
        self.profile = UserProfile.objects.create(
            user=self.user, rut='12.345.678-5', full_name='Delegado de prueba',
            email='delegado-crud@example.test', delegation=self.delegation,
            position=Position.objects.get(name='Delegado Municipal'),
        )
        self.profile.roles.add(self.role)
        self.client.force_login(self.user)

    def attention(self, code, delegation=None):
        return Activity.objects.create(
            activity_code=code, activity_date=timezone.localdate(),
            contact_name='Vecino de prueba', problem_description='Consulta de prueba',
            executed_action='Recepción', delegation=delegation or self.delegation,
            user=self.user,
        )

    def test_standard_role_shows_delete_and_persists_only_local_soft_deletion(self):
        self.assertTrue({'lectura', 'edicion', 'derivacion', 'cierre'} <= role_permission_codes(self.role))
        self.assertTrue(self.role.permission_definitions.filter(code='cierre').exists())
        attention = self.attention('DELEGADO-LOCAL-CRUD')
        other = Delegation.objects.create(name='Sede CRUD ajena', scope='Prueba')
        foreign = self.attention('DELEGADO-AJENO-CRUD', other)
        listing = reverse('activities:dashboard_delegado_section', args=['atenciones'])
        response = self.client.get(listing)
        self.assertContains(response, 'Nueva atención')
        self.assertContains(response, f'data-action="edit" data-id="{attention.pk}"')
        self.assertContains(response, f'data-action="delete" data-id="{attention.pk}"')
        self.assertNotContains(response, foreign.activity_code)

        self.assertEqual(self.client.delete(reverse('activities:api_atencion_detail', args=[foreign.pk])).status_code, 404)
        foreign.refresh_from_db()
        self.assertIsNone(foreign.deleted_at)
        self.assertEqual(self.client.delete(reverse('activities:api_atencion_detail', args=[attention.pk])).status_code, 200)
        attention.refresh_from_db()
        self.assertIsNotNone(attention.deleted_at)
        self.assertTrue(AuditLog.objects.filter(
            user=self.user, action='DELETE', affected_table='actividad',
            affected_record_id=str(attention.pk),
        ).exists())
        self.assertNotContains(self.client.get(listing), attention.activity_code)

    def test_grant_preserves_custom_permissions_and_existing_catalog_links(self):
        existing = PermissionDefinition.objects.get(code='delegaciones.view')
        self.role.permissions_data = ['lectura', 'edicion', 'derivacion', 'funcion.personalizada']
        self.role.save(update_fields=['permissions_data', 'updated_at'])
        self.role.permission_definitions.set([existing])
        other_role = Role.objects.get(name='Usuario de Consulta')
        other_permissions = list(other_role.permissions_data)
        grant = importlib.import_module(
            'organization.migrations.0016_delegado_deletion_permission',
        ).grant_delegado_deletion
        schema_editor = SimpleNamespace(connection=connection)
        grant(apps, schema_editor)
        grant(apps, schema_editor)
        self.role.refresh_from_db()
        other_role.refresh_from_db()
        self.assertEqual(self.role.permissions_data, [
            'lectura', 'edicion', 'derivacion', 'funcion.personalizada', 'cierre',
        ])
        self.assertSetEqual(set(self.role.permission_definitions.values_list('code', flat=True)), {
            'delegaciones.view', 'cierre',
        })
        self.assertEqual(other_role.permissions_data, other_permissions)
        self.assertEqual(UserProfile.objects.count(), 1)
