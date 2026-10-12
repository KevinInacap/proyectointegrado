"""Regresiones de navegación y permisos del anexo C6 de la segunda evaluación."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from organization.access import set_role_permission_codes
from organization.models import Delegation, Position, Role, UserProfile
from .views import POSITION_DASHBOARD_CONTENT


class PositionNavigationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('navegacion-qa')
        self.role = Role.objects.create(name='Navegación QA', permissions_data=['lectura', 'edicion', 'derivacion', 'cierre'])
        self.delegation = Delegation.objects.create(name='Sede QA', scope='Zona QA')
        self.profile = UserProfile.objects.create(user=self.user, rut='99000000-1',
            full_name='Persona de Ensayo', email='navegacion@example.test', delegation=self.delegation)
        self.profile.roles.add(self.role)
        self.client.force_login(self.user)

    def test_every_cargo_has_navigable_authorized_sections(self):
        for position in POSITION_DASHBOARD_CONTENT:
            with self.subTest(position=position):
                self.profile.position = Position.objects.get_or_create(name=position)[0]
                self.profile.save()
                page = self.client.get(reverse('activities:dashboard'), follow=True)
                self.assertEqual(page.status_code, 200)
                self.assertContains(page, self.delegation.code)
                self.assertContains(page, self.role.name)
                cards = page.context['dashboard_cards']
                self.assertEqual(len(cards), 3)
                for card in cards:
                    detail = self.client.get(card['url'])
                    self.assertContains(detail, 'Funcionalidad en desarrollo')
                    self.assertEqual(detail.context['selected_module']['title'], card['title'])
                    self.assertContains(detail, 'Volver a mi inicio')

    def test_revocation_blocks_open_module_and_direct_url(self):
        self.profile.position = Position.objects.get_or_create(name='Gestor Territorial')[0]
        self.profile.save()
        url = reverse('activities:dashboard_module', args=['seguimiento'])
        self.assertEqual(self.client.get(url).status_code, 200)
        set_role_permission_codes(self.role, ['lectura'])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertNotContains(self.client.get(reverse('activities:dashboard_gestor')), 'Abrir Seguimiento')

    def test_anonymous_and_inactive_profiles_cannot_open_modules(self):
        url = reverse('activities:dashboard_module', args=['seguimiento'])
        self.profile.status = 'Inactivo'
        self.profile.save()
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)
