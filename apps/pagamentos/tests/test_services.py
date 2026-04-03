"""
Unit tests for apps/pagamentos/services.py (PIX manual flow).
Test cases are added progressively by each wave.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from apps.restaurantes.models import Restaurante
from apps.pedidos.models import Pedido
from apps.pagamentos.models import Pagamento


def _make_restaurante():
    """Factory: creates a Restaurante with a linked User for tests."""
    user = User.objects.create_user(username='testrest', password='pass')
    return Restaurante.objects.create(
        proprietario=user,
        nome='Restaurante Teste',
        subdominio='testrest',
    )


def _make_pedido(restaurante):
    """Factory: creates a minimal Pedido in 'aguardando' state."""
    return Pedido.objects.create(
        restaurante=restaurante,
        cliente_nome='Cliente Teste',
        cliente_telefone='11999999999',
        status='aguardando',
        pago=False,
        subtotal='50.00',
        taxa_entrega='5.00',
        imposto='0.00',
        total='55.00',
    )
