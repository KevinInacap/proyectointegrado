from django.db import migrations, models
import django.db.models.deletion


def link_existing_neighbors(apps, schema_editor):
    Activity = apps.get_model('activities', 'Activity')
    Vecino = apps.get_model('activities', 'Vecino')
    database = schema_editor.connection.alias
    for activity in Activity.objects.using(database).filter(neighbor__isnull=True).iterator():
        matches = Vecino.objects.using(database).filter(
            nombre__iexact=activity.contact_name,
            deleted_at__isnull=True,
        )
        if activity.contact_phone:
            by_contact = matches.filter(telefono=activity.contact_phone)
            if by_contact.exists():
                matches = by_contact
        if matches.count() == 1:
            activity.neighbor_id = matches.values_list('pk', flat=True).first()
            activity.save(using=database, update_fields=['neighbor'])


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0005_activity_attention_type_activity_subattention'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='neighbor',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='activities', to='activities.vecino',
                verbose_name='Vecino asociado',
            ),
        ),
        migrations.RunPython(link_existing_neighbors, migrations.RunPython.noop),
    ]
