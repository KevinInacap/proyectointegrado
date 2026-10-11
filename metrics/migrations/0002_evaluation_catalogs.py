import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('metrics', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='AttentionType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Última actualización')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Fecha de eliminación lógica')),
                ('code', models.CharField(max_length=30, unique=True)),
                ('name', models.CharField(max_length=120, unique=True)),
                ('description', models.TextField(blank=True, default='')),
                ('status', models.CharField(choices=[('Activo', 'Activo'), ('Inactivo', 'Inactivo')], default='Activo', max_length=20)),
            ],
            options={'ordering': ['name', 'id']},
        ),
        migrations.AddField(model_name='measurementitem', name='code', field=models.CharField(blank=True, max_length=30, null=True, unique=True, verbose_name='Código del ítem')),
        migrations.AddField(model_name='goal', name='code', field=models.CharField(blank=True, max_length=30, null=True, unique=True, verbose_name='Código de la meta')),
        migrations.AddField(model_name='goal', name='status', field=models.CharField(choices=[('Activo', 'Activo'), ('Inactivo', 'Inactivo')], default='Activo', max_length=20)),
        migrations.CreateModel(
            name='SubAttention',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Última actualización')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Fecha de eliminación lógica')),
                ('code', models.CharField(max_length=30, unique=True)),
                ('name', models.CharField(max_length=120)),
                ('description', models.TextField(blank=True, default='')),
                ('status', models.CharField(choices=[('Activo', 'Activo'), ('Inactivo', 'Inactivo')], default='Activo', max_length=20)),
                ('attention_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='subattentions', to='metrics.attentiontype')),
            ],
            options={'ordering': ['attention_type_id', 'name', 'id'], 'constraints': [models.UniqueConstraint(fields=('attention_type', 'name'), name='unique_subattention_name_per_type')]},
        ),
    ]
