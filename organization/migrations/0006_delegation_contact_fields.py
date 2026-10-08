from django.db import migrations, models


DETAILS = {
    'Delegación Centro Histórico': {
        'address': 'Prat 451, Edificio Consistorial (Plaza de Armas)',
        'phone': '+56 51 220 6600', 'email': 'delegacion.centro@laserena.cl',
        'schedule': 'Lunes a Viernes 08:30 a 14:00 hrs', 'manager_name': 'Marcelo Salazar Peña',
        'photo_url': '/static/img/delegacion_centro.jpg',
    },
    'Delegación Las Compañías': {
        'address': 'Av. Espejo del Sol 210, Las Compañías', 'phone': '+56 51 220 6710',
        'email': 'delegacion.companias@laserena.cl', 'schedule': 'Lunes a Viernes 08:30 a 14:00 hrs',
        'manager_name': 'Gonzalo Pizarro Rojas', 'photo_url': '/static/img/delegacion_companias.jpg',
    },
    'Delegación La Pampa': {
        'address': 'Av. Juan Cisternas 2855, La Pampa', 'phone': '+56 51 220 6820',
        'email': 'delegacion.pampa@laserena.cl', 'schedule': 'Lunes a Viernes 08:30 a 14:00 hrs',
        'manager_name': 'Patricia Vega Albarracín', 'photo_url': '/static/img/delegacion_pampa.jpg',
    },
    'Delegación Avenida del Mar': {
        'address': 'Av. del Mar 1200 (Frente a Costanera)', 'phone': '+56 51 220 6900',
        'email': 'delegacion.mar@laserena.cl', 'schedule': 'Lunes a Domingo 09:00 a 18:00 hrs',
        'manager_name': 'Christian Cerda Núñez', 'photo_url': '/static/img/delegacion_costa.jpg',
    },
    'Delegación La Antena': {
        'address': 'Calle 18 de Septiembre 340, La Antena', 'phone': '+56 51 220 6840',
        'email': 'delegacion.antena@laserena.cl', 'schedule': 'Lunes a Viernes 08:30 a 14:00 hrs',
        'manager_name': 'Arturo Godoy Rivera', 'photo_url': '/static/img/delegacion_antena.jpg',
    },
    'Delegación Sector Rural': {
        'address': 'Ruta 41 Km 15, Sector Algarrobito', 'phone': '+56 51 220 6950',
        'email': 'delegacion.rural@laserena.cl', 'schedule': 'Lunes a Viernes 08:30 a 14:00 hrs',
        'manager_name': 'Fernando Carvajal Pizarro', 'photo_url': '/static/img/delegacion_rural.jpg',
    },
}


def populate_details(apps, schema_editor):
    Delegation = apps.get_model('organization', 'Delegation')
    for name, values in DETAILS.items():
        Delegation.objects.filter(name=name).update(**values)


class Migration(migrations.Migration):
    dependencies = [('organization', '0005_permissiondefinition')]
    operations = [
        migrations.AddField(model_name='delegation', name='address', field=models.CharField(blank=True, default='', max_length=200, verbose_name='Dirección')),
        migrations.AddField(model_name='delegation', name='phone', field=models.CharField(blank=True, default='', max_length=30, verbose_name='Teléfono')),
        migrations.AddField(model_name='delegation', name='email', field=models.EmailField(blank=True, default='', max_length=120, verbose_name='Correo de contacto')),
        migrations.AddField(model_name='delegation', name='schedule', field=models.CharField(blank=True, default='', max_length=120, verbose_name='Horario de atención')),
        migrations.AddField(model_name='delegation', name='manager_name', field=models.CharField(blank=True, default='', max_length=150, verbose_name='Delegado o encargado')),
        migrations.AddField(model_name='delegation', name='photo_url', field=models.CharField(blank=True, default='', max_length=255, verbose_name='Ruta o URL de fotografía')),
        migrations.AddField(model_name='delegation', name='description', field=models.TextField(blank=True, default='', verbose_name='Descripción territorial')),
        migrations.RunPython(populate_details, migrations.RunPython.noop),
    ]
