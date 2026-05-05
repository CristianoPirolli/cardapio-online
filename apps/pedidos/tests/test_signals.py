from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from apps.pedidos.models import Pedido
from apps.restaurantes.models import Restaurante


class PedidoSignalsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='sig_owner', password='123')
        self.restaurante = Restaurante.objects.create(
            nome='Sig Restaurante',
            subdominio='sig-rest',
            proprietario=self.user,
            endereco='Rua D', cidade='SP', estado='SP', cep='01000-000',
            telefone='11555555555', email='sig@test.com',
            taxa_entrega=Decimal('0'), pedido_minimo=Decimal('0'),
            taxa_imposto=Decimal('0'), ativo=True,
        )

    @patch('apps.pedidos.signals.NotificationService.novo_pedido')
    def test_signal_dispara_novo_pedido_ao_criar(self, mock_novo):
        Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='Teste',
            cliente_telefone='11999999999',
            status='recebido',
            pago=True,
        )
        mock_novo.assert_called_once()

    @patch('apps.pedidos.signals.NotificationService.status_mudou')
    def test_signal_dispara_status_mudou_ao_alterar_status(self, mock_mudou):
        pedido = Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='Teste2',
            cliente_telefone='11999999998',
            status='recebido',
            pago=True,
        )
        pedido_recarregado = Pedido.objects.get(pk=pedido.pk)
        pedido_recarregado.status = 'preparo'
        pedido_recarregado._skip_status_validation = True
        pedido_recarregado.save()

        mock_mudou.assert_called_once_with(pedido_recarregado, 'recebido')

    @patch('apps.pedidos.signals.NotificationService.status_mudou')
    def test_signal_nao_dispara_se_status_nao_mudou(self, mock_mudou):
        pedido = Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='Teste3',
            cliente_telefone='11999999997',
            status='recebido',
            pago=True,
        )
        pedido_recarregado = Pedido.objects.get(pk=pedido.pk)
        pedido_recarregado.observacoes = 'Atualizado'
        pedido_recarregado.save()

        mock_mudou.assert_not_called()
