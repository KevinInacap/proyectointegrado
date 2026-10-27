from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from organization.models import Delegation, Position, Role, UserProfile
from social.models import SocialCase, SocialManagement
from .models import Activity, Vecino


class DelegadoSectionTests(TestCase):
    sections = ('atenciones', 'casos-sociales', 'vecinos', 'equipo', 'seguimiento')

    def setUp(self):
        self.delegation = Delegation.objects.create(name='Sede local', scope='Centro')
        self.other = Delegation.objects.create(name='Sede ajena', scope='Sur')
        self.position = Position.objects.get(name='Delegado Municipal')
        self.role = Role.objects.create(name='Consulta de secciones', permissions_data=['lectura'])
        self.user = get_user_model().objects.create_user(username='delegado-secciones', password='test-pass')
        self.profile = UserProfile.objects.create(
            user=self.user, rut='10000000-0', full_name='Delegado Local',
            email='delegado@example.com', position=self.position, delegation=self.delegation,
        )
        self.profile.roles.add(self.role)
        self.client.force_login(self.user)

    def url(self, section):
        return reverse('activities:dashboard_delegado_section', args=[section])

    def attention(self, code, status='Pending', **kwargs):
        return Activity.objects.create(
            activity_code=code, activity_date='2026-01-02', contact_name='Vecina Local',
            problem_description='Alumbrado', executed_action='Recepción',
            delegation=kwargs.pop('delegation', self.delegation), validation_status=status, **kwargs,
        )

    def test_sections_have_distinct_reloadable_urls_and_only_their_own_content(self):
        expected_ids = {'atenciones': 'atenciones', 'seguimiento': 'atenciones',
                        'casos-sociales': 'casos-sociales', 'vecinos': 'vecinos', 'equipo': 'equipo'}
        for section in ('inicio', *self.sections):
            url = reverse('activities:dashboard_delegado') if section == 'inicio' else self.url(section)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, f'data-page-section="{section}"')
            sidebar = response.content.decode().partition('<nav class="primary-nav"')[2].partition('</nav>')[0]
            self.assertEqual(sidebar.count('aria-current="page"'), 1)
            self.assertIn(f'href="{url}" aria-current="page"', sidebar)
            for target in self.sections:
                self.assertIn(f'href="{self.url(target)}"', sidebar)
            for content_id in set(expected_ids.values()):
                if content_id == expected_ids.get(section):
                    self.assertContains(response, f'id="{content_id}"')
                else:
                    self.assertNotContains(response, f'id="{content_id}"')
            if section != 'inicio':
                self.assertContains(response, f'action="{url}"')

    def test_social_cases_filter_latest_live_stage_and_paginate_without_leaking(self):
        cases = [SocialCase.objects.create(
            user_rut=f'2000000{i}-0', user_name=f'Caso local {i}', delegation=self.delegation,
            entry_date='2026-01-02', contact_phone='912345678',
        ) for i in range(9)]
        SocialCase.objects.create(user_rut='99999999-9', user_name='Caso ajeno',
                                  delegation=self.other, entry_date='2026-01-02')
        SocialManagement.objects.create(case=cases[0], stage=2, management_type='Visita',
                                        management_date='2026-01-02', result='Realizada')
        SocialManagement.objects.create(case=cases[0], stage=3, management_type='Resolución',
                                        management_date='2026-01-02', result='Anulada', deleted_at=timezone.now())
        url = self.url('casos-sociales')
        first = self.client.get(url)
        second = self.client.get(url, {'page': 2})
        self.assertEqual(len(first.context['page']), 8)
        self.assertEqual(len(second.context['page']), 1)
        self.assertNotContains(first, 'Caso ajeno')
        filtered = self.client.get(url, {'q': 'Caso local', 'etapa': '2', 'page': 'invalid'})
        self.assertEqual(list(filtered.context['page']), [cases[0]])
        self.assertEqual(filtered.context['page'][0].latest_stage, 2)
        self.assertEqual(self.client.get(url, {'etapa': '1'}).context['page'].paginator.count, 8)
        self.assertEqual(self.client.get(url, {'etapa': '3'}).context['page'].paginator.count, 0)

    def test_neighbors_preserve_search_and_state_across_pages(self):
        for i in range(10):
            Vecino.objects.create(nombre=f'Vecino local {i}', rut=f'3000000{i}-0',
                                  territorio=self.delegation.name, estado='Activo')
        Vecino.objects.create(nombre='Vecino ajeno', rut='99999999-9', territorio=self.other.name)
        Vecino.objects.create(nombre='Vecino local inactivo', rut='88888888-8',
                              territorio=self.delegation.name, estado='Inactivo')
        url = self.url('vecinos')
        first = self.client.get(url, {'q': 'Vecino local', 'estado': 'Activo'})
        second = self.client.get(url, {'q': 'Vecino local', 'estado': 'Activo', 'page': 2})
        self.assertEqual(first.context['page'].paginator.count, 10)
        self.assertEqual(len(first.context['page']), 8)
        self.assertEqual(len(second.context['page']), 2)
        self.assertContains(first, 'q=Vecino+local&amp;estado=Activo&amp;page=2')
        self.assertNotContains(first, 'Vecino ajeno')
        self.assertNotContains(first, 'Vecino local inactivo')
        self.assertEqual(self.client.get(url, {'estado': 'Inactivo'}).context['page'].paginator.count, 1)

    def test_team_search_position_pagination_and_active_delegation_scope(self):
        other_position = Position.objects.get(name='Gestor Territorial')
        for i in range(9):
            user = get_user_model().objects.create_user(username=f'miembro-{i}')
            UserProfile.objects.create(user=user, rut=f'4000000{i}-0', full_name=f'Funcionario local {i}',
                                       email=f'miembro{i}@example.com', position=other_position,
                                       delegation=self.delegation)
        for name, delegation, active in (('Funcionario ajeno', self.other, True),
                                         ('Funcionario inactivo', self.delegation, False)):
            user = get_user_model().objects.create_user(username=name, is_active=active)
            UserProfile.objects.create(user=user, rut=name, full_name=name, email=f'{user.pk}@example.com',
                                       position=other_position, delegation=delegation)
        url = self.url('equipo')
        response = self.client.get(url, {'q': 'Funcionario', 'cargo': other_position.pk})
        self.assertEqual(response.context['page'].paginator.count, 9)
        self.assertEqual(len(response.context['page']), 8)
        self.assertNotContains(response, 'Funcionario ajeno')
        self.assertNotContains(response, 'Funcionario inactivo')
        self.assertContains(response, f'q=Funcionario&amp;cargo={other_position.pk}&amp;page=2')
        self.assertEqual(len(self.client.get(url, {'q': 'Funcionario', 'cargo': other_position.pk, 'page': 2}).context['page']), 1)

    def test_followup_cannot_be_changed_to_show_approved_or_rejected_records(self):
        pending = self.attention('PENDIENTE')
        correction = self.attention('CORREGIR', 'Requires correction')
        self.attention('APROBADA', 'Approved')
        self.attention('RECHAZADA', 'Rejected')
        self.attention('AJENA', delegation=self.other)
        self.attention('ELIMINADA', deleted_at=timezone.now())
        url = self.url('seguimiento')
        self.assertEqual(set(self.client.get(url).context['page']), {pending, correction})
        self.assertEqual(set(self.client.get(url, {'estado': 'Approved'}).context['page']), {pending, correction})
        filtered = self.client.get(url, {'q': 'Alumbrado', 'estado': 'Requires correction'})
        self.assertEqual(list(filtered.context['page']), [correction])

    def test_every_section_checks_cargo_permissions_and_assigned_delegation(self):
        self.attention('LOCAL-SECRET')
        self.role.permissions_data = []
        self.role.save()
        for section in self.sections:
            response = self.client.get(self.url(section))
            self.assertContains(response, 'Tu rol no tiene accesos habilitados')
            self.assertNotContains(response, 'LOCAL-SECRET')
            self.assertNotContains(response, 'data-page-section=')
        self.role.permissions_data = ['lectura']
        self.role.save()
        self.profile.delegation = None
        self.profile.save()
        for section in self.sections:
            self.assertContains(self.client.get(self.url(section)), 'Falta asignar tu delegación')
        self.profile.position = Position.objects.get(name='Gestor Territorial')
        self.profile.save()
        for section in self.sections:
            self.assertEqual(self.client.get(self.url(section)).status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.get(self.url('atenciones')).status_code, 302)

    def test_unknown_section_and_legacy_attention_links(self):
        self.assertEqual(self.client.get(self.url('inexistente')).status_code, 404)
        home = reverse('activities:dashboard_delegado')
        self.assertRedirects(self.client.get(home, {'q': 'Vecina', 'page': 2}),
                             f'{self.url("atenciones")}?q=Vecina&page=2')
        self.assertRedirects(self.client.get(home, {'estado': 'followup', 'q': 'Vecina'}),
                             f'{self.url("seguimiento")}?q=Vecina')
