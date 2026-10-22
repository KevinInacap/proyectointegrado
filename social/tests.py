import json
from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from organization.models import Delegation, Position, Role, UserProfile
from core.models import AuditLog
from .models import SocialCase, SocialManagement, SocialNotification, SocialReviewRequest


class SocialDashboardPermissionTests(TestCase):
    def setUp(self):
        self.delegation = Delegation.objects.create(name='Delegación Social Test', scope='Zona de prueba')
        self.other_delegation = Delegation.objects.create(name='Otra Delegación Test', scope='Otra zona')
        self.position = Position.objects.get(name='Asistente Social')
        self.role = Role.objects.get(name='Asistente Social')
        self.user = get_user_model().objects.create_user(
            username='asistente-social-test', password='Safe!TestPass2026',
        )
        self.profile = UserProfile.objects.create(
            user=self.user, rut='12.345.678-5', full_name='Asistente de Prueba',
            email='asistente-social-test@example.test', delegation=self.delegation,
            position=self.position,
        )
        self.profile.roles.add(self.role)
        self.client.force_login(self.user)
        self.admin = get_user_model().objects.create_user(
            username='social-admin-test', password='Safe!AdminPass2026', is_staff=True,
        )
        self.admin_profile = UserProfile.objects.create(
            user=self.admin, rut='15.555.555-5', full_name='Administradora de Prueba',
            email='social-admin-test@example.test', delegation=self.delegation,
            position=Position.objects.get(name='Administrador General'),
        )
        self.admin_role, _ = Role.objects.get_or_create(
            name='Administrador', defaults={'is_system': True, 'permissions_data': ['lectura']},
        )
        self.admin_profile.roles.add(self.admin_role)
        self.admin_client = Client()
        self.admin_client.force_login(self.admin)
        self.own_case = SocialCase.objects.create(
            user_rut='13.222.111-3', user_name='Vecina de mi sede',
            delegation=self.delegation, entry_date=date(2026, 1, 10),
        )
        self.other_case = SocialCase.objects.create(
            user_rut='14.222.111-0', user_name='Vecino de otra sede',
            delegation=self.other_delegation, entry_date=date(2026, 1, 11),
        )

    def test_dashboard_without_read_permission_shows_no_social_records(self):
        self.role.permissions_data = []
        self.role.permission_definitions.clear()
        self.role.save(update_fields=['permissions_data', 'updated_at'])

        response = self.client.get(reverse('activities:dashboard_asistente'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tu rol no tiene accesos habilitados')
        self.assertNotContains(response, self.own_case.user_name)

    def test_social_dashboard_api_requires_authentication_and_permission(self):
        api = reverse('social:api_casos')
        self.client.logout()
        self.assertEqual(self.client.get(api).status_code, 403)

        self.client.force_login(self.user)
        self.role.permissions_data = []
        self.role.permission_definitions.clear()
        self.role.save(update_fields=['permissions_data', 'updated_at'])
        self.assertEqual(self.client.get(api).status_code, 403)

    def test_social_api_scopes_list_and_detail_to_assigned_delegation(self):
        response = self.client.get(reverse('social:api_casos'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([case['id'] for case in response.json()['cases']], [self.own_case.pk])
        other_detail = reverse('social:api_caso_detalle', args=[self.other_case.pk])
        self.assertEqual(self.client.get(other_detail).status_code, 404)

    def test_social_dashboard_route_rejects_a_different_cargo(self):
        self.profile.position = Position.objects.get(name='Delegado Municipal')
        self.profile.save(update_fields=['position', 'updated_at'])

        response = self.client.get(reverse('activities:dashboard_asistente'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('core:login'))

    def test_new_social_case_creates_pending_review_and_admin_notification(self):
        response = self.client.post(reverse('social:api_casos'), data=json.dumps({
            'user_rut': '12.345.678-5',
            'user_name': 'Vecina Nueva',
            'contact_phone': '+56 9 1111 2222',
            'delegation_id': self.delegation.pk,
            'entry_date': '2026-10-01',
            'initial_problem': 'Solicita orientación por apoyo familiar.',
        }), content_type='application/json')

        self.assertEqual(response.status_code, 201, response.content)
        caso = SocialCase.objects.get(user_name='Vecina Nueva')
        review = SocialReviewRequest.objects.get(case=caso)
        self.assertEqual(review.status, 'pendiente')
        self.assertEqual(review.request_type, 'revision')
        self.assertEqual(review.requester, self.user)
        self.assertEqual(review.requester_name, self.profile.full_name)
        self.assertEqual(review.requester_position, 'Asistente Social')
        self.assertEqual(review.requester_delegation, self.delegation.name)
        self.assertTrue(review.management_id)
        notification = SocialNotification.objects.get(review_request=review, recipient=self.admin)
        self.assertIn(self.profile.full_name, notification.message)
        self.assertIn('Asistente Social', notification.message)
        self.assertIn(self.delegation.name, notification.message)

        admin_response = self.admin_client.get(reverse('social:api_solicitudes_sociales'))
        self.assertEqual(admin_response.status_code, 200)
        self.assertEqual(admin_response.json()['pending_count'], 1)
        self.assertEqual(admin_response.json()['requests'][0]['id'], review.pk)

    def test_admin_dashboard_includes_database_backed_review_inbox_and_counter(self):
        SocialReviewRequest.objects.create(
            request_type='revision', case=self.own_case, requester=self.user,
            requester_name=self.profile.full_name, requester_position='Asistente Social',
            requester_delegation=self.delegation.name, reason='Verificar antecedentes recibidos.',
            target_label=f'Caso #{self.own_case.pk}',
        )
        response = self.admin_client.get(reverse('activities:dashboard_admin'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="view-solicitudes-sociales"')
        self.assertContains(response, 'Solicitudes sociales')
        self.assertEqual(response.context['social_pending_request_count'], 1)

    def test_case_correction_waits_for_admin_approval_then_updates_database(self):
        response = self.client.post(
            reverse('social:api_solicitud_caso', args=[self.own_case.pk]),
            data=json.dumps({
                'request_type': 'edicion',
                'reason': 'El nombre fue digitado con un error.',
                'requested_changes': {'user_name': 'Nombre Corregido'},
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        review_id = response.json()['review_request_id']
        self.own_case.refresh_from_db()
        self.assertEqual(self.own_case.user_name, 'Vecina de mi sede')

        resolved = self.admin_client.post(
            reverse('social:api_resolver_solicitud_social', args=[review_id]),
            data=json.dumps({'decision': 'aprobada', 'resolution_note': 'Corrección verificada.'}),
            content_type='application/json',
        )
        self.assertEqual(resolved.status_code, 200, resolved.content)
        self.own_case.refresh_from_db()
        review = SocialReviewRequest.objects.get(pk=review_id)
        self.assertEqual(self.own_case.user_name, 'Nombre Corregido')
        self.assertEqual(review.status, 'aprobada')
        self.assertEqual(review.reviewed_by, self.admin)
        self.assertIsNotNone(review.resolved_at)
        self.assertTrue(SocialNotification.objects.filter(
            review_request=review, recipient=self.user, event_type='result',
        ).exists())
        self.assertTrue(AuditLog.objects.filter(
            affected_table='solicitud_revision_social', affected_record_id=str(review_id), action='UPDATE',
        ).exists())

    def test_rejecting_correction_keeps_original_case_data(self):
        response = self.client.post(
            reverse('social:api_solicitud_caso', args=[self.own_case.pk]),
            data=json.dumps({
                'request_type': 'edicion', 'reason': 'Se solicita corregir un dato.',
                'requested_changes': {'contact_phone': '+56 9 9999 0000'},
            }),
            content_type='application/json',
        )
        review_id = response.json()['review_request_id']
        rejected = self.admin_client.post(
            reverse('social:api_resolver_solicitud_social', args=[review_id]),
            data=json.dumps({'decision': 'rechazada', 'resolution_note': 'No coincide con el respaldo.'}),
            content_type='application/json',
        )
        self.assertEqual(rejected.status_code, 200, rejected.content)
        self.own_case.refresh_from_db()
        self.assertEqual(self.own_case.contact_phone, '')
        self.assertEqual(SocialReviewRequest.objects.get(pk=review_id).status, 'rechazada')

    def test_adding_social_management_creates_review_and_notification(self):
        response = self.client.post(
            reverse('social:api_avanzar_etapa', args=[self.own_case.pk]),
            data=json.dumps({
                'stage': 2,
                'management_type': 'Visita domiciliaria',
                'management_date': '2026-10-20',
                'result': 'Se realizó visita y se verificaron antecedentes.',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        management = SocialManagement.objects.get(case=self.own_case, stage=2)
        review = SocialReviewRequest.objects.get(management=management)
        self.assertEqual(review.status, 'pendiente')
        self.assertTrue(SocialNotification.objects.filter(review_request=review, recipient=self.admin).exists())

    def test_assistant_dashboard_territorial_tables_do_not_leak_other_delegations(self):
        own_visit = SocialManagement.objects.create(
            case=self.own_case, stage=2, management_type='Visita propia',
            management_date=date(2026, 10, 20), result='Seguimiento local.',
        )
        other_visit = SocialManagement.objects.create(
            case=self.other_case, stage=2, management_type='Visita ajena',
            management_date=date(2026, 10, 20), result='Dato fuera de sede.',
        )
        other_close_case = SocialCase.objects.create(
            user_rut='15.222.111-7', user_name='Persona de otra delegación',
            delegation=self.other_delegation, entry_date=date(2026, 1, 12),
        )
        other_subsidy = SocialManagement.objects.create(
            case=other_close_case, stage=3, management_type='Ayuda ajena',
            management_date=date(2026, 10, 20), result='Dato reservado a otra sede.',
        )

        response = self.client.get(reverse('activities:dashboard_asistente'))

        self.assertEqual(response.status_code, 200)
        visits = list(response.context['visitas_terreno'])
        subsidies = list(response.context['subsidios_entregados'])
        self.assertEqual([item.pk for item in visits], [own_visit.pk])
        self.assertNotIn(other_visit.pk, [item.pk for item in visits])
        self.assertEqual(subsidies, [])
        self.assertNotIn(other_subsidy.pk, [item.pk for item in subsidies])
        self.assertEqual(list(response.context['delegations']), [self.delegation])

    def test_non_administrator_cannot_read_or_resolve_admin_requests(self):
        self.assertEqual(self.client.get(reverse('social:api_solicitudes_sociales')).status_code, 403)
        self.assertEqual(self.client.post(
            reverse('social:api_resolver_solicitud_social', args=[999999]),
            data=json.dumps({'decision': 'aprobada'}), content_type='application/json',
        ).status_code, 403)

    def test_admin_can_mark_only_own_notifications_read(self):
        review = SocialReviewRequest.objects.create(
            request_type='revision', case=self.own_case, requester=self.user,
            requester_name=self.profile.full_name, requester_position='Asistente Social',
            requester_delegation=self.delegation.name, reason='Revisar registro social.',
            target_label='Caso de prueba',
        )
        notification = SocialNotification.objects.create(
            recipient=self.admin, review_request=review, event_type='request', message='Revisar caso.',
        )
        response = self.admin_client.post(
            reverse('social:api_notificaciones_sociales'),
            data=json.dumps({'ids': [notification.pk]}), content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertIsNotNone(notification.read_at)
