import json
import importlib
from datetime import date
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.apps import apps
from django.db import connection
from django.test import Client, TestCase
from django.urls import reverse

from organization.models import Delegation, Position, Role, UserProfile
from core.models import AuditLog
from activities.models import Activity, Vecino
from metrics.models import AttentionType, SubAttention
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

        response = self.client.get(reverse('social:dashboard_asistente'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tu rol no tiene accesos habilitados')
        self.assertNotContains(response, self.own_case.user_name)

    def test_integrated_dashboard_uses_social_cases_not_neighbor_registry(self):
        Vecino.objects.create(
            rut='21.571.404-7', nombre='Solo en padrón', direccion='Calle uno',
            territorio=self.delegation.name,
        )
        response = self.client.get(reverse('activities:dashboard_asistente'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [case['id'] for case in response.context['casos_sociales']],
            [self.own_case.pk],
        )
        self.assertNotIn('Solo en padrón', [case['nombre'] for case in response.context['casos_sociales']])
        self.assertEqual(response.context['vecinos_data'][0]['nombre'], 'Solo en padrón')
        self.assertContains(response, 'social-cases-data')

    def test_integrated_dashboard_escapes_case_data_and_scopes_metrics(self):
        self.own_case.user_name = '</script><img src=x onerror=alert(1)>'
        self.own_case.save(update_fields=['user_name', 'updated_at'])
        response = self.client.get(reverse('activities:dashboard_asistente'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '</script><img src=x onerror=alert(1)>')
        self.assertContains(response, r'\u003C/script\u003E')
        self.assertEqual(response.context['goal_data']['target'], None)
        metrics = self.client.get(reverse('activities:dashboard_asistente') + '?metrics=1')
        self.assertEqual(metrics.status_code, 200)
        self.assertIsNone(metrics.json()['goal']['target'])

    def test_integrated_dashboard_revoked_read_permission_hides_records(self):
        self.role.permissions_data = []
        self.role.permission_definitions.clear()
        self.role.save(update_fields=['permissions_data', 'updated_at'])
        response = self.client.get(reverse('activities:dashboard_asistente'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.own_case.user_name)

    def test_integrated_dashboard_inactive_delegation_hides_records(self):
        self.delegation.status = 'Inactivo'
        self.delegation.save(update_fields=['status', 'updated_at'])
        response = self.client.get(reverse('activities:dashboard_asistente'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.own_case.user_name)

    def test_admin_cannot_create_case_in_an_implicit_or_invalid_delegation(self):
        payload = {
            'user_rut': '12.345.678-5', 'user_name': 'Sin sede',
            'entry_date': '2026-10-01', 'initial_problem': 'Solicitud de prueba.',
        }
        endpoint = reverse('social:api_casos')
        for value in (None, 'otra', self.other_delegation.pk + 100):
            response = self.admin_client.post(
                endpoint, data=json.dumps(dict(payload, delegation_id=value)),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 400)
        self.assertFalse(SocialCase.objects.filter(user_name='Sin sede').exists())

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

        response = self.client.get(reverse('social:dashboard_asistente'))

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
        self.assertEqual(caso.activity.neighbor.rut, caso.user_rut)
        self.assertEqual(caso.activity.delegation, self.delegation)
        self.assertEqual(caso.activity.validation_status, 'Pending')
        self.assertIsNone(caso.activity.attention_type_id)
        self.assertIsNone(caso.managements.get(stage=1).catalog_id)
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

    def test_case_creates_classified_attention_and_neighbor_without_duplicate_on_retry(self):
        attention_type = AttentionType.objects.create(code='SOC-TIPO', name='Atención social de prueba')
        subattention = SubAttention.objects.create(
            code='SOC-SUB', name='Solicitud social de prueba', attention_type=attention_type,
        )
        payload = {
            'user_rut': '12.345.678-5', 'user_name': 'Vecina Nueva',
            'contact_phone': '+56 9 1111 2222', 'delegation_id': self.delegation.pk,
            'entry_date': '2026-10-01', 'initial_problem': 'Solicitud de apoyo familiar.',
            'attention_type_id': attention_type.pk, 'subattention_id': subattention.pk,
        }
        endpoint = reverse('social:api_casos')
        first = self.client.post(endpoint, data=json.dumps(payload), content_type='application/json')
        repeated = self.client.post(endpoint, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(repeated.status_code, 200, repeated.content)
        self.assertEqual(first.json()['case']['id'], repeated.json()['case']['id'])
        case = SocialCase.objects.get(pk=first.json()['case']['id'])
        self.assertEqual(Activity.objects.filter(pk=case.activity_id).count(), 1)
        self.assertEqual(Vecino.objects.filter(rut=case.user_rut).count(), 1)
        self.assertEqual(case.activity.attention_type, attention_type)
        self.assertEqual(case.activity.subattention, subattention)
        self.assertEqual(case.activity.neighbor.territorio, self.delegation.name)
        dashboard = self.client.get(reverse('activities:dashboard_asistente'))
        self.assertContains(dashboard, 'id="casoTipoAtencion"')
        self.assertContains(dashboard, 'id="emerSubAtencion"')
        self.assertContains(dashboard, subattention.name)
        self.assertIn(case.activity_id, [row['id'] for row in self.client.get(reverse('activities:api_atenciones')).json()['atenciones']])
        self.assertIn(case.activity.neighbor_id, [row['id'] for row in self.client.get(reverse('activities:api_vecinos')).json()['vecinos']])

    def test_case_rejects_wrong_catalog_pair_and_neighbor_from_other_delegation(self):
        first_type = AttentionType.objects.create(code='SOC-T1', name='Tipo social 1')
        second_type = AttentionType.objects.create(code='SOC-T2', name='Tipo social 2')
        sub = SubAttention.objects.create(code='SOC-S2', name='Sub social 2', attention_type=second_type)
        payload = {
            'user_rut': '12.345.678-5', 'user_name': 'Vecina Nueva',
            'delegation_id': self.delegation.pk, 'entry_date': '2026-10-01',
            'initial_problem': 'Consulta social.',
            'attention_type_id': first_type.pk, 'subattention_id': sub.pk,
        }
        endpoint = reverse('social:api_casos')
        invalid = self.client.post(endpoint, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(invalid.status_code, 400)
        self.assertFalse(SocialCase.objects.filter(user_name='Vecina Nueva').exists())

        Vecino.objects.create(rut=payload['user_rut'], nombre='Otra sede', territorio=self.other_delegation.name)
        payload['attention_type_id'] = second_type.pk
        conflict = self.client.post(endpoint, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(conflict.status_code, 409, conflict.content)
        self.assertFalse(SocialCase.objects.filter(user_name='Vecina Nueva').exists())
        self.assertEqual(Vecino.objects.get(rut=payload['user_rut']).territorio, self.other_delegation.name)

    def test_admin_with_assigned_delegation_can_register_case_in_another_one(self):
        response = self.admin_client.post(reverse('social:api_casos'), data=json.dumps({
            'user_rut': '12.345.678-5', 'user_name': 'Vecina de otra sede',
            'delegation_id': self.other_delegation.pk, 'entry_date': '2026-10-01',
            'initial_problem': 'Solicitud territorial.',
        }), content_type='application/json')
        self.assertEqual(response.status_code, 201, response.content)
        case = SocialCase.objects.get(pk=response.json()['case']['id'])
        self.assertEqual(case.activity.delegation, self.other_delegation)
        self.assertIn(case.pk, [row['id'] for row in self.admin_client.get(reverse('social:api_casos')).json()['cases']])

    def test_approved_correction_updates_linked_records_and_case_archive_hides_attention(self):
        created = self.client.post(reverse('social:api_casos'), data=json.dumps({
            'user_rut': '12.345.678-5', 'user_name': 'Nombre anterior',
            'delegation_id': self.delegation.pk, 'entry_date': '2026-10-01',
            'initial_problem': 'Consulta social.',
        }), content_type='application/json')
        self.assertEqual(created.status_code, 201, created.content)
        case = SocialCase.objects.get(pk=created.json()['case']['id'])
        requested = self.client.post(reverse('social:api_solicitud_caso', args=[case.pk]), data=json.dumps({
            'request_type': 'edicion', 'reason': 'Nombre corregido con antecedentes.',
            'requested_changes': {'user_name': 'Nombre corregido'},
        }), content_type='application/json')
        review_id = requested.json()['review_request_id']
        resolved = self.admin_client.post(reverse('social:api_resolver_solicitud_social', args=[review_id]),
                                          data=json.dumps({'decision': 'aprobada'}), content_type='application/json')
        self.assertEqual(resolved.status_code, 200, resolved.content)
        case.refresh_from_db()
        self.assertEqual(case.activity.contact_name, 'Nombre corregido')
        self.assertEqual(case.activity.neighbor.nombre, 'Nombre corregido')

        archived = self.admin_client.delete(reverse('social:api_caso_detalle', args=[case.pk]))
        self.assertEqual(archived.status_code, 200, archived.content)
        case.activity.refresh_from_db()
        self.assertIsNotNone(case.activity.deleted_at)
        self.assertIsNone(case.activity.neighbor.deleted_at)

    def test_correction_cannot_take_neighbor_from_another_delegation(self):
        created = self.client.post(reverse('social:api_casos'), data=json.dumps({
            'user_rut': '12.345.678-5', 'user_name': 'Vecina Original',
            'delegation_id': self.delegation.pk, 'entry_date': '2026-10-01',
            'initial_problem': 'Consulta social.',
        }), content_type='application/json')
        self.assertEqual(created.status_code, 201, created.content)
        case = SocialCase.objects.get(pk=created.json()['case']['id'])
        outside = Vecino.objects.create(
            rut='21.571.404-7', nombre='Vecino externo', territorio=self.other_delegation.name,
        )
        requested = self.client.post(reverse('social:api_solicitud_caso', args=[case.pk]), data=json.dumps({
            'request_type': 'edicion', 'reason': 'Se solicita verificar el RUT.',
            'requested_changes': {'user_rut': outside.rut},
        }), content_type='application/json')
        resolved = self.admin_client.post(
            reverse('social:api_resolver_solicitud_social', args=[requested.json()['review_request_id']]),
            data=json.dumps({'decision': 'aprobada'}), content_type='application/json',
        )
        self.assertEqual(resolved.status_code, 409, resolved.content)
        case.refresh_from_db()
        self.assertEqual(case.user_rut, '12.345.678-5')
        self.assertEqual(case.activity.neighbor.rut, case.user_rut)
        outside.refresh_from_db()
        self.assertEqual(outside.territorio, self.other_delegation.name)
        self.assertEqual(SocialReviewRequest.objects.get(pk=requested.json()['review_request_id']).status, 'pendiente')

    def test_backfill_keeps_cross_delegation_neighbor_out_of_historic_case(self):
        Vecino.objects.create(rut=self.own_case.user_rut, nombre='Otra sede', territorio=self.other_delegation.name)
        first_stage = SocialManagement.objects.create(
            case=self.own_case, stage=1, management_type='Ingreso',
            management_date=self.own_case.entry_date, result='Solicitud histórica.',
        )
        SocialReviewRequest.objects.create(
            request_type='revision', status='aprobada', case=self.own_case,
            management=first_stage, requester=self.user, requester_name=self.profile.full_name,
            reason='Revisión histórica.',
        )
        migration = importlib.import_module('social.migrations.0004_backfill_case_intake')
        schema_editor = SimpleNamespace(connection=connection)
        migration.backfill_case_intake(apps, schema_editor)
        migration.backfill_case_intake(apps, schema_editor)
        self.own_case.refresh_from_db()
        self.assertIsNotNone(self.own_case.activity_id)
        self.assertIsNone(self.own_case.activity.neighbor_id)
        self.assertEqual(self.own_case.activity.delegation, self.delegation)
        self.assertEqual(self.own_case.activity.validation_status, 'Approved')
        self.assertEqual(Activity.objects.filter(social_case=self.own_case).count(), 1)

    def test_admin_decision_updates_only_initial_attention_status(self):
        created = self.client.post(reverse('social:api_casos'), data=json.dumps({
            'user_rut': '12.345.678-5', 'user_name': 'Vecina Nueva',
            'delegation_id': self.delegation.pk, 'entry_date': '2026-10-01',
            'initial_problem': 'Consulta social.',
        }), content_type='application/json')
        self.assertEqual(created.status_code, 201, created.content)
        case = SocialCase.objects.get(pk=created.json()['case']['id'])
        review_id = created.json()['review_request_id']
        resolved = self.admin_client.post(reverse('social:api_resolver_solicitud_social', args=[review_id]),
                                          data=json.dumps({'decision': 'rechazada'}), content_type='application/json')
        self.assertEqual(resolved.status_code, 200, resolved.content)
        case.activity.refresh_from_db()
        self.assertEqual(case.activity.validation_status, 'Rejected')
        advanced = self.client.post(reverse('social:api_avanzar_etapa', args=[case.pk]), data=json.dumps({
            'stage': 2, 'management_type': 'Visita domiciliaria',
            'management_date': '2026-10-20', 'result': 'Se verificaron antecedentes.',
        }), content_type='application/json')
        self.assertEqual(advanced.status_code, 200, advanced.content)
        self.admin_client.post(reverse('social:api_resolver_solicitud_social', args=[advanced.json()['review_request_id']]),
                               data=json.dumps({'decision': 'aprobada'}), content_type='application/json')
        case.activity.refresh_from_db()
        self.assertEqual(case.activity.validation_status, 'Rejected')

        approved_case = self.client.post(reverse('social:api_casos'), data=json.dumps({
            'user_rut': '21.571.404-7', 'user_name': 'Vecino Aprobado',
            'delegation_id': self.delegation.pk, 'entry_date': '2026-10-01',
            'initial_problem': 'Segunda consulta social.',
        }), content_type='application/json')
        self.assertEqual(approved_case.status_code, 201, approved_case.content)
        self.admin_client.post(reverse('social:api_resolver_solicitud_social', args=[approved_case.json()['review_request_id']]),
                               data=json.dumps({'decision': 'aprobada'}), content_type='application/json')
        second = SocialCase.objects.get(pk=approved_case.json()['case']['id'])
        self.assertEqual(second.activity.validation_status, 'Approved')

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
        self.assertNotIn('[Respaldo:', management.result)

    def test_report_does_not_invent_professional_registration_or_diagnosis(self):
        response = self.client.get(reverse('social:api_informe_social', args=[self.own_case.pk]))
        self.assertEqual(response.status_code, 200)
        report = response.json()['report']
        self.assertEqual(report['profesional']['registro_profesional'], 'Registro profesional no informado')
        self.assertIn('Borrador', report['conclusion_diagnostica'])
        self.assertNotIn('verificada territorialmente', report['conclusion_diagnostica'])

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

        response = self.client.get(reverse('social:dashboard_asistente'))

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
