import json

from django.urls import reverse
from django.utils.crypto import salted_hmac

from organization.models import UserProfile


def current_session_state(request):
    """Identifica el contexto vigente sin enviar cookies ni credenciales al cliente."""
    anonymous = {'fingerprint': '', 'redirect_url': reverse('core:login')}
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not user.is_active:
        return anonymous
    profile = (UserProfile.objects.select_related('position', 'delegation')
               .prefetch_related('roles__permission_definitions')
               .filter(user_id=user.pk, status='Activo', deleted_at__isnull=True).first())
    if (not profile or not profile.position or profile.position.status != 'Activo'
            or profile.position.deleted_at is not None):
        return anonymous

    # Incluye permisos y cargo persistidos: una pestaña antigua tampoco debe
    # mantener controles habilitados cuando administración cambia el perfil.
    roles = sorted([
        (role.pk, role.name, sorted(role.permissions_data or []), sorted([
            (permission.pk, permission.code)
            for permission in role.permission_definitions.all()
            if permission.deleted_at is None
        ]))
        for role in profile.roles.all() if role.deleted_at is None
    ])
    context = {
        'session': request.session.session_key or '',
        'user': user.pk,
        'privileges': (user.is_staff, user.is_superuser),
        'profile': str(profile.updated_at),
        'position': (profile.position_id, profile.position.name, str(profile.position.updated_at)),
        'delegation': (profile.delegation_id, str(profile.delegation.updated_at)) if profile.delegation else None,
        'roles': roles,
    }
    fingerprint = salted_hmac('sgr.browser-session', json.dumps(context, sort_keys=True)).hexdigest()
    from .views import dashboard_route_for_position
    return {
        'fingerprint': fingerprint,
        'redirect_url': reverse(dashboard_route_for_position(profile.position.name)),
    }


def session_guard_context(request):
    return {'session_guard_fingerprint': current_session_state(request)['fingerprint']}
