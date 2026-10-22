from django.db import migrations


def grant_verifier_validation(apps, schema_editor):
    database = schema_editor.connection.alias
    PermissionDefinition = apps.get_model('organization', 'PermissionDefinition')
    Role = apps.get_model('organization', 'Role')
    permission, _ = PermissionDefinition.objects.using(database).get_or_create(
        code='validar_evidencia',
        defaults={
            'module_id': 'atenciones',
            'name': 'Validar evidencias',
            'description': 'Aprobar, rechazar o solicitar corrección con observación y trazabilidad.',
            'is_system': True,
        },
    )
    role = Role.objects.using(database).filter(name__iexact='Verificador Técnico', deleted_at__isnull=True).first()
    if not role:
        return
    permissions = list(role.permissions_data or [])
    if 'validar_evidencia' not in permissions:
        permissions.append('validar_evidencia')
        role.permissions_data = permissions
        role.save(using=database, update_fields=['permissions_data', 'updated_at'])
    role.permission_definitions.add(permission)


class Migration(migrations.Migration):
    dependencies = [('organization', '0013_position_base_roles')]
    operations = [migrations.RunPython(grant_verifier_validation, migrations.RunPython.noop)]
