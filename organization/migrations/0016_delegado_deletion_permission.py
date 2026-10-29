from django.db import migrations


def grant_delegado_deletion(apps, schema_editor):
    database = schema_editor.connection.alias
    Role = apps.get_model('organization', 'Role')
    PermissionDefinition = apps.get_model('organization', 'PermissionDefinition')
    role = Role.objects.using(database).filter(
        name__iexact='Delegado Municipal', deleted_at__isnull=True,
    ).first()
    if role is None:
        return

    permission, _ = PermissionDefinition.objects.using(database).get_or_create(
        code='cierre',
        defaults={
            'module_id': 'atenciones',
            'name': 'Dar de baja registros',
            'description': 'Dar de baja registros autorizados con confirmación y auditoría.',
            'is_system': True,
        },
    )
    permissions = list(role.permissions_data or [])
    if 'cierre' not in permissions:
        permissions.append('cierre')
        role.permissions_data = permissions
        role.save(using=database, update_fields=['permissions_data', 'updated_at'])
    role.permission_definitions.add(permission)


class Migration(migrations.Migration):
    dependencies = [('organization', '0015_grant_validation_permission_to_admins')]
    operations = [
        migrations.RunPython(grant_delegado_deletion, migrations.RunPython.noop),
    ]

