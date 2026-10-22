from django.db import migrations


def seed_missing_position_roles(apps, schema_editor):
    database = schema_editor.connection.alias
    Position = apps.get_model('organization', 'Position')
    Role = apps.get_model('organization', 'Role')

    for position in Position.objects.using(database).filter(
        status='Activo', deleted_at__isnull=True,
    ).iterator():
        normalized = position.name.strip().casefold()
        if normalized == 'administrador general':
            role_name = 'Administrador'
        elif normalized in {'superadministrador', 'super administrador'}:
            role_name = 'SuperAdministrador'
        else:
            role_name = position.name.strip()

        role = Role.objects.using(database).filter(name__iexact=role_name).first()
        if role is None:
            role = Role.objects.using(database).create(
                name=role_name[:50],
                description=(position.description or f'Rol base para el cargo {position.name}.')[:255],
                is_system=True,
                permissions_data=[],
            )
        elif role.deleted_at is not None:
            role.deleted_at = None
            role.is_system = True
            role.save(using=database, update_fields=['deleted_at', 'is_system', 'updated_at'])

        for profile in position.users.using(database).filter(deleted_at__isnull=True).iterator():
            profile.roles.add(role)


class Migration(migrations.Migration):
    dependencies = [('organization', '0012_seed_position_roles')]
    operations = [migrations.RunPython(seed_missing_position_roles, migrations.RunPython.noop)]
