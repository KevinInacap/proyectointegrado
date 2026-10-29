import json
import re
import datetime
from uuid import uuid4
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.db.models import Value
from django.db.models.functions import Replace, Upper
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator

from core.models import AuditLog
from organization.models import Delegation, UserProfile
from organization.access import is_administrator_role, role_permission_codes
from activities.models import ServiceCatalog, Vecino, Activity
from metrics.models import AttentionType, SubAttention, Goal, MeasurementPeriod
from .models import SocialCase, SocialManagement, SocialReviewRequest, SocialNotification


def _actor(request):
    """Obtiene el perfil autenticado del usuario."""
    if not request.user.is_authenticated or not request.user.is_active:
        return None
    return UserProfile.objects.select_related('delegation', 'position').filter(
        user=request.user, status='Activo', deleted_at__isnull=True
    ).first()


def _is_admin(request):
    profile = _actor(request)
    if not profile:
        return False
    if request.user.is_superuser:
        return True
    return any(is_administrator_role(role) for role in profile.roles.filter(deleted_at__isnull=True))


def _has_social_permission(request, permission):
    profile = _actor(request)
    if not profile:
        return False
    if _is_admin(request):
        return True
    return any(
        permission.casefold() in role_permission_codes(role)
        for role in profile.roles.filter(deleted_at__isnull=True).prefetch_related('permission_definitions')
    )


def _social_api_denial(request, permission):
    """Protege datos sociales por sesión, cargo, delegación y permiso vigente."""
    profile = _actor(request)
    if not profile:
        return JsonResponse({'success': False, 'message': 'Autenticación requerida.'}, status=403)
    if _is_admin(request):
        return None
    if (not profile.position or profile.position.name.casefold() != 'asistente social'
            or profile.position.status != 'Activo' or profile.position.deleted_at is not None):
        return JsonResponse({'success': False, 'message': 'El cargo no tiene acceso al módulo social.'}, status=403)
    if (not profile.delegation or profile.delegation.status != 'Activo'
            or profile.delegation.deleted_at is not None):
        return JsonResponse({'success': False, 'message': 'Se requiere una delegación activa.'}, status=403)
    if not _has_social_permission(request, permission):
        return JsonResponse({'success': False, 'message': f'El rol no tiene habilitado el permiso de {permission}.'}, status=403)
    return None


def _user_delegation_scope(request):
    if _is_admin(request):
        return None  # All delegations
    profile = _actor(request)
    if (profile and profile.delegation and profile.delegation.status == 'Activo'
            and profile.delegation.deleted_at is None):
        return profile.delegation
    return None


def _social_admin_api_denial(request):
    if not _actor(request):
        return JsonResponse({'success': False, 'message': 'Autenticación requerida.'}, status=403)
    if not _is_admin(request):
        return JsonResponse({'success': False, 'message': 'Solo administración puede revisar estas solicitudes.'}, status=403)
    return None


def _admin_users():
    profiles = UserProfile.objects.filter(
        status='Activo', deleted_at__isnull=True, user__is_active=True,
    ).select_related('user').prefetch_related('roles')
    return [
        profile.user for profile in profiles
        if any(role.deleted_at is None and is_administrator_role(role) for role in profile.roles.all())
    ]


def _create_review_request(request, *, request_type, case, reason, management=None,
                           requested_changes=None, target_label=''):
    profile = _actor(request)
    position = profile.position.name if profile and profile.position else ''
    delegation = profile.delegation.name if profile and profile.delegation else ''
    review = SocialReviewRequest.objects.create(
        request_type=request_type,
        case=case,
        management=management,
        requester=request.user,
        requester_name=profile.full_name if profile else request.user.get_username(),
        requester_position=position,
        requester_delegation=delegation,
        target_label=(target_label or f"Caso #{case.pk}") if case else (target_label or 'Gestión social'),
        reason=reason[:1200],
        requested_changes=requested_changes or {},
    )
    action = 'solicita corregir' if request_type == 'edicion' else 'solicita revisar'
    details = f"{review.requester_name} · {position or 'Cargo no asignado'} · {delegation or 'Sin delegación'} {action} {review.target_label}."
    for admin_user in _admin_users():
        SocialNotification.objects.create(
            recipient=admin_user,
            review_request=review,
            event_type='request',
            message=details,
        )
    return review


def _serialize_review_request(review):
    case = review.case
    management = review.management
    return {
        'id': review.pk,
        'request_type': review.request_type,
        'request_type_label': review.get_request_type_display(),
        'status': review.status,
        'status_label': review.get_status_display(),
        'requester_name': review.requester_name,
        'requester_position': review.requester_position,
        'requester_delegation': review.requester_delegation,
        'target_label': review.target_label,
        'reason': review.reason,
        'requested_changes': review.requested_changes,
        'resolution_note': review.resolution_note,
        'created_at': timezone.localtime(review.created_at).strftime('%d/%m/%Y %H:%M'),
        'resolved_at': timezone.localtime(review.resolved_at).strftime('%d/%m/%Y %H:%M') if review.resolved_at else None,
        'reviewer_name': review.reviewed_by.profile.full_name if review.reviewed_by and hasattr(review.reviewed_by, 'profile') else '',
        'case': {
            'id': case.pk,
            'name': case.user_name,
            'rut': case.user_rut,
            'delegation': case.delegation.name if case.delegation else '',
            'entry_date': case.entry_date.isoformat(),
        } if case else None,
        'management': {
            'id': management.pk,
            'stage': management.stage,
            'type': management.management_type,
            'date': management.management_date.isoformat(),
            'result': management.result,
        } if management else None,
    }


def _notify_requester(review):
    if not review.requester_id:
        return
    outcome = 'aprobada' if review.status == 'aprobada' else 'rechazada'
    SocialNotification.objects.get_or_create(
        recipient=review.requester,
        review_request=review,
        event_type='result',
        defaults={
            'message': f"Tu solicitud de {review.get_request_type_display().lower()} para {review.target_label} fue {outcome}."
        },
    )


def _clean_rut(rut_str):
    return re.sub(r'[^0-9kK]', '', str(rut_str or '')).upper()


def _format_rut(rut_str):
    cleaned = _clean_rut(rut_str)
    if len(cleaned) < 2:
        return rut_str
    body, dv = cleaned[:-1], cleaned[-1]
    groups = []
    while body:
        groups.insert(0, body[-3:])
        body = body[:-3]
    return f"{'.'.join(groups)}-{dv}"


def _validate_rut_m11(rut_str):
    cleaned = _clean_rut(rut_str)
    if len(cleaned) < 2 or not cleaned[:-1].isdigit():
        return False
    body, dv = cleaned[:-1], cleaned[-1]
    total, mult = 0, 2
    for digit in reversed(body):
        total += int(digit) * mult
        mult = 2 if mult == 7 else mult + 1
    res = 11 - (total % 11)
    expected = '0' if res == 11 else ('K' if res == 10 else str(res))
    return dv == expected


def _neighbor_by_rut(rut):
    normalized = Replace(
        Replace(Replace(Upper('rut'), Value('.'), Value('')), Value('-'), Value('')),
        Value(' '), Value(''),
    )
    return Vecino.objects.annotate(normalized_rut=normalized).filter(
        normalized_rut=_clean_rut(rut),
    ).first()


def _neighbor_for_case(caso, *, previous_rut=None):
    """Reuse a citizen only within the case's delegation; never move a record silently."""
    vecino = _neighbor_by_rut(caso.user_rut)
    if vecino and (vecino.deleted_at or (vecino.territorio or '').casefold() != caso.delegation.name.casefold()):
        raise ValidationError('Este RUT pertenece a un vecino inactivo o de otra delegación. Solicita a administración regularizar su padrón.')
    if not vecino and previous_rut and caso.activity_id and caso.activity.neighbor_id:
        previous = caso.activity.neighbor
        if (_clean_rut(previous.rut) == _clean_rut(previous_rut)
                and previous.deleted_at is None
                and (previous.territorio or '').casefold() == caso.delegation.name.casefold()
                and not previous.activities.exclude(pk=caso.activity_id).exists()):
            previous.rut = caso.user_rut
            vecino = previous
    if not vecino:
        vecino = Vecino(rut=caso.user_rut, territorio=caso.delegation.name)
    vecino.nombre = caso.user_name
    if caso.contact_phone:
        vecino.telefono = caso.contact_phone
    vecino.estado = 'Activo'
    vecino.save()
    return vecino


def _attention_pair(data):
    type_id, sub_id = data.get('attention_type_id'), data.get('subattention_id')
    if type_id in (None, '') and sub_id in (None, ''):
        return None, None, None  # Clients predating the catalog selection remain valid.
    if (isinstance(type_id, bool) or isinstance(sub_id, bool)
            or not str(type_id).isdecimal() or not str(sub_id).isdecimal()):
        return None, None, 'Selecciona un Tipo de Atención y una Sub Atención válidos.'
    attention_type = AttentionType.objects.filter(
        pk=type_id, status='Activo', deleted_at__isnull=True,
    ).first()
    subattention = SubAttention.objects.filter(
        pk=sub_id, status='Activo', deleted_at__isnull=True,
        attention_type=attention_type, attention_type__deleted_at__isnull=True,
    ).first() if attention_type else None
    if not subattention:
        return None, None, 'La Sub Atención no pertenece al Tipo de Atención activo seleccionado.'
    return attention_type, subattention, None


def _sync_case_activity(caso, *, previous_rut=None, problem=None, actor=None,
                        attention_type=None, subattention=None):
    """Maintain the intake attention and neighbor for a social case atomically."""
    vecino = _neighbor_for_case(caso, previous_rut=previous_rut)
    activity = caso.activity if caso.activity_id else Activity(
        activity_code=f'SOC-{caso.pk:08d}-{uuid4().hex[:6].upper()}',
        delegation=caso.delegation, user=actor,
        validation_status='Pending',
    )
    activity.neighbor = vecino
    activity.contact_name = caso.user_name
    activity.contact_phone = caso.contact_phone
    activity.activity_date = caso.entry_date
    if attention_type and subattention:
        activity.attention_type = attention_type
        activity.subattention = subattention
    if problem is not None:
        activity.problem_description = problem
    elif not activity.problem_description:
        activity.problem_description = caso.managements.filter(stage=1, deleted_at__isnull=True).values_list('result', flat=True).first() or 'Solicitud social'
    if not activity.executed_action:
        activity.executed_action = 'Ingreso de caso social para evaluación y revisión administrativa.'
    activity.save()
    if caso.activity_id != activity.pk:
        caso.activity = activity
        caso.save(update_fields=['activity', 'updated_at'])
    return activity


def _serialize_case(c):
    managements = list(c.managements.filter(deleted_at__isnull=True).order_by('stage'))
    stages_data = [
        {
            'id': m.id,
            'stage': m.stage,
            'management_type': m.management_type,
            'catalog': m.catalog.service if m.catalog else '',
            'catalog_id': m.catalog_id,
            'management_date': m.management_date.strftime('%d/%m/%Y'),
            'management_date_iso': m.management_date.isoformat(),
            'result': m.result,
        }
        for m in managements
    ]
    curr_stage = max([m.stage for m in managements], default=1)
    return {
        'id': c.id,
        'activity_id': c.activity_id,
        'neighbor_id': c.activity.neighbor_id if c.activity_id else None,
        'user_name': c.user_name,
        'user_rut': c.user_rut,
        'contact_phone': c.contact_phone,
        'delegation_id': c.delegation_id,
        'delegation': c.delegation.name if c.delegation else '',
        'entry_date': c.entry_date.strftime('%d/%m/%Y'),
        'entry_date_iso': c.entry_date.isoformat(),
        'current_stage': curr_stage,
        'status_label': (
            'Etapa 1: Ingreso' if curr_stage == 1 else (
                'Etapa 2: Visita en Terreno' if curr_stage == 2 else 'Etapa 3: Resuelto / Cierre'
            )
        ),
        'is_resolved': curr_stage == 3,
        'can_advance': curr_stage < 3,
        'next_stage': min(curr_stage + 1, 3),
        'stages': stages_data,
        'total_stages': len(stages_data),
    }


def _validated_case_changes(data):
    allowed = {'user_name', 'user_rut', 'contact_phone', 'entry_date', 'initial_problem'}
    if set(data) - allowed:
        return None, 'La solicitud contiene campos que no se pueden modificar.'
    changes = {}
    if 'user_name' in data:
        name = str(data.get('user_name') or '').strip()
        if not name or len(name) > 150:
            return None, 'El nombre debe contener entre 1 y 150 caracteres.'
        changes['user_name'] = name
    if 'user_rut' in data:
        rut = str(data.get('user_rut') or '').strip()
        if not _validate_rut_m11(rut) or len(_format_rut(rut)) > SocialCase._meta.get_field('user_rut').max_length:
            return None, 'El RUT propuesto no es válido.'
        changes['user_rut'] = _format_rut(rut)
    if 'contact_phone' in data:
        phone = str(data.get('contact_phone') or '').strip()
        if len(phone) > 20:
            return None, 'El teléfono no puede superar 20 caracteres.'
        changes['contact_phone'] = phone
    if 'entry_date' in data:
        try:
            entry_date = datetime.date.fromisoformat(str(data.get('entry_date') or ''))
        except ValueError:
            return None, 'La fecha de ingreso propuesta no es válida.'
        if entry_date > timezone.localdate():
            return None, 'La fecha de ingreso no puede ser futura.'
        changes['entry_date'] = entry_date.isoformat()
    if 'initial_problem' in data:
        problem = str(data.get('initial_problem') or '').strip()
        if not problem or len(problem) > 4000:
            return None, 'El diagnóstico o motivo del caso debe contener entre 1 y 4000 caracteres.'
        changes['initial_problem'] = problem
    if not changes:
        return None, 'Indica al menos un dato que quieras corregir.'
    return changes, None


def dashboard_asistente_view(request):
    """
    Panel Principal de Trabajo para Asistente Social.
    Ilustre Municipalidad de La Serena.
    Cumple con RN-012, RF-015 y matriz RBAC.
    """
    profile = _actor(request)
    if not profile:
        return redirect('core:login')

    if (not profile.position or profile.position.name.casefold() != 'asistente social'
            or profile.position.status != 'Activo' or profile.position.deleted_at is not None):
        return redirect('core:login')

    if not _has_social_permission(request, 'lectura'):
        from activities.views import _position_dashboard
        return _position_dashboard(request, 'Asistente Social')

    user_delegation = _user_delegation_scope(request)
    is_admin = _is_admin(request)

    # Scoping de casos sociales
    cases_qs = SocialCase.objects.filter(deleted_at__isnull=True).select_related('delegation').prefetch_related('managements')
    if user_delegation:
        cases_qs = cases_qs.filter(delegation=user_delegation)
    elif not is_admin:
        cases_qs = cases_qs.none()

    # KPIs de Casos
    total_cases = cases_qs.count()
    
    # Cálculos por etapa (RN-012)
    stage1_cases = 0
    stage2_cases = 0
    stage3_cases = 0

    all_cases_list = list(cases_qs)
    for c in all_cases_list:
        st = c.current_stage
        if st == 1:
            stage1_cases += 1
        elif st == 2:
            stage2_cases += 1
        elif st == 3:
            stage3_cases += 1

    # No entregar al trabajador opciones de sedes ajenas en el formulario.
    delegations = Delegation.objects.filter(status='Activo', deleted_at__isnull=True).order_by('name')
    if user_delegation:
        delegations = delegations.filter(pk=user_delegation.pk)
    elif not is_admin:
        delegations = delegations.none()

    # Catálogo de servicios / prestaciones
    catalogs = ServiceCatalog.objects.filter(status='Activo', deleted_at__isnull=True).order_by('service')

    # Vecinos de la delegación o comuna
    vecinos_qs = Vecino.objects.filter(deleted_at__isnull=True)
    if user_delegation:
        vecinos_qs = vecinos_qs.filter(territorio__iexact=user_delegation.name)
    elif not is_admin:
        vecinos_qs = vecinos_qs.none()
    vecinos = vecinos_qs.order_by('nombre')[:100]

    # Meta SGR y Semáforo (RN-007, RN-008)
    # Período actual
    today = timezone.localdate()
    period = MeasurementPeriod.objects.filter(
        deleted_at__isnull=True, status='Abierto', start_date__lte=today, end_date__gte=today,
    ).order_by('-start_date').first()
    if not period:
        period = MeasurementPeriod.objects.filter(deleted_at__isnull=True).order_by('-start_date').first()
    computable_days = period.computable_days if period else 0
    days_elapsed = min(max((today - period.start_date).days + 1, 0), computable_days) if period and computable_days else 0
    meta_esperada_pct = round((days_elapsed / computable_days) * 100, 1) if computable_days else None

    # Meta específica Asistente Social
    asistente_goal = Goal.objects.filter(
        deleted_at__isnull=True,
        status='Activo',
        position=profile.position,
        period=period
    ).select_related('item').filter(item__status='Activo', item__deleted_at__isnull=True).order_by('item__name').first()
    target_value = float(asistente_goal.target_value) if asistente_goal else None
    goal_weight = float(asistente_goal.weight) if asistente_goal else None

    # Avance real: gestiones realizadas
    total_gestiones = SocialManagement.objects.filter(deleted_at__isnull=True)
    if user_delegation:
        total_gestiones = total_gestiones.filter(case__delegation=user_delegation)
    elif not is_admin:
        total_gestiones = total_gestiones.none()
    if period:
        total_gestiones = total_gestiones.filter(
            management_date__gte=period.start_date, management_date__lte=period.end_date,
        )
    gestiones_count = total_gestiones.count()

    avance_pct = round((gestiones_count / target_value) * 100, 1) if target_value else None

    # Semáforo RN-008
    if avance_pct is None or meta_esperada_pct is None:
        semaforo_color = 'neutral'
        semaforo_texto = 'Sin meta activa para este cargo y período'
    elif avance_pct >= meta_esperada_pct:
        semaforo_color = 'green'
        semaforo_texto = 'Verde (Cumplimiento Normal)'
    elif avance_pct >= (meta_esperada_pct * 0.6):
        semaforo_color = 'amber'
        semaforo_texto = 'Ámbar (Prevención)'
    else:
        semaforo_color = 'red'
        semaforo_texto = 'Rojo (Rezago)'

    # Visitas domiciliarias programadas / en terreno (Etapa 2)
    visitas_terreno = SocialManagement.objects.filter(
        stage=2, deleted_at__isnull=True
    ).select_related('case', 'case__delegation').order_by('-management_date')

    # Subsidios y ayudas entregadas (Etapa 3)
    subsidios_entregados = SocialManagement.objects.filter(
        stage=3, deleted_at__isnull=True
    ).select_related('case', 'catalog', 'case__delegation').order_by('-management_date')
    if user_delegation:
        visitas_terreno = visitas_terreno.filter(case__delegation=user_delegation)
        subsidios_entregados = subsidios_entregados.filter(case__delegation=user_delegation)
    elif not is_admin:
        visitas_terreno = visitas_terreno.none()
        subsidios_entregados = subsidios_entregados.none()
    visitas_terreno = visitas_terreno[:10]
    subsidios_entregados = subsidios_entregados[:10]

    user_name = profile.full_name if profile else request.user.get_full_name() or request.user.username
    user_rut = profile.rut if profile else '18.420.915-K'
    delegation_name = user_delegation.name if user_delegation else 'Consolidado Comunal (Todas las Sedes)'

    context = {
        'user_name': user_name,
        'first_name': user_name.split()[0] if user_name else 'Asistente',
        'user_rut': user_rut,
        'user_role': 'Asistente Social',
        'current_delegation': delegation_name,
        'delegations': delegations,
        'catalogs': catalogs,
        'vecinos': vecinos,
        'cases': [_serialize_case(c) for c in cases_qs[:50]],
        'total_cases': total_cases,
        'stage1_cases': stage1_cases,
        'stage2_cases': stage2_cases,
        'stage3_cases': stage3_cases,
        'gestiones_count': gestiones_count,
        'target_value': int(target_value) if target_value is not None else None,
        'goal_weight': goal_weight,
        'goal_item_name': asistente_goal.item.name if asistente_goal else 'Sin ítem asignado',
        'goal_unit': asistente_goal.unit_of_measure if asistente_goal else 'gestiones',
        'has_goal': target_value is not None,
        'avance_pct': avance_pct,
        'avance_bar_width': min(max(avance_pct or 0, 0), 100),
        'avance_label': f'{avance_pct:g}%' if avance_pct is not None else 'Sin meta',
        'meta_esperada_pct': f'{meta_esperada_pct:g}%' if meta_esperada_pct is not None else '—',
        'semaforo_color': semaforo_color,
        'semaforo_texto': semaforo_texto,
        'visitas_terreno': visitas_terreno,
        'subsidios_entregados': subsidios_entregados,
        'today': timezone.localdate().isoformat(),
        'period_name': period.name if period else 'Sin período configurado',
    }
    return render(request, 'activities/dashboard_asistente.html', context)


# =========================================================================
# APIs REST / AJAX PARA EL DASHBOARD DE ASISTENTE SOCIAL
# =========================================================================

def api_casos_sociales(request):
    """Listar o crear Casos Sociales con validación Módulo 11."""
    if request.method not in {'GET', 'POST'}:
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)

    denied = _social_api_denial(request, 'lectura' if request.method == 'GET' else 'edicion')
    if denied:
        return denied

    user_delegation = _user_delegation_scope(request)

    if request.method == 'GET':
        qs = SocialCase.objects.filter(deleted_at__isnull=True).select_related('delegation').prefetch_related('managements')
        if user_delegation:
            qs = qs.filter(delegation=user_delegation)
        else:
            delegation_filter = request.GET.get('delegacion', '').strip()
            if delegation_filter:
                qs = qs.filter(delegation__name__iexact=delegation_filter)

        query = request.GET.get('q', '').strip()
        if query:
            qs = qs.filter(
                Q(user_name__icontains=query)
                | Q(user_rut__icontains=query)
                | Q(delegation__name__icontains=query)
                | Q(managements__result__icontains=query)
            ).distinct()

        stage_filter = request.GET.get('stage') or request.GET.get('etapa')
        if stage_filter and str(stage_filter).isdigit():
            # Filtrar por etapa actual
            target_stage = int(stage_filter)
            cases_matching = [c for c in qs if c.current_stage == target_stage]
        else:
            cases_matching = list(qs[:100])

        serialized_all = [_serialize_case(c) for c in cases_matching]
        paginator = Paginator(serialized_all, 8)
        page_obj = paginator.get_page(request.GET.get('page') or 1)
        return JsonResponse({
            'success': True,
            'cases': serialized_all,
            'paginated_cases': list(page_obj.object_list),
            'pagination': {
                'page': page_obj.number,
                'num_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_previous': page_obj.has_previous(),
                'has_next': page_obj.has_next(),
                'start_index': page_obj.start_index() if paginator.count else 0,
                'end_index': page_obj.end_index() if paginator.count else 0,
            },
        })

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'success': False, 'message': 'Datos JSON inválidos.'}, status=400)
        if not isinstance(data, dict):
            return JsonResponse({'success': False, 'message': 'El cuerpo debe ser un objeto JSON.'}, status=400)

        rut_raw = str(data.get('user_rut', '')).strip()
        nombre = str(data.get('user_name', '')).strip()
        telefono = str(data.get('contact_phone', '')).strip()
        delegation_id = data.get('delegation_id')
        entry_date_str = data.get('entry_date') or timezone.localdate().isoformat()
        initial_problem = str(data.get('initial_problem', '')).strip()

        if not nombre or not rut_raw:
            return JsonResponse({'success': False, 'message': 'El nombre y el RUT del vecino son obligatorios.'}, status=400)

        if not _validate_rut_m11(rut_raw):
            return JsonResponse({'success': False, 'message': 'El RUT ingresado no es válido (Módulo 11).'}, status=400)

        rut_formateado = _format_rut(rut_raw)
        if len(rut_formateado) > SocialCase._meta.get_field('user_rut').max_length:
            return JsonResponse({'success': False, 'message': 'El RUT supera el largo permitido.'}, status=400)
        attention_type, subattention, classification_error = _attention_pair(data)
        if classification_error:
            return JsonResponse({'success': False, 'message': classification_error}, status=400)

        # Delegación
        if user_delegation:
            if delegation_id not in (None, '', user_delegation.pk, str(user_delegation.pk)):
                return JsonResponse({'success': False, 'message': 'Solo puedes registrar casos en tu delegación.'}, status=403)
            delegation = user_delegation
        else:
            if isinstance(delegation_id, bool) or not str(delegation_id or '').isdecimal():
                return JsonResponse({'success': False, 'message': 'Selecciona una delegación activa para el caso.'}, status=400)
            delegation = Delegation.objects.filter(pk=delegation_id, status='Activo', deleted_at__isnull=True).first()
        if not delegation:
            return JsonResponse({'success': False, 'message': 'Selecciona una delegación activa para el caso.'}, status=400)
        if len(nombre) > 150 or len(telefono) > 20 or len(initial_problem) > 4000:
            return JsonResponse({'success': False, 'message': 'El nombre admite 150 caracteres, el teléfono 20 y el motivo de ingreso 4000.'}, status=400)

        try:
            entry_date = datetime.date.fromisoformat(str(entry_date_str))
            if entry_date > timezone.localdate():
                return JsonResponse({'success': False, 'message': 'La fecha de ingreso no puede ser futura.'}, status=400)
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'message': 'La fecha de ingreso no es válida.'}, status=400)

        problem = initial_problem or 'Ingreso de solicitud social y evaluación preliminar de vulnerabilidad socioeconómica.'
        try:
            with transaction.atomic():
                # Serializa los envíos repetidos del mismo funcionario en motores con row locks.
                get_user_model().objects.select_for_update().get(pk=request.user.pk)
                recent = SocialCase.objects.filter(
                    user_rut=rut_formateado, user_name=nombre, delegation=delegation,
                    entry_date=entry_date, activity__user=request.user,
                    created_at__gte=timezone.now() - datetime.timedelta(seconds=30),
                    managements__stage=1, managements__result=problem,
                    deleted_at__isnull=True,
                ).first()
                if recent:
                    review_id = recent.review_requests.filter(management__stage=1).values_list('pk', flat=True).first()
                    return JsonResponse({
                        'success': True, 'message': 'La solicitud ya estaba registrada.',
                        'case': _serialize_case(recent), 'review_request_id': review_id,
                    })

                caso = SocialCase.objects.create(
                    user_rut=rut_formateado, user_name=nombre, contact_phone=telefono,
                    delegation=delegation, entry_date=entry_date,
                )
                gestion1 = SocialManagement.objects.create(
                    case=caso, stage=1, catalog=None,
                    management_type='Ingreso y recepción de antecedentes',
                    management_date=entry_date, result=problem,
                )
                activity = _sync_case_activity(
                    caso, problem=problem, actor=request.user,
                    attention_type=attention_type, subattention=subattention,
                )
                AuditLog.objects.create(
                    user=request.user, affected_table='caso_social',
                    affected_record_id=str(caso.id), action='CREATE',
                    new_value=_serialize_case(caso), source_ip=request.META.get('REMOTE_ADDR'),
                )
                AuditLog.objects.create(
                    user=request.user, affected_table='actividad',
                    affected_record_id=str(activity.pk), action='CREATE',
                    new_value={'social_case_id': caso.pk, 'activity_code': activity.activity_code,
                               'delegation': delegation.name},
                    source_ip=request.META.get('REMOTE_ADDR'),
                )
                review = None
                if not _is_admin(request):
                    review = _create_review_request(
                        request, request_type='revision', case=caso, management=gestion1,
                        reason='Nuevo caso social registrado; requiere revisión administrativa.',
                        target_label=f'Caso #{caso.pk} · {caso.user_name} · Etapa 1',
                    )
        except ValidationError as error:
            return JsonResponse({'success': False, 'message': error.messages[0]}, status=409)
        except IntegrityError:
            if _neighbor_by_rut(rut_formateado):
                return JsonResponse({
                    'success': False,
                    'message': 'El RUT ya está registrado; recarga el padrón y revisa su delegación.',
                }, status=409)
            raise

        return JsonResponse({
            'success': True,
            'message': f'Ficha Social de {caso.user_name} registrada con éxito (Etapa 1: Ingreso).' + (' La administración recibió una solicitud de revisión.' if review else ''),
            'case': _serialize_case(caso),
            'review_request_id': review.pk if review else None,
        }, status=201)


def api_caso_detalle(request, pk):
    """Detalle, edición y baja lógica de un Caso Social."""
    if request.method not in {'GET', 'POST', 'PUT', 'DELETE'}:
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    permission = 'lectura' if request.method == 'GET' else ('cierre' if request.method == 'DELETE' else 'edicion')
    denied = _social_api_denial(request, permission)
    if denied:
        return denied

    user_delegation = _user_delegation_scope(request)
    qs = SocialCase.objects.filter(deleted_at__isnull=True).select_related('delegation').prefetch_related('managements')
    if user_delegation:
        qs = qs.filter(delegation=user_delegation)
    elif not _is_admin(request):
        qs = qs.none()

    caso = qs.filter(pk=pk).first()
    if not caso:
        return JsonResponse({'success': False, 'message': 'Caso Social no encontrado o fuera de tu jurisdicción.'}, status=404)

    if request.method == 'GET':
        return JsonResponse({'success': True, 'case': _serialize_case(caso)})

    elif request.method in {'PUT', 'POST'}:
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'success': False, 'message': 'Datos JSON inválidos.'}, status=400)
        if not isinstance(data, dict):
            return JsonResponse({'success': False, 'message': 'El cuerpo debe ser un objeto JSON.'}, status=400)

        request_type = str(data.pop('request_type', '')).strip().casefold()
        reason = str(data.pop('reason', '')).strip()
        changes, error = _validated_case_changes(data)
        if error:
            return JsonResponse({'success': False, 'message': error}, status=400)

        if not _is_admin(request) and request_type == 'solicitud':
            if len(reason) < 8:
                return JsonResponse({'success': False, 'message': 'Explica brevemente por qué se requiere la corrección (mínimo 8 caracteres).'}, status=400)
            with transaction.atomic():
                review = _create_review_request(
                    request,
                    request_type='edicion',
                    case=caso,
                    reason=reason,
                    requested_changes=changes,
                    target_label=f"Caso #{caso.pk} · {caso.user_name}",
                )
                AuditLog.objects.create(
                    user=request.user,
                    affected_table='solicitud_revision_social',
                    affected_record_id=str(review.pk),
                    action='CREATE',
                    new_value=_serialize_review_request(review),
                    source_ip=request.META.get('REMOTE_ADDR'),
                )
            return JsonResponse({
                'success': True,
                'message': f'La corrección del caso #{caso.pk} quedó pendiente de aprobación administrativa.',
                'review_request_id': review.pk,
            }, status=202)

        prev = _serialize_case(caso)
        previous_rut = caso.user_rut
        initial_problem = changes.pop('initial_problem', None)
        try:
            with transaction.atomic():
                for field, value in changes.items():
                    setattr(caso, field, datetime.date.fromisoformat(value) if field == 'entry_date' else value)
                caso.full_clean()
                caso.save()
                if initial_problem:
                    stage1_mgmt = caso.managements.filter(stage=1, deleted_at__isnull=True).first()
                    if stage1_mgmt:
                        stage1_mgmt.result = initial_problem
                        stage1_mgmt.save(update_fields=['result', 'updated_at'])
                    else:
                        SocialManagement.objects.create(
                            case=caso, stage=1, catalog=None,
                            management_type='Ingreso y recepción de antecedentes',
                            management_date=caso.entry_date, result=initial_problem,
                        )
                _sync_case_activity(caso, previous_rut=previous_rut, problem=initial_problem, actor=request.user)
                AuditLog.objects.create(
                    user=request.user, affected_table='caso_social',
                    affected_record_id=str(caso.id), action='UPDATE',
                    previous_value=prev, new_value=_serialize_case(caso),
                    source_ip=request.META.get('REMOTE_ADDR'),
                )
        except ValidationError as error:
            return JsonResponse({'success': False, 'message': error.messages[0]}, status=409)
        return JsonResponse({'success': True, 'message': f'Ficha social de {caso.user_name} actualizada en la base de datos.', 'case': _serialize_case(caso)})

    elif request.method == 'DELETE':
        prev = _serialize_case(caso)
        with transaction.atomic():
            caso.deleted_at = timezone.now()
            caso.save(update_fields=['deleted_at', 'updated_at'])
            if caso.activity_id:
                Activity.objects.filter(pk=caso.activity_id).update(deleted_at=caso.deleted_at)
            AuditLog.objects.create(
                user=request.user, affected_table='caso_social',
                affected_record_id=str(caso.id), action='DELETE',
                previous_value=prev, source_ip=request.META.get('REMOTE_ADDR'),
            )
        return JsonResponse({'success': True, 'message': f'Caso social #{caso.id} dado de baja.'})

    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)


def api_avanzar_etapa(request, pk):
    """
    Avanza la gestión del caso a la Etapa 2 o Etapa 3 conforme a RN-012.
    RN-012: Máximo 3 etapas consecutivas (1: Ingreso, 2: Terreno/Evidencia, 3: Cierre/Subsidio).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método POST requerido.'}, status=405)

    denied = _social_api_denial(request, 'derivacion')
    if denied:
        return denied

    cases = SocialCase.objects.filter(pk=pk, deleted_at__isnull=True).prefetch_related('managements')
    user_delegation = _user_delegation_scope(request)
    if user_delegation:
        cases = cases.filter(delegation=user_delegation)
    elif not _is_admin(request):
        cases = cases.none()
    caso = cases.first()
    if not caso:
        return JsonResponse({'success': False, 'message': 'Caso social inexistente.'}, status=404)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'message': 'JSON inválido.'}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({'success': False, 'message': 'El cuerpo debe ser un objeto JSON.'}, status=400)

    curr_stage = caso.current_stage
    if curr_stage >= 3:
        return JsonResponse({
            'success': False,
            'message': 'Por normativa comunal (RN-012), este caso ya completó las 3 etapas máximas permitidas y se encuentra cerrado.'
        }, status=400)

    next_stage = curr_stage + 1
    try:
        target_stage = int(data.get('stage') or next_stage)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': 'La etapa indicada no es válida.'}, status=400)
    if target_stage != next_stage:
        return JsonResponse({
            'success': False,
            'message': f'Secuencia inválida (RN-012). Debe registrar la Etapa {next_stage} antes de continuar.'
        }, status=400)

    tipo_gestion = str(data.get('management_type') or (
        "Visita en terreno y levantamiento técnico" if next_stage == 2 else "Resolución, dictamen y entrega de prestación"
    )).strip()
    if not tipo_gestion or len(tipo_gestion) > 100:
        return JsonResponse({'success': False, 'message': 'El tipo de gestión debe tener entre 1 y 100 caracteres.'}, status=400)

    resultado = str(data.get('result', '')).strip()
    if not resultado:
        return JsonResponse({'success': False, 'message': 'El informe o resultado de la gestión es obligatorio.'}, status=400)

    # Catálogo de servicio vinculado
    catalog_id = data.get('catalog_id')
    catalog = None
    if catalog_id:
        if isinstance(catalog_id, bool) or not str(catalog_id).isdigit():
            return JsonResponse({'success': False, 'message': 'El servicio seleccionado no es válido.'}, status=400)
        catalog = ServiceCatalog.objects.filter(pk=catalog_id, deleted_at__isnull=True).first()
        if not catalog:
            return JsonResponse({'success': False, 'message': 'El servicio seleccionado ya no está disponible.'}, status=400)

    # Un código solo se registra si corresponde a un respaldo real aportado.
    evidence_code = str(data.get('evidence_code', '')).strip()
    if evidence_code:
        resultado = f"[Respaldo: {evidence_code}] {resultado}"

    # Si es etapa 3: Ayuda o subsidio entregado
    benefit = str(data.get('benefit', '')).strip()
    if next_stage == 3 and benefit:
        resultado = f"[Subsidio/Prestación: {benefit}] {resultado}"

    try:
        date_obj = datetime.date.fromisoformat(str(data.get('management_date') or timezone.localdate().isoformat()))
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': 'La fecha de gestión no es válida.'}, status=400)
    if date_obj > timezone.localdate():
        return JsonResponse({'success': False, 'message': 'La fecha de gestión no puede ser futura.'}, status=400)

    with transaction.atomic():
        mgmt = SocialManagement.objects.create(
            case=caso,
            stage=next_stage,
            catalog=catalog,
            management_type=tipo_gestion,
            management_date=date_obj,
            result=resultado
        )

        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            affected_table='gestion_social',
            affected_record_id=str(mgmt.id),
            action='CREATE',
            new_value={
                'case_id': caso.id,
                'stage': next_stage,
                'type': tipo_gestion,
                'result': resultado
            },
            source_ip=request.META.get('REMOTE_ADDR')
        )

        review = None
        if not _is_admin(request):
            review = _create_review_request(
                request,
                request_type='revision',
                case=caso,
                management=mgmt,
                reason=f"Nueva gestión social de etapa {next_stage} registrada; requiere revisión administrativa.",
                target_label=f"Caso #{caso.pk} · {caso.user_name} · Etapa {next_stage}",
            )

    return JsonResponse({
        'success': True,
        'message': f'Etapa {next_stage} registrada exitosamente para {caso.user_name}.' + (' La administración recibió una solicitud de revisión.' if review else ''),
        'case': _serialize_case(caso),
        'review_request_id': review.pk if review else None,
    })


def api_solicitud_caso(request, pk):
    """Registrar una solicitud explícita de revisión/corrección de un asistente."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método POST requerido.'}, status=405)
    denied = _social_api_denial(request, 'edicion')
    if denied:
        return denied
    if _is_admin(request):
        return JsonResponse({'success': False, 'message': 'Administración puede actuar directamente sobre el caso.'}, status=400)

    scope = _user_delegation_scope(request)
    caso = SocialCase.objects.filter(pk=pk, deleted_at__isnull=True, delegation=scope).first() if scope else None
    if not caso:
        return JsonResponse({'success': False, 'message': 'Caso no encontrado dentro de tu delegación.'}, status=404)
    try:
        data = json.loads(request.body)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': 'Datos JSON inválidos.'}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({'success': False, 'message': 'El cuerpo debe ser un objeto JSON.'}, status=400)

    request_type = str(data.get('request_type', 'revision')).strip().casefold()
    reason = str(data.get('reason', '')).strip()
    if request_type not in {'revision', 'edicion'}:
        return JsonResponse({'success': False, 'message': 'Tipo de solicitud no válido.'}, status=400)
    if len(reason) < 8:
        return JsonResponse({'success': False, 'message': 'Explica brevemente el motivo (mínimo 8 caracteres).'}, status=400)

    changes = {}
    if request_type == 'edicion':
        proposed = data.get('requested_changes')
        if not isinstance(proposed, dict):
            return JsonResponse({'success': False, 'message': 'Incluye los datos propuestos para la corrección.'}, status=400)
        changes, error = _validated_case_changes(proposed)
        if error:
            return JsonResponse({'success': False, 'message': error}, status=400)
    elif data.get('requested_changes'):
        return JsonResponse({'success': False, 'message': 'Una solicitud de revisión no debe incluir cambios de datos.'}, status=400)

    with transaction.atomic():
        review = _create_review_request(
            request,
            request_type=request_type,
            case=caso,
            reason=reason,
            requested_changes=changes,
            target_label=f"Caso #{caso.pk} · {caso.user_name}",
        )
        AuditLog.objects.create(
            user=request.user,
            affected_table='solicitud_revision_social',
            affected_record_id=str(review.pk),
            action='CREATE',
            new_value=_serialize_review_request(review),
            source_ip=request.META.get('REMOTE_ADDR'),
        )
    return JsonResponse({
        'success': True,
        'message': f"Solicitud de {review.get_request_type_display().lower()} enviada a administración.",
        'review_request_id': review.pk,
    }, status=201)


def api_solicitudes_sociales(request):
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': 'Método GET requerido.'}, status=405)
    denied = _social_admin_api_denial(request)
    if denied:
        return denied
    status = request.GET.get('status', 'pendiente')
    valid_statuses = {value for value, _ in SocialReviewRequest.STATUS_CHOICES}
    if status not in valid_statuses and status != 'todas':
        return JsonResponse({'success': False, 'message': 'Filtro de estado no válido.'}, status=400)
    qs = SocialReviewRequest.objects.filter(deleted_at__isnull=True).select_related(
        'case', 'case__delegation', 'management', 'requester', 'reviewed_by',
    )
    if status != 'todas':
        qs = qs.filter(status=status)
    requests_data = [_serialize_review_request(item) for item in qs[:200]]
    pending_count = SocialReviewRequest.objects.filter(status='pendiente', deleted_at__isnull=True).count()
    return JsonResponse({'success': True, 'requests': requests_data, 'count': len(requests_data), 'pending_count': pending_count})


def api_resolver_solicitud_social(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método POST requerido.'}, status=405)
    denied = _social_admin_api_denial(request)
    if denied:
        return denied
    try:
        data = json.loads(request.body)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': 'Datos JSON inválidos.'}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({'success': False, 'message': 'El cuerpo debe ser un objeto JSON.'}, status=400)
    decision = str(data.get('decision', '')).strip().casefold()
    note = str(data.get('resolution_note', '')).strip()
    if decision not in {'aprobada', 'rechazada'}:
        return JsonResponse({'success': False, 'message': 'Selecciona aprobar o rechazar la solicitud.'}, status=400)
    if len(note) > 1000:
        return JsonResponse({'success': False, 'message': 'La observación no puede superar 1000 caracteres.'}, status=400)

    with transaction.atomic():
        review = SocialReviewRequest.objects.select_for_update().filter(
            pk=pk, deleted_at__isnull=True,
        ).first()
        if not review:
            return JsonResponse({'success': False, 'message': 'Solicitud no encontrada.'}, status=404)
        if review.status != 'pendiente':
            return JsonResponse({'success': False, 'message': 'Esta solicitud ya fue resuelta.'}, status=409)

        previous_case = _serialize_case(review.case) if review.case else None
        if decision == 'aprobada' and review.request_type == 'edicion':
            caso = SocialCase.objects.select_for_update().filter(
                pk=review.case_id, deleted_at__isnull=True,
            ).first()
            if not caso:
                return JsonResponse({'success': False, 'message': 'El caso asociado ya no está disponible; la solicitud no se resolvió.'}, status=409)
            changes, error = _validated_case_changes(review.requested_changes or {})
            if error:
                return JsonResponse({'success': False, 'message': f'La corrección guardada ya no es válida: {error}'}, status=409)
            previous_rut = caso.user_rut
            try:
                with transaction.atomic():
                    for field, value in changes.items():
                        setattr(caso, field, datetime.date.fromisoformat(value) if field == 'entry_date' else value)
                    caso.full_clean()
                    caso.save()
                    _sync_case_activity(caso, previous_rut=previous_rut, actor=request.user)
            except ValidationError as error:
                return JsonResponse({'success': False, 'message': error.messages[0]}, status=409)
            review.case = caso

        review.status = decision
        review.reviewed_by = request.user
        review.resolution_note = note
        review.resolved_at = timezone.now()
        review.save(update_fields=['status', 'reviewed_by', 'resolution_note', 'resolved_at', 'updated_at'])
        if (review.request_type == 'revision' and review.management_id
                and review.management.stage == 1 and review.case and review.case.activity_id):
            Activity.objects.filter(pk=review.case.activity_id).update(
                validation_status='Approved' if decision == 'aprobada' else 'Rejected',
            )
        _notify_requester(review)
        AuditLog.objects.create(
            user=request.user,
            affected_table='solicitud_revision_social',
            affected_record_id=str(review.pk),
            action='UPDATE',
            previous_value={'status': 'pendiente', 'case': previous_case},
            new_value={
                'status': review.status,
                'resolution_note': review.resolution_note,
                'reviewed_by': request.user.get_username(),
                'case': _serialize_case(review.case) if review.case else None,
            },
            source_ip=request.META.get('REMOTE_ADDR'),
        )

    return JsonResponse({
        'success': True,
        'message': f"Solicitud {review.get_status_display().lower()} correctamente.",
        'request': _serialize_review_request(review),
    })


def api_notificaciones_sociales(request):
    denied = _social_admin_api_denial(request)
    if denied:
        return denied
    notifications = SocialNotification.objects.filter(
        recipient=request.user, event_type='request', deleted_at__isnull=True,
    ).select_related('review_request')
    if request.method == 'GET':
        rows = [{
            'id': item.pk,
            'request_id': item.review_request_id,
            'message': item.message,
            'created_at': timezone.localtime(item.created_at).strftime('%d/%m/%Y %H:%M'),
            'is_read': item.read_at is not None,
        } for item in notifications[:40]]
        unread_count = notifications.filter(read_at__isnull=True).count()
        return JsonResponse({'success': True, 'notifications': rows, 'unread_count': unread_count})
    if request.method == 'POST':
        try:
            data = json.loads(request.body or '{}')
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'message': 'Datos JSON inválidos.'}, status=400)
        mark_all = isinstance(data, dict) and data.get('all') is True
        ids = data.get('ids', []) if isinstance(data, dict) else None
        if mark_all:
            updated = notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
            return JsonResponse({'success': True, 'updated': updated})
        if ids is None or not isinstance(ids, list) or any(isinstance(value, bool) or not str(value).isdigit() for value in ids):
            return JsonResponse({'success': False, 'message': 'Lista de notificaciones no válida.'}, status=400)
        target = notifications.filter(pk__in=[int(value) for value in ids], read_at__isnull=True)
        updated = target.update(read_at=timezone.now())
        return JsonResponse({'success': True, 'updated': updated})
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)


def api_informe_social(request, pk):
    """
    Prepara un borrador trazable del informe social municipal, sin firma.
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    denied = _social_api_denial(request, 'lectura')
    if denied:
        return denied

    cases = SocialCase.objects.filter(pk=pk, deleted_at__isnull=True).select_related('delegation').prefetch_related('managements')
    user_delegation = _user_delegation_scope(request)
    if user_delegation:
        cases = cases.filter(delegation=user_delegation)
    elif not _is_admin(request):
        cases = cases.none()
    caso = cases.first()
    if not caso:
        return JsonResponse({'success': False, 'message': 'Caso social no encontrado.'}, status=404)

    profile = _actor(request)
    worker_name = profile.full_name if profile else "Asistente Social Municipal"
    worker_rut = profile.rut if profile else ""

    managements = list(caso.managements.filter(deleted_at__isnull=True).order_by('stage'))

    report_data = {
        'folio': f"INF-SOC-{caso.id:05d}-{timezone.localdate().year}",
        'fecha_emision': timezone.now().strftime('%d de %B de %Y'),
        'municipalidad': "Ilustre Municipalidad de La Serena",
        'departamento': "Dirección de Desarrollo Comunitario (DIDECO) · Asistencia Social",
        'delegacion': caso.delegation.name if caso.delegation else "Sede Central",
        'vecino': {
            'nombre': caso.user_name,
            'rut': caso.user_rut,
            'telefono': caso.contact_phone,
            'fecha_ingreso': caso.entry_date.strftime('%d/%m/%Y'),
        },
        'profesional': {
            'nombre': worker_name,
            'rut': worker_rut,
            'cargo': "Asistente Social / Trabajador Social",
            'registro_profesional': "Registro profesional no informado",
        },
        'etapa_actual': caso.status_label,
        'gestiones': [
            {
                'etapa': m.stage,
                'tipo': m.management_type,
                'fecha': m.management_date.strftime('%d/%m/%Y'),
                'servicio': m.catalog.service if m.catalog else "Atención Social General",
                'dictamen': m.result,
            }
            for m in managements
        ],
        'conclusion_diagnostica': (
            "Borrador generado a partir de las gestiones registradas. "
            "La evaluación socioeconómica y el dictamen deben ser redactados y validados "
            "por un profesional responsable antes de emitir un documento oficial."
        ),
    }

    return JsonResponse({'success': True, 'report': report_data})

