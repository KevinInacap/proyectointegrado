from django.db import migrations


# Values inserted by migration 0006 were illustrative and had not been verified.
# Clear only fields that still exactly match those fixtures, preserving any values
# an administrator has since replaced with verified information.
UNVERIFIED_VALUES = {
    'Delegación Centro Histórico': {
        'address': 'Prat 451, Edificio Consistorial (Plaza de Armas)',
        'phone': '+56 51 220 6600',
        'email': 'delegacion.centro@laserena.cl',
        'schedule': 'Lunes a Viernes 08:30 a 14:00 hrs',
        'manager_name': 'Marcelo Salazar Peña',
    },
    'Delegación Las Compañías': {
        'address': 'Av. Espejo del Sol 210, Las Compañías',
        'phone': '+56 51 220 6710',
        'email': 'delegacion.companias@laserena.cl',
        'schedule': 'Lunes a Viernes 08:30 a 14:00 hrs',
        'manager_name': 'Gonzalo Pizarro Rojas',
    },
    'Delegación La Pampa': {
        'address': 'Av. Juan Cisternas 2855, La Pampa',
        'phone': '+56 51 220 6820',
        'email': 'delegacion.pampa@laserena.cl',
        'schedule': 'Lunes a Viernes 08:30 a 14:00 hrs',
        'manager_name': 'Patricia Vega Albarracín',
    },
    'Delegación Avenida del Mar': {
        'address': 'Av. del Mar 1200 (Frente a Costanera)',
        'phone': '+56 51 220 6900',
        'email': 'delegacion.mar@laserena.cl',
        'schedule': 'Lunes a Domingo 09:00 a 18:00 hrs',
        'manager_name': 'Christian Cerda Núñez',
    },
    'Delegación La Antena': {
        'address': 'Calle 18 de Septiembre 340, La Antena',
        'phone': '+56 51 220 6840',
        'email': 'delegacion.antena@laserena.cl',
        'schedule': 'Lunes a Viernes 08:30 a 14:00 hrs',
        'manager_name': 'Arturo Godoy Rivera',
    },
    'Delegación Sector Rural': {
        'address': 'Ruta 41 Km 15, Sector Algarrobito',
        'phone': '+56 51 220 6950',
        'email': 'delegacion.rural@laserena.cl',
        'schedule': 'Lunes a Viernes 08:30 a 14:00 hrs',
        'manager_name': 'Fernando Carvajal Pizarro',
    },
}


def clear_unverified_values(apps, schema_editor):
    Delegation = apps.get_model('organization', 'Delegation')
    database = schema_editor.connection.alias
    for name, fields in UNVERIFIED_VALUES.items():
        delegation = Delegation.objects.using(database).filter(name=name).first()
        if delegation is None:
            continue
        for field, old_value in fields.items():
            Delegation.objects.using(database).filter(
                pk=delegation.pk,
                **{field: old_value},
            ).update(**{field: ''})


class Migration(migrations.Migration):
    dependencies = [('organization', '0006_delegation_contact_fields')]

    operations = [migrations.RunPython(clear_unverified_values, migrations.RunPython.noop)]
