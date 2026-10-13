from datetime import timedelta

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.utils.dateparse import parse_date
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from organization.access import is_administrator_role
from organization.models import UserProfile
from .models import CollectiveAgenda


@never_cache
@require_GET
def api_agenda(request):
    """Entrega al panel administrador compromisos del mes solicitado, sin datos personales."""
    user = request.user
    if not user.is_authenticated or not user.is_active:
        return JsonResponse({"error": "No autorizado."}, status=403)

    if not user.is_superuser:
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            return JsonResponse({"error": "No autorizado."}, status=403)
        if profile.status != "Activo" or profile.deleted_at is not None:
            return JsonResponse({"error": "No autorizado."}, status=403)
        role_names = profile.roles.filter(deleted_at__isnull=True).values_list("name", flat=True)
        if not any(is_administrator_role(name) for name in role_names):
            return JsonResponse({"error": "No autorizado."}, status=403)

    start = parse_date(request.GET.get("desde", ""))
    end = parse_date(request.GET.get("hasta", ""))
    if not start or not end or start > end or (end - start) > timedelta(days=366):
        return JsonResponse({"error": "Rango de fechas inválido."}, status=400)

    commitments = (
        CollectiveAgenda.objects.filter(
            deleted_at__isnull=True,
            committed_date__range=(start, end),
        )
        .select_related("delegation")
        .order_by("committed_date", "id")
    )
    results = [
        {
            "fecha": item.committed_date.isoformat(),
            "estado": item.status,
            "territorio": item.territory,
            "area": item.support_area,
            "descripcion": item.description,
            "delegacion": item.delegation.name,
        }
        for item in commitments
    ]
    return JsonResponse({"count": len(results), "results": results})
