from django.db import migrations


def seed_system_roles(apps, schema_editor):
    Role = apps.get_model('organization', 'Role')
    roles = [
        ('Administrador General', 'Control total del sistema, usuarios, seguridad y configuración.', ['lectura', 'edicion', 'derivacion', 'cierre'], True),
        ('Coordinador del Sistema', 'Coordinación comunal, seguimiento y derivación de requerimientos.', ['lectura', 'edicion', 'derivacion'], True),
        ('Delegado Municipal', 'Gestión territorial y supervisión de una delegación.', ['lectura', 'edicion', 'derivacion'], True),
        ('Gestor Territorial', 'Registro y actualización de atenciones y actividades en terreno.', ['lectura', 'edicion', 'derivacion'], True),
        ('Verificador Técnico', 'Revisión técnica, observación y validación de evidencias.', ['lectura', 'edicion', 'cierre'], True),
        ('Usuario de Consulta', 'Acceso de solo lectura a información autorizada.', ['lectura'], True),
    ]
    for name, description, permissions, is_system in roles:
        Role.objects.get_or_create(
            name=name,
            defaults={'description': description, 'permissions_data': permissions, 'is_system': is_system},
        )


class Migration(migrations.Migration):
    dependencies = [('organization', '0003_seed_reference_catalogs')]
    operations = [migrations.RunPython(seed_system_roles, migrations.RunPython.noop)]
