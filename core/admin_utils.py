from django.core.exceptions import PermissionDenied

def get_user_delegation(request):
    """
    Función auxiliar de scoping (Unidad 2 - Clase 5):
    Obtiene el ámbito organizacional (Delegación) del usuario autenticado.
    - Superusuario técnico: conserva acceso global (retorna None).
    - Usuario operativo sin perfil o sin delegación: falla de forma controlada con PermissionDenied.
    - Usuario operativo con ámbito: retorna su objeto Delegation.
    """
    if request.user.is_superuser:
        return None
    
    profile = getattr(request.user, "profile", None)
    if profile is None or getattr(profile, "delegation_id", None) is None:
        raise PermissionDenied("El usuario no posee una delegación territorial asignada.")
    
    return profile.delegation

# Alias semántico directo para máxima compatibilidad con las láminas de Clase 5
get_user_organization = get_user_delegation
