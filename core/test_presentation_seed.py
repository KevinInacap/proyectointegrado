from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from activities.models import Activity, Vecino
from metrics.models import Goal
from organization.models import Delegation, Position, Role, UserProfile


@override_settings(DEBUG=True)
class PresentationSeedTests(TestCase):
    def setUp(self):
        Position.objects.get_or_create(name='Gestor Territorial')
        self.role, _ = Role.objects.update_or_create(name='Gestor Territorial', defaults={'permissions_data': ['permiso_original']})
        for name in ['Delegación Centro Histórico', 'Delegación Las Compañías', 'Delegación La Pampa']:
            Delegation.objects.get_or_create(name=name, defaults={'scope': 'Prueba'})

    def test_repeatable_with_no_login_accounts_or_permission_changes(self):
        for _ in range(2):
            call_command('seed_presentation', stdout=StringIO())
        self.assertEqual(UserProfile.objects.count(), 3)
        self.assertEqual(Vecino.objects.count(), 3)
        self.assertEqual(Activity.objects.count(), 3)
        self.assertEqual(Goal.objects.count(), 3)
        self.assertEqual(sum(Goal.objects.values_list('weight', flat=True)), 100)
        for user in get_user_model().objects.all():
            self.assertFalse(user.is_active)
            self.assertFalse(user.has_usable_password())
            self.assertFalse(user.is_staff)
        for activity in Activity.objects.all():
            activity.full_clean()
            self.assertEqual(activity.subattention.attention_type, activity.attention_type)
        self.role.refresh_from_db()
        self.assertEqual(self.role.permissions_data, ['permiso_original'])

    @override_settings(DEBUG=False)
    def test_production_is_rejected(self):
        with self.assertRaises(CommandError):
            call_command('seed_presentation', stdout=StringIO())
        self.assertEqual(UserProfile.objects.count(), 0)

    def test_missing_dependencies_are_not_created(self):
        self.role.delete()
        with self.assertRaises(CommandError):
            call_command('seed_presentation', stdout=StringIO())
        self.assertEqual(UserProfile.objects.count(), 0)
