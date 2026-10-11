from django.db import migrations, models


def link_existing_role_permissions(apps, schema_editor):
    database = schema_editor.connection.alias
    Role = apps.get_model('organization', 'Role')
    PermissionDefinition = apps.get_model('organization', 'PermissionDefinition')

    for role in Role.objects.using(database).all().iterator():
        codes = {
            str(code).strip().casefold()
            for code in (role.permissions_data or [])
            if str(code).strip()
        }
        definitions = PermissionDefinition.objects.using(database).filter(
            code__in=codes,
            deleted_at__isnull=True,
        )
        role.permission_definitions.add(*definitions)


class Migration(migrations.Migration):
    dependencies = [('organization', '0008_seed_permission_catalog_and_administrator_role')]
    operations = [
        migrations.AddField(
            model_name='role',
            name='permission_definitions',
            field=models.ManyToManyField(
                blank=True,
                related_name='roles',
                to='organization.permissiondefinition',
                verbose_name='Permisos detallados del catálogo',
            ),
        ),
        migrations.RunPython(link_existing_role_permissions, migrations.RunPython.noop),
    ]
