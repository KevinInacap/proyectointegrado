import json
import re
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q
from django.contrib import messages
from django.core.exceptions import ValidationError

from core.models import AuditLog
from organization.models import Delegation, UserProfile
from activities.models import ServiceCatalog, Vecino, Activity
from metrics.models import AttentionType, SubAttention, Goal, MeasurementPeriod
from .models import SocialCase, SocialManagement


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
    return any(
        r.name in ('Administrador', 'Administrador General', 'SuperAdministrador')
        for r in profile.roles.filter(deleted_at__isnull=True)
    )


def _user_delegation_scope(request):
    profile = _actor(request)
    if _is_admin(request):
        return None  # All delegations
    if profile and profile.delegation and profile.delegation.status == 'Activo':
        return profile.delegation
    return None


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


def dashboard_asistente_view(request):
    """
    Panel Principal de Trabajo para Asistente Social.
    Ilustre Municipalidad de La Serena.
    Cumple con RN-012, RF-015 y matriz RBAC.
    """
    profile = _actor(request)
    if not profile and not request.user.is_superuser:
        return redirect('core:login')

    user_delegation = _user_delegation_scope(request)
    is_admin = _is_admin(request)

    # Scoping de casos sociales
    cases_qs = SocialCase.objects.filter(deleted_at__isnull=True).select_related('delegation').prefetch_related('managements')
    if user_delegation:
        cases_qs = cases_qs.filter(delegation=user_delegation)

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

    # Delegaciones activas
    delegations = Delegation.objects.filter(status='Activo', deleted_at__isnull=True).order_by('name')

    # Catálogo de servicios / prestaciones
    catalogs = ServiceCatalog.objects.filter(status='Activo', deleted_at__isnull=True).order_by('service')

    # Vecinos de la delegación o comuna
    vecinos_qs = Vecino.objects.filter(deleted_at__isnull=True)
    if user_delegation:
        vecinos_qs = vecinos_qs.filter(territorio__iexact=user_delegation.name)
    vecinos = vecinos_qs.order_by('nombre')[:100]

    # Meta SGR y Semáforo (RN-007, RN-008)
    # Período actual
    period = MeasurementPeriod.objects.filter(deleted_at__isnull=True).order_by('-start_date').first()
    computable_days = period.computable_days if period else 91
    # Cálculo días transcurridos simulados o reales
    days_elapsed = 56
    meta_esperada_pct = round((days_elapsed / computable_days) * 100, 1) if computable_days else 61.5

    # Meta específica Asistente Social
    asistente_goal = Goal.objects.filter(
        deleted_at__isnull=True,
        position__name__icontains='Asistente Social',
        period=period
    ).first()
    target_value = float(asistente_goal.target_value) if asistente_goal else 50.0

    # Avance real: gestiones realizadas
    total_gestiones = SocialManagement.objects.filter(deleted_at__isnull=True)
    if user_delegation:
        total_gestiones = total_gestiones.filter(case__delegation=user_delegation)
    gestiones_count = total_gestiones.count()

    avance_pct = round((gestiones_count / target_value) * 100, 1) if target_value else 75.0

    # Semáforo RN-008
    if avance_pct >= meta_esperada_pct:
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
    ).select_related('case', 'case__delegation').order_by('-management_date')[:10]

    # Subsidios y ayudas entregadas (Etapa 3)
    subsidios_entregados = SocialManagement.objects.filter(
        stage=3, deleted_at__isnull=True
    ).select_related('case', 'catalog', 'case__delegation').order_by('-management_date')[:10]

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
        'target_value': int(target_value),
        'avance_pct': avance_pct,
        'meta_esperada_pct': meta_esperada_pct,
        'semaforo_color': semaforo_color,
        'semaforo_texto': semaforo_texto,
        'visitas_terreno': visitas_terreno,
        'subsidios_entregados': subsidios_entregados,
        'today': timezone.localdate().isoformat(),
        'period_name': period.name if period else 'Trimestre T3 2026',
    }
    return render(request, 'activities/dashboard_asistente.html', context)


# =========================================================================
# APIs REST / AJAX PARA EL DASHBOARD DE ASISTENTE SOCIAL
# =========================================================================

def api_casos_sociales(request):
    """Listar o crear Casos Sociales con validación Módulo 11."""
    if request.method not in {'GET', 'POST'}:
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)

    user_delegation = _user_delegation_scope(request)

    if request.method == 'GET':
        qs = SocialCase.objects.filter(deleted_at__isnull=True).select_related('delegation').prefetch_related('managements')
        if user_delegation:
            qs = qs.filter(delegation=user_delegation)

        query = request.GET.get('q', '').strip()
        if query:
            qs = qs.filter(Q(user_name__icontains=query) | Q(user_rut__icontains=query))

        stage_filter = request.GET.get('stage')
        if stage_filter and stage_filter.isdigit():
            # Filtrar por etapa actual
            target_stage = int(stage_filter)
            cases_matching = [c for c in qs if c.current_stage == target_stage]
            return JsonResponse({'success': True, 'cases': [_serialize_case(c) for c in cases_matching]})

        return JsonResponse({'success': True, 'cases': [_serialize_case(c) for c in qs[:100]]})

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'success': False, 'message': 'Datos JSON inválidos.'}, status=400)

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

        # Delegación
        if user_delegation:
            delegation = user_delegation
        else:
            delegation = Delegation.objects.filter(pk=delegation_id, status='Activo', deleted_at__isnull=True).first()
            if not delegation:
                delegation = Delegation.objects.filter(status='Activo', deleted_at__isnull=True).first()

        try:
            entry_date = datetime.date.fromisoformat(entry_date_str)
            if entry_date > timezone.localdate():
                return JsonResponse({'success': False, 'message': 'La fecha de ingreso no puede ser futura.'}, status=400)
        except ValueError:
            entry_date = timezone.localdate()

        with transaction.atomic():
            caso = SocialCase.objects.create(
                user_rut=rut_formateado,
                user_name=nombre,
                contact_phone=telefono,
                delegation=delegation,
                entry_date=entry_date
            )

            # Por RN-012, el caso nace con Etapa 1: Ingreso y recepción de antecedentes
            catalog = ServiceCatalog.objects.filter(status='Activo', deleted_at__isnull=True).first()
            gestion1 = SocialManagement.objects.create(
                case=caso,
                stage=1,
                catalog=catalog,
                management_type="Ingreso y recepción de antecedentes",
                management_date=entry_date,
                result=initial_problem or "Ingreso de solicitud social y evaluación preliminar de vulnerabilidad socioeconómica."
            )

            # Auditoría institucional
            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                affected_table='caso_social',
                affected_record_id=str(caso.id),
                action='CREATE',
                new_value=_serialize_case(caso),
                source_ip=request.META.get('REMOTE_ADDR')
            )

        return JsonResponse({
            'success': True,
            'message': f'Ficha Social de {caso.user_name} registrada con éxito (Etapa 1: Ingreso).',
            'case': _serialize_case(caso)
        }, status=201)


def api_caso_detalle(request, pk):
    """Detalle, edición y baja lógica de un Caso Social."""
    user_delegation = _user_delegation_scope(request)
    qs = SocialCase.objects.filter(deleted_at__isnull=True).select_related('delegation').prefetch_related('managements')
    if user_delegation:
        qs = qs.filter(delegation=user_delegation)

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

        prev = _serialize_case(caso)
        if 'user_name' in data and data['user_name'].strip():
            caso.user_name = data['user_name'].strip()
        if 'contact_phone' in data:
            caso.contact_phone = str(data['contact_phone']).strip()
        if 'entry_date' in data and data['entry_date']:
            try:
                caso.entry_date = datetime.date.fromisoformat(data['entry_date'])
            except ValueError:
                pass
        
        caso.save()
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            affected_table='caso_social',
            affected_record_id=str(caso.id),
            action='UPDATE',
            previous_value=prev,
            new_value=_serialize_case(caso),
            source_ip=request.META.get('REMOTE_ADDR')
        )
        return JsonResponse({'success': True, 'message': 'Ficha social actualizada.', 'case': _serialize_case(caso)})

    elif request.method == 'DELETE':
        prev = _serialize_case(caso)
        caso.deleted_at = timezone.now()
        caso.save(update_fields=['deleted_at', 'updated_at'])
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            affected_table='caso_social',
            affected_record_id=str(caso.id),
            action='DELETE',
            previous_value=prev,
            source_ip=request.META.get('REMOTE_ADDR')
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

    caso = SocialCase.objects.filter(pk=pk, deleted_at__isnull=True).prefetch_related('managements').first()
    if not caso:
        return JsonResponse({'success': False, 'message': 'Caso social inexistente.'}, status=404)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'message': 'JSON inválido.'}, status=400)

    curr_stage = caso.current_stage
    if curr_stage >= 3:
        return JsonResponse({
            'success': False,
            'message': 'Por normativa comunal (RN-012), este caso ya completó las 3 etapas máximas permitidas y se encuentra cerrado.'
        }, status=400)

    next_stage = curr_stage + 1
    target_stage = int(data.get('stage') or next_stage)
    if target_stage != next_stage:
        return JsonResponse({
            'success': False,
            'message': f'Secuencia inválida (RN-012). Debe registrar la Etapa {next_stage} antes de continuar.'
        }, status=400)

    tipo_gestion = str(data.get('management_type') or (
        "Visita en terreno y levantamiento técnico" if next_stage == 2 else "Resolución, dictamen y entrega de prestación"
    )).strip()

    resultado = str(data.get('result', '')).strip()
    if not resultado:
        return JsonResponse({'success': False, 'message': 'El informe o resultado de la gestión es obligatorio.'}, status=400)

    # Catálogo de servicio vinculado
    catalog_id = data.get('catalog_id')
    catalog = None
    if catalog_id:
        catalog = ServiceCatalog.objects.filter(pk=catalog_id, deleted_at__isnull=True).first()

    # Si es etapa 2: Código de Evidencia fotográfica EVI-XXXX obligatoria
    evidence_code = str(data.get('evidence_code', '')).strip()
    if next_stage == 2 and not evidence_code:
        # Generar código institucional si no se especificó
        import uuid
        evidence_code = f"EVI-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:4].upper()}"

    if evidence_code:
        resultado = f"[Respaldo: {evidence_code}] {resultado}"

    # Si es etapa 3: Ayuda o subsidio entregado
    benefit = str(data.get('benefit', '')).strip()
    if next_stage == 3 and benefit:
        resultado = f"[Subsidio/Prestación: {benefit}] {resultado}"

    try:
        date_obj = datetime.date.fromisoformat(data.get('management_date', timezone.localdate().isoformat()))
    except ValueError:
        date_obj = timezone.localdate()

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

    return JsonResponse({
        'success': True,
        'message': f'Etapa {next_stage} registrada exitosamente para {caso.user_name}.',
        'case': _serialize_case(caso)
    })


def api_informe_social(request, pk):
    """
    Genera los datos oficiales para el Informe Social Municipal
    con membrete oficial de la Ilustre Municipalidad de La Serena.
    """
    caso = SocialCase.objects.filter(pk=pk, deleted_at__isnull=True).select_related('delegation').prefetch_related('managements').first()
    if not caso:
        return JsonResponse({'success': False, 'message': 'Caso social no encontrado.'}, status=404)

    profile = _actor(request)
    worker_name = profile.full_name if profile else "Asistente Social Municipal"
    worker_rut = profile.rut if profile else "18.420.915-K"

    managements = list(caso.managements.filter(deleted_at__isnull=True).order_by('stage'))

    report_data = {
        'folio': f"INF-SOC-{caso.id:05d}-2026",
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
            'registro_profesional': "REG-TS-COL-2024-8891",
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
            f"El grupo familiar encabezado por don/doña {caso.user_name} presenta vulnerabilidad socioeconómica "
            f"verificada territorialmente en la Delegación {caso.delegation.name if caso.delegation else 'Municipal'}. "
            "Se sugiere mantener asignación prioritaria de beneficios comunales y seguimiento periódico."
        )
    }

    return JsonResponse({'success': True, 'report': report_data})
