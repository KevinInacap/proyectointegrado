from django.db import migrations, models
import django.db.models.deletion


def link_unambiguous_base_roles(apps, schema_editor):
    Position = apps.get_model('organization', 'Position')
    Role = apps.get_model('organization', 'Role')
    database = schema_editor.connection.alias
    for role in Role.objects.using(database).all().iterator():
        ids = list(Position.objects.using(database).filter(base_role_id=role.pk).values_list('pk', flat=True)[:2])
        if len(ids) == 1:
            Role.objects.using(database).filter(pk=role.pk).update(position_id=ids[0])


class Migration(migrations.Migration):
    dependencies = [('organization', '0017_position_base_role')]
    operations = [
        migrations.AddField(model_name='role', name='position', field=models.ForeignKey(
            to='organization.position', on_delete=django.db.models.deletion.PROTECT,
            null=True, blank=True, related_name='access_roles', verbose_name='Cargo del rol')),
        migrations.RunPython(link_unambiguous_base_roles, migrations.RunPython.noop),
    ]
