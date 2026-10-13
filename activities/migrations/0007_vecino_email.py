from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('activities', '0006_activity_vecino'),
    ]

    operations = [
        migrations.AddField(
            model_name='vecino',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True, verbose_name='Correo electrónico'),
        ),
    ]
