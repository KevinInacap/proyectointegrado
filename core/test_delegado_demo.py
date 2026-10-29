from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from activities.models import Activity, Vecino
from activities.views import _valid_vecino_rut
from core.management.commands.seed_delegado_demo import CODE_PREFIX, EMAIL, RECORD_COUNT, USERNAME
from organization.models import Delegation, UserProfile


@override_settings(DEBUG=True, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class DelegadoDemoTests(TestCase):
    password = 'AcademicaLocal2026!'

    def seed(self, password=None):
        with patch.dict('os.environ', {'SGR_DELEGADO_DEMO_PASSWORD': self.password if password is None else password}):
            call_command('seed_delegado_demo', stdout=StringIO())

    def test_idempotent_account_and_twelve_searchable_pending_records_without_other_profiles(self):
        self.seed()
        user = get_user_model().objects.get(username=USERNAME)
        first_password = user.password
        ids = list(Activity.objects.filter(activity_code__startswith=CODE_PREFIX).values_list('pk', flat=True))
        self.seed(password='')
        user.refresh_from_db()
        self.assertEqual(user.password, first_password)
        self.assertTrue(user.check_password(self.password))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(UserProfile.objects.count(), 1)
        self.assertEqual(Vecino.objects.count(), RECORD_COUNT)
        self.assertEqual(list(Activity.objects.filter(activity_code__startswith=CODE_PREFIX).values_list('pk', flat=True)), ids)
        self.assertTrue(all(_valid_vecino_rut(rut) for rut in Vecino.objects.values_list('rut', flat=True)))
        self.client.force_login(user)
        url = reverse('activities:dashboard_delegado_section', args=['atenciones'])
        response = self.client.get(url, {'q': CODE_PREFIX, 'estado': 'Pending', 'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'].paginator.count, RECORD_COUNT)
        self.assertEqual(len(response.context['page']), 4)
        self.assertContains(response, 'q=DEMO-DEL-')
        self.assertContains(response, 'estado=Pending')
        self.assertEqual(Activity.objects.filter(delegation=user.profile.delegation).count(), RECORD_COUNT)

    def test_repeated_seed_preserves_edits_bajas_credentials_and_unrelated_records(self):
        other = get_user_model().objects.create_user(username='cuenta.existente', password='ClaveExistente2026!', email='existente@example.test')
        other_password = other.password
        delegation = Delegation.objects.exclude(name='Delegación Las Compañías').first()
        unrelated = Activity.objects.create(
            activity_code='ATENCION-EXISTENTE', activity_date=timezone.localdate(), delegation=delegation,
            contact_name='Registro conservado', problem_description='Solicitud existente', executed_action='Acción existente',
        )
        self.seed()
        edited = Activity.objects.get(activity_code=f'{CODE_PREFIX}001')
        edited.problem_description = 'Cambio realizado durante la defensa'
        edited.validation_status = 'Approved'
        edited.save()
        deleted = Activity.objects.get(activity_code=f'{CODE_PREFIX}002')
        deleted.deleted_at = timezone.now()
        deleted.save()
        deleted_at = deleted.deleted_at
        self.seed(password='OtraClave2026!')
        edited.refresh_from_db()
        deleted.refresh_from_db()
        other.refresh_from_db()
        unrelated.refresh_from_db()
        self.assertEqual(edited.problem_description, 'Cambio realizado durante la defensa')
        self.assertEqual(edited.validation_status, 'Approved')
        self.assertEqual(deleted.deleted_at, deleted_at)
        self.assertEqual(other.password, other_password)
        self.assertEqual(other.email, 'existente@example.test')
        self.assertEqual(unrelated.problem_description, 'Solicitud existente')
        self.assertEqual(UserProfile.objects.count(), 1)

    def test_collision_late_in_seed_rolls_back_new_account_neighbors_and_activities(self):
        collision = Activity.objects.create(
            activity_code=f'{CODE_PREFIX}012', activity_date=timezone.localdate(),
            contact_name='Ajeno', problem_description='No reemplazar', executed_action='Conservar',
        )
        with self.assertRaises(CommandError):
            self.seed()
        self.assertFalse(get_user_model().objects.filter(username=USERNAME).exists())
        self.assertFalse(UserProfile.objects.exists())
        self.assertFalse(Vecino.objects.exists())
        self.assertEqual(Activity.objects.count(), 1)
        collision.refresh_from_db()
        self.assertEqual(collision.problem_description, 'No reemplazar')

    def test_existing_username_is_not_adopted_or_replaced(self):
        existing = get_user_model().objects.create_user(username=USERNAME, password='Original2026!', email='real@example.test')
        password = existing.password
        with self.assertRaises(CommandError):
            self.seed()
        existing.refresh_from_db()
        self.assertEqual(existing.email, 'real@example.test')
        self.assertEqual(existing.password, password)
        self.assertFalse(UserProfile.objects.exists())

    def test_password_required_only_for_first_creation_and_never_printed(self):
        with self.assertRaises(CommandError):
            self.seed(password='')
        self.assertFalse(get_user_model().objects.filter(username=USERNAME).exists())
        output = StringIO()
        with patch.dict('os.environ', {'SGR_DELEGADO_DEMO_PASSWORD': self.password}):
            call_command('seed_delegado_demo', stdout=output)
        self.assertNotIn(self.password, output.getvalue())
        self.assertIn(EMAIL, output.getvalue())

    @override_settings(DEBUG=False)
    def test_production_guard_leaves_database_unchanged(self):
        with self.assertRaises(CommandError):
            self.seed()
        self.assertFalse(get_user_model().objects.filter(username=USERNAME).exists())
        self.assertFalse(UserProfile.objects.exists())
        self.assertFalse(Vecino.objects.exists())
        self.assertFalse(Activity.objects.exists())

