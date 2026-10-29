from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from organization.models import Delegation, Position, Role, UserProfile

from .models import Activity, Vecino


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class DelegadoSearchCountTests(TestCase):
    def setUp(self):
        self.delegation = Delegation.objects.create(name='Sede de búsqueda', scope='Prueba')
        self.other = Delegation.objects.create(name='Sede de búsqueda ajena', scope='Prueba')
        self.user = get_user_model().objects.create_user(username='delegado-busqueda')
        profile = UserProfile.objects.create(
            user=self.user, rut='12.345.678-5', full_name='Delegado de búsqueda',
            email='delegado-busqueda@example.test', delegation=self.delegation,
            position=Position.objects.get(name='Delegado Municipal'),
        )
        profile.roles.add(Role.objects.get(name='Delegado Municipal'))
        self.client.force_login(self.user)
        self.url = reverse('activities:dashboard_delegado_section', args=['atenciones'])

    def attention(self, code, status='Pending', **kwargs):
        return Activity.objects.create(
            activity_code=code, activity_date=timezone.localdate(),
            contact_name='Vecina de prueba', problem_description='Solicitud de prueba',
            executed_action='Registro', validation_status=status,
            delegation=kwargs.pop('delegation', self.delegation), user=self.user, **kwargs,
        )

    def test_empty_search_has_zero_counts_in_every_tab(self):
        self.attention('REGISTRO-LOCAL')
        self.attention('REGISTRO-APROBADO', 'Approved')
        response = self.client.get(self.url, {'q': 'SIN-COINCIDENCIA'})
        self.assertEqual(response.context['page'].paginator.count, 0)
        self.assertEqual(response.context['attention_scope_counts'], {
            'total': 0, 'followup': 0, 'approved': 0,
        })

    def test_search_counts_span_status_tabs_and_preserve_pagination(self):
        for index in range(9):
            self.attention(f'LUMINARIA-PENDIENTE-{index}')
        self.attention('LUMINARIA-CORREGIR', 'Requires correction')
        self.attention('LUMINARIA-APROBADA', 'Approved')
        self.attention('LUMINARIA-RECHAZADA', 'Rejected')
        self.attention('OTRA-SOLICITUD')
        self.attention('LUMINARIA-AJENA', delegation=self.other)
        self.attention('LUMINARIA-ELIMINADA', deleted_at=timezone.now())
        params = {'q': 'LUMINARIA', 'estado': 'Pending'}
        first = self.client.get(self.url, params)
        second = self.client.get(self.url, {**params, 'page': 2})
        for response in (first, second):
            self.assertEqual(response.context['attention_scope_counts'], {
                'total': 12, 'followup': 10, 'approved': 1,
            })
            self.assertEqual(response.context['page'].paginator.count, 9)
        self.assertEqual(len(first.context['page']), 8)
        self.assertEqual(len(second.context['page']), 1)
        self.assertContains(first, 'q=LUMINARIA&amp;estado=Pending&amp;page=2')
        approved = self.client.get(self.url, {'q': 'LUMINARIA', 'estado': 'Approved'})
        self.assertEqual(approved.context['page'].paginator.count, 1)
        self.assertEqual(approved.context['attention_scope_counts'], first.context['attention_scope_counts'])
        followup = self.client.get(
            reverse('activities:dashboard_delegado_section', args=['seguimiento']),
            {'q': 'LUMINARIA', 'estado': 'Approved'},
        )
        self.assertEqual(followup.context['page'].paginator.count, 10)
        self.assertTrue(all(item.validation_status in {'Pending', 'Requires correction'} for item in followup.context['page']))

    def test_search_counts_also_respect_neighbor_and_unlinked_filters(self):
        neighbor = Vecino.objects.create(
            nombre='Vecina de búsqueda', rut='11.111.111-1', territorio=self.delegation.name,
        )
        other_neighbor = Vecino.objects.create(
            nombre='Otra vecina', rut='22.222.222-2', territorio=self.delegation.name,
        )
        self.attention('BUSCAR-VECINA-PENDIENTE', neighbor=neighbor)
        self.attention('BUSCAR-VECINA-APROBADA', 'Approved', neighbor=neighbor)
        self.attention('BUSCAR-OTRA-VECINA', neighbor=other_neighbor)
        self.attention('BUSCAR-SIN-VINCULO')
        self.attention('OTRO-REGISTRO-VECINA', neighbor=neighbor)
        linked = self.client.get(self.url, {'q': 'BUSCAR', 'vecino': neighbor.pk})
        self.assertEqual(linked.context['page'].paginator.count, 2)
        self.assertEqual(linked.context['attention_scope_counts'], {
            'total': 2, 'followup': 1, 'approved': 1,
        })
        unlinked = self.client.get(self.url, {'q': 'BUSCAR', 'vinculo': 'sin-vincular'})
        self.assertEqual(unlinked.context['page'].paginator.count, 1)
        self.assertEqual(unlinked.context['attention_scope_counts'], {
            'total': 1, 'followup': 1, 'approved': 0,
        })

