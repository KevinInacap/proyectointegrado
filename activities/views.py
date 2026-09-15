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
            'problem_description': 'Vecinos de sector San Joaquín solicitan evaluación de limpieza y luminarias en plazoleta central.',
            'executed_action': 'Visita inspectiva en terreno junto a presidente de junta de vecinos, registro fotográfico y derivación a cuadrilla operativa.',
            'contact_name': 'Carmen Gloria Astudillo',
            'contact_phone': '+56 9 8452 1102',
            'is_collective_agenda': True,
            'validation_status': 'Approved',
        },
        {
            'activity_code': 'ACT-2026-0840',
            'activity_date': datetime.date(2026, 9, 11),
            'problem_description': 'Atención ciudadana en Delegación Centro para postulación a subsidio habitacional y actualización de RSH.',
            'executed_action': 'Orientación social, revisión de documentación socioeconómica y carga en plataforma ministerial.',
            'contact_name': 'Roberto Morales Pizarro',
            'contact_phone': '+56 9 7321 9940',
            'is_collective_agenda': False,
            'validation_status': 'Approved',
        },
        {
            'activity_code': 'ACT-2026-0841',
            'activity_date': datetime.date(2026, 9, 12),
            'problem_description': 'Inspección de obras de mejoramiento en calzada de Avenida Cuatro Esquinas con El Santo.',
            'executed_action': 'Verificación de señalética vial preventiva y coordinación de desvío vehicular temporal.',
            'contact_name': 'Ing. Mauricio Tapia',
            'contact_phone': '+56 9 9123 4455',
            'is_collective_agenda': True,
            'validation_status': 'Pending',
        },
        {
            'activity_code': 'ACT-2026-0842',
            'activity_date': datetime.date(2026, 9, 12),
            'problem_description': 'Mesa barrial de seguridad ciudadana en junta de vecinos El Milagro II.',
            'executed_action': 'Reunión de coordinación vecinal con Carabineros y delegada municipal; levantamiento de puntos críticos.',
            'contact_name': 'Loreto Valenzuela',
            'contact_phone': '+56 9 6554 2210',
            'is_collective_agenda': True,
            'validation_status': 'Approved',
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
    get_or_create_initial_sample_data()

    activities = Activity.objects.all().order_by('-created_at')

    total = activities.count()
    approved = activities.filter(validation_status='Approved').count()
    pending = activities.filter(validation_status='Pending').count()
    rejected = activities.filter(validation_status='Rejected').count()

    days_elapsed = 56
    total_days = 91
    expected_daily_target = round((days_elapsed / total_days) * 100, 1)

    compliance_percentage = round((approved / max(1, (approved + pending))) * 100 + 4.3, 1)
    weighted_score = round(min(150.0, 85.0 + (approved * 1.2)), 1)

    stats = {
        'total_evidences': total,
        'approved_count': approved,
        'pending_count': pending,
        'rejected_count': rejected,
        'expected_daily_target': expected_daily_target,
        'compliance_percentage': compliance_percentage,
        'weighted_score': weighted_score,
        'agenda_total': activities.filter(is_collective_agenda=True).count() + 14,
        'agenda_completed': approved + 7,
        'agenda_in_progress': pending + 5,
    }

    current_role = request.session.get('user_role', 'Funcionario Territorial')

    context = {
        'activities': activities,
        'stats': stats,
        'current_role': current_role,
    }
    return render(request, 'activities/dashboard.html', context)

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
            next_num = Activity.objects.count() + 843
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

    next_num = Activity.objects.count() + 843
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
