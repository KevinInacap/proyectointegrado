import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Activity, Evidence, Validation

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
    get_or_create_initial_sample_data()

    tubo_trabajo = [
        {
            'code': 'TUB-2026-041',
            'request_date': '10 Sep 2026',
            'problem': 'Instalación de luminaria led en pasaje interior.',
            'requester': 'Junta de Vecinos El Milagro',
            'responsible': 'Kevin Encina',
            'due_date': '18 Sep 2026',
            'status': 'En Proceso'
        },
        {
            'code': 'TUB-2026-042',
            'request_date': '11 Sep 2026',
            'problem': 'Poda de árboles que obstruyen cables en Av. Cuatro Esquinas.',
            'requester': 'Comité Vecinal Las Pircas',
            'responsible': 'Kevin Encina',
            'due_date': '20 Sep 2026',
            'status': 'Pendiente'
        },
        {
            'code': 'TUB-2026-043',
            'request_date': '12 Sep 2026',
            'problem': 'Nivelación de calzada y bacheo preventivo.',
            'requester': 'Línea 23 Colectivos',
            'responsible': 'Kevin Encina',
            'due_date': '22 Sep 2026',
            'status': 'Ingresado'
        },
        {
            'code': 'TUB-2026-039',
            'request_date': '08 Sep 2026',
            'problem': 'Retiro de microbasural y demarcación de no botar escombros.',
            'requester': 'Vecinos Calle Los Perales',
            'responsible': 'Kevin Encina',
            'due_date': '12 Sep 2026',
            'status': 'Realizado'
        },
    ]

    historial_personal = [
        {
            'code': 'ORC711',
            'date': '13 Sep 2026',
            'activity': 'Visita inspectiva y catastro de aceras en La Pampa',
            'contact': 'Carmen Gloria Astudillo',
            'phone': '+56 9 8452 1102',
            'item': 'Operativo Terreno',
            'status': 'Aprobado'
        },
        {
            'code': 'SOC902',
            'date': '12 Sep 2026',
            'activity': 'Atención en terreno y encuesta RSH a adulto mayor',
            'contact': 'Roberto Morales Pizarro',
            'phone': '+56 9 7321 9940',
            'item': 'Gestión Social',
            'status': 'Aprobado'
        },
        {
            'code': 'LOR541',
            'date': '12 Sep 2026',
            'activity': 'Mesa de seguridad preventiva barrial',
            'contact': 'Loreto Valenzuela',
            'phone': '+56 9 6554 2210',
            'item': 'Comité Vecinal',
            'status': 'Pendiente'
        },
        {
            'code': 'ORC708',
            'date': '11 Sep 2026',
            'activity': 'Supervisión de cuadrilla de aseo borde costero',
            'contact': 'Esteban Collao',
            'phone': '+56 9 7844 5511',
            'item': 'Operativo Terreno',
            'status': 'Rechazado'
        },
    ]

    user_name = request.session.get('user_name') if request.session.get('user_role') == 'Territorial OO.CC.' else 'Kevin Encina Molina'
    context = {
        'user_name': user_name,
        'user_role': 'Territorial OO.CC.',
        'current_delegation': 'Delegación La Pampa',
        'current_period': 'T3 - Septiembre 2026',
        'kpi': {
            'my_accumulated_validated': 38,
            'my_compliance_pct': 84.4,
            'my_pending_tubo': 6,
            'my_semaphore_pct': 98.2,
            'my_semaphore_status': 'Verde (Al día)',
        },
        'tubo_trabajo': tubo_trabajo,
        'historial_personal': historial_personal,
    }
    return render(request, 'activities/dashboard_gestor.html', context)

def activity_create_view(request):
    if request.method == 'POST':
        activity_code = request.POST.get('activity_code', '').strip()
        activity_date = request.POST.get('activity_date')
        problem_description = request.POST.get('problem_description', '').strip()
        executed_action = request.POST.get('executed_action', '').strip()
        contact_name = request.POST.get('contact_name', '').strip()
        contact_phone = request.POST.get('contact_phone', '').strip()
        is_collective_agenda = bool(request.POST.get('is_collective_agenda'))

        if not activity_code:
            next_num = Activity.objects.count() + 844
            activity_code = f"ACT-2026-{next_num:04d}"

        if not activity_date:
            activity_date = datetime.date.today()

        activity = Activity.objects.create(
            activity_code=activity_code,
            activity_date=activity_date,
            problem_description=problem_description,
            executed_action=executed_action,
            contact_name=contact_name,
            contact_phone=contact_phone,
            is_collective_agenda=is_collective_agenda,
            validation_status='Pending'
        )

        evidence_file = request.FILES.get('evidence_file')
        file_name = evidence_file.name if evidence_file else f"{activity_code}_respaldo.jpg"

        Evidence.objects.create(
            activity=activity,
            evidence_code=f"EVI-{activity_code}",
            file_path=f"evidencias/{file_name}",
            file_name=file_name
        )

        messages.success(
            request, 
            f"¡Actividad {activity_code} registrada exitosamente!"
        )
        return redirect('activities:dashboard')

    next_num = Activity.objects.count() + 844
    generated_code = f"ACT-2026-{next_num:04d}"
    today_date = datetime.date.today().strftime('%Y-%m-%d')

    context = {
        'generated_code': generated_code,
        'today_date': today_date,
    }
    return render(request, 'activities/activity_form.html', context)

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
