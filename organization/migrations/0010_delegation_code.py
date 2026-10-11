from django.db import migrations, models


def backfill_codes(apps, schema_editor):
    Delegation = apps.get_model('organization', 'Delegation')
    database = schema_editor.connection.alias
    for delegation in Delegation.objects.using(database).filter(code__isnull=True).iterator():
        Delegation.objects.using(database).filter(pk=delegation.pk).update(code=f'DEL-{delegation.pk:03d}')


class Migration(migrations.Migration):
    dependencies = [('organization', '0009_role_permission_definitions')]
    operations = [
        migrations.AddField(
            model_name='delegation',
            name='code',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True, verbose_name='Código de delegación'),
        ),
        migrations.RunPython(backfill_codes, migrations.RunPython.noop),
    ]
