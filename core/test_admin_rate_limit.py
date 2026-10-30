import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import AdminCreationQuota
from metrics.models import AttentionType
from organization.models import Position


@override_settings(SGR_ADMIN_CREATE_LIMIT=2, SGR_ADMIN_CREATE_WINDOW_SECONDS=60,
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AdminCreationLimitTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.admin = users.objects.create_superuser(username='cuota-admin', password='test')
        self.other = users.objects.create_superuser(username='cuota-otro', password='test')
        self.client.force_login(self.admin)

    def post(self, url, data):
        return self.client.post(url, json.dumps(data), content_type='application/json')

    def test_limit_is_shared_across_catalogs_and_resets_after_window(self):
        positions = reverse('organization:api_positions')
        self.assertEqual(self.post(positions, {'name': 'Cargo cuota uno'}).status_code, 200)
        self.assertEqual(self.post('/api/catalogs/attention-types/', {
            'code': 'QA-1', 'name': 'Atención cuota uno',
        }).status_code, 201)
        blocked = self.post(positions, {'name': 'Cargo bloqueado'})
        self.assertEqual(blocked.status_code, 429)
        self.assertIn('Retry-After', blocked)
        self.assertFalse(Position.objects.filter(name='Cargo bloqueado').exists())
        self.assertEqual(AttentionType.objects.filter(name='Atención cuota uno').count(), 1)
        self.assertEqual(self.client.get(positions).status_code, 200)
        AdminCreationQuota.objects.filter(user=self.admin).update(window_started_at=timezone.now() - timedelta(seconds=61))
        self.assertEqual(self.post(positions, {'name': 'Cargo cuota nuevo'}).status_code, 200)

    def test_quota_is_per_user_and_unauthorized_calls_do_not_consume_it(self):
        positions = reverse('organization:api_positions')
        self.post(positions, {'name': 'Cargo A'})
        self.post(positions, {'name': 'Cargo B'})
        self.client.force_login(self.other)
        self.assertEqual(self.post(positions, {'name': 'Cargo C'}).status_code, 200)
        user = get_user_model().objects.create_user(username='sin-permisos')
        self.client.force_login(user)
        self.assertEqual(self.post(positions, {'name': 'Cargo D'}).status_code, 403)
        self.assertFalse(AdminCreationQuota.objects.filter(user=user).exists())
