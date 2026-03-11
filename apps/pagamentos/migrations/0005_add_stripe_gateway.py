# Generated manually - Add Stripe gateway choice

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pagamentos', '0004_remove_mp_gateway'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pagamento',
            name='gateway',
            field=models.CharField(
                choices=[('stripe', 'Stripe'), ('mock', 'Mock (Simulação)')],
                default='mock',
                max_length=10,
                verbose_name='Gateway',
            ),
        ),
    ]
