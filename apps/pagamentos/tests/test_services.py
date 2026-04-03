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


class PagamentoModelTest(TestCase):
    """Tests for Pagamento model fields added in Wave 1."""

    def setUp(self):
        self.restaurante = _make_restaurante()
        self.pedido = _make_pedido(self.restaurante)

    def test_can_create_pix_manual_pagamento(self):
        """Pagamento with gateway='pix_manual' must be creatable."""
        pagamento = Pagamento.objects.create(
            pedido=self.pedido,
            gateway='pix_manual',
            valor='55.00',
            status='pendente',
        )
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.gateway, 'pix_manual')

    def test_comprovante_is_nullable(self):
        """Pagamento created without comprovante must have comprovante='' or None."""
        pagamento = Pagamento.objects.create(
            pedido=self.pedido,
            gateway='pix_manual',
            valor='55.00',
            status='pendente',
        )
        self.assertFalse(bool(pagamento.comprovante))

    def test_pix_manual_in_gateway_choices(self):
        """GATEWAY_CHOICES must include pix_manual."""
        choices_values = [c[0] for c in Pagamento.GATEWAY_CHOICES]
        self.assertIn('pix_manual', choices_values)


from apps.pagamentos.services import (
    criar_pagamento_pix_manual,
    confirmar_pix_manual,
    rejeitar_pix_manual,
)


class PixManualServiceTest(TestCase):
    """Unit tests for PIX manual service functions (REQ-03, REQ-04, REQ-05)."""

    def setUp(self):
        self.restaurante = _make_restaurante()
        self.pedido = _make_pedido(self.restaurante)

    def test_criar_pagamento_pix_manual_creates_record(self):
        """criar_pagamento_pix_manual must create a Pagamento with correct fields."""
        pagamento = criar_pagamento_pix_manual(self.pedido)
        self.assertEqual(pagamento.gateway, 'pix_manual')
        self.assertEqual(pagamento.status, 'pendente')
        self.assertEqual(pagamento.pedido, self.pedido)
        self.assertFalse(self.pedido.pago)

    def test_criar_pagamento_pix_manual_is_idempotent(self):
        """Calling twice returns the same Pagamento, not a duplicate."""
        p1 = criar_pagamento_pix_manual(self.pedido)
        p2 = criar_pagamento_pix_manual(self.pedido)
        self.assertEqual(p1.id, p2.id)
        self.assertEqual(Pagamento.objects.filter(pedido=self.pedido).count(), 1)

    def test_confirmar_pix_manual_sets_pago_true(self):
        """confirmar_pix_manual must set pedido.pago=True and status=recebido."""
        pagamento = criar_pagamento_pix_manual(self.pedido)
        # Move pedido to aguardando_confirmacao (simulating customer upload)
        self.pedido.status = 'aguardando_confirmacao'
        self.pedido.save()

        confirmar_pix_manual(pagamento)

        self.pedido.refresh_from_db()
        pagamento.refresh_from_db()
        self.assertTrue(self.pedido.pago)
        self.assertEqual(self.pedido.status, 'recebido')
        self.assertEqual(pagamento.status, 'aprovado')

    def test_rejeitar_pix_manual_cancels_pedido(self):
        """rejeitar_pix_manual must cancel the pedido and leave pago=False."""
        pagamento = criar_pagamento_pix_manual(self.pedido)
        self.pedido.status = 'aguardando_confirmacao'
        self.pedido.save()

        rejeitar_pix_manual(pagamento)

        self.pedido.refresh_from_db()
        pagamento.refresh_from_db()
        self.assertFalse(self.pedido.pago)
        self.assertEqual(self.pedido.status, 'cancelado')
        self.assertEqual(pagamento.status, 'recusado')

    def test_confirmar_pix_manual_is_idempotent(self):
        """Calling confirmar on already-approved pagamento does not raise."""
        pagamento = criar_pagamento_pix_manual(self.pedido)
        self.pedido.status = 'aguardando_confirmacao'
        self.pedido.save()
        confirmar_pix_manual(pagamento)

        # Call again — must not raise, must not change status
        pagamento.refresh_from_db()
        confirmar_pix_manual(pagamento)
        self.assertEqual(pagamento.status, 'aprovado')
