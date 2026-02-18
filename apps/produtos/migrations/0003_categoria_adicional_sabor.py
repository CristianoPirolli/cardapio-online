from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0002_produtotamanho'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoria',
            name='adicional_sabor',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=8,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name='Adicional por Sabor (R$)',
                help_text='Valor opcional somado ao preço base da pizza para sabores desta categoria.',
            ),
        ),
    ]
