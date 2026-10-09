import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import Activity, Evidence, Validation
from organization.models import Delegation
from core.models import AuditLog


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
    if not profile or not profile.delegation_id or profile.delegation.status != 'Activo':
        return qs.none()
    return qs.filter(delegation_id=profile.delegation_id)


def _delegation_for_write(request, value):
    profile = _actor(request)
    if not profile:
        return None
    requested = str(value or '').strip()
    if not requested and not _is_admin(request):
        return profile.delegation if profile.delegation and profile.delegation.status == 'Activo' else None
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
    role = request.session.get('user_role')
    if role not in allowed_roles:
        return redirect('core:login')
    return None

def get_or_create_initial_sample_data():
    if Activity.objects.exists():
        return

    sample_activities = [
        {
            'activity_code': 'ACT-2026-0839',
            'activity_date': datetime.date(2026, 9, 10),
            'problem_description': 'Postulación a subsidio habitacional y actualización de RSH en junta vecinal.',
            'executed_action': 'Revisión técnica de antecedentes, carga digital en plataforma y emisión de comprobante.',
            'contact_name': 'Carmen Gloria Astudillo',
            'contact_phone': '+56 9 8452 1102',
            'is_collective_agenda': True,
            'validation_status': 'Approved',
        },
        {
            'activity_code': 'ACT-2026-0840',
            'activity_date': datetime.date(2026, 9, 11),
            'problem_description': 'Inspección de obras viales y señalética preventiva en cruce Cuatro Esquinas.',
            'executed_action': 'Visita en terreno junto a equipo de tránsito, levantamiento de demarcación vial.',
            'contact_name': 'Roberto Morales Pizarro',
            'contact_phone': '+56 9 7321 9940',
            'is_collective_agenda': False,
            'validation_status': 'Approved',
        },
        {
            'activity_code': 'ACT-2026-0841',
            'activity_date': datetime.date(2026, 9, 12),
            'problem_description': 'Atención ciudadana por luminarias dañadas y microbasural en sector El Milagro.',
            'executed_action': 'Derivación formal a cuadrilla de operaciones y retiro de escombros programado.',
            'contact_name': 'Mauricio Tapia Gómez',
            'contact_phone': '+56 9 9123 4455',
            'is_collective_agenda': True,
            'validation_status': 'Pending',
        },
        {
            'activity_code': 'ACT-2026-0842',
            'activity_date': datetime.date(2026, 9, 12),
            'problem_description': 'Mesa barrial de seguridad ciudadana y coordinación preventiva con Carabineros.',
            'executed_action': 'Levantamiento de compromisos vecinales, calendario de patrullaje preventivo.',
            'contact_name': 'Loreto Valenzuela Ramos',
            'contact_phone': '+56 9 6554 2210',
            'is_collective_agenda': True,
            'validation_status': 'Approved',
        },
        {
            'activity_code': 'ACT-2026-0843',
            'activity_date': datetime.date(2026, 9, 13),
            'problem_description': 'Solicitud urgente de evaluación social por filtración y daño en techumbre.',
            'executed_action': 'Visita asistente social en terreno, informe socioeconómico preliminar.',
            'contact_name': 'Esteban Collao Barraza',
            'contact_phone': '+56 9 7844 5511',
            'is_collective_agenda': False,
            'validation_status': 'Requires correction',
        },
    ]

    for item in sample_activities:
        act = Activity.objects.create(**item)
        Evidence.objects.create(
            activity=act,
            evidence_code=f"EVI-{act.activity_code}",
            file_path=f"evidencias/{act.activity_code}.jpg",
            file_name=f"{act.activity_code}.jpg"
        )
        if act.validation_status == 'Approved':
            Validation.objects.create(
                activity=act,
                decision='Approved',
                observations='Validación técnica conforme en terreno por jefatura de delegación.'
            )

def dashboard_view(request):
    role = request.session.get('user_role', '')
    if 'Administrador' in role or 'Alcaldía' in role:
        return redirect('activities:dashboard_admin')
    elif 'Supervisor' in role or 'Verificador' in role:
        return redirect('activities:dashboard_verificador')
    else:
        return redirect('activities:dashboard_gestor')

def dashboard_admin_view(request):
    access_denied = _session_role_required(request, {'Administrador General'})
    if access_denied:
        return access_denied

    get_or_create_initial_sample_data()

    delegations = [
        {'name': 'Centro Histórico', 'compliance': 95.0, 'color': '#10B981', 'status': 'Verde'},
        {'name': 'La Pampa', 'compliance': 92.0, 'color': '#2563EB', 'status': 'Verde'},
        {'name': 'Avenida del Mar', 'compliance': 91.0, 'color': '#06B6D4', 'status': 'Verde'},
        {'name': 'Las Compañías', 'compliance': 88.0, 'color': '#7C3AED', 'status': 'Verde'},
        {'name': 'La Antena', 'compliance': 84.0, 'color': '#F59E0B', 'status': 'Ámbar'},
        {'name': 'Sector Rural', 'compliance': 71.4, 'color': '#EF4444', 'status': 'Rojo'},
    ]

    parametrizacion = [
        {
            'cargo': 'Territorial OO.CC.',
            'item': 'Operativos Vecinales y Terreno',
            'ponderador': 35,
            'meta_trimestre': '45 operativos',
            'dias_periodo': 91
        },
        {
            'cargo': 'Gestor Social',
            'item': 'Atenciones RSH y Fichas Sociales',
            'ponderador': 30,
            'meta_trimestre': '130 atenciones',
            'dias_periodo': 91
        },
        {
            'cargo': 'Prevención y Seguridad',
            'item': 'Comités Vecinales de Seguridad',
            'ponderador': 20,
            'meta_trimestre': '25 reuniones',
            'dias_periodo': 91
        },
        {
            'cargo': 'Medio Ambiente / Obras',
            'item': 'Fiscalización y Retiro de Escombros',
            'ponderador': 15,
            'meta_trimestre': '30 inspecciones',
            'dias_periodo': 91
        },
    ]

    auditoria_logs = [
        {
            'usuario': 'Jorge Cortés (Verificador)',
            'fecha': '13 Sep 2026, 15:42',
            'accion': 'Aprobación de Evidencia COM1761',
            'delegacion': 'Las Compañías',
            'estado': 'Válido'
        },
        {
            'usuario': 'Patricia Vega (Gestora)',
            'fecha': '13 Sep 2026, 14:15',
            'accion': 'Carga fotográfica ACT-2026-0843',
            'delegacion': 'La Pampa',
            'estado': 'Ingresado'
        },
        {
            'usuario': 'Jorge Cortés (Verificador)',
            'fecha': '13 Sep 2026, 12:30',
            'accion': 'Devolución técnica ACT-2026-0842 (Foto borrosa)',
            'delegacion': 'Sector Rural',
            'estado': 'Devuelto'
        },
        {
            'usuario': 'Administrador General',
            'fecha': '12 Sep 2026, 09:00',
            'accion': 'Ajuste de ponderadores meta T3 (100% verificado)',
            'delegacion': 'Consolidado Comunal',
            'estado': 'Auditoría'
        },
        {
            'usuario': 'Kevin Encina (Gestor)',
            'fecha': '12 Sep 2026, 17:20',
            'accion': 'Cierre de compromiso en Tubo TUB-2026-019',
            'delegacion': 'La Pampa',
            'estado': 'Realizado'
        },
    ]

    user_name = request.session.get('user_name') if request.session.get('user_role') == 'Administrador General' else 'Alcaldía La Serena'
    context = {
        'user_name': user_name,
        'user_role': 'Alcaldía / Control Central',
        'current_delegation': request.GET.get('delegacion', 'Consolidado Comunal'),
        'current_period': 'T3 - Septiembre 2026',
        'kpi': {
            'comunal_compliance': 88.4,
            'total_evidences': 1482,
            'tubo_total': 245,
            'tubo_completed': 198,
            'tubo_pending': 47,
            'critical_delegation': 'Sector Rural',
            'critical_pct': 71.4,
        },
        'delegations': delegations,
        'parametrizacion': parametrizacion,
        'auditoria_logs': auditoria_logs,
    }
    return render(request, 'activities/dashboard_admin.html', context)

def dashboard_verificador_view(request):
    access_denied = _session_role_required(request, {'Verificador Técnico', 'Verificador'})
    if access_denied:
        return access_denied

    get_or_create_initial_sample_data()

    evidence_queue = [
        {
            'code': 'COM1761',
            'date': '13 Sep 2026',
            'official': 'Kevin Encina Molina',
            'item': 'Operativo en Terreno',
            'description': 'Reparación y despeje de calzada en Cuatro Esquinas.',
            'thumbnail': 'https://images.unsplash.com/photo-1590381105924-c72589b9ef3f?w=160&auto=format&fit=crop&q=80',
            'status': 'Pendiente'
        },
        {
            'code': 'SOC763',
            'date': '13 Sep 2026',
            'official': 'Scarlett Williams Medalla',
            'item': 'Atención Social RSH',
            'description': 'Visita domiciliaria para postulación subsidio habitacional.',
            'thumbnail': 'https://images.unsplash.com/photo-1450133064473-71024230f91b?w=160&auto=format&fit=crop&q=80',
            'status': 'Pendiente'
        },
        {
            'code': 'TRA892',
            'date': '12 Sep 2026',
            'official': 'Mauricio Tapia Gómez',
            'item': 'Inspección de Tránsito',
            'description': 'Verificación de señalética vial y reductores de velocidad.',
            'thumbnail': 'https://images.unsplash.com/photo-1578575437130-527eed3abbec?w=160&auto=format&fit=crop&q=80',
            'status': 'Pendiente'
        },
        {
            'code': 'SEC404',
            'date': '12 Sep 2026',
            'official': 'Loreto Valenzuela Ramos',
            'item': 'Mesa Barrial de Seguridad',
            'description': 'Reunión de coordinación con junta de vecinos y Carabineros.',
            'thumbnail': 'https://images.unsplash.com/photo-1577495508048-b635879837f1?w=160&auto=format&fit=crop&q=80',
            'status': 'Pendiente'
        },
    ]

    officials_monitoring = [
        {
            'name': 'Kevin Encina Molina',
            'role': 'Territorial OO.CC.',
            'days_elapsed': 56,
            'expected_meta': 61.5,
            'current_compliance': 102.4,
            'status_label': 'Verde',
            'status_class': 'success'
        },
        {
            'name': 'Scarlett Williams Medalla',
            'role': 'Gestor Social',
            'days_elapsed': 56,
            'expected_meta': 61.5,
            'current_compliance': 98.2,
            'status_label': 'Ámbar',
            'status_class': 'warning'
        },
        {
            'name': 'Mauricio Tapia Gómez',
            'role': 'Apoyo Adm. y Obras',
            'days_elapsed': 56,
            'expected_meta': 61.5,
            'current_compliance': 104.0,
            'status_label': 'Verde',
            'status_class': 'success'
        },
        {
            'name': 'Carlos Rivera Silva',
            'role': 'Inspector de Terreno',
            'days_elapsed': 56,
            'expected_meta': 61.5,
            'current_compliance': 54.0,
            'status_label': 'Rojo',
            'status_class': 'danger'
        },
    ]

    user_name = request.session.get('user_name') if request.session.get('user_role') == 'Supervisor Territorial' else 'Jorge Cortés Pavez'
    context = {
        'user_name': user_name,
        'user_role': 'Supervisor Territorial',
        'current_delegation': 'Delegación Las Compañías',
        'current_period': 'T3 - Septiembre 2026',
        'kpi': {
            'pending_reviews': 14,
            'points_validated_today': 28,
            'rejected_count': 3,
            'delegation_avg': 96.8,
            'delegation_status': 'Verde (Óptimo)'
        },
        'evidence_queue': evidence_queue,
        'officials_monitoring': officials_monitoring,
    }
    return render(request, 'activities/dashboard_verificador.html', context)

def dashboard_gestor_view(request):
    access_denied = _session_role_required(request, {'Gestor Territorial', 'Funcionario', 'Funcionario / Gestor Territorial'})
    if access_denied:
        return access_denied

    get_or_create_initial_sample_data()

    tubo_trabajo = [
        {
            'code': 'TUB-2026-041',
            'request_date': '10 Sep',
            'problem': 'Instalación de luminaria LED en pasaje interior.',
            'requester': 'Junta de Vecinos El Milagro',
            'phone': '+56 9 8452 1102',
            'responsible': 'Kevin Encina',
            'due_date': '18 Sep 2026',
            'status': 'En Proceso'
        },
        {
            'code': 'TUB-2026-042',
            'request_date': '11 Sep',
            'problem': 'Poda de árboles que obstruyen cables en Av. Cuatro Esquinas.',
            'requester': 'Comité Vecinal Las Pircas',
            'phone': '+56 9 9331 4455',
            'responsible': 'Kevin Encina',
            'due_date': '20 Sep 2026',
            'status': 'Pendiente'
        },
        {
            'code': 'TUB-2026-043',
            'request_date': '12 Sep',
            'problem': 'Nivelación de calzada y bacheo preventivo.',
            'requester': 'Línea 23 Colectivos',
            'phone': '+56 9 7622 8891',
            'responsible': 'Kevin Encina',
            'due_date': '22 Sep 2026',
            'status': 'Pendiente'
        },
        {
            'code': 'TUB-2026-039',
            'request_date': '08 Sep',
            'problem': 'Retiro de microbasural y demarcación preventiva.',
            'requester': 'Vecinos Calle Los Perales',
            'phone': '+56 9 6554 2210',
            'responsible': 'Kevin Encina',
            'due_date': '12 Sep 2026',
            'status': 'Realizado'
        },
    ]

    # Registros propios del funcionario activo (Kevin Encina) para auditoría y edición
    mis_evidencias = [
        {
            'code': 'ORC-2026-711',
            'date': '13 Sep 2026',
            'activity_type': 'Operativo Terreno',
            'activity': 'Visita inspectiva y catastro de aceras en La Pampa',
            'contact': 'Carmen Gloria Astudillo (JJ.VV. El Milagro)',
            'phone': '+56 9 8452 1102',
            'thumbnail': '/static/img/faro_laserena_daylight.jpg',
            'hash_inmutable': 'SHA-256: d8f3a199bc4012e87a21f649281c0029b4e112aa84e5671',
            'supervisor_status': 'Aprobada',
            'status': 'Realizado',
            'due_date': '13 Sep 2026',
            'supervisor_note': 'Validación técnica conforme en terreno por jefatura de delegación.',
            'last_modified': '13 Sep 2026, 16:30'
        },
        {
            'code': 'SOC-2026-902',
            'date': '12 Sep 2026',
            'activity_type': 'Gestión Social',
            'activity': 'Atención en terreno y encuesta RSH a adulto mayor',
            'contact': 'Roberto Morales Pizarro',
            'phone': '+56 9 7321 9940',
            'thumbnail': '/static/img/faro_laserena_daylight.jpg',
            'hash_inmutable': 'SHA-256: a1b2c3d4e5f6789012345678abcdef9012345678fedcba0',
            'supervisor_status': 'Aprobada',
            'status': 'Realizado',
            'due_date': '12 Sep 2026',
            'supervisor_note': 'Ficha RSH digitada y cotejada con Registro Social de Hogares.',
            'last_modified': '12 Sep 2026, 17:15'
        },
        {
            'code': 'LOR-2026-541',
            'date': '12 Sep 2026',
            'activity_type': 'Comité Vecinal',
            'activity': 'Mesa de seguridad preventiva barrial',
            'contact': 'Loreto Valenzuela (JJ.VV. Tierras Blancas)',
            'phone': '+56 9 6554 2210',
            'thumbnail': '/static/img/faro_laserena_daylight.jpg',
            'hash_inmutable': 'SHA-256: 7f8e9d0c1b2a345678901234abcdef0123456789abcdef1',
            'supervisor_status': 'En Revisión',
            'status': 'En Proceso',
            'due_date': '19 Sep 2026',
            'supervisor_note': 'En espera de corroboración con acta de asistencia vecinal.',
            'last_modified': '12 Sep 2026, 18:40'
        },
        {
            'code': 'ORC-2026-708',
            'date': '11 Sep 2026',
            'activity_type': 'Operativo Terreno',
            'activity': 'Supervisión de cuadrilla de aseo borde costero',
            'contact': 'Esteban Collao (Cuadrilla Sur)',
            'phone': '+56 9 7844 5511',
            'thumbnail': '/static/img/faro_laserena_daylight.jpg',
            'hash_inmutable': 'SHA-256: 4e5d6c7b8a90123456789012abcdef34567890abcdef12',
            'supervisor_status': 'Observada',
            'status': 'Pendiente',
            'due_date': '18 Sep 2026',
            'supervisor_note': 'Observación: Fotografía con ángulo lejano; se solicita re-adjuntar registro de cuadrilla trabajando.',
            'last_modified': '11 Sep 2026, 14:20'
        },
        {
            'code': 'ACT-2026-0839',
            'date': '10 Sep 2026',
            'activity_type': 'Fiscalización Obras',
            'activity': 'Verificación de reparación de bacheo en Av. El Santo',
            'contact': 'Dirección de Tránsito / Vecinos',
            'phone': '+56 9 8452 1100',
            'thumbnail': '/static/img/faro_laserena_daylight.jpg',
            'hash_inmutable': 'SHA-256: c3d4e5f6a1b2012345678901abcdef678901abcdef34',
            'supervisor_status': 'Aprobada',
            'status': 'Realizado',
            'due_date': '10 Sep 2026',
            'supervisor_note': 'Certificación de término de obras provisorias archivada.',
            'last_modified': '10 Sep 2026, 12:00'
        },
        {
            'code': 'SEC-2026-0312',
            'date': '09 Sep 2026',
            'activity_type': 'Seguridad Ciudadana',
            'activity': 'Levantamiento de punto ciego e instalación de foco solar',
            'contact': 'Comité Vecinal Las Pircas',
            'phone': '+56 9 9331 4455',
            'thumbnail': '/static/img/faro_laserena_daylight.jpg',
            'hash_inmutable': 'SHA-256: b2c3d4e5f6a1789012345678abcdef0123456789fedcba',
            'supervisor_status': 'En Revisión',
            'status': 'En Proceso',
            'due_date': '17 Sep 2026',
            'supervisor_note': 'Pendiente visto bueno de inspector de alumbrado público.',
            'last_modified': '09 Sep 2026, 19:10'
        },
    ]

    historial_personal = mis_evidencias

    user_name = request.session.get('user_name') or (request.user.get_full_name() if request.user.is_authenticated else 'Kevin Encina Molina')
    user_rut = request.session.get('user_rut', '12.345.678-K')
    user_role = request.session.get('user_role', 'Territorial OO.CC.')
    user_delegation = request.session.get('user_delegation', 'Delegación La Pampa')
    first_name = user_name.split()[0] if user_name else 'Funcionario'

    ciudadania_records = [
        {
            'rut': '14.821.309-4',
            'name': 'María Eugenia Tapia Rojas',
            'address': 'Calle Los Lúcumos 1240, La Pampa',
            'phone': '+56 9 8452 1190',
            'rsh_tramo': '40%',
            'rsh_status': 'Vulnerable Prioritario',
            'last_attention': '14 Sep 2026',
            'case_type': 'Subsidio Agua Potable y Ficha RSH',
            'stage': 2,
            'status': 'En Seguimiento'
        },
        {
            'rut': '11.543.882-K',
            'name': 'Rosa Elena Castillo Barraza',
            'address': 'Pje. Los Arrayanes 412, La Pampa',
            'phone': '+56 9 9331 4455',
            'rsh_tramo': '50%',
            'rsh_status': 'Medio Vulnerable',
            'last_attention': '13 Sep 2026',
            'case_type': 'Ayuda Social Paliativa Emergencia',
            'stage': 1,
            'status': 'Pendiente Doc.'
        },
        {
            'rut': '16.290.714-3',
            'name': 'Carlos Hernán Álvarez Godoy',
            'address': 'Av. Gabriel González Videla 2850, La Pampa',
            'phone': '+56 9 7622 8891',
            'rsh_tramo': '60%',
            'rsh_status': 'Sector Medio',
            'last_attention': '11 Sep 2026',
            'case_type': 'Orientación Subsidio Habitacional DS-49',
            'stage': 3,
            'status': 'Completado'
        },
        {
            'rut': '18.402.195-2',
            'name': 'Camila Ignacia Pizarro Cortés',
            'address': 'Calle Cisternas 1950, La Florida / La Pampa',
            'phone': '+56 9 6554 9901',
            'rsh_tramo': '40%',
            'rsh_status': 'Vulnerable Prioritario',
            'last_attention': '09 Sep 2026',
            'case_type': 'Postulación Beca Municipal Estudiantil',
            'stage': 2,
            'status': 'En Revisión'
        },
        {
            'rut': '9.874.321-1',
            'name': 'Guillermo Segundo Mondaca Vega',
            'address': 'Pje. Los Perales 510, San Joaquín',
            'phone': '+56 9 5412 3344',
            'rsh_tramo': '40%',
            'rsh_status': 'Adulto Mayor Prioritario',
            'last_attention': '08 Sep 2026',
            'case_type': 'Atención Domiciliaria RSH Adulto Mayor',
            'stage': 3,
            'status': 'Completado'
        },
    ]

    active_cases_count = len([t for t in tubo_trabajo if t.get('status') != 'Realizado'])
    citizens_count = len(ciudadania_records)

    # Data model estructurado para módulos del portal según rol/permisos
    dashboard_sections = [
        {
            'id': 'gestion',
            'title': 'Gestión',
            'subtitle': 'Operaciones y seguimiento de solicitudes en terreno',
            'modules': [
                {
                    'id': 'module-cases',
                    'title': 'Agregar / Ver casos',
                    'description': 'Gestiona, registra y realiza seguimiento a los casos asignados a tu unidad en terreno.',
                    'icon': 'bi-folder2-open',
                    'variant': 'primary',  # Azul institucional
                    'action_label': 'Gestionar casos',
                    'onclick': 'openCasesSection()',
                    'badge': f'{active_cases_count} en tubo',
                    'meta': 'Tubo de trabajo activo'
                }
            ]
        },
        {
            'id': 'consulta',
            'title': 'Consulta',
            'subtitle': 'Padrón vecinal y registros sociales comunales',
            'modules': [
                {
                    'id': 'module-citizenship',
                    'title': 'Revisar datos de la ciudadanía',
                    'description': 'Consulta información verificada, historial de atenciones y datos comunales de vecinas y vecinos.',
                    'icon': 'bi-people-fill',
                    'variant': 'secondary',  # Carmesí / Burdeo institucional
                    'action_label': 'Consultar ciudadanía',
                    'onclick': 'openCitizenshipSection()',
                    'badge': f'{citizens_count} fichas',
                    'meta': 'Fichas RSH y Territorio'
                }
            ]
        }
    ]

    context = {
        'first_name': first_name,
        'user_name': user_name,
        'user_role': user_role,
        'user_rut': user_rut,
        'current_delegation': user_delegation,
        'current_period': 'T3 - Septiembre 2026',
        'dashboard_sections': dashboard_sections,
        'kpi': {
            'my_accumulated_validated': 38,
            'my_compliance_pct': 84.4,
            'my_pending_tubo': 6,
            'my_semaphore_pct': 98.2,
            'my_semaphore_status': 'Verde (Al día)',
        },
        'tubo_trabajo': tubo_trabajo,
        'historial_personal': historial_personal,
        'mis_evidencias': mis_evidencias,
        'ciudadania_records': ciudadania_records,
    }
    return render(request, 'activities/dashboard_gestor.html', context)

def activity_create_view(request):
    if not _has_matrix_permission(request, 'edicion'):
        return _permission_denied('edicion')
    if request.method == 'GET':
        return render(request, 'activities/activity_form.html', {
            'generated_code': '', 'today_date': timezone.localdate().isoformat(),
        })
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)

    delegation = _delegation_for_write(request, request.POST.get('delegation'))
    if not delegation:
        return JsonResponse({'success': False, 'message': 'Delegación no autorizada.'}, status=403)
    problem = request.POST.get('problem_description', '').strip()
    action = request.POST.get('executed_action', '').strip()
    contact = request.POST.get('contact_name', '').strip()
    phone = request.POST.get('contact_phone', '').strip()
    try:
        date = datetime.date.fromisoformat(request.POST.get('activity_date', ''))
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Fecha inválida.'}, status=400)
    if not all((problem, action, contact)) or len(contact) > 150 or len(phone) > 20:
        return JsonResponse({'success': False, 'message': 'Faltan datos obligatorios o exceden su límite.'}, status=400)
    if date > timezone.localdate():
        return JsonResponse({'success': False, 'message': 'La fecha no puede ser futura.'}, status=400)
    from uuid import uuid4
    act = Activity(
        activity_code=f"ACT-{timezone.now():%Y%m%d}-{uuid4().hex[:12].upper()}",
        activity_date=date, problem_description=problem, executed_action=action,
        contact_name=contact, contact_phone=phone,
        is_collective_agenda=request.POST.get('is_collective_agenda') in {'1', 'true', 'on'},
        validation_status='Pending', delegation=delegation, user=request.user,
    )
    act.full_clean()
    act.save()
    messages.success(request, f"Actividad {act.activity_code} registrada.")
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
    if not any((catalog_id, attention_type, subattention_type)):
        return None, None
    qs = ServiceCatalog.objects.filter(status='Activo', deleted_at__isnull=True)
    if catalog_id is not None:
        try:
            catalog = qs.get(pk=int(catalog_id))
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


def _attention_result(a):
    evid = a.evidences.first()
    val = a.validations.first()
    return {
        'id': a.id, 'activity_code': a.activity_code,
        'evidence_code': evid.evidence_code if evid else '',
        'contact_name': a.contact_name, 'contact_phone': a.contact_phone,
        'delegation': a.delegation.name if a.delegation else '',
        'catalog_id': a.catalog_id,
        'attention_type': a.catalog.attention_type if a.catalog else '',
        'subattention_type': a.catalog.subattention_type if a.catalog else '',
        'service': a.catalog.service if a.catalog else '',
        'title': a.problem_description, 'description': a.executed_action,
        'problem_description': a.problem_description,
        'executed_action': a.executed_action,
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
        qs = _activity_scope(request).select_related('delegation', 'catalog').prefetch_related('evidences', 'validations')
        return JsonResponse({'success': True, 'atenciones': [_attention_result(a) for a in qs.order_by('-activity_date', '-created_at')]})

    data = _attention_payload(request)
    if data is None:
        return JsonResponse({'success': False, 'message': 'Solicitud JSON inválida.'}, status=400)
    delegation = _delegation_for_write(request, data.get('delegation'))
    if not delegation:
        return JsonResponse({'success': False, 'message': 'Delegación no autorizada o inactiva.'}, status=403)
    catalog, error = _attention_catalog(data)
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
    from django.db import transaction
    from django.db.models import Q
    from uuid import uuid4
    with transaction.atomic():
        # Lock the actor on databases that support row locks. A retry with the same
        # client code returns the existing record instead of creating another.
        type(request.user).objects.select_for_update().get(pk=request.user.pk)
        if code:
            existing = Activity.objects.filter(activity_code=code).first()
            if existing:
                if (existing.user_id == request.user.pk and existing.deleted_at is None
                        and existing.contact_name == contact and existing.problem_description == problem
                        and existing.executed_action == action and existing.delegation_id == delegation.id):
                    return JsonResponse({'success': True, 'id': existing.id, 'message': 'Atención ya registrada.'})
                return JsonResponse({'success': False, 'message': 'Código ya utilizado.'}, status=409)
        else:
            cutoff = timezone.now() - datetime.timedelta(seconds=30)
            existing = _activity_scope(request).filter(
                user=request.user, delegation=delegation, contact_name=contact,
                problem_description=problem, executed_action=action,
                created_at__gte=cutoff
            ).first()
            if existing:
                return JsonResponse({'success': True, 'id': existing.id, 'message': 'Atención ya registrada.'})
            code = f"ACT-{timezone.now():%Y%m%d}-{uuid4().hex[:12].upper()}"
        act = Activity.objects.create(
            activity_code=code, activity_date=timezone.localdate(),
            problem_description=problem, executed_action=action,
            contact_name=contact, contact_phone=phone,
            is_collective_agenda=data.get('is_collective_agenda', False),
            validation_status='Pending', delegation=delegation,
            catalog=catalog, user=request.user
        )
    return JsonResponse({'success': True, 'id': act.id, 'message': f'Atención {code} registrada.'}, status=201)


def api_atencion_detail(request, pk):
    if request.method not in {'GET', 'POST', 'PUT', 'DELETE'}:
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
    permission = 'lectura' if request.method == 'GET' else ('cierre' if request.method == 'DELETE' else 'edicion')
    if not _has_matrix_permission(request, permission):
        return _permission_denied(permission)
    a = _activity_scope(request).select_related('delegation', 'catalog').filter(pk=pk).first()
    if not a:
        return JsonResponse({'success': False, 'message': 'Atención no encontrada.'}, status=404)
    if request.method == 'GET':
        return JsonResponse({'success': True, 'atencion': _attention_result(a)})
    if request.method == 'DELETE':
        a.deleted_at = timezone.now()
        a.save(update_fields=['deleted_at', 'updated_at'])
        return JsonResponse({'success': True, 'message': 'Atención dada de baja.'})
    data = _attention_payload(request)
    if data is None:
        return JsonResponse({'success': False, 'message': 'Solicitud JSON inválida.'}, status=400)
    if 'validation_status' in data:
        return JsonResponse({'success': False, 'message': 'La validación corresponde al verificador.'}, status=403)
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
    for key, limit in (('contact_name', 150), ('contact_phone', 20), ('problem_description', 10000), ('executed_action', 10000)):
        if key in data:
            value = _attention_text(data, key, limit, required=key != 'contact_phone')
            if value is None:
                return JsonResponse({'success': False, 'message': f'{key} inválido.'}, status=400)
            setattr(a, key, value)
    a.save()
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

    rol_name = data.get('rol_name', '').strip()
    permiso = data.get('permiso', '').strip().lower()
    enabled = bool(data.get('enabled', False))

    allowed_permissions = {'lectura', 'edicion', 'derivacion', 'cierre'}
    if permiso not in allowed_permissions:
        return JsonResponse({'success': False, 'message': 'Permiso no válido para esta matriz.'}, status=400)

    rol = Role.objects.filter(name__iexact=rol_name).first()
    if not rol:
        return JsonResponse({'success': False, 'message': 'El rol indicado no existe.'}, status=404)

    perms = set(p.lower() for p in (rol.permissions_data or []))
    if enabled:
        perms.add(permiso)
    else:
        perms.discard(permiso)

    previous_permissions = sorted(rol.permissions_data or [])
    rol.permissions_data = sorted(perms)
    rol.save(update_fields=['permissions_data', 'updated_at'])

    AuditLog.objects.create(
        user=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
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

