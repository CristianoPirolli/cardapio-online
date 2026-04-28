from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.pedidos.models import Pedido
from apps.restaurantes.models import Restaurante


class PedidoTrackingStatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner_tracking', password='123')
        self.restaurante = Restaurante.objects.create(
            nome='Restaurante Tracking',
            subdominio='restaurante-tracking',
            proprietario=self.user,
            endereco='Rua A, 10',
            cidade='Cidade',
            estado='SP',
            cep='01000-000',
            telefone='11999999999',
            email='restaurante-tracking@test.com',
            taxa_entrega=Decimal('5.00'),
            pedido_minimo=Decimal('10.00'),
            taxa_imposto=Decimal('10.00'),
            ativo=True,
        )

    def _criar_pedido(self, status='aguardando', forma_pagamento='pix'):
        return Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='Cliente Teste',
            cliente_telefone='11911111111',
            cliente_email='cliente@test.com',
            endereco_entrega='Rua B, 20',
            tipo_entrega='delivery',
            forma_pagamento=forma_pagamento,
            subtotal=Decimal('20.00'),
            taxa_entrega=Decimal('5.00'),
            imposto=Decimal('2.00'),
            total=Decimal('27.00'),
            status=status,
            pago=False,
        )

    def test_customer_status_mapping(self):
        casos = [
            ('aguardando', 'aguardando_pix', 'pix'),
            ('aguardando_confirmacao', 'aguardando_pix', 'pix'),
            ('recebido', 'confirmado', 'pix'),
            ('preparo', 'em_preparo', 'pix'),
            ('entrega', 'saiu_entrega', 'pix'),
            ('concluido', 'entregue', 'pix'),
            ('cancelado', 'cancelado', 'pix'),
            # Pedidos com dinheiro não mostram 'aguardando_pix'
            ('recebido', 'confirmado', 'dinheiro'),
            ('preparo', 'em_preparo', 'dinheiro'),
            ('entrega', 'saiu_entrega', 'dinheiro'),
            ('concluido', 'entregue', 'dinheiro'),
            # Pedidos com cartão também não mostram 'aguardando_pix'
            ('recebido', 'confirmado', 'cartao'),
            ('entrega', 'saiu_entrega', 'cartao'),
        ]
        for status_interno, status_cliente, forma in casos:
            pedido = self._criar_pedido(status=status_interno, forma_pagamento=forma)
            self.assertEqual(
                pedido.customer_status, status_cliente,
                f'Status interno {status_interno} com forma {forma} deveria retornar {status_cliente}'
            )

    def test_endpoint_retorna_customer_status_e_terminal_false(self):
        pedido = self._criar_pedido(status='preparo')

        response = self.client.get(reverse('acompanhar_pedido_status', args=[pedido.id]))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['status'], 'preparo')
        self.assertEqual(body['customer_status'], 'em_preparo')
        self.assertEqual(body['customer_status_display'], 'Em Preparo')
        self.assertFalse(body['terminal'])

    def test_endpoint_retorna_terminal_true_para_concluido(self):
        pedido = self._criar_pedido(status='concluido')

        response = self.client.get(reverse('acompanhar_pedido_status', args=[pedido.id]))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['customer_status'], 'entregue')
        self.assertTrue(body['terminal'])

