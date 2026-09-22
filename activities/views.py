import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Activity, Evidence, Validation

def dashboard_view(request):
    return redirect('core:login')

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
