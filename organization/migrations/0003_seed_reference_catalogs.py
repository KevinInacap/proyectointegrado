from django.db import migrations


def seed_reference_catalogs(apps, schema_editor):
    Delegation = apps.get_model('organization', 'Delegation')
    Position = apps.get_model('organization', 'Position')

    delegations = [
        ('Delegación Las Compañías', 'Las Compañías'),
        ('Delegación Centro Histórico', 'Centro Histórico'),
        ('Delegación La Pampa', 'La Pampa'),
        ('Delegación Avenida del Mar', 'Avenida del Mar y borde costero'),
        ('Delegación La Antena', 'La Antena'),
        ('Delegación Sector Rural', 'Sector rural comunal'),
    ]
    positions = [
        ('Administrador General', 'Administración y seguridad integral del SGR'),
        ('Coordinador del Sistema', 'Coordinación operativa y seguimiento comunal'),
        ('Delegado Municipal', 'Dirección territorial de una delegación municipal'),
        ('Gestor Territorial', 'Gestión de actividades y atención en terreno'),
        ('Asistente Social', 'Atención social y acompañamiento de casos'),
        ('Verificador Técnico', 'Revisión y validación de evidencias'),
        ('Auditor Municipal', 'Fiscalización, calidad y auditoría'),
    ]

    for name, scope in delegations:
        Delegation.objects.get_or_create(name=name, defaults={'scope': scope, 'status': 'Activo'})
    for name, description in positions:
        Position.objects.get_or_create(name=name, defaults={'description': description, 'status': 'Activo'})


class Migration(migrations.Migration):
    dependencies = [('organization', '0002_role_is_system_role_permissions_data')]
    operations = [migrations.RunPython(seed_reference_catalogs, migrations.RunPython.noop)]
