from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organization.models import Delegation, Role, UserProfile
from .models import CollectiveAgenda


class AdminAgendaApiTests(TestCase):
    def setUp(self):
        self.delegation = Delegation.objects.create(name="Delegación de prueba", scope="Sector de prueba")
        self.admin_role, _ = Role.objects.get_or_create(name="Administrador")
        self.admin = get_user_model().objects.create_user(username="admin-agenda", password="test-pass")
        self.profile = UserProfile.objects.create(
            user=self.admin,
            rut="12345678-5",
            full_name="Administrador de prueba",
            email="admin-agenda@example.com",
            delegation=self.delegation,
            status="Activo",
        )
        self.profile.roles.add(self.admin_role)
        self.url = reverse("agenda:api_agenda")
        self.client.force_login(self.admin)

    def test_returns_month_commitments_without_requester_data(self):
        CollectiveAgenda.objects.create(
            delegation=self.delegation,
            requester="Dato privado",
            territory="Las Compañías",
            support_area="Social",
            description="Revisar luminarias",
            committed_date=date(2026, 10, 12),
            status="Pendiente",
        )
        response = self.client.get(self.url, {"desde": "2026-10-01", "hasta": "2026-10-31"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["descripcion"], "Revisar luminarias")
        self.assertNotIn("requester", payload["results"][0])
        self.assertNotIn("Dato privado", response.content.decode())

    def test_requires_administrator_role(self):
        self.profile.roles.clear()
        response = self.client.get(self.url, {"desde": "2026-10-01", "hasta": "2026-10-31"})
        self.assertEqual(response.status_code, 403)

    def test_rejects_invalid_or_excessive_date_range(self):
        invalid = self.client.get(self.url, {"desde": "2026-10-31", "hasta": "2026-10-01"})
        excessive = self.client.get(self.url, {"desde": "2025-01-01", "hasta": "2026-12-31"})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(excessive.status_code, 400)
