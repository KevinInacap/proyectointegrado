import datetime
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Activity, Evidence, Validation
from organization.models import Delegation, UserProfile
from core.models import AuditLog
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
        request.user.is_superuser or profile.roles.filter(
            name='Administrador General', deleted_at__isnull=True
        ).exists()
    ))


def _has_matrix_permission(request, permission):
    profile = _actor(request)
    if not profile:
        return False
    if _is_admin(request):
        return True
    return any(
        permission.lower() in {str(p).lower() for p in (role.permissions_data or [])}
        for role in profile.roles.filter(deleted_at__isnull=True)
    )


def _activity_scope(request):
    profile = _actor(request)
    qs = Activity.objects.filter(deleted_at__isnull=True)
    if _is_admin(request):
        return qs
    if (not profile or not profile.delegation_id or profile.delegation.status != 'Activo'
            or profile.delegation.deleted_at is not None):
        return qs.none()
    return qs.filter(delegation_id=profile.delegation_id)


def _delegation_for_write(request, value):
    profile = _actor(request)
    if not profile:
        return None
    requested = str(value or '').strip()
    if not requested and not _is_admin(request):
        return profile.delegation if (profile.delegation and profile.delegation.status == 'Activo'
                                      and profile.delegation.deleted_at is None) else None
    if not requested:
        return None
    # Names and IDs must match exactly. Never use substring matching for access control.
    qs = Delegation.objects.filter(status='Activo', deleted_at__isnull=True)
    delegation = qs.filter(pk=int(requested)).first() if requested.isdecimal() else qs.filter(name__iexact=requested).first()
    if delegation and (_is_admin(request) or delegation.pk == profile.delegation_id):
        return delegation
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

def dashboard_view(request):
    profile = _actor(request)
    if not profile:
        return redirect('core:login')
    roles = set(profile.roles.filter(deleted_at__isnull=True).values_list('name', flat=True))
    if _is_admin(request):
        return redirect('activities:dashboard_admin')
    if roles.intersection({'Coordinador del Sistema', 'Coordinador'}):
        return redirect('activities:dashboard_coordinador')
    if roles.intersection({'Delegado Municipal', 'Delegado'}):
        return redirect('activities:dashboard_delegado')
    if 'Usuario de Consulta' in roles:
        return redirect('activities:dashboard_consulta')
    if roles.intersection({'Verificador Técnico', 'Verificador'}):
        return redirect('activities:dashboard_verificador')
    if roles.intersection({'Gestor Territorial', 'Funcionario', 'Funcionario / Gestor Territorial'}):
        return redirect('activities:dashboard_gestor')
    return redirect('core:login')


def _readonly_landing(request, role_name, title):
    profile = _actor(request)
    aliases = {
        'Coordinador del Sistema': {'Coordinador del Sistema', 'Coordinador'},
        'Delegado Municipal': {'Delegado Municipal', 'Delegado'},
        'Usuario de Consulta': {'Usuario de Consulta'},
    }
    if not profile:
        return redirect('core:login')
    current_role = profile.roles.filter(
        name__in=aliases[role_name], deleted_at__isnull=True
    ).values_list('name', flat=True).first()
    if not current_role:
        return redirect('core:login')
    module_catalog = {
        'Coordinador del Sistema': [
            {'slug': 'atenciones', 'name': 'Atenciones comunales', 'description': 'Consulta registros visibles según el alcance autorizado.'},
            {'slug': 'metas', 'name': 'Metas y períodos', 'description': 'Interfaz de seguimiento de metas y períodos de evaluación.'},
            {'slug': 'reportes', 'name': 'Reportes comunales', 'description': 'Espacio para reportes consolidados del sistema.'},
        ],
        'Delegado Municipal': [
            {'slug': 'atenciones', 'name': 'Atenciones de la sede', 'description': 'Consulta los registros de tu delegación.'},
            {'slug': 'equipo', 'name': 'Equipo territorial', 'description': 'Vista del personal asignado a tu delegación.'},
            {'slug': 'seguimiento', 'name': 'Seguimiento de casos', 'description': 'Interfaz para el seguimiento territorial de casos.'},
        ],
        'Usuario de Consulta': [
            {'slug': 'atenciones', 'name': 'Atenciones consultables', 'description': 'Consulta información dentro del alcance de tu perfil.'},
            {'slug': 'indicadores', 'name': 'Indicadores', 'description': 'Vista de indicadores institucionales autorizados.'},
            {'slug': 'reportes', 'name': 'Reportes', 'description': 'Vista de consulta para reportes disponibles.'},
        ],
    }
    role_key = next(key for key, names in aliases.items() if current_role in names)
    available_modules = module_catalog[role_key]
    from django.core.paginator import Paginator
    from django.db.models import Q
    can_read = _has_matrix_permission(request, 'lectura')
    can_edit = _has_matrix_permission(request, 'edicion')
    module_slug = request.GET.get('module', '').strip()
    if module_slug and (not can_read or module_slug not in {item['slug'] for item in available_modules}):
        return JsonResponse({'detail': 'Módulo no disponible para este perfil.'}, status=404)
    selected_module = next((item for item in available_modules if item['slug'] == module_slug), None)
    search = request.GET.get('q', '').strip()[:150]
    records = _activity_scope(request) if can_read else Activity.objects.none()
    if search:
        records = records.filter(Q(activity_code__icontains=search) | Q(problem_description__icontains=search))
    page = Paginator(records.select_related('delegation').order_by('-activity_date', '-pk'), 5).get_page(request.GET.get('page'))
    activity_count = page.paginator.count
    if role_key == 'Coordinador del Sistema':
        headline = 'Coordinación comunal'
        intro = 'Seguimiento de metas, períodos y resultados municipales.'
        sections = [{'name': 'Registros visibles', 'status': f'{activity_count} atenciones dentro del alcance autorizado'}]
    elif role_key == 'Delegado Municipal':
        team_count = UserProfile.objects.filter(
            delegation_id=profile.delegation_id, status='Activo', deleted_at__isnull=True,
        ).count() if profile.delegation_id else 0
        headline = 'Gestión de delegación'
        intro = 'Revisión de atenciones y personal de tu sede, según los permisos asignados.'
        sections = [{'name': 'Registros visibles', 'status': f'{activity_count} atenciones · {team_count} perfiles activos en la delegación'}]
    else:
        headline = 'Consulta municipal'
        intro = 'Vista de solo lectura con información disponible para tu perfil.'
        sections = [{'name': 'Alcance territorial', 'status': profile.delegation.name if profile.delegation else 'Acceso según permisos asignados'}]
    for module in available_modules:
        module['status'] = (
            f'{activity_count} registros disponibles' if module['slug'] == 'atenciones' and can_read
            else 'Vista de referencia · lógica pendiente de esta entrega'
        )
    return render(request, 'activities/dashboard_role.html', {
        'role_name': current_role,
        'full_name': profile.full_name,
        'delegation_name': profile.delegation.name if profile.delegation else 'Sin delegación',
        'sections': sections,
        'modules': available_modules if can_read else [],
        'selected_module': selected_module,
        'can_edit': can_edit,
        'dashboard_title': title,
        'dashboard_headline': headline,
        'dashboard_intro': intro,
        'can_read': can_read,
        'records_page': page,
        'search': search,
    })


def dashboard_coordinador_view(request):
    return _readonly_landing(request, 'Coordinador del Sistema', 'Coordinación del Sistema')


def dashboard_delegado_view(request):
    return _readonly_landing(request, 'Delegado Municipal', 'Delegación Municipal')


def dashboard_consulta_view(request):
    return _readonly_landing(request, 'Usuario de Consulta', 'Consulta')


def dashboard_admin_view(request):
    if not _is_admin(request):
        return redirect('core:login')
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
    user_role = profile.roles.filter(deleted_at__isnull=True).values_list('name', flat=True).first() if profile else 'Administrador General'
    context = {
        'user_name': user_name,
        'user_role': user_role,
        'live_delegation_count': active_delegations.count(),
        'live_attention_count': attention_qs.count(),
        'live_neighbor_count': Vecino.objects.filter(deleted_at__isnull=True).count(),
        'current_delegation': request.GET.get('delegacion', 'Consolidado Comunal'),
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
    access_denied = _session_role_required(request, {'Verificador Técnico', 'Verificador'})
    if access_denied:
        return access_denied

    profile = _actor(request)
    pending = _activity_scope(request).filter(
        validation_status='Pending'
    ).select_related('user', 'attention_type', 'catalog').prefetch_related('evidences', 'validations')
    evidence_queue = []
    for activity in pending:
        evidence = next((item for item in activity.evidences.all() if item.deleted_at is None), None)
        if evidence is None:
            continue
        official = activity.user.get_full_name() or activity.user.username if activity.user else 'Funcionario no asignado'
        item_name = activity.attention_type.name if activity.attention_type_id else (
            activity.catalog.service if activity.catalog_id else 'Sin clasificación'
        )
        thumbnail = evidence.file_path
        if not thumbnail.startswith(('http://', 'https://', '/')):
            thumbnail = f"/media/{thumbnail.lstrip('/')}"
        evidence_queue.append({
            'code': evidence.evidence_code,
            'date': activity.activity_date.strftime('%d %b %Y'),
            'official': official,
            'item': item_name,
            'description': activity.problem_description,
            'thumbnail': thumbnail,
            'status': activity.get_validation_status_display(),
        })

    from metrics.models import MeasurementPeriod
    today = timezone.localdate()
    pending_count = pending.count()
    approved_today = Validation.objects.filter(
        decision='Approved', created_at__date=today, deleted_at__isnull=True,
    ).count()
    rejected_count = Validation.objects.filter(
        decision__in=['Rejected', 'Requires correction'], created_at__date=today,
        deleted_at__isnull=True,
    ).count()
    latest_period = MeasurementPeriod.objects.filter(
        deleted_at__isnull=True,
    ).order_by('-start_date').first()
    current_period = latest_period.name if latest_period else 'Sin período configurado'
    user_name = profile.full_name if profile else request.user.get_full_name() or request.user.username
    user_role = profile.roles.filter(deleted_at__isnull=True).values_list('name', flat=True).first() if profile else 'Verificador Técnico'
    context = {
        'user_name': user_name,
        'user_role': user_role,
        'user_rut': profile.rut if profile else '',
        'current_delegation': profile.delegation.name if profile and profile.delegation else 'Sin delegación asignada',
        'current_period': current_period,
        'demo_data': False,
        'kpi': {
            'pending_reviews': pending_count,
            'points_validated_today': approved_today,
            'rejected_count': rejected_count,
            'delegation_avg': None,
            'delegation_status': 'Sin datos de medición',
        },
        'evidence_queue': evidence_queue,
        'officials_monitoring': [],
    }
    return render(request, 'activities/dashboard_verificador.html', context)


def dashboard_gestor_view(request):
    access_denied = _session_role_required(request, {'Gestor Territorial', 'Funcionario', 'Funcionario / Gestor Territorial'})
    if access_denied:
        return access_denied

    profile = _actor(request)
    from social.models import SocialCase
    from metrics.models import MeasurementPeriod

    activities = Activity.objects.filter(
        user=request.user, deleted_at__isnull=True,
    ).select_related('attention_type', 'catalog').prefetch_related('evidences', 'validations')
    activity_rows = list(activities)
    status_labels = {
        'Pending': 'Pendiente',
        'Approved': 'Aprobada',
        'Rejected': 'Rechazada',
        'Requires correction': 'Requiere corrección',
    }
    evidence_labels = {
        'Pending': 'En Revisión',
        'Approved': 'Aprobada',
        'Rejected': 'Observada',
        'Requires correction': 'Observada',
    }
    tubo_trabajo = [{
        'code': activity.activity_code,
        'request_date': activity.activity_date.strftime('%d %b %Y'),
        'problem': activity.problem_description,
        'requester': activity.contact_name or 'Contacto no registrado',
        'phone': activity.contact_phone or 'Sin teléfono registrado',
        'responsible': profile.full_name if profile else request.user.get_full_name() or request.user.username,
        'due_date': 'Sin plazo registrado',
        'status': status_labels.get(activity.validation_status, activity.validation_status),
    } for activity in activity_rows if activity.is_collective_agenda]

    mis_evidencias = []
    for activity in activity_rows:
        validation = activity.validations.filter(deleted_at__isnull=True).order_by('-created_at').first()
        for evidence in activity.evidences.all():
            if evidence.deleted_at is not None:
                continue
            thumbnail = evidence.file_path
            if not thumbnail.startswith(('http://', 'https://', '/')):
                thumbnail = f"/media/{thumbnail.lstrip('/')}"
            mis_evidencias.append({
                'code': evidence.evidence_code,
                'date': activity.activity_date.strftime('%d %b %Y'),
                'activity_type': activity.attention_type.name if activity.attention_type_id else (
                    activity.catalog.service if activity.catalog_id else 'Sin clasificación'
                ),
                'activity': activity.problem_description,
                'contact': activity.contact_name or 'Contacto no registrado',
                'phone': activity.contact_phone or 'Sin teléfono registrado',
                'thumbnail': thumbnail,
                'hash_inmutable': 'Huella digital no disponible',
                'supervisor_status': evidence_labels.get(activity.validation_status, activity.validation_status),
                'status': evidence_labels.get(activity.validation_status, activity.validation_status),
                'due_date': 'Sin plazo registrado',
                'supervisor_note': validation.observations if validation else 'Sin observaciones registradas',
                'last_modified': timezone.localtime(activity.updated_at).strftime('%d %b %Y, %H:%M'),
            })

    cases = SocialCase.objects.filter(
        delegation_id=profile.delegation_id if profile and profile.delegation_id else None,
        deleted_at__isnull=True,
    ).prefetch_related('managements') if profile and profile.delegation_id else SocialCase.objects.none()
    ciudadania_records = []
    for case in cases:
        management = case.managements.filter(deleted_at__isnull=True).order_by('-stage').first()
        ciudadania_records.append({
            'rut': case.user_rut,
            'name': case.user_name,
            'address': 'Sin dirección registrada',
            'phone': case.contact_phone or 'Sin teléfono registrado',
            'rsh_tramo': 'Sin dato registrado',
            'rsh_status': 'No informado',
            'last_attention': management.management_date.strftime('%d %b %Y') if management else case.entry_date.strftime('%d %b %Y'),
            'case_type': management.management_type if management else 'Sin gestión registrada',
            'stage': management.stage if management else 1,
            'status': 'En seguimiento' if management else 'Ingreso',
        })

    latest_period = MeasurementPeriod.objects.filter(deleted_at__isnull=True).order_by('-start_date').first()
    user_name = profile.full_name if profile else request.user.get_full_name() or request.user.username
    approved_count = sum(activity.validation_status == 'Approved' for activity in activity_rows)
    active_cases_count = sum(activity.validation_status != 'Approved' for activity in activity_rows if activity.is_collective_agenda)
    citizens_count = len(ciudadania_records)
    evidence_statuses = [item['supervisor_status'] for item in mis_evidencias]
    context = {
        'first_name': user_name.split()[0] if user_name else 'Funcionario',
        'user_name': user_name,
        'user_role': profile.roles.filter(deleted_at__isnull=True).values_list('name', flat=True).first() if profile else 'Funcionario',
        'user_position': profile.position.name if profile and profile.position else 'Sin cargo asignado',
        'user_status': profile.status if profile else 'Sin perfil',
        'user_rut': profile.rut if profile else '',
        'current_delegation': profile.delegation.name if profile and profile.delegation else 'Sin delegación asignada',
        'current_period': latest_period.name if latest_period else 'Sin período configurado',
        'demo_data': False,
        'dashboard_sections': [],
        'kpi': {
            'my_accumulated_validated': approved_count,
            'my_compliance_pct': None,
            'my_pending_tubo': active_cases_count,
            'my_semaphore_pct': None,
            'my_semaphore_status': 'Sin medición',
            'evidence_total': len(mis_evidencias),
            'evidence_approved': evidence_statuses.count('Aprobada'),
            'evidence_pending': evidence_statuses.count('En Revisión'),
            'evidence_observed': evidence_statuses.count('Observada'),
        },
        'tubo_trabajo': tubo_trabajo,
        'historial_personal': mis_evidencias,
        'mis_evidencias': mis_evidencias,
        'ciudadania_records': ciudadania_records,
        'active_cases_count': active_cases_count,
        'citizens_count': citizens_count,
    }
    from metrics.models import AttentionType, SubAttention
    context.update({
        'today_date': timezone.localdate().isoformat(),
        'attention_types': AttentionType.objects.filter(status='Activo', deleted_at__isnull=True).order_by('name'),
        'subattentions': SubAttention.objects.filter(
            status='Activo', deleted_at__isnull=True,
            attention_type__status='Activo', attention_type__deleted_at__isnull=True,
        ).select_related('attention_type').order_by('attention_type__name', 'name'),
    })
    return render(request, 'activities/dashboard_gestor.html', context)

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
    if not all((problem, action, contact)) or len(contact) > 150 or len(phone) > 20:
        return invalid_form('Completa solicitante, descripción y acción; revisa también el largo del nombre y teléfono.')
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
        'direccion': str(data.get('direccion', '')).strip(),
        'telefono': str(data.get('telefono', '')).strip(),
        'territorio': str(data.get('territorio', '')).strip(),
        'estado': str(data.get('estado', 'Activo')).strip(),
    }


def _serialize_vecino(vecino):
    return {
        'id': vecino.id,
        'nombre': vecino.nombre,
        'rut': vecino.rut,
        'direccion': vecino.direccion or '',
        'telefono': vecino.telefono or '',
        'territorio': vecino.territorio or '',
        'gestion': 'Solicitud',
        'estado': vecino.estado,
    }

def _vecino_scope(request):
    profile = _actor(request)
    qs = Vecino.objects.filter(deleted_at__isnull=True)
    if _is_admin(request):
        return qs
    if not profile or not profile.delegation_id or profile.delegation.status != 'Activo':
        return qs.none()
    return qs.filter(territorio__iexact=profile.delegation.name)


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
        if not _is_admin(request):
            profile = _actor(request)
            if payload['territorio'].casefold() != profile.delegation.name.casefold():
                return JsonResponse({'success': False, 'message': 'Territorio no autorizado.'}, status=403)
        if not payload['nombre'] or not payload['rut'] or not payload['direccion']:
            return JsonResponse({'success': False, 'message': 'Nombre, RUT y dirección son obligatorios.'}, status=400)
        if not _valid_vecino_rut(payload['rut']):
            return JsonResponse({'success': False, 'message': 'RUT inválido. Revisa el número y el dígito verificador.'}, status=400)
        if payload['estado'] not in {'Activo', 'Inactivo'}:
            return JsonResponse({'success': False, 'message': 'Estado de vecino no válido.'}, status=400)
        if any(_normalize_vecino_rut(v.rut) == _normalize_vecino_rut(payload['rut']) for v in _vecino_scope(request)):
            return JsonResponse({'success': False, 'message': 'Ya existe un vecino registrado con ese RUT.'}, status=400)
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
        return JsonResponse({'success': False, 'message': 'Vecino no encontrado'}, status=404)
        
    if request.method == 'GET':
        return JsonResponse({'success': True, 'vecino': _serialize_vecino(vecino)})
    if request.method == 'PUT' or request.method == 'POST':
        try:
            data = json.loads(request.body)
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'message': 'Solicitud JSON inválida.'}, status=400)
        payload = _vecino_payload(data)
        if not _is_admin(request):
            profile = _actor(request)
            if payload['territorio'].casefold() != profile.delegation.name.casefold():
                return JsonResponse({'success': False, 'message': 'Territorio no autorizado.'}, status=403)
        if not payload['nombre'] or not payload['rut'] or not payload['direccion']:
            return JsonResponse({'success': False, 'message': 'Nombre, RUT y dirección son obligatorios.'}, status=400)
        if not _valid_vecino_rut(payload['rut']):
            return JsonResponse({'success': False, 'message': 'RUT inválido. Revisa el número y el dígito verificador.'}, status=400)
        duplicate = any(_normalize_vecino_rut(v.rut) == _normalize_vecino_rut(payload['rut']) for v in _vecino_scope(request).exclude(pk=vecino.pk))
        if duplicate:
            return JsonResponse({'success': False, 'message': 'Ya existe otro vecino registrado con ese RUT.'}, status=400)
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
        qs = _activity_scope(request).select_related('delegation', 'catalog', 'attention_type', 'subattention').prefetch_related('evidences', 'validations')
        return JsonResponse({'success': True, 'atenciones': [_attention_result(a) for a in qs.order_by('-activity_date', '-created_at')]})

    data = _attention_payload(request)
    if data is None:
        return JsonResponse({'success': False, 'message': 'Solicitud JSON inválida.'}, status=400)
    delegation = _delegation_for_write(request, data.get('delegation'))
    if not delegation:
        return JsonResponse({'success': False, 'message': 'Delegación no autorizada o inactiva.'}, status=403)
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
    problem = _attention_text(data, 'problem_description', 10000) if 'problem_description' in data else _attention_text(data, 'title', 10000, required=True)
    action = _attention_text(data, 'executed_action', 10000) if 'executed_action' in data else _attention_text(data, 'description', 10000, required=True)
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
            catalog=catalog, user=request.user, **typed_fields
        )
    return JsonResponse({'success': True, 'id': act.id, 'message': f'Atención {code} registrada.'}, status=201)


def api_atencion_detail(request, pk):
    if request.method not in {'GET', 'POST', 'PUT', 'DELETE'}:
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    permission = 'lectura' if request.method == 'GET' else ('cierre' if request.method == 'DELETE' else 'edicion')
    if not _has_matrix_permission(request, permission):
        return _permission_denied(permission)
    a = _activity_scope(request).select_related('delegation', 'catalog', 'attention_type', 'subattention').filter(pk=pk).first()
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
    for key, limit in (('contact_name', 150), ('contact_phone', 20), ('problem_description', 10000), ('executed_action', 10000)):
        if key in data:
            value = _attention_text(data, key, limit, required=key != 'contact_phone')
            if value is None:
                return JsonResponse({'success': False, 'message': f'{key} inválido.'}, status=400)
            setattr(a, key, value)
    with transaction.atomic():
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
        return JsonResponse({'success': False, 'message': 'Se requiere el rol Administrador General.'}, status=403)

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
        ).first()
        if not rol:
            return JsonResponse({'success': False, 'message': 'El rol indicado no existe o ya no está activo.'}, status=404)

        previous_permissions = list(rol.permissions_data or [])
        perms = set(str(permission).lower() for permission in previous_permissions)
        if enabled:
            perms.add(permiso)
        else:
            perms.discard(permiso)

        rol.permissions_data = sorted(perms)
        rol.save(update_fields=['permissions_data', 'updated_at'])
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            affected_table='rol',
            affected_record_id=str(rol.pk),
            action='UPDATE',
            previous_value={'role': rol.name, 'permissions': previous_permissions},
            new_value={'role': rol.name, 'permissions': rol.permissions_data, 'changed_permission': permiso, 'enabled': enabled},
            source_ip=request.META.get('REMOTE_ADDR'),
        )

    return JsonResponse({
        'success': True,
        'message': f"Permiso de {permiso.capitalize()} {'activado' if enabled else 'desactivado'} para '{rol.name}' en la base de datos.",
        'permissions': list(perms)
    })

