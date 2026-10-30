from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from organization.models import Position, Role


@override_settings(DEBUG=True)
class SeedPositionRoleLinkTests(TestCase):
    def test_new_consultation_position_links_existing_system_role(self):
        role = Role.objects.get(name='Usuario de Consulta')
        self.assertTrue(role.is_system)
        self.assertIsNone(role.position_id)
        self.assertFalse(Position.objects.filter(name='Usuario de Consulta').exists())
        role.permissions_data = ['lectura', 'reportes.view']
        role.save(update_fields=['permissions_data', 'updated_at'])
        call_command('seed_data', stdout=StringIO())
        position = Position.objects.get(name='Usuario de Consulta')
        role.refresh_from_db()
        self.assertEqual(role.position_id, position.pk)
        self.assertEqual(position.base_role_id, role.pk)
        self.assertEqual(role.permissions_data, ['lectura', 'reportes.view'])
        call_command('seed_data', stdout=StringIO())
        self.assertEqual(Position.objects.filter(name='Usuario de Consulta').count(), 1)
        self.assertEqual(Role.objects.filter(name='Usuario de Consulta').count(), 1)

    def test_personalized_role_with_same_name_is_not_promoted_or_linked(self):
        role = Role.objects.get(name='Usuario de Consulta')
        role.is_system = False
        role.permissions_data = ['usuarios.delete']
        role.save(update_fields=['is_system', 'permissions_data', 'updated_at'])
        call_command('seed_data', stdout=StringIO())
        role.refresh_from_db()
        position = Position.objects.get(name='Usuario de Consulta')
        self.assertFalse(role.is_system)
        self.assertIsNone(role.position_id)
        self.assertIsNone(position.base_role_id)
        self.assertEqual(role.permissions_data, ['usuarios.delete'])
