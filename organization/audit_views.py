"""Historial de auditoría y límites de consulta territorial."""
from django.db.models import CharField, Q
from django.db.models.functions import Cast
from django.http import JsonResponse

from core.models import AuditLog
from .authorization import _has_administrator_role, permission_gate
from .models import Delegation, UserProfile


def _territorial_audit_logs(request):
    """Solo muestra trazas cuyo actor y destino territorial pueden verificarse."""
    logs = AuditLog.objects.filter(deleted_at__isnull=True)
    if _has_administrator_role(request.user):
        return logs
    actor = UserProfile.objects.select_related('delegation', 'position').filter(
        user=request.user, status='Activo', deleted_at__isnull=True,
    ).first()
    if (not actor or not actor.delegation_id or actor.delegation.status != 'Activo'
            or actor.delegation.deleted_at is not None or not actor.position
            or actor.position.status != 'Activo' or actor.position.deleted_at is not None):
        return logs.none()

    from activities.models import Activity, Vecino
    from social.models import SocialCase, SocialManagement, SocialReviewRequest

    # AuditLog no conserva una delegación histórica propia. Los registros sin
    # destino verificable (incluidos catálogos globales) quedan para Administración.
    sources = (
        ('usuario', UserProfile.objects.filter(delegation_id=actor.delegation_id, deleted_at__isnull=True)),
        ('delegacion', Delegation.objects.filter(pk=actor.delegation_id, deleted_at__isnull=True)),
        ('actividad', Activity.objects.filter(delegation_id=actor.delegation_id, deleted_at__isnull=True)),
        ('vecino', Vecino.objects.filter(territorio__iexact=actor.delegation.name, deleted_at__isnull=True)),
        ('caso_social', SocialCase.objects.filter(delegation_id=actor.delegation_id, deleted_at__isnull=True)),
        ('gestion_social', SocialManagement.objects.filter(case__delegation_id=actor.delegation_id, case__deleted_at__isnull=True, deleted_at__isnull=True)),
        ('solicitud_revision_social', SocialReviewRequest.objects.filter(case__delegation_id=actor.delegation_id, case__deleted_at__isnull=True, deleted_at__isnull=True)),
    )
    targets = Q(pk__in=[])
    for table, objects in sources:
        identifiers = objects.annotate(audit_id=Cast('pk', CharField())).values('audit_id')
        targets |= Q(affected_table=table, affected_record_id__in=identifiers)
    return logs.filter(user__profile__delegation_id=actor.delegation_id).filter(targets)


@permission_gate({'GET': 'auditoria.view'})
def api_audit_logs(request):
    """
    Retorna el historial de auditoría y trazabilidad de acciones realizadas por administradores.
    """
    logs_qs = _territorial_audit_logs(request).select_related('user').order_by('-created_at')[:150]
    logs_data = []

    for l in logs_qs:
        admin_name = 'Sistema Municipal'
        admin_username = 'sistema'
        if l.user:
            admin_name = l.user.get_full_name() or l.user.username
            admin_username = l.user.username

        desc = ""
        nv = l.new_value or {}
        ov = l.previous_value or {}

        if l.action == 'CREATE':
            target_name = nv.get('full_name') or nv.get('code') or f"#{l.affected_record_id}"
            desc = f"Creó nuevo registro en {l.affected_table}: {target_name}"
        elif l.action == 'UPDATE':
            if nv.get('action_type') == 'TOGGLE_STATUS':
                desc = f"Cambió estado a '{nv.get('status')}' (ID #{l.affected_record_id})"
            elif nv.get('action_type') == 'PASSWORD_RESET':
                desc = f"Restableció contraseña de acceso para usuario ID #{l.affected_record_id}"
            else:
                target_name = nv.get('full_name') or ov.get('full_name') or f"ID #{l.affected_record_id}"
                desc = f"Modificó perfil / roles de {target_name}"
        elif l.action == 'DELETE':
            target_name = ov.get('full_name') or ov.get('name') or f"ID #{l.affected_record_id}"
            desc = f"Eliminó permanentemente a: {target_name}"
        elif l.action == 'VALIDATE':
            decision = nv.get('decision', 'Revisado')
            desc = f"Validó actividad ({decision})"
        else:
            desc = f"Operación {l.action} en {l.affected_table}"

        logs_data.append({
            'id': l.id,
            'timestamp': l.created_at.strftime('%d/%m/%Y %H:%M:%S') if l.created_at else '',
            'admin_username': admin_username,
            'admin_name': admin_name,
            'action': l.action,
            'affected_table': l.affected_table,
            'affected_record_id': l.affected_record_id,
            'description': desc,
            'details': nv or ov
        })

    return JsonResponse({
        'success': True,
        'logs': logs_data
    })
