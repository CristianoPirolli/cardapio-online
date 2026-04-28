from django.db import migrations


def fix_historical_orders(apps, schema_editor):
    """
    Corrige pedidos históricos de dinheiro/cartão que estavam em status 'aguardando'.

    Com a nova lógica:
    - PIX começa em 'aguardando' (esperando comprovante)
    - Dinheiro/Cartão começam em 'recebido' (já confirmado)

    Pedidos antigos de dinheiro/cartão em status 'aguardando' são movidos para 'recebido'
    e marcados como pagos para aparecerem no painel do restaurante.
    """
    Pedido = apps.get_model('pedidos', 'Pedido')

    # Encontrar pedidos de dinheiro/cartão em status 'aguardando'
    pedidos_incorretos = Pedido.objects.filter(
        forma_pagamento__in=['dinheiro', 'cartao'],
        status='aguardando',
    )

    count = pedidos_incorretos.count()
    if count > 0:
        pedidos_incorretos.update(
            status='recebido',
            pago=True,
        )
        print(f"Corrigidos {count} pedidos de dinheiro/cartão")


def revert_fix(apps, schema_editor):
    # Esta reversão é intencional deixar como está (não reverter)
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('pedidos', '0011_alter_pedido_forma_pagamento'),
    ]

    operations = [
        migrations.RunPython(fix_historical_orders, revert_fix),
    ]
