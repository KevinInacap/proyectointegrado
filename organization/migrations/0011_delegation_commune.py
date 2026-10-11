from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('organization', '0010_delegation_code')]
    operations = [
        migrations.AddField(
            model_name='delegation',
            name='commune',
            field=models.CharField(default='La Serena', max_length=100, verbose_name='Comuna'),
        ),
    ]
