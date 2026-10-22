from django.db import migrations
from uuid import uuid4


def compact_rut(value):
    return ''.join(char for char in (value or '').upper() if char.isdigit() or char == 'K')


def backfill_case_intake(apps, schema_editor):
    SocialCase = apps.get_model('social', 'SocialCase')
    SocialManagement = apps.get_model('social', 'SocialManagement')
    SocialReviewRequest = apps.get_model('social', 'SocialReviewRequest')
    Vecino = apps.get_model('activities', 'Vecino')
    Activity = apps.get_model('activities', 'Activity')
    db = schema_editor.connection.alias

    neighbors = {compact_rut(row.rut): row for row in Vecino.objects.using(db).all()}
    for case in SocialCase.objects.using(db).filter(deleted_at__isnull=True, activity__isnull=True).select_related('delegation').iterator():
        rut = compact_rut(case.user_rut)
        neighbor = neighbors.get(rut)
        if neighbor and (neighbor.deleted_at or (neighbor.territorio or '').casefold() != case.delegation.name.casefold()):
            # A shared RUT from another territory needs an administrative decision.
            neighbor = None
        elif not neighbor:
            neighbor = Vecino.objects.using(db).create(
                rut=case.user_rut, nombre=case.user_name, telefono=case.contact_phone,
                territorio=case.delegation.name, estado='Activo',
            )
            neighbors[rut] = neighbor

        first = SocialManagement.objects.using(db).filter(case_id=case.pk, stage=1, deleted_at__isnull=True).first()
        review = SocialReviewRequest.objects.using(db).filter(case_id=case.pk, management=first).order_by('created_at').first() if first else None
        status = {'aprobada': 'Approved', 'rechazada': 'Rejected'}.get(review.status, 'Pending') if review else 'Pending'
        # El texto histórico no permite reconstruir un par tipo/subatención fiable.
        activity = Activity.objects.using(db).create(
            activity_code=f'SOC-{case.pk:08d}-{uuid4().hex[:6].upper()}',
            user_id=review.requester_id if review else None,
            delegation_id=case.delegation_id,
            neighbor_id=neighbor.pk if neighbor else None,
            activity_date=case.entry_date,
            problem_description=first.result if first else 'Solicitud social',
            executed_action='Ingreso de caso social para evaluación y revisión administrativa.',
            contact_name=case.user_name, contact_phone=case.contact_phone,
            validation_status=status,
        )
        SocialCase.objects.using(db).filter(pk=case.pk).update(activity_id=activity.pk)


class Migration(migrations.Migration):
    dependencies = [
        ('social', '0003_socialcase_activity'),
        ('activities', '0007_vecino_email'),
    ]
    operations = [migrations.RunPython(backfill_case_intake, migrations.RunPython.noop)]
