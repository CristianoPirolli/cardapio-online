from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pedidos', '0007_add_aguardando_status'),
    ]

    operations = [
        # Remove o índice antigo (referencia stripe_payment_intent_id)
        migrations.RemoveIndex(
            model_name='pedido',
            name='idx_pedido_stripe',
        ),
        # Renomeia a coluna no banco
        migrations.RenameField(
            model_name='pedido',
            old_name='stripe_payment_intent_id',
            new_name='external_payment_id',
        ),
        # Atualiza verbose_name
        migrations.AlterField(
            model_name='pedido',
            name='external_payment_id',
            field=models.CharField(
                blank=True,
                max_length=255,
                verbose_name='ID do Pagamento (Gateway)',
            ),
        ),
        # Recria o índice com o novo nome de coluna e nome de índice
        migrations.AddIndex(
            model_name='pedido',
            index=models.Index(
                fields=['external_payment_id'],
                name='idx_pedido_ext_payment',
            ),
        ),
    ]
