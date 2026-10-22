from django.db import migrations
from django.db.models import Q


ADMIN_ROLE_NAMES = (
    'Administrador',
    'SuperAdministrador',
    'Administrador General',
    'Super Administrador',
)


def grant_system_permissions_to_admin_roles(apps, schema_editor):
    database = schema_editor.connection.alias
    Role = apps.get_model('organization', 'Role')
    PermissionDefinition = apps.get_model('organization', 'PermissionDefinition')
    admin_roles = Role.objects.using(database).filter(
        Q(name__in=ADMIN_ROLE_NAMES) | Q(name__iexact='administrador'),
        deleted_at__isnull=True,
    )
    system_permissions = PermissionDefinition.objects.using(database).filter(
        is_system=True,
        deleted_at__isnull=True,
    )
    codes = list(system_permissions.values_list('code', flat=True))
    for role in admin_roles:
        current = {str(code).strip() for code in (role.permissions_data or []) if str(code).strip()}
        merged = sorted(current | set(codes))
        if merged != sorted(current):
            role.permissions_data = merged
            role.save(using=database, update_fields=['permissions_data', 'updated_at'])
        role.permission_definitions.add(*system_permissions)


class Migration(migrations.Migration):
    dependencies = [('organization', '0014_verifier_validation_permission')]

    operations = [
        migrations.RunPython(grant_system_permissions_to_admin_roles, migrations.RunPython.noop),
    ]
