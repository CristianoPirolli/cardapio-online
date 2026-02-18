from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('restaurantes', '0002_alter_restaurante_proprietario'),
    ]

    operations = [
        migrations.AddField(
            model_name='restaurante',
            name='tempo_entrega_min',
            field=models.PositiveIntegerField(
                default=45,
                validators=[django.core.validators.MinValueValidator(1)],
                verbose_name='Tempo de Entrega (min)',
            ),
        ),
        migrations.AddField(
            model_name='restaurante',
            name='tempo_retirada_min',
            field=models.PositiveIntegerField(
                default=25,
                validators=[django.core.validators.MinValueValidator(1)],
                verbose_name='Tempo de Retirada (min)',
            ),
        ),
    ]
