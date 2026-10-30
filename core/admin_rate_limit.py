"""Límite persistente de altas organizacionales para evitar envíos masivos."""
from functools import wraps
from math import ceil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

from .models import AdminCreationQuota


def consume_admin_creation(request):
    """Registra una alta autorizada y devuelve 429 si agotó su cuota."""
    limit = settings.SGR_ADMIN_CREATE_LIMIT
    seconds = settings.SGR_ADMIN_CREATE_WINDOW_SECONDS
    with transaction.atomic():
        # Serializa incluso la creación inicial del contador entre procesos.
        user = get_user_model().objects.select_for_update().get(pk=request.user.pk)
        now = timezone.now()
        quota, _ = AdminCreationQuota.objects.get_or_create(user=user, defaults={'window_started_at': now})
        elapsed = (now - quota.window_started_at).total_seconds()
        if elapsed < 0 or elapsed >= seconds:
            quota.window_started_at = now
            quota.attempts = 0
            elapsed = 0
        if quota.attempts >= limit:
            retry = max(1, ceil(seconds - elapsed))
            response = JsonResponse({
                'success': False,
                'message': f'Demasiados intentos de creación. Espera {retry} segundos e inténtalo nuevamente.',
            }, status=429)
            response['Retry-After'] = str(retry)
            return response
        quota.attempts += 1
        quota.save(update_fields=['window_started_at', 'attempts'])
    return None


def limit_admin_creation(view):
    """Cuenta peticiones POST tras autorización; las ventanas se reutilizan por usuario."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.method == 'POST':
            blocked = consume_admin_creation(request)
            if blocked is not None:
                return blocked
        return view(request, *args, **kwargs)
    return wrapped
