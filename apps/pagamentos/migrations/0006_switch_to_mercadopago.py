from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pagamentos', '0005_add_stripe_gateway'),
    ]

    operations = [
        # Renomeia o campo stripe_payment_intent_id → external_payment_id
        migrations.RenameField(
            model_name='pagamento',
            old_name='stripe_payment_intent_id',
            new_name='external_payment_id',
        ),
        # Atualiza verbose_name do campo renomeado
        migrations.AlterField(
            model_name='pagamento',
            name='external_payment_id',
            field=models.CharField(
                blank=True,
                max_length=255,
                verbose_name='ID do Pagamento (Gateway)',
            ),
        ),
        # Substitui 'stripe' por 'mercadopago' nas opções de gateway
        migrations.AlterField(
            model_name='pagamento',
            name='gateway',
            field=models.CharField(
                choices=[
                    ('mercadopago', 'Mercado Pago'),
                    ('mock', 'Mock (Simulação)'),
                ],
                default='mock',
                max_length=15,
                verbose_name='Gateway',
            ),
        ),
    ]
