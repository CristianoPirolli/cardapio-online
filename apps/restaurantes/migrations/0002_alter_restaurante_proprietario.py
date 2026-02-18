from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('restaurantes', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='restaurante',
            name='proprietario',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='restaurante',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Proprietário',
            ),
        ),
    ]
