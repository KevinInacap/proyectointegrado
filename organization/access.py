import re
import unicodedata


ADMINISTRATOR_ROLE_NAME = 'Administrador'
SUPER_ADMINISTRATOR_ROLE_NAME = 'SuperAdministrador'
SUPER_ADMINISTRATOR_RUT = '21.571.404-7'
LEGACY_ADMINISTRATOR_ROLE_NAMES = {'administrador general', 'superadministrador', 'super administrador'}


def _normalized_name(value):
    value = unicodedata.normalize('NFKD', str(value or ''))
    return ''.join(char for char in value if not unicodedata.combining(char)).strip().casefold()


def is_super_administrator(user_or_profile):
    """Verifica si el usuario es el SuperAdministrador institucional autorizado."""
    if not user_or_profile:
        return False
    profile = getattr(user_or_profile, 'profile', user_or_profile)
    rut = getattr(profile, 'rut', '')
    if not rut:
        return False
    norm_rut = re.sub(r'[^0-9kK]', '', str(rut)).upper()
    target_rut = re.sub(r'[^0-9kK]', '', SUPER_ADMINISTRATOR_RUT).upper()
    if norm_rut != target_rut:
        return False
    if hasattr(profile, 'roles'):
        return profile.roles.filter(
            deleted_at__isnull=True,
            name__in=[SUPER_ADMINISTRATOR_ROLE_NAME, 'Super Administrador', 'superadministrador']
        ).exists()
    return False


def is_administrator_role(role_or_name):
    """Recognize the canonical system role and its pre-migration name only."""
    name = getattr(role_or_name, 'name', role_or_name)
    normalized = _normalized_name(name)
    return (
        normalized in (_normalized_name(ADMINISTRATOR_ROLE_NAME), _normalized_name(SUPER_ADMINISTRATOR_ROLE_NAME))
        or normalized in LEGACY_ADMINISTRATOR_ROLE_NAMES
    )


def role_permission_codes(role):
    """Return persisted legacy capabilities plus normalized catalog permissions."""
    codes = {str(code).strip().casefold() for code in (role.permissions_data or []) if str(code).strip()}
    if role.pk and hasattr(role, 'permission_definitions'):
        codes.update(
            str(code).strip().casefold()
            for code in role.permission_definitions.values_list('code', flat=True)
            if str(code).strip()
        )
    return codes


def set_role_permission_codes(role, permissions):
    """Persist the compatibility JSON and the normalized many-to-many grants together."""
    codes = sorted({str(code).strip().casefold() for code in permissions if str(code).strip()})
    role.permissions_data = codes
    role.save(update_fields=['permissions_data', 'updated_at'])
    if role.pk and hasattr(role, 'permission_definitions'):
        role.permission_definitions.set(
            role.permission_definitions.model.objects.filter(
                code__in=codes,
                deleted_at__isnull=True,
            )
        )
    return codes
