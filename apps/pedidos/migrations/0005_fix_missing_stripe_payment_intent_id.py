from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pedidos', '0004_add_indexes'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE pedidos_pedido "
                "ADD COLUMN IF NOT EXISTS stripe_payment_intent_id varchar(255) NOT NULL DEFAULT '';"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]

