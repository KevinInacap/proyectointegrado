from django.db import migrations


POSITION_ROLES = (
    (
        'Asistente Social',
        'Atención social y seguimiento de casos de la delegación asignada.',
        ['lectura', 'edicion', 'derivacion'],
    ),
    (
        'Auditor Municipal',
        'Consulta de actividad, trazabilidad e informes de auditoría.',
        ['lectura'],
    ),
)


def seed_position_roles(apps, schema_editor):
    database = schema_editor.connection.alias
    Role = apps.get_model('organization', 'Role')
    PermissionDefinition = apps.get_model('organization', 'PermissionDefinition')
    for name, description, permissions in POSITION_ROLES:
        role, _ = Role.objects.using(database).get_or_create(
            name=name,
            defaults={
                'description': description,
                'permissions_data': permissions,
                'is_system': True,
            },
        )
        if not role.is_system or role.deleted_at is not None:
            continue
        definitions = PermissionDefinition.objects.using(database).filter(
            code__in=permissions,
            deleted_at__isnull=True,
        )
        role.permission_definitions.add(*definitions)

    UserProfile = apps.get_model('organization', 'UserProfile')
    for profile in UserProfile.objects.using(database).filter(
        deleted_at__isnull=True,
        position__status='Activo',
        position__deleted_at__isnull=True,
    ).select_related('position').iterator():
        normalized_position = profile.position.name.strip().casefold()
        if normalized_position == 'administrador general':
            role_name = 'Administrador'
        elif normalized_position in {'superadministrador', 'super administrador'}:
            role_name = 'SuperAdministrador'
        else:
            role_name = profile.position.name.strip()
        role = Role.objects.using(database).filter(
            name__iexact=role_name,
            deleted_at__isnull=True,
            is_system=True,
        ).first()
        if role:
            profile.roles.add(role)


class Migration(migrations.Migration):
    dependencies = [('organization', '0011_delegation_commune')]
    operations = [migrations.RunPython(seed_position_roles, migrations.RunPython.noop)]
