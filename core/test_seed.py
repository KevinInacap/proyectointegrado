from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from organization.models import Delegation, Position, Role, UserProfile
from activities.models import Activity
from unittest.mock import patch


@override_settings(DEBUG=True)
class SeedDataPasswordTests(TestCase):
    def test_academic_users_are_five_per_delegation_without_usable_password(self):
        from core.management.commands.seed_academic_users import SAMPLES
        call_command('seed_data', verbosity=0)
        call_command('seed_academic_users', verbosity=0)
        call_command('seed_academic_users', verbosity=0)
        profiles = UserProfile.objects.filter(user__username__startswith='muestra_sgr_')
        self.assertEqual(profiles.count(), 30)
        for delegation in Delegation.objects.filter(code__in=SAMPLES):
            self.assertEqual(profiles.filter(delegation=delegation).count(), 5)
        for profile in profiles.select_related('user'):
            self.assertTrue(profile.email.endswith('@pnk.cl'))
            self.assertFalse(profile.user.has_usable_password())
    def test_rerunning_seed_does_not_reset_existing_password(self):
        with patch.dict('os.environ', {'SGR_SEED_PASSWORD': 'Test-Only-Seed-Key-2026!'}):
            call_command('seed_data', '--include-demo-data', verbosity=0)
        user = User.objects.get(username='admin')
        user.set_password('NuevaClavePrivada2026!')
        user.save(update_fields=['password'])

        with patch.dict('os.environ', {'SGR_SEED_PASSWORD': 'Different-Test-Key-2026!'}):
            call_command('seed_data', '--include-demo-data', verbosity=0)

        user.refresh_from_db()
        self.assertTrue(user.check_password('NuevaClavePrivada2026!'))
        self.assertFalse(user.check_password('Admin1234!'))

    def test_seed_initializes_role_matrix_permissions_used_by_the_app(self):
        call_command('seed_data', verbosity=0)
        expected = {
            'Coordinador del Sistema': {'lectura', 'edicion', 'derivacion'},
            'Delegado Municipal': {'lectura', 'edicion', 'derivacion'},
            'Gestor Territorial': {'lectura', 'edicion', 'derivacion'},
            'Verificador Técnico': {'lectura', 'edicion', 'cierre'},
            'Usuario de Consulta': {'lectura'},
        }
        for name, permissions in expected.items():
            with self.subTest(role=name):
                self.assertTrue(permissions.issubset(set(Role.objects.get(name=name).permissions_data)))

    def test_default_seed_keeps_master_catalogs_without_fake_users_or_activity(self):
        call_command('seed_data', verbosity=0)

        self.assertGreater(Delegation.objects.count(), 0)
        self.assertGreater(Position.objects.count(), 0)
        self.assertGreater(Role.objects.count(), 0)
        self.assertFalse(Role.objects.filter(name='Administrador General').exists())
        self.assertEqual(Role.objects.filter(is_system=True).count(), 6)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Activity.objects.count(), 0)

    def test_demo_administrator_uses_admin_cargo_and_application_role(self):
        with patch.dict('os.environ', {'SGR_SEED_PASSWORD': 'Test-Only-Seed-Key-2026!'}):
            call_command('seed_data', '--include-demo-data', verbosity=0)

        user = User.objects.get(username='admin')
        profile = UserProfile.objects.get(user=user)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(profile.position.name, 'Administrador General')
        self.assertTrue(profile.roles.filter(name='Administrador').exists())
