from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from .services import publish_chat_message


@login_required
def chat_room(request):
    profile = getattr(request.user, "profile", None)
    delegation_name = ""
    if profile and getattr(profile, "delegation", None):
        delegation_name = profile.delegation.name
    return render(request, "websocket/chat.html", {
        "profile": profile,
        "delegation_name": delegation_name,
    })


@login_required
@require_POST
def send_message(request):
    try:
        profile = getattr(request.user, "profile", None)
        if profile is None:
            org_id = None
        else:
            org_id = getattr(profile, "organization_id", None) or getattr(profile, "delegation_id", None)
            if hasattr(profile, "delegation") and profile.delegation:
                org_id = org_id or profile.delegation.id
    except ObjectDoesNotExist:
        org_id = None

    if org_id is None:
        return JsonResponse({"error": "Sin organización"}, status=403)

    message = request.POST.get("message", "").strip()
    if not 1 <= len(message) <= 300:
        return JsonResponse({"error": "Mensaje inválido"}, status=400)

    publish_chat_message(request.user, org_id, message)
    return JsonResponse({"ok": True})
