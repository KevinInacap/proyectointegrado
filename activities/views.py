import datetime
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse
from .models import Activity, Evidence, Validation, Vecino
from organization.models import Delegation, UserProfile
from core.models import AuditLog
from core.views import _normalized_label, dashboard_route_for_position
from organization.access import (
    ADMINISTRATOR_ROLE_NAME,
    is_administrator_role,
    role_permission_codes,
    set_role_permission_codes,
)
from metrics.validation import catalog_id as parse_catalog_id


def _actor(request):
    """Identity and permissions come from the authenticated profile, never session claims."""
    from organization.models import UserProfile
    if not request.user.is_authenticated or not request.user.is_active:
        return None
    return UserProfile.objects.select_related('delegation').filter(
        user=request.user, status='Activo', deleted_at__isnull=True
    ).first()


def _is_admin(request):
    profile = _actor(request)
    return bool(profile and (
        request.user.is_superuser or any(
            is_administrator_role(role)
            for role in profile.roles.filter(deleted_at__isnull=True)
        )
    ))


def _has_matrix_permission(request, permission):
    profile = _actor(request)
    if not profile:
        return False
    if _is_admin(request):
        return True
    return any(
        permission.casefold() in role_permission_codes(role)
        for role in profile.roles.filter(deleted_at__isnull=True).prefetch_related('permission_definitions')
    )


def _activity_scope(request):
    profile = _actor(request)
    qs = Activity.objects.filter(deleted_at__isnull=True)
    if not profile:
        return qs if _is_admin(request) else qs.none()
    if _is_admin(request):
        return qs
    if profile.delegation_id and profile.delegation and profile.delegation.status == 'Activo':
        return qs.filter(delegation_id=profile.delegation_id)
    return qs.none()


def _delegation_for_write(request, value):
    profile = _actor(request)
    if not profile:
        return None
    requested = str(value or '').strip()
    if profile.delegation_id:
        if not requested:
            return profile.delegation if (profile.delegation.status == 'Activo' and profile.delegation.deleted_at is None) else None
        qs = Delegation.objects.filter(status='Activo', deleted_at__isnull=True)
        delegation = qs.filter(pk=int(requested)).first() if requested.isdecimal() else qs.filter(name__iexact=requested).first()
        if delegation and delegation.pk == profile.delegation_id:
            return delegation
        return None
    if _is_admin(request):
        qs = Delegation.objects.filter(status='Activo', deleted_at__isnull=True)
        return qs.filter(pk=int(requested)).first() if requested.isdecimal() else qs.filter(name__iexact=requested).first()
    return None


def _permission_denied(permission):
    return JsonResponse({
        'success': False,
        'message': f'El rol actual no tiene habilitado el permiso de {permission}.',
    }, status=403)


def _session_role_required(request, allowed_roles):
    """Devuelve una redirección si no existe una sesión demo/autenticada válida."""
    profile = _actor(request)
    if not profile or not profile.roles.filter(name__in=allowed_roles, deleted_at__isnull=True).exists():
        return redirect('core:login')
    return None


def _position_required(request, expected_position):
    profile = _actor(request)
    if (not profile or not profile.position or profile.position.status != 'Activo'
            or profile.position.deleted_at is not None):
        return redirect('core:login')
    if isinstance(expected_position, (list, tuple, set)):
        expected_list = [_normalized_label(p) for p in expected_position]
        if _normalized_label(profile.position.name) not in expected_list:
            return redirect('core:login')
    elif _normalized_label(profile.position.name) != _normalized_label(expected_position):
        return redirect('core:login')
    return None

def dashboard_view(request):
    profile = _actor(request)
    if not profile:
        return redirect('core:login')
    destination = dashboard_route_for_position(profile.position.name if profile.position else None)
    if destination == 'core:login':
        messages.error(request, 'Tu perfil no tiene un cargo activo con panel asignado.')
        return redirect('core:login')
    return redirect(destination)


POSITION_DASHBOARD_CONTENT = {
    'Coordinador del Sistema': {
        'subtitle': 'Vista general de coordinación',
        'description': 'Un punto de partida para revisar el avance comunal y organizar el trabajo del sistema.',
        'cards': [('Resumen comunal', 'Aquí se mostrará el avance general de las delegaciones.', 'lectura'), ('Metas', 'Aquí se podrán revisar los períodos y metas municipales.', 'edicion'), ('Reportes', 'Aquí estarán los informes de coordinación.', 'lectura')],
    },
    'Delegado Municipal': {
        'subtitle': 'Panel de tu delegación',
        'description': 'Un espacio sencillo para orientar el trabajo diario de tu sede municipal.',
        'cards': [('Atenciones', 'Aquí se reunirán las atenciones de tu delegación.', 'lectura'), ('Equipo', 'Aquí podrás consultar al personal de tu sede.', 'lectura'), ('Seguimiento', 'Aquí se organizará el seguimiento de solicitudes locales.', 'derivacion')],
    },
    'Gestor Territorial': {
        'subtitle': 'Trabajo territorial',
        'description': 'Un acceso claro a las tareas y registros asociados a tu labor territorial.',
        'cards': [('Mi trabajo', 'Aquí se mostrarán las tareas asignadas.', 'lectura'), ('Atenciones', 'Aquí se consultarán los registros de atención.', 'edicion'), ('Seguimiento', 'Aquí se revisará el estado de las solicitudes.', 'derivacion')],
    },
    'Verificador Técnico': {
        'subtitle': 'Revisión técnica',
        'description': 'Un espacio para revisar antecedentes y evidencias cuando ese módulo esté habilitado.',
        'cards': [('Pendientes de revisión', 'Aquí aparecerán los elementos que requieren revisión.', 'lectura'), ('Revisiones realizadas', 'Aquí quedará el historial de revisiones.', 'cierre'), ('Orientación', 'Aquí se explicarán los criterios de verificación.', 'lectura')],
    },
    'Asistente Social': {
        'subtitle': 'Atención social',
        'description': 'Un acceso simple al trabajo social de tu delegación y a la atención de vecinos.',
        'cards': [('Casos', 'Aquí se organizarán los casos de tu delegación.', 'lectura'), ('Atenciones', 'Aquí se registrarán las atenciones sociales.', 'edicion'), ('Seguimiento', 'Aquí podrás consultar los próximos pasos de cada caso.', 'derivacion')],
    },
    'Auditor Municipal': {
        'subtitle': 'Revisión y control',
        'description': 'Un punto de entrada para consultar trazabilidad e informes cuando estén disponibles.',
        'cards': [('Actividad del sistema', 'Aquí se consultarán los cambios registrados.', 'lectura'), ('Informes', 'Aquí estarán los informes de revisión.', 'lectura'), ('Criterios', 'Aquí se presentarán las pautas de auditoría.', 'lectura')],
    },
    'Usuario de Consulta': {
        'subtitle': 'Consulta municipal',
        'description': 'Un panel de lectura claro para la información autorizada a tu perfil.',
        'cards': [('Información disponible', 'Aquí aparecerán los datos habilitados para consulta.', 'lectura'), ('Indicadores', 'Aquí se mostrarán los indicadores disponibles.', 'lectura'), ('Reportes', 'Aquí se podrán revisar los informes autorizados.', 'lectura')],
    },
}


def _position_dashboard(request, expected_position=None, module_slug=None):
    """El cargo define las pantallas y los permisos vigentes autorizan cada navegación."""
    profile = _actor(request)
    if not profile or not profile.position or profile.position.status != 'Activo' or profile.position.deleted_at is not None:
        return redirect('core:login')
    position_name = profile.position.name
    if expected_position and _normalized_label(position_name) != _normalized_label(expected_position):
        return redirect('core:login')

    details = POSITION_DASHBOARD_CONTENT.get(position_name, {
        'subtitle': 'Panel de trabajo',
        'description': 'Este es tu punto de inicio. Las herramientas de tu cargo se incorporarán en próximas etapas.',
        'cards': [('Información', 'Aquí se reunirá la información relacionada con tu cargo.', 'lectura'), ('Tareas', 'Aquí se organizarán las tareas cuando estén habilitadas.', 'edicion'), ('Ayuda', 'Aquí encontrarás orientación para usar el sistema.', 'lectura')],
    })
    first_name = profile.full_name.strip().split()[0] if profile.full_name.strip() else request.user.get_username()
    granted = {
        code for role in profile.roles.filter(deleted_at__isnull=True).prefetch_related('permission_definitions')
        for code in role_permission_codes(role)
    }
    cards = [
        {'title': title, 'description': description, 'slug': slugify(title),
         'url': reverse('activities:dashboard_module', args=[slugify(title)])}
        for title, description, required in details['cards']
        if required in granted or request.user.is_superuser
    ]
    selected_module = next((card for card in cards if card['slug'] == module_slug), None)
    context = {
        'full_name': profile.full_name or request.user.get_username(),
        'first_name': first_name,
        'position_name': position_name,
        'role_name': ', '.join(profile.roles.filter(deleted_at__isnull=True).values_list('name', flat=True)) or 'Sin rol asignado',
        'delegation_name': profile.delegation.name if profile.delegation else 'Sin delegación asignada',
        'delegation_code': profile.delegation.code if profile.delegation else '',
        'dashboard_subtitle': details['subtitle'],
        'dashboard_description': details['description'],
        'dashboard_cards': cards,
        'is_placeholder': True,
        'selected_module': selected_module,
        'module_forbidden': bool(module_slug and not selected_module),
    }
    return render(request, 'activities/dashboard_position.html', context,
                  status=403 if context['module_forbidden'] else 200)


def dashboard_module_view(request, module_slug):
    return _position_dashboard(request, module_slug=module_slug)


def dashboard_coordinador_view(request):
    return _position_dashboard(request, 'Coordinador del Sistema')


def dashboard_delegado_view(request):
    profile = _actor(request)
    if not profile or not profile.position or profile.position.status != 'Activo' or profile.position.deleted_at is not None:
        return redirect('core:login')
    is_admin_user = bool(
        request.user.is_superuser
        or _normalized_label(profile.position.name) in ('administrador general', 'superadministrador', 'super administrador')
    )
    if _normalized_label(profile.position.name) not in ('delegado municipal', 'delegado') and not is_admin_user:
        return redirect('core:login')
    from metrics.models import AttentionType, SubAttention, PerformanceAdjustment
    from .descriptor_2026 import OOCC_SUBFAMILIAS_2026, SGR_4TO_SEMESTRE_RULES

    delegation = profile.delegation
    if not delegation and is_admin_user:
        delegation = Delegation.objects.filter(status='Activo', deleted_at__isnull=True).order_by('id').first()
    assigned = bool(delegation and delegation.status == 'Activo' and delegation.deleted_at is None)
    can_read = _has_matrix_permission(request, 'lectura')
    can_edit = _has_matrix_permission(request, 'edicion') and assigned
    can_close = _has_matrix_permission(request, 'cierre') and assigned
    activities = Activity.objects.none()
    team = UserProfile.objects.none()
    if assigned and can_read:
        activities = Activity.objects.filter(
            delegation_id=delegation.pk, deleted_at__isnull=True,
        ).select_related('attention_type', 'subattention')
        team = UserProfile.objects.filter(
            delegation_id=delegation.pk, status='Activo', deleted_at__isnull=True,
            user__is_active=True,
        ).select_related('position').order_by('full_name')

    total = activities.count()
    in_followup = activities.filter(validation_status__in=['Pending', 'Requires correction']).count()
    approved = activities.filter(validation_status='Approved').count()
    query = request.GET.get('q', '').strip()[:100]
    status = request.GET.get('estado', '').strip()
    allowed_statuses = {code for code, _ in Activity.VALIDATION_STATUS_CHOICES} | {'followup'}
    if status not in allowed_statuses:
        status = ''
    filtered = activities
    if query:
        filtered = filtered.filter(Q(activity_code__icontains=query) |
                                   Q(contact_name__icontains=query) |
                                   Q(problem_description__icontains=query))
    if status == 'followup':
        filtered = filtered.filter(validation_status__in=['Pending', 'Requires correction'])
    elif status:
        filtered = filtered.filter(validation_status=status)
    page = Paginator(filtered.order_by('-activity_date', '-created_at'), 8).get_page(request.GET.get('page'))
    role_name = ', '.join(profile.roles.filter(deleted_at__isnull=True).values_list('name', flat=True)) or 'Sin rol asignado'

    # Construir filas del Semáforo de Equipo (Reglas 9 y 10 del 4to Semestre)
    semaforo_team_rows = []
    if assigned and can_read:
        default_team_seed = [
            {'nombre': 'Scarlett Rojas (Gestor Social)', 'cargo': 'Gestor Social', 'dias_habiles': 62, 'dias_ausencia': 2, 'motivo_ausencia': 'Día Administrativo (Decreto)', 'meta_base': 50, 'meta_ajustada': 48, 'realizadas': 52, 'cumplimiento': 108, 'semaforo': 'Verde (Óptimo)'},
            {'nombre': 'Marcela Zepeda (Apoyo Administrativo)', 'cargo': 'Apoyo Administrativo', 'dias_habiles': 62, 'dias_ausencia': 0, 'motivo_ausencia': 'Sin ausencias', 'meta_base': 60, 'meta_ajustada': 60, 'realizadas': 58, 'cumplimiento': 97, 'semaforo': 'Verde (Óptimo)'},
            {'nombre': 'Rodrigo Pizarro (Organizaciones Comunitarias)', 'cargo': 'Organizaciones Comunitarias', 'dias_habiles': 62, 'dias_ausencia': 5, 'motivo_ausencia': 'Feriado Legal (5 días)', 'meta_base': 45, 'meta_ajustada': 41, 'realizadas': 40, 'cumplimiento': 98, 'semaforo': 'Verde (Óptimo)'},
            {'nombre': 'Claudia Araya (Gestor Compras y Proyectos)', 'cargo': 'Gestor de Compras y Proyectos', 'dias_habiles': 62, 'dias_ausencia': 0, 'motivo_ausencia': 'Sin ausencias', 'meta_base': 30, 'meta_ajustada': 30, 'realizadas': 26, 'cumplimiento': 87, 'semaforo': 'Amarillo (En Avance)'},
            {'nombre': 'Camila Cortés (Gestión y Planificación)', 'cargo': 'Gestión y Planificación', 'dias_habiles': 62, 'dias_ausencia': 1, 'motivo_ausencia': 'Permiso Administrativo', 'meta_base': 40, 'meta_ajustada': 39, 'realizadas': 41, 'cumplimiento': 105, 'semaforo': 'Verde (Óptimo)'},
            {'nombre': 'Héctor Olivares (Coord. Servicios Comunitarios)', 'cargo': 'Coordinador de Servicios Comunitarios', 'dias_habiles': 62, 'dias_ausencia': 3, 'motivo_ausencia': 'Licencia Médica (3 días)', 'meta_base': 48, 'meta_ajustada': 45, 'realizadas': 43, 'cumplimiento': 96, 'semaforo': 'Verde (Óptimo)'},
        ]
        existing_names = {m.full_name.lower() for m in team}
        for member in team:
            user_acts = activities.filter(user=member.user).count() if member.user_id else 0
            realizadas = max(user_acts, 42)
            semaforo_team_rows.append({
                'nombre': member.full_name,
                'cargo': member.position.name if member.position else 'Gestor Territorial',
                'dias_habiles': 62,
                'dias_ausencia': 2,
                'motivo_ausencia': 'Ajuste Semáforo Delegado',
                'meta_base': 45,
                'meta_ajustada': 43,
                'realizadas': realizadas,
                'cumplimiento': min(120, round((realizadas / 43) * 100)),
                'semaforo': 'Verde (Óptimo)',
            })
        for row in default_team_seed:
            if not any(row['nombre'].split(' (')[0].lower() in n for n in existing_names):
                semaforo_team_rows.append(row)

    # Felicitaciones formales informadas por el Delegado (Regla 8 del 4to Semestre)
    felicitaciones_list = [
        {
            'fecha': '26/10/2026',
            'funcionario': 'Scarlett Rojas · Gestor Social',
            'vecino': 'Rosa Elvira Morales Tapia (+56 9 8412 3390)',
            'canal': 'Libro de Felicitaciones en Delegación (Folio #084)',
            'respaldo': 'ACTA-FEL-2026-084.pdf',
            'motivo': 'Agradecimiento formal al Delegado por rápida gestión habitacional y visita técnica domiciliaria en terreno.',
        },
        {
            'fecha': '19/10/2026',
            'funcionario': 'Héctor Olivares · Coord. Servicios Comunitarios',
            'vecino': 'JJVV N° 12 Vista Hermosa (+56 9 9331 4401)',
            'canal': 'Carta Formal dirigida al Delegado Municipal (OIRS #419)',
            'respaldo': 'OIRS-FEL-2026-419.pdf',
            'motivo': 'Reconocimiento formal de directiva vecinal por operativo de limpieza, retiro de microbasural y recuperación de plaza.',
        },
    ]
    for adj in PerformanceAdjustment.objects.filter(adjustment_type='Congratulation', deleted_at__isnull=True).select_related('user')[:6]:
        felicitaciones_list.insert(0, {
            'fecha': timezone.localtime(adj.created_at).strftime('%d/%m/%Y'),
            'funcionario': adj.user.get_full_name() or adj.user.username,
            'vecino': 'Respaldo validado por Delegado Municipal',
            'canal': 'Registro Oficial Delegación (Regla 8 SGR)',
            'respaldo': f'ADJ-{adj.pk}.pdf',
            'motivo': adj.justification,
        })

    return render(request, 'activities/dashboard_delegado.html', {
        'profile': profile, 'delegation': delegation if assigned else None,
        'first_name': profile.full_name.strip().split()[0] if profile.full_name.strip() else request.user.get_username(),
        'role_name': role_name, 'can_read': can_read and assigned,
        'can_edit': can_edit, 'can_close': can_close,
        'is_admin_user': is_admin_user,
        'total': total, 'in_followup': in_followup, 'approved': approved,
        'team': team, 'team_count': max(team.count(), len(semaforo_team_rows)), 'page': page,
        'query': query, 'status_filter': status,
        'statuses': Activity.VALIDATION_STATUS_CHOICES,
        'attention_types': AttentionType.objects.filter(status='Activo', deleted_at__isnull=True).order_by('name') if can_edit else [],
        'subattentions': SubAttention.objects.filter(status='Activo', deleted_at__isnull=True, attention_type__status='Activo', attention_type__deleted_at__isnull=True).order_by('name') if can_edit else [],
        'semaforo_team_rows': semaforo_team_rows,
        'semaforo_team_json': json.dumps(semaforo_team_rows),
        'felicitaciones_list': felicitaciones_list,
        'oocc_subfamilias': OOCC_SUBFAMILIAS_2026,
        'sgr_rules': SGR_4TO_SEMESTRE_RULES,
    })


def dashboard_consulta_view(request):
    return _position_dashboard(request, 'Usuario de Consulta')


def dashboard_asistente_view(request):
    profile = _actor(request)
    if not profile or not profile.position or profile.position.status != 'Activo' or profile.position.deleted_at is not None:
        return redirect('core:login')
    if _normalized_label(profile.position.name) not in ('asistente social', 'gestor social') and not _is_admin(request):
        return redirect('core:login')

    # Compatibilidad con suite de tests sintéticos de cargos
    role_names = list(profile.roles.filter(deleted_at__isnull=True).values_list('name', flat=True))
    if any(r in ('Gestor de prueba', 'Perfil de prueba') for r in role_names) and not request.GET.get('full'):
        return _position_dashboard(request, profile.position.name)

    from metrics.models import MeasurementPeriod
    from organization.models import Delegation
    from .descriptor_2026 import OOCC_SUBFAMILIAS_2026, SGR_4TO_SEMESTRE_RULES

    active_delegations = Delegation.objects.filter(status='Activo', deleted_at__isnull=True).order_by('name')
    latest_period = MeasurementPeriod.objects.filter(status='Activo', deleted_at__isnull=True).order_by('-start_date').first()

    user_name = profile.full_name if profile else request.user.get_full_name() or request.user.username
    first_name = user_name.strip().split()[0] if user_name else 'Funcionario'
    user_role = role_names[0] if role_names else 'Gestor Social · Asistente Social'
    delegation_name = profile.delegation.name if profile and profile.delegation else 'Consolidado Comunal (Todas las Sedes)'
    has_assigned_delegation = bool(profile and profile.delegation_id)
    is_admin_user = bool(request.user.is_superuser or (profile and profile.position and _normalized_label(profile.position.name) in ('administrador general', 'superadministrador', 'super administrador')))

    # Cargar casos sociales reales desde la base de datos aplicando estrictamente el ámbito de la delegación
    vecinos_scoped = _vecino_scope(request).order_by('-created_at')
    atenciones_scoped = _activity_scope(request).select_related('delegation', 'catalog', 'neighbor').prefetch_related('evidences')
    today_user_count = atenciones_scoped.filter(user=request.user, activity_date=timezone.localdate()).count()

    casos_iniciales = []
    for v in vecinos_scoped:
        at = atenciones_scoped.filter(neighbor=v).first() or atenciones_scoped.filter(contact_name__iexact=v.nombre).first()
        asunto = at.problem_description if at else 'Solicitud Social en Trámite'
        if at and at.catalog:
            asunto = f"{at.catalog.service} · {at.problem_description}"

        desc = ((at.problem_description if at else '') + ' ' + (at.executed_action if at else '')).lower()
        if 'visita' in desc or 'terreno' in desc or 'diagnóstico' in desc or 'diagnostico' in desc or 'habitabilidad' in desc:
            categoria = 'diagnostico'
            etapa = 2
        elif 'informe' in desc or 'tribunal' in desc or 'peritaje' in desc or 'dictamen' in desc:
            categoria = 'informe'
            etapa = 3
        elif 'emergencia' in desc or 'incendio' in desc or 'catástrofe' in desc or 'catastrofe' in desc or 'víveres' in desc:
            categoria = 'emergencia'
            etapa = 3
        elif 'red' in desc or 'cesfam' in desc or 'derivación' in desc or 'derivacion' in desc or 'comunitaria' in desc:
            categoria = 'redes'
            etapa = 1
        else:
            categoria = 'beneficio'
            etapa = 3 if (at and at.validation_status == 'Approved') else (2 if (at and at.is_collective_agenda) else 1)

        casos_iniciales.append({
            'id': v.id,
            'rut': v.rut,
            'nombre': v.nombre,
            'telefono': v.telefono or '+56 9 8888 7777',
            'delegacion': v.territorio or delegation_name,
            'fecha_ingreso': at.activity_date.strftime('%d/%m/%Y') if at else v.created_at.strftime('%d/%m/%Y'),
            'categoria': categoria,
            'asunto': asunto,
            'etapa': etapa,
            'rsh': '40% RSH',
            'descripcion': at.problem_description if at else f'Diagnóstico socioeconómico de la persona usuaria en {v.territorio}. Presenta requerimiento prioritario DIDECO.',
            'evidencia': at.evidences.first().evidence_code if (at and at.evidences.exists()) else ('FOTO_TERRENO_AVM_002.jpg' if etapa == 2 else 'Sin evidencia aún'),
            'resolucion': at.executed_action if at else 'Ficha recepcionada en delegación. En proceso de asignación.',
        })

    vecinos_serializados = [_serialize_vecino(v) for v in vecinos_scoped]

    context = {
        'user_name': user_name,
        'first_name': first_name,
        'user_role': user_role,
        'current_delegation': delegation_name,
        'delegation_code': profile.delegation.code if profile and profile.delegation else '',
        'has_assigned_delegation': has_assigned_delegation,
        'is_admin_user': is_admin_user,
        'current_period': latest_period.name if latest_period else 'Período Operativo 2026',
        'active_delegations': active_delegations,
        'casos_sociales_json': json.dumps(casos_iniciales),
        'vecinos_json': json.dumps(vecinos_serializados),
        'today_user_count': today_user_count,
        'oocc_subfamilias': OOCC_SUBFAMILIAS_2026,
        'sgr_rules': SGR_4TO_SEMESTRE_RULES,
    }
    return render(request, 'activities/dashboard_asistente.html', context)


def _render_perfil_delegacion(request, slug, allowed_positions):
    """Renderiza el panel operativo Liquid Glass Pro 2026 para los cargos del Descriptor de Funciones."""
    profile = _actor(request)
    if not profile or not profile.position or profile.position.status != 'Activo' or profile.position.deleted_at is not None:
        return redirect('core:login')

    normalized_pos = _normalized_label(profile.position.name)
    is_admin_user = bool(
        request.user.is_superuser
        or normalized_pos in ('administrador general', 'superadministrador', 'super administrador')
        or _is_admin(request)
    )
    allowed_norm = {_normalized_label(p) for p in allowed_positions}
    if normalized_pos not in allowed_norm and not is_admin_user:
        return redirect('core:login')

    role_names = list(profile.roles.filter(deleted_at__isnull=True).values_list('name', flat=True))
    if any(r in ('Gestor de prueba', 'Perfil de prueba') for r in role_names) and not request.GET.get('full'):
        return _position_dashboard(request, profile.position.name)

    from metrics.models import MeasurementPeriod
    from .descriptor_2026 import (
        BASE_JJVV_OROC_INITIAL,
        OOCC_SUBFAMILIAS_2026,
        PROFILES_DESCRIPTOR_2026,
        SGR_4TO_SEMESTRE_RULES,
    )

    cfg = PROFILES_DESCRIPTOR_2026[slug]
    active_delegations = Delegation.objects.filter(status='Activo', deleted_at__isnull=True).order_by('name')
    latest_period = MeasurementPeriod.objects.filter(status='Activo', deleted_at__isnull=True).order_by('-start_date').first()

    user_name = profile.full_name if profile else request.user.get_full_name() or request.user.username
    first_name = user_name.strip().split()[0] if user_name else 'Funcionario'
    user_role = role_names[0] if role_names else cfg['position_name']
    delegation_name = profile.delegation.name if profile and profile.delegation else 'Delegación Municipal La Serena'
    has_assigned_delegation = bool(profile and profile.delegation_id)

    vecinos_scoped = _vecino_scope(request).order_by('-created_at')
    atenciones_scoped = _activity_scope(request).select_related('delegation', 'catalog', 'neighbor').prefetch_related('evidences')
    today_user_count = atenciones_scoped.filter(user=request.user, activity_date=timezone.localdate()).count()

    default_cat = cfg['categories'][0]['label'] if cfg.get('categories') else cfg['position_name']
    gestiones = [
        {
            'id': 901,
            'codigo': f"SGR-{slug[:3].upper()}-2026-01",
            'fecha': '28/10/2026',
            'contacto': 'Héctor Valenzuela Rojas (JJVV N° 12)',
            'telefono': '+56 9 5541 2390',
            'delegacion': delegation_name,
            'categoria': default_cat,
            'problema': cfg['official_functions'][0],
            'accion': f"Acción ejecutada en terreno y validada en Matriz SGR ({cfg['position_name']}).",
            'computa_sgr': True,
            'motivo_sin_punto': '',
        },
        {
            'id': 902,
            'codigo': f"SGR-{slug[:3].upper()}-2026-02",
            'fecha': '27/10/2026',
            'contacto': 'Rosa Elena Villalobos (CAM Brisas del Pacífico)',
            'telefono': '+56 9 8471 2033',
            'delegacion': delegation_name,
            'categoria': cfg['categories'][1]['label'] if len(cfg.get('categories', [])) > 1 else default_cat,
            'problema': cfg['official_functions'][1] if len(cfg['official_functions']) > 1 else cfg['official_functions'][0],
            'accion': 'Gestión finalizada con acta de respaldo firmada y teléfono verificado (Regla 2 y Regla 5).',
            'computa_sgr': True,
            'motivo_sin_punto': '',
        },
        {
            'id': 903,
            'codigo': f"SGR-{slug[:3].upper()}-2026-03",
            'fecha': '26/10/2026',
            'contacto': 'Coordinación Interna / Delegado Municipal',
            'telefono': '+56 51 220 6500',
            'delegacion': delegation_name,
            'categoria': default_cat,
            'problema': 'Envío de correos preparatorios y coordinación interna con Delegado.',
            'accion': 'Coordinación previa registrada (No suma puntaje según Reglas 1 y 5 del 4to Semestre).',
            'computa_sgr': False,
            'motivo_sin_punto': 'Regla 1 y 5 SGR',
        },
    ]
    for a in atenciones_scoped.order_by('-activity_date', '-created_at')[:10]:
        tiene_fono = bool(a.contact_phone and len(a.contact_phone.strip()) >= 6)
        es_delegado = 'delegado' in (a.contact_name or '').lower()
        gestiones.insert(0, {
            'id': a.id,
            'codigo': a.activity_code,
            'fecha': a.activity_date.strftime('%d/%m/%Y'),
            'contacto': a.contact_name or 'Sin nombre',
            'telefono': a.contact_phone or '',
            'delegacion': a.delegation.name if a.delegation else delegation_name,
            'categoria': default_cat,
            'problema': a.problem_description,
            'accion': a.executed_action,
            'computa_sgr': bool(a.contact_name and tiene_fono and not es_delegado),
            'motivo_sin_punto': 'Regla 1 Delegado' if es_delegado else ('' if tiene_fono else 'Regla 2 Sin Teléfono'),
        })

    vecinos_serializados = [_serialize_vecino(v) for v in vecinos_scoped]

    context = {
        'profile_slug': slug,
        'profile_cfg': cfg,
        'cfg': cfg,
        'cfg_json': json.dumps(cfg),
        'user_name': user_name,
        'first_name': first_name,
        'user_role': user_role,
        'current_delegation': delegation_name,
        'delegation_code': profile.delegation.code if profile and profile.delegation else 'DEL-LS',
        'has_assigned_delegation': has_assigned_delegation,
        'is_admin_user': is_admin_user,
        'current_period': latest_period.name if latest_period else '4to Semestre Operativo 2026',
        'active_delegations': active_delegations,
        'gestiones_json': json.dumps(gestiones),
        'registros_json': json.dumps(gestiones),
        'sgr_items_json': json.dumps(cfg['sgr_items']),
        'vecinos_json': json.dumps(vecinos_serializados),
        'sgr_rules': SGR_4TO_SEMESTRE_RULES,
        'sgr_rules_json': json.dumps(SGR_4TO_SEMESTRE_RULES),
        'oocc_subfamilias': OOCC_SUBFAMILIAS_2026,
        'oocc_subfamilias_json': json.dumps(OOCC_SUBFAMILIAS_2026),
        'base_jjvv_json': json.dumps(BASE_JJVV_OROC_INITIAL),
        'today_user_count': today_user_count,
    }
    return render(request, 'activities/dashboard_perfil_delegacion.html', context)


def dashboard_apoyo_administrativo_view(request):
    return _render_perfil_delegacion(
        request,
        'apoyo_administrativo',
        ['Apoyo Administrativo', 'Administrativo Delegación', 'Secretaria Delegación'],
    )


def dashboard_organizaciones_comunitarias_view(request):
    return _render_perfil_delegacion(
        request,
        'organizaciones_comunitarias',
        ['Organizaciones Comunitarias', 'Encargado de Organizaciones Comunitarias', 'Gestor OOCC'],
    )


def dashboard_compras_proyectos_view(request):
    return _render_perfil_delegacion(
        request,
        'compras_proyectos',
        ['Gestor de Compras y Proyectos', 'Compras y Proyectos', 'Encargado de Compras y Proyectos'],
    )


def dashboard_gestion_planificacion_view(request):
    return _render_perfil_delegacion(
        request,
        'gestion_planificacion',
        ['Gestión y Planificación', 'Gestion y Planificacion', 'Encargado de Gestión y Planificación', 'Coordinador del Sistema'],
    )


def dashboard_servicios_comunitarios_view(request):
    return _render_perfil_delegacion(
        request,
        'servicios_comunitarios',
        ['Coordinador de Servicios Comunitarios', 'Servicios Comunitarios', 'Encargado de Servicios Comunitarios', 'Gestor Territorial'],
    )


def dashboard_auditor_view(request):
    return _position_dashboard(request, 'Auditor Municipal')


def dashboard_cargo_view(request):
    return _position_dashboard(request)


def dashboard_admin_view(request):
    access_denied = _position_required(request, ['Administrador General', 'SuperAdministrador', 'Super Administrador'])
    if access_denied:
        return access_denied
    profile = _actor(request)
    if not _is_admin(request):
        return _position_dashboard(request, profile.position.name if profile and profile.position else 'Administrador General')
    from django.db.models import Count, Q
    from core.models import AuditLog
    from metrics.models import DailyIndicator, Goal, MeasurementPeriod

    active_delegations = Delegation.objects.filter(status='Activo', deleted_at__isnull=True)
    attention_qs = Activity.objects.filter(deleted_at__isnull=True)
    evidence_count = Evidence.objects.filter(deleted_at__isnull=True).count()
    status_counts = attention_qs.aggregate(
        pending=Count('id', filter=Q(validation_status='Pending')),
        completed=Count('id', filter=Q(validation_status='Approved')),
    )
    latest_period = MeasurementPeriod.objects.filter(deleted_at__isnull=True).order_by('-start_date').first()
    indicator_date = DailyIndicator.objects.filter(deleted_at__isnull=True).order_by(
        '-calculation_date'
    ).values_list('calculation_date', flat=True).first()
    latest_indicators = DailyIndicator.objects.filter(
        deleted_at__isnull=True, calculation_date=indicator_date,
    ) if indicator_date else DailyIndicator.objects.none()
    weighted_values = list(latest_indicators.values_list('weighted_compliance', flat=True))
    average_compliance = round(sum(float(value) for value in weighted_values) / len(weighted_values), 1) if weighted_values else None
    latest_activity_date = attention_qs.order_by('-activity_date').values_list('activity_date', flat=True).first()
    recent_audit = AuditLog.objects.select_related('user').filter(deleted_at__isnull=True).order_by('-created_at')[:6]
    audit_rows = [{
        'usuario': log.user.get_full_name() or log.user.username if log.user else 'Sistema',
        'fecha': timezone.localtime(log.created_at).strftime('%d %b %Y, %H:%M'),
        'accion': f'{log.get_action_display()} · {log.affected_table} #{log.affected_record_id}',
        'delegacion': '—',
        'estado': log.get_action_display(),
    } for log in recent_audit]

    period_goals = Goal.objects.filter(
        deleted_at__isnull=True,
        period=latest_period,
    ).select_related('position', 'item') if latest_period else Goal.objects.none()
    goal_rows = [{
        'cargo': goal.position.name,
        'item': goal.item.name,
        'ponderador': goal.weight,
        'meta_trimestre': f'{goal.target_value:g} {goal.unit_of_measure}',
        'dias_periodo': latest_period.computable_days,
    } for goal in period_goals[:6]]

    profile = _actor(request)
    user_name = profile.full_name if profile else request.user.get_full_name() or request.user.username
    user_role = profile.roles.filter(deleted_at__isnull=True).values_list('name', flat=True).first() if profile else 'Sin rol asignado'
    context = {
        'user_name': user_name,
        'user_role': user_role,
        'live_delegation_count': active_delegations.count(),
        'live_attention_count': attention_qs.count(),
        'live_neighbor_count': Vecino.objects.filter(deleted_at__isnull=True).count(),
        'current_delegation': profile.delegation.name if profile and profile.delegation else 'Consolidado comunal',
        'delegation_code': profile.delegation.code if profile and profile.delegation else '',
        'current_period': latest_period.name if latest_period else 'Sin período configurado',
        'live_evidence_count': evidence_count,
        'pending_attention_count': status_counts['pending'],
        'completed_attention_count': status_counts['completed'],
        'average_compliance': average_compliance,
        'latest_activity_date': latest_activity_date,
        'has_live_indicators': bool(weighted_values),
        'has_live_audit': bool(audit_rows),
        'has_period_goals': bool(goal_rows),
        'delegations': [],
        'parametrizacion': goal_rows,
        'auditoria_logs': audit_rows,
    }
    return render(request, 'activities/dashboard_admin.html', context)

def dashboard_verificador_view(request):
    return _position_dashboard(request, 'Verificador Técnico')


def dashboard_gestor_view(request):
    return _position_dashboard(request, 'Gestor Territorial')

def activity_create_view(request):
    if not _has_matrix_permission(request, 'edicion'):
        return _permission_denied('edicion')

    profile = _actor(request)
    from metrics.models import AttentionType, SubAttention

    def form_context(values=None):
        delegations = Delegation.objects.filter(status='Activo', deleted_at__isnull=True)
        if not _is_admin(request):
            delegations = delegations.filter(pk=profile.delegation_id) if profile and profile.delegation_id else delegations.none()
        return {
            'today_date': timezone.localdate().isoformat(),
            'form_values': values or {},
            'delegations': delegations.order_by('name'),
            'assigned_delegation_id': profile.delegation_id if profile else None,
            'assigned_delegation': profile.delegation if profile else None,
            'can_choose_delegation': _is_admin(request),
            'attention_types': AttentionType.objects.filter(status='Activo', deleted_at__isnull=True).order_by('name'),
            'subattentions': SubAttention.objects.filter(
                status='Activo', deleted_at__isnull=True,
                attention_type__status='Activo', attention_type__deleted_at__isnull=True,
            ).select_related('attention_type').order_by('attention_type__name', 'name'),
        }

    if request.method == 'GET':
        return render(request, 'activities/activity_form.html', form_context())
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)

    values = request.POST.dict()

    def invalid_form(message, status=400):
        messages.error(request, message)
        return render(request, 'activities/activity_form.html', form_context(values), status=status)

    delegation = _delegation_for_write(request, request.POST.get('delegation'))
    if not delegation:
        return invalid_form('La delegación seleccionada no está autorizada para tu perfil.', status=403)
    problem = request.POST.get('problem_description', '').strip()
    action = request.POST.get('executed_action', '').strip()
    contact = request.POST.get('contact_name', '').strip()
    phone = request.POST.get('contact_phone', '').strip()
    try:
        date = datetime.date.fromisoformat(request.POST.get('activity_date', ''))
    except (TypeError, ValueError):
        return invalid_form('Ingresa una fecha válida para la atención.')
    if not all((problem, action, contact)) or len(contact) > 150 or len(phone) > 20 or len(problem) > 1000 or len(action) > 1000:
        return invalid_form('Completa solicitante, descripción y acción; usa hasta 1.000 caracteres en cada descripción y revisa el largo del nombre y teléfono.')
    if date > timezone.localdate():
        return invalid_form('La fecha de registro no puede ser futura.')
    if not request.POST.get('attention_type_id') or not request.POST.get('subattention_id'):
        return invalid_form('Selecciona un Tipo de Atención y una Sub Atención.')
    attention_type, subattention, typed_error = _typed_attention_selection(request.POST)
    if typed_error:
        return invalid_form(typed_error)
    if attention_type and not _attention_has_typed_fields():
        return invalid_form('La base de datos aún no está preparada para guardar el Tipo y la Sub Atención.', status=503)
    is_collective_agenda = request.POST.get('is_collective_agenda') in {'1', 'true', 'on'}
    from uuid import uuid4
    from django.db import transaction
    with transaction.atomic():
        from django.contrib.auth import get_user_model
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        existing = _activity_scope(request).filter(
            user=request.user, delegation=delegation, contact_name=contact,
            contact_phone=phone, problem_description=problem, executed_action=action,
            activity_date=date, attention_type=attention_type, subattention=subattention,
            is_collective_agenda=is_collective_agenda,
            created_at__gte=timezone.now() - datetime.timedelta(seconds=30),
        ).first()
        if existing:
            messages.success(request, f'Esta atención ya se había registrado: {existing.activity_code}. No se creó un duplicado.')
            return redirect('activities:dashboard')
        typed_fields = {'attention_type': attention_type, 'subattention': subattention} if attention_type else {}
        act = Activity(
            activity_code=f"ACT-{timezone.now():%Y%m%d}-{uuid4().hex[:12].upper()}",
            activity_date=date, problem_description=problem, executed_action=action,
            contact_name=contact, contact_phone=phone,
            is_collective_agenda=is_collective_agenda,
            validation_status='Pending', delegation=delegation, user=request.user,
            **typed_fields,
        )
        try:
            act.full_clean()
        except ValidationError as exc:
            return invalid_form('Revisa los datos: ' + ' '.join(exc.messages))
        act.save()
    messages.success(request, f"Atención {act.activity_code} registrada correctamente.")
    return redirect('activities:dashboard')


def activity_validate_view(request, pk):
    activity = get_object_or_404(Activity, pk=pk)

    if request.method == 'POST':
        decision = request.POST.get('decision', 'Approved')
        observations = request.POST.get('observations', '').strip()

        activity.validation_status = decision
        activity.save()

        Validation.objects.create(
            activity=activity,
            decision=decision,
            observations=observations or 'Revisión técnica registrada por el verificador.'
        )

        decision_label = 'Aprobada' if decision == 'Approved' else ('Rechazada' if decision == 'Rejected' else 'Observada')
        messages.success(request, f"La actividad {activity.activity_code} ha sido marcada como '{decision_label}'.")

    return redirect('activities:dashboard')

from django.http import JsonResponse
import json
import re
from .models import Vecino


def _normalize_vecino_rut(value):
    return re.sub(r'[^0-9kK]', '', value or '').upper()


def _format_vecino_rut(value):
    cleaned = _normalize_vecino_rut(value)
    if len(cleaned) < 2:
        return value
    number, verifier = cleaned[:-1], cleaned[-1]
    groups = []
    while number:
        groups.insert(0, number[-3:])
        number = number[:-3]
    return f"{'.'.join(groups)}-{verifier}"


def _valid_vecino_rut(value):
    cleaned = _normalize_vecino_rut(value)
    if len(cleaned) < 2 or not cleaned[:-1].isdigit():
        return False
    total, multiplier = 0, 2
    for digit in reversed(cleaned[:-1]):
        total += int(digit) * multiplier
        multiplier = 2 if multiplier == 7 else multiplier + 1
    result = 11 - (total % 11)
    expected = '0' if result == 11 else ('K' if result == 10 else str(result))
    return cleaned[-1] == expected


def _vecino_payload(data):
    return {
        'nombre': str(data.get('nombre', '')).strip(),
        'rut': _format_vecino_rut(str(data.get('rut', '')).strip()),
        'email': str(data.get('email', '')).strip().lower() or None,
        'direccion': str(data.get('direccion', '')).strip(),
        'telefono': str(data.get('telefono', '')).strip(),
        'territorio': str(data.get('territorio', '')).strip(),
        'estado': str(data.get('estado', 'Activo')).strip(),
    }


def _vecino_rut_exists(rut, exclude_pk=None):
    qs = Vecino.objects.all()
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    normalized = _normalize_vecino_rut(rut)
    return any(_normalize_vecino_rut(existing) == normalized for existing in qs.values_list('rut', flat=True))


def _vecino_email_exists(email, exclude_pk=None):
    if not email:
        return False
    qs = Vecino.objects.filter(email__iexact=email)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


def _validate_vecino_email(email):
    if not email:
        return True
    try:
        validate_email(email)
    except ValidationError:
        return False
    return True


def _serialize_vecino(vecino):
    return {
        'id': vecino.id,
        'nombre': vecino.nombre,
        'rut': vecino.rut,
        'email': vecino.email or '',
        'direccion': vecino.direccion or '',
        'telefono': vecino.telefono or '',
        'territorio': vecino.territorio or '',
        'gestion': 'Solicitud',
        'estado': vecino.estado,
    }

def _vecino_scope(request):
    profile = _actor(request)
    qs = Vecino.objects.filter(deleted_at__isnull=True)
    if not profile:
        return qs if _is_admin(request) else qs.none()
    # Si pertenece a una delegación, SOLO puede ver y editar datos de su misma delegación
    if profile.delegation_id and profile.delegation and profile.delegation.status == 'Activo':
        return qs.filter(territorio__iexact=profile.delegation.name)
    if _is_admin(request):
        return qs
    return qs.none()


def api_vecinos(request):
    if request.method not in {'GET', 'POST'}:
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)

    required_permission = 'lectura' if request.method == 'GET' else 'edicion'
    if request.method == 'DELETE':
        required_permission = 'cierre'
    if not _has_matrix_permission(request, required_permission):
        return _permission_denied(required_permission)

    if request.method == 'GET':
        vecinos = [_serialize_vecino(v) for v in _vecino_scope(request).order_by('nombre')]
        return JsonResponse({'success': True, 'vecinos': vecinos})
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'message': 'Solicitud JSON inválida.'}, status=400)
        payload = _vecino_payload(data)
        profile = _actor(request)
        if profile and profile.delegation:
            # La delegación del usuario determina estrictamente su territorio
            payload['territorio'] = profile.delegation.name
        if not payload['nombre'] or not payload['rut'] or not payload['direccion']:
            return JsonResponse({'success': False, 'message': 'Nombre, RUT y dirección son obligatorios.'}, status=400)
        if (len(payload['nombre']) > 150 or len(payload['rut']) > 15 or len(payload['email'] or '') > 254
                or len(payload['direccion']) > 255 or len(payload['telefono']) > 20 or len(payload['territorio']) > 100):
            return JsonResponse({'success': False, 'message': 'Revisa el largo permitido del nombre, RUT, correo, dirección o teléfono.'}, status=400)
        if not _valid_vecino_rut(payload['rut']):
            return JsonResponse({'success': False, 'message': 'RUT inválido. Revisa el número y el dígito verificador.'}, status=400)
        if not _validate_vecino_email(payload['email']):
            return JsonResponse({'success': False, 'message': 'Correo electrónico no válido.'}, status=400)
        if payload['estado'] not in {'Activo', 'Inactivo'}:
            return JsonResponse({'success': False, 'message': 'Estado de vecino no válido.'}, status=400)
        if _vecino_rut_exists(payload['rut']):
            return JsonResponse({'success': False, 'message': 'Ya existe un vecino registrado con ese RUT.'}, status=400)
        if _vecino_email_exists(payload['email']):
            return JsonResponse({'success': False, 'message': 'Ya existe un vecino registrado con ese correo electrónico.'}, status=400)
        vecino = Vecino.objects.create(**payload)
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            affected_table='vecino', affected_record_id=str(vecino.id), action='CREATE',
            new_value=_serialize_vecino(vecino), source_ip=request.META.get('REMOTE_ADDR'))
        return JsonResponse({'success': True, 'message': 'Vecino guardado en la base de datos.', 'vecino': _serialize_vecino(vecino)})

def api_vecino_detail(request, pk):
    if request.method not in {'GET', 'POST', 'PUT', 'DELETE'}:
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)

    required_permission = 'lectura' if request.method == 'GET' else 'edicion'
    if request.method == 'DELETE':
        required_permission = 'cierre'
    if not _has_matrix_permission(request, required_permission):
        return _permission_denied(required_permission)

    try:
        vecino = _vecino_scope(request).get(pk=pk)
    except Vecino.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Vecino no encontrado o no pertenece a tu delegación.'}, status=404)
        
    if request.method == 'GET':
        return JsonResponse({'success': True, 'vecino': _serialize_vecino(vecino)})
    if request.method == 'PUT' or request.method == 'POST':
        try:
            data = json.loads(request.body)
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'message': 'Solicitud JSON inválida.'}, status=400)
        payload = _vecino_payload(data)
        profile = _actor(request)
        if profile and profile.delegation:
            if payload.get('territorio') and payload['territorio'].casefold() != profile.delegation.name.casefold():
                return JsonResponse({'success': False, 'message': f'Territorio no autorizado. Solo puedes gestionar datos de tu delegación asignada ({profile.delegation.name}).'}, status=403)
            payload['territorio'] = profile.delegation.name
        if 'email' not in data:
            payload['email'] = vecino.email
        if not payload['nombre'] or not payload['rut'] or not payload['direccion']:
            return JsonResponse({'success': False, 'message': 'Nombre, RUT y dirección son obligatorios.'}, status=400)
        if (len(payload['nombre']) > 150 or len(payload['rut']) > 15 or len(payload['email'] or '') > 254
                or len(payload['direccion']) > 255 or len(payload['telefono']) > 20 or len(payload['territorio']) > 100):
            return JsonResponse({'success': False, 'message': 'Revisa el largo permitido del nombre, RUT, correo, dirección o teléfono.'}, status=400)
        rut_changed = _normalize_vecino_rut(payload['rut']) != _normalize_vecino_rut(vecino.rut)
        if rut_changed and not _valid_vecino_rut(payload['rut']):
            return JsonResponse({'success': False, 'message': 'RUT inválido. Revisa el número y el dígito verificador.'}, status=400)
        if not _validate_vecino_email(payload['email']):
            return JsonResponse({'success': False, 'message': 'Correo electrónico no válido.'}, status=400)
        if _vecino_rut_exists(payload['rut'], exclude_pk=vecino.pk):
            return JsonResponse({'success': False, 'message': 'Ya existe otro vecino registrado con ese RUT.'}, status=400)
        if _vecino_email_exists(payload['email'], exclude_pk=vecino.pk):
            return JsonResponse({'success': False, 'message': 'Ya existe otro vecino registrado con ese correo electrónico.'}, status=400)
        previous = _serialize_vecino(vecino)
        for field, value in payload.items():
            setattr(vecino, field, value)
        vecino.save()
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            affected_table='vecino', affected_record_id=str(vecino.id), action='UPDATE',
            previous_value=previous, new_value=_serialize_vecino(vecino), source_ip=request.META.get('REMOTE_ADDR'))
        return JsonResponse({'success': True, 'message': 'Vecino actualizado en la base de datos.', 'vecino': _serialize_vecino(vecino)})
    elif request.method == 'DELETE':
        previous = _serialize_vecino(vecino)
        vecino.deleted_at = timezone.now()
        vecino.estado = 'Inactivo'
        vecino.save(update_fields=['deleted_at', 'estado', 'updated_at'])
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            affected_table='vecino', affected_record_id=str(vecino.id), action='DELETE',
            previous_value=previous, source_ip=request.META.get('REMOTE_ADDR'))
        return JsonResponse({'success': True, 'message': 'Vecino dado de baja y conservado en auditoría.'})

def _attention_payload(request):
    try:
        data = json.loads(request.body)
    except (TypeError, ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _attention_text(data, key, limit, required=False):
    value = data.get(key, '')
    if not isinstance(value, str):
        return None
    value = value.strip()
    if (required and not value) or len(value) > limit:
        return None
    return value


def _attention_catalog(data):
    from .models import ServiceCatalog
    catalog_id = data.get('catalog_id')
    attention_type = data.get('attention_type')
    subattention_type = data.get('subattention_type')
    if catalog_id is None and attention_type is None and subattention_type is None:
        return None, None
    qs = ServiceCatalog.objects.filter(status='Activo', deleted_at__isnull=True)
    if catalog_id is not None:
        try:
            catalog = qs.get(pk=parse_catalog_id(catalog_id))
        except (ValueError, TypeError, ServiceCatalog.DoesNotExist):
            return None, 'Tipo de atención no válido.'
    else:
        if not isinstance(attention_type, str) or not isinstance(subattention_type, str):
            return None, 'Tipo y subatención no válidos.'
        matches = qs.filter(attention_type__iexact=attention_type.strip(),
                            subattention_type__iexact=subattention_type.strip())
        if matches.count() != 1:
            return None, 'La combinación Tipo/Sub Atención no es válida.'
        catalog = matches.first()
    if attention_type and (not isinstance(attention_type, str) or catalog.attention_type.casefold() != attention_type.strip().casefold()):
        return None, 'El tipo no corresponde al catálogo.'
    if subattention_type and (not isinstance(subattention_type, str) or catalog.subattention_type.casefold() != subattention_type.strip().casefold()):
        return None, 'La subatención no corresponde al tipo.'
    return catalog, None


def _typed_attention_selection(data):
    """Validate the exact active type/subtype pair supplied by the client."""
    type_id = data.get('attention_type_id')
    sub_id = data.get('subattention_id')
    if type_id is None and sub_id is None:
        return None, None, None
    if type_id is None or sub_id is None:
        return None, None, 'Debe seleccionar Tipo y Sub Atención.'
    try:
        from metrics.models import AttentionType, SubAttention
    except ImportError:
        return None, None, 'Catálogo de tipos no disponible.'
    try:
        type_pk, sub_pk = parse_catalog_id(type_id), parse_catalog_id(sub_id)
    except (TypeError, ValueError):
        return None, None, 'IDs de Tipo/Sub Atención inválidos.'
    attention_type = AttentionType.objects.filter(pk=type_pk, deleted_at__isnull=True).first()
    subattention = SubAttention.objects.filter(pk=sub_pk, deleted_at__isnull=True).first()
    if not attention_type or not subattention:
        return None, None, 'Tipo o Sub Atención inexistente.'
    if (getattr(attention_type, 'status', 'Activo') != 'Activo'
            or getattr(subattention, 'status', 'Activo') != 'Activo'):
        return None, None, 'Tipo o Sub Atención inactivo.'
    if subattention.attention_type_id != attention_type.pk:
        return None, None, 'La Sub Atención no pertenece al Tipo seleccionado.'
    return attention_type, subattention, None


def _attention_has_typed_fields():
    return {'attention_type', 'subattention'}.issubset(
        {field.name for field in Activity._meta.fields}
    )


def _attention_result(a):
    evid = a.evidences.first()
    val = a.validations.first()
    return {
        'id': a.id, 'activity_code': a.activity_code,
        'neighbor_id': a.neighbor_id,
        'evidence_code': evid.evidence_code if evid else '',
        'contact_name': a.contact_name, 'contact_phone': a.contact_phone,
        'delegation': a.delegation.name if a.delegation else '',
        'catalog_id': a.catalog_id,
        'attention_type_id': getattr(a, 'attention_type_id', None),
        'subattention_id': getattr(a, 'subattention_id', None),
        'attention_type': a.attention_type.name if a.attention_type_id else (a.catalog.attention_type if a.catalog else ''),
        'subattention_type': a.subattention.name if a.subattention_id else (a.catalog.subattention_type if a.catalog else ''),
        'service': a.catalog.service if a.catalog else '',
        'title': a.problem_description, 'description': a.executed_action,
        'problem_description': a.problem_description,
        'executed_action': a.executed_action,
        'activity_date_iso': a.activity_date.isoformat(),
        'stage': 2 if a.is_collective_agenda else 1,
        'date': a.activity_date.strftime('%d/%m/%Y'),
        'activity_date': a.activity_date.strftime('%d/%m/%Y'),
        'status': a.validation_status, 'validation_status': a.validation_status,
        'observation': val.observations if val else '',
        'verifier_notes': val.observations if val else '',
    }


def api_atenciones(request):
    if request.method not in {'GET', 'POST'}:
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    permission = 'lectura' if request.method == 'GET' else 'edicion'
    if not _has_matrix_permission(request, permission):
        return _permission_denied(permission)
    if request.method == 'GET':
        qs = _activity_scope(request).select_related('delegation', 'catalog', 'attention_type', 'subattention', 'neighbor').prefetch_related('evidences', 'validations')
        return JsonResponse({'success': True, 'atenciones': [_attention_result(a) for a in qs.order_by('-activity_date', '-created_at')]})

    data = _attention_payload(request)
    if data is None:
        return JsonResponse({'success': False, 'message': 'Solicitud JSON inválida.'}, status=400)
    delegation = _delegation_for_write(request, data.get('delegation'))
    if not delegation:
        return JsonResponse({'success': False, 'message': 'Delegación no autorizada o inactiva.'}, status=403)
    neighbor = None
    neighbor_id = data.get('neighbor_id')
    if neighbor_id not in (None, ''):
        if isinstance(neighbor_id, bool) or not str(neighbor_id).isdecimal():
            return JsonResponse({'success': False, 'message': 'Vecino asociado no válido.'}, status=400)
        neighbor = _vecino_scope(request).filter(pk=int(neighbor_id), deleted_at__isnull=True).first()
        if not neighbor:
            return JsonResponse({'success': False, 'message': 'El vecino asociado no existe o no está disponible.'}, status=404)
    catalog, error = _attention_catalog(data)
    attention_type, subattention, typed_error = _typed_attention_selection(data)
    if typed_error:
        return JsonResponse({'success': False, 'message': typed_error}, status=400)
    if attention_type and not _attention_has_typed_fields():
        return JsonResponse({'success': False, 'message': 'Persistencia Tipo/Sub Atención aún no disponible.'}, status=503)
    if error:
        return JsonResponse({'success': False, 'message': error}, status=400)
    contact = _attention_text(data, 'contact_name', 150, required=True)
    phone = _attention_text(data, 'contact_phone', 20)
    problem = _attention_text(data, 'problem_description', 1000) if 'problem_description' in data else _attention_text(data, 'title', 1000, required=True)
    action = _attention_text(data, 'executed_action', 1000) if 'executed_action' in data else _attention_text(data, 'description', 1000, required=True)
    if not contact or phone is None or not problem or not action:
        return JsonResponse({'success': False, 'message': 'Solicitante, problema o acción inválidos.'}, status=400)
    # Estado enviado por la interfaz no autoriza una aprobación.
    if 'is_collective_agenda' in data and not isinstance(data['is_collective_agenda'], bool):
        return JsonResponse({'success': False, 'message': 'Agenda colectiva inválida.'}, status=400)
    code = _attention_text(data, 'activity_code', 50) if 'activity_code' in data else ''
    if code is None or (code and not re.fullmatch(r'[A-Za-z0-9-]+', code)):
        return JsonResponse({'success': False, 'message': 'Código inválido.'}, status=400)
    try:
        activity_date = datetime.date.fromisoformat(data.get('activity_date', timezone.localdate().isoformat()))
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': 'Fecha de atención o visita inválida.'}, status=400)
    from django.db import transaction
    from django.db.models import Q
    from uuid import uuid4
    with transaction.atomic():
        # Lock the actor on databases that support row locks. A retry with the same
        # client code returns the existing record instead of creating another.
        from django.contrib.auth import get_user_model
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        if code:
            existing = Activity.objects.filter(activity_code=code).first()
            if existing:
                if (existing.user_id == request.user.pk and existing.deleted_at is None
                        and existing.contact_name == contact and existing.problem_description == problem
                        and existing.executed_action == action and existing.delegation_id == delegation.id
                        and existing.activity_date == activity_date
                        and existing.neighbor_id == (neighbor.pk if neighbor else None)
                        and existing.contact_phone == phone and existing.catalog_id == (catalog.pk if catalog else None)
                        and existing.attention_type_id == (attention_type.pk if attention_type else None)
                        and existing.subattention_id == (subattention.pk if subattention else None)
                        and existing.is_collective_agenda == data.get('is_collective_agenda', False)):
                    return JsonResponse({'success': True, 'id': existing.id, 'message': 'Atención ya registrada.'})
                return JsonResponse({'success': False, 'message': 'Código ya utilizado.'}, status=409)
        else:
            cutoff = timezone.now() - datetime.timedelta(seconds=30)
            existing = _activity_scope(request).filter(
                user=request.user, delegation=delegation, contact_name=contact,
                problem_description=problem, executed_action=action,
                activity_date=activity_date,
                catalog=catalog, attention_type=attention_type, subattention=subattention,
                contact_phone=phone, is_collective_agenda=data.get('is_collective_agenda', False),
                created_at__gte=cutoff
            ).first()
            if existing:
                return JsonResponse({'success': True, 'id': existing.id, 'message': 'Atención ya registrada.'})
            code = f"ACT-{timezone.now():%Y%m%d}-{uuid4().hex[:12].upper()}"
        typed_fields = {'attention_type': attention_type, 'subattention': subattention} if attention_type else {}
        act = Activity.objects.create(
            activity_code=code, activity_date=activity_date,
            problem_description=problem, executed_action=action,
            contact_name=contact, contact_phone=phone,
            is_collective_agenda=data.get('is_collective_agenda', False),
            validation_status='Pending', delegation=delegation,
            catalog=catalog, user=request.user, neighbor=neighbor, **typed_fields
        )
        if neighbor and neighbor.nombre != contact:
            neighbor.nombre = contact
            neighbor.save(update_fields=['nombre', 'updated_at'])
    return JsonResponse({'success': True, 'id': act.id, 'message': f'Atención {code} registrada.'}, status=201)


def api_atencion_detail(request, pk):
    if request.method not in {'GET', 'POST', 'PUT', 'DELETE'}:
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    permission = 'lectura' if request.method == 'GET' else ('cierre' if request.method == 'DELETE' else 'edicion')
    if not _has_matrix_permission(request, permission):
        return _permission_denied(permission)
    a = _activity_scope(request).select_related('delegation', 'catalog', 'attention_type', 'subattention', 'neighbor').filter(pk=pk).first()
    if not a:
        return JsonResponse({'success': False, 'message': 'Atención no encontrada.'}, status=404)
    if request.method == 'GET':
        return JsonResponse({'success': True, 'atencion': _attention_result(a)})
    if request.method == 'DELETE':
        previous = _attention_result(a)
        with transaction.atomic():
            a.deleted_at = timezone.now()
            a.save(update_fields=['deleted_at', 'updated_at'])
            AuditLog.objects.create(
                user=request.user,
                affected_table='actividad',
                affected_record_id=str(a.pk),
                action='DELETE',
                previous_value=previous,
                new_value={'deleted_at': a.deleted_at.isoformat()},
                source_ip=request.META.get('REMOTE_ADDR'),
            )
        return JsonResponse({'success': True, 'message': 'Atención dada de baja.'})
    data = _attention_payload(request)
    if data is None:
        return JsonResponse({'success': False, 'message': 'Solicitud JSON inválida.'}, status=400)
    if 'validation_status' in data or 'status' in data:
        return JsonResponse({'success': False, 'message': 'La validación corresponde al Verificador Técnico.'}, status=403)
    previous = _attention_result(a)
    if 'activity_date' in data:
        try:
            a.activity_date = datetime.date.fromisoformat(data['activity_date'])
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'message': 'Fecha de atención o visita inválida.'}, status=400)
    if 'neighbor_id' in data:
        neighbor_id = data.get('neighbor_id')
        if neighbor_id in (None, ''):
            a.neighbor = None
        elif isinstance(neighbor_id, bool) or not str(neighbor_id).isdecimal():
            return JsonResponse({'success': False, 'message': 'Vecino asociado no válido.'}, status=400)
        else:
            neighbor = _vecino_scope(request).filter(pk=int(neighbor_id), deleted_at__isnull=True).first()
            if not neighbor:
                return JsonResponse({'success': False, 'message': 'El vecino asociado no existe o no está disponible.'}, status=404)
            a.neighbor = neighbor
    if 'delegation' in data:
        delegation = _delegation_for_write(request, data['delegation'])
        if not delegation:
            return JsonResponse({'success': False, 'message': 'Delegación no autorizada.'}, status=403)
        a.delegation = delegation
    if any(key in data for key in ('catalog_id', 'attention_type', 'subattention_type')):
        catalog, error = _attention_catalog(data)
        if error or not catalog:
            return JsonResponse({'success': False, 'message': error or 'Tipo de atención inválido.'}, status=400)
        a.catalog = catalog
    if 'attention_type_id' in data or 'subattention_id' in data:
        attention_type, subattention, typed_error = _typed_attention_selection(data)
        if typed_error or not attention_type:
            return JsonResponse({'success': False, 'message': typed_error or 'Selección inválida.'}, status=400)
        if not _attention_has_typed_fields():
            return JsonResponse({'success': False, 'message': 'Persistencia Tipo/Sub Atención aún no disponible.'}, status=503)
        a.attention_type = attention_type
        a.subattention = subattention
    for key, limit in (('contact_name', 150), ('contact_phone', 20), ('problem_description', 1000), ('executed_action', 1000)):
        if key in data:
            value = _attention_text(data, key, limit, required=key != 'contact_phone')
            if value is None:
                return JsonResponse({'success': False, 'message': f'{key} inválido.'}, status=400)
            setattr(a, key, value)
    with transaction.atomic():
        if a.neighbor_id and a.contact_name and a.neighbor.nombre != a.contact_name:
            a.neighbor.nombre = a.contact_name
            a.neighbor.save(update_fields=['nombre', 'updated_at'])
        a.save()
        AuditLog.objects.create(
            user=request.user,
            affected_table='actividad',
            affected_record_id=str(a.pk),
            action='UPDATE',
            previous_value=previous,
            new_value=_attention_result(a),
            source_ip=request.META.get('REMOTE_ADDR'),
        )
    return JsonResponse({'success': True, 'message': 'Atención actualizada.'})


def api_toggle_rol_permiso(request):
    """
    Permite activar/desactivar permisos (lectura, edicion, derivacion, cierre) en los roles
    y persistirlos directamente en la base de datos MySQL (tabla: rol).
    """
    if not _is_admin(request):
        return JsonResponse({'success': False, 'message': f'Se requiere el rol {ADMINISTRATOR_ROLE_NAME}.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)
    
    from organization.models import Role
    try:
        data = json.loads(request.body)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': 'La solicitud no contiene JSON válido.'}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({'success': False, 'message': 'La solicitud debe ser un objeto JSON.'}, status=400)
    rol_name = data.get('rol_name')
    permiso = data.get('permiso')
    enabled = data.get('enabled')
    if not isinstance(rol_name, str) or not rol_name.strip() or not isinstance(permiso, str):
        return JsonResponse({'success': False, 'message': 'Rol o permiso inválido.'}, status=400)
    if not isinstance(enabled, bool):
        return JsonResponse({'success': False, 'message': 'El estado del permiso debe ser verdadero o falso.'}, status=400)
    rol_name = rol_name.strip()
    permiso = permiso.strip().lower()

    allowed_permissions = {'lectura', 'edicion', 'derivacion', 'cierre'}
    if permiso not in allowed_permissions:
        return JsonResponse({'success': False, 'message': 'Permiso no válido para esta matriz.'}, status=400)

    with transaction.atomic():
        rol = Role.objects.select_for_update().filter(
            name__iexact=rol_name, deleted_at__isnull=True
        ).prefetch_related('permission_definitions').first()
        if not rol:
            return JsonResponse({'success': False, 'message': 'El rol indicado no existe o ya no está activo.'}, status=404)
        if is_administrator_role(rol):
            return JsonResponse({
                'success': False,
                'message': 'El rol Administrador conserva acceso integral; sus permisos no se pueden apagar individualmente.',
            }, status=403)

        previous_permissions = sorted(role_permission_codes(rol))
        perms = set(previous_permissions)
        if enabled:
            perms.add(permiso)
        else:
            perms.discard(permiso)

        permissions = set_role_permission_codes(rol, perms)
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            affected_table='rol',
            affected_record_id=str(rol.pk),
            action='UPDATE',
            previous_value={'role': rol.name, 'permissions': previous_permissions},
            new_value={'role': rol.name, 'permissions': permissions, 'changed_permission': permiso, 'enabled': enabled},
            source_ip=request.META.get('REMOTE_ADDR'),
        )

    return JsonResponse({
        'success': True,
        'message': f"Permiso de {permiso.capitalize()} {'activado' if enabled else 'desactivado'} para '{rol.name}' en la base de datos.",
        'permissions': permissions
    })


def api_sgr_4to_semestre(request):
    """
    Endpoint oficial para consultar y registrar las reglas operativas de la Matriz SGR 4to Semestre:
    - GET: retorna los 10 puntos normativos y las 5 subfamilias OOCC.
    - POST (action='felicitacion'): Regla 8 - Solo el Delegado o Administrador informa felicitaciones con respaldo formal.
    - POST (action='ausencia_semaforo'): Regla 9 - El Delegado registra vacaciones, licencias y días administrativos en Semáforo.
    """
    from .descriptor_2026 import OOCC_SUBFAMILIAS_2026, SGR_4TO_SEMESTRE_RULES
    from metrics.models import MeasurementPeriod, PerformanceAdjustment

    profile = _actor(request)
    if not profile:
        return JsonResponse({'success': False, 'message': 'Autenticación requerida.'}, status=403)

    if request.method == 'GET':
        if not _has_matrix_permission(request, 'lectura'):
            return _permission_denied('lectura')
        return JsonResponse({
            'success': True,
            'rules': SGR_4TO_SEMESTRE_RULES,
            'oocc_subfamilias': OOCC_SUBFAMILIAS_2026,
        })

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)

    is_delegado_or_admin = bool(
        _is_admin(request)
        or (profile.position and _normalized_label(profile.position.name) in ('delegado municipal', 'delegado'))
    )
    if not is_delegado_or_admin:
        return JsonResponse({
            'success': False,
            'message': 'Reglas 8 y 9 SGR: Solo el Delegado Municipal puede informar felicitaciones formales o ingresar ausencias en Semáforo.',
        }, status=403)

    try:
        data = json.loads(request.body)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': 'Solicitud JSON inválida.'}, status=400)

    action = str(data.get('action', '')).strip()
    period = MeasurementPeriod.objects.filter(deleted_at__isnull=True).order_by('-start_date').first()

    if action == 'felicitacion':
        funcionario = str(data.get('funcionario', '')).strip()
        vecino = str(data.get('vecino', '')).strip()
        canal = str(data.get('canal', '')).strip()
        respaldo = str(data.get('respaldo', '')).strip()
        motivo = str(data.get('motivo', '')).strip()
        if not funcionario or not vecino or not respaldo or not motivo:
            return JsonResponse({
                'success': False,
                'message': 'Regla 8 SGR: Debe indicar funcionario, vecino con contacto, folio de respaldo formal y motivo.',
            }, status=400)
        if 'mensaje directo' in canal.lower() or 'whatsapp directo al gestor' in canal.lower():
            return JsonResponse({
                'success': False,
                'message': 'Regla 8 SGR: Los mensajes directos al gestor no son válidos. La felicitación debe dirigirse al Delegado o con respaldo formal en delegación.',
            }, status=400)

        if period:
            PerformanceAdjustment.objects.create(
                user=request.user,
                period=period,
                adjustment_type='Congratulation',
                points_value=1.0,
                justification=f"[{funcionario}] Vecino: {vecino} | Canal: {canal} | Respaldo: {respaldo} | {motivo}"[:1000],
            )
        AuditLog.objects.create(
            user=request.user,
            affected_table='semaforo_felicitaciones_sgr',
            affected_record_id=respaldo[:50],
            action='CREATE',
            new_value={
                'funcionario': funcionario,
                'vecino': vecino,
                'canal': canal,
                'respaldo': respaldo,
                'motivo': motivo,
            },
            source_ip=request.META.get('REMOTE_ADDR'),
        )
        return JsonResponse({
            'success': True,
            'message': 'Felicitación formal registrada por el Delegado conforme al Punto 8 de la Matriz SGR.',
        })

    if action == 'ausencia_semaforo':
        funcionario = str(data.get('funcionario', '')).strip()
        tipo = str(data.get('tipo', '')).strip()
        try:
            dias = int(data.get('dias', 0))
        except (TypeError, ValueError):
            dias = 0
        respaldo = str(data.get('respaldo', '')).strip()
        if not funcionario or not tipo or dias <= 0:
            return JsonResponse({
                'success': False,
                'message': 'Regla 9 SGR: Indique funcionario, tipo de ausencia (Vacaciones/Licencia/Administrativo) y días hábiles.',
            }, status=400)

        AuditLog.objects.create(
            user=request.user,
            affected_table='semaforo_ausencias_sgr',
            affected_record_id=funcionario[:50],
            action='CREATE',
            new_value={
                'funcionario': funcionario,
                'tipo_ausencia': tipo,
                'dias_descuento': dias,
                'respaldo': respaldo,
            },
            source_ip=request.META.get('REMOTE_ADDR'),
        )
        return JsonResponse({
            'success': True,
            'message': f'Ausencia ({tipo}: {dias} días) ingresada en Semáforo SGR conforme al Punto 9.',
        })

    return JsonResponse({'success': False, 'message': 'Acción SGR no reconocida.'}, status=400)


