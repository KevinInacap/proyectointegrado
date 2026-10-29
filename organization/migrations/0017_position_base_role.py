from django.db import migrations, models
import django.db.models.deletion


def link_roles(apps, schema_editor):
    Position = apps.get_model('organization', 'Position')
    Role = apps.get_model('organization', 'Role')
    aliases = {'administrador general': 'Administrador', 'superadministrador': 'SuperAdministrador', 'super administrador': 'SuperAdministrador'}
    for position in Position.objects.using(schema_editor.connection.alias).all():
        name = aliases.get(position.name.strip().casefold(), position.name.strip())
        role = Role.objects.using(schema_editor.connection.alias).filter(name__iexact=name, is_system=True, deleted_at__isnull=True).first()
        if role:
            Position.objects.using(schema_editor.connection.alias).filter(pk=position.pk).update(base_role_id=role.pk)


class Migration(migrations.Migration):
    dependencies = [('organization', '0016_delegado_deletion_permission')]
    operations = [
        migrations.AddField(model_name='position', name='base_role', field=models.ForeignKey(
            to='organization.role', on_delete=django.db.models.deletion.PROTECT,
            null=True, blank=True, related_name='base_positions', verbose_name='Rol base del cargo')),
        migrations.RunPython(link_roles, migrations.RunPython.noop),
    ]
