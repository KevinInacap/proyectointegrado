"""Autorización y ámbitos compartidos por las vistas de organización."""
from functools import wraps

from django.http import JsonResponse

from .access import ADMINISTRATOR_ROLE_NAME, is_administrator_role, role_permission_codes
from .models import Delegation, UserProfile


def admin_only(view_func):
    """Autoriza con la cuenta y el rol vigentes, nunca con la sesión editable."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated or not user.is_active:
            return JsonResponse({'success': False, 'message': 'Autenticación requerida.'}, status=403)
        if not _has_administrator_role(user):
            return JsonResponse({'success': False, 'message': f'Se requiere el rol {ADMINISTRATOR_ROLE_NAME}.'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapped


def _has_administrator_role(user):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    profile = UserProfile.objects.filter(
        user=user, status='Activo', deleted_at__isnull=True,
    ).prefetch_related('roles').first()
    return bool(profile and any(
        is_administrator_role(role)
        for role in profile.roles.all()
        if role.deleted_at is None
    ))


def _users_scope(request):
    profiles = UserProfile.objects.filter(deleted_at__isnull=True)
    if _has_administrator_role(request.user):
        return profiles
    actor = UserProfile.objects.select_related('delegation').filter(
        user=request.user, status='Activo', deleted_at__isnull=True,
    ).first()
    if (not actor or not actor.delegation_id or actor.delegation.status != 'Activo'
            or actor.delegation.deleted_at is not None):
        return profiles.none()
    return profiles.filter(delegation_id=actor.delegation_id)


def _delegations_scope(request):
    """No expone datos territoriales fuera de la sede del funcionario."""
    delegations = Delegation.objects.filter(deleted_at__isnull=True)
    if _has_administrator_role(request.user):
        return delegations
    actor = UserProfile.objects.select_related('delegation').filter(
        user=request.user, status='Activo', deleted_at__isnull=True,
    ).first()
    if (not actor or not actor.delegation_id or actor.delegation.status != 'Activo'
            or actor.delegation.deleted_at is not None):
        return delegations.none()
    return delegations.filter(pk=actor.delegation_id)


def permission_gate(method_permissions):
    """Autoriza cada operación con permisos del rol vigente; nunca confía en la sesión."""
    def decorate(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            user = getattr(request, 'user', None)
            if not user or not user.is_authenticated or not user.is_active:
                return JsonResponse({'success': False, 'message': 'Autenticación requerida.'}, status=403)
            if request.method not in method_permissions:
                return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)
            if user.is_superuser:
                return view_func(request, *args, **kwargs)
            profile = UserProfile.objects.filter(
                user=user, status='Activo', deleted_at__isnull=True,
            ).prefetch_related('roles').first()
            if not profile:
                return JsonResponse({'success': False, 'message': 'Perfil activo requerido.'}, status=403)
            role_rows = [role for role in profile.roles.all() if role.deleted_at is None]
            if any(is_administrator_role(role) for role in role_rows):
                return view_func(request, *args, **kwargs)
            if (not profile.position or profile.position.status != 'Activo'
                    or profile.position.deleted_at is not None):
                return JsonResponse({'success': False, 'message': 'Cargo activo requerido.'}, status=403)
            required = method_permissions.get(request.method)
            granted = {code for role in role_rows for code in role_permission_codes(role)}
            if required and required.casefold() in granted:
                return view_func(request, *args, **kwargs)
            if required:
                return JsonResponse({'success': False, 'message': f'El rol no tiene habilitado {required}.'}, status=403)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorate
