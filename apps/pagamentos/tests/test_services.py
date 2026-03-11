from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.pagamentos.models import Pagamento
from apps.pagamentos.services import (
    criar_pagamento,
    confirmar_pagamento_mock,
    confirmar_pagamento_stripe,
)
from apps.pedidos.models import Pedido
from apps.restaurantes.models import Restaurante


class PagamentoMockTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner_pag', password='123')
        self.restaurante = Restaurante.objects.create(
            nome='Restaurante Pagamentos',
            subdominio='restaurante-pagamentos',
            proprietario=self.user,
            endereco='Rua A, 10',
            cidade='Cidade',
            estado='SP',
            cep='01000-000',
            telefone='11999999999',
            email='restaurante@teste.com',
            taxa_entrega=Decimal('5.00'),
            pedido_minimo=Decimal('10.00'),
            taxa_imposto=Decimal('5.00'),
            ativo=True,
        )
        self.pedido = Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='Cliente Teste',
            cliente_telefone='11911111111',
            cliente_email='cliente@teste.com',
            endereco_entrega='Rua B, 20',
            tipo_entrega='delivery',
            subtotal=Decimal('40.00'),
            taxa_entrega=Decimal('5.00'),
            imposto=Decimal('2.35'),
            total=Decimal('47.35'),
        )

    @override_settings(PAYMENT_GATEWAY='mock')
    def test_criar_pagamento_mock(self):
        resultado = criar_pagamento(self.pedido)

        self.assertEqual(resultado['gateway'], 'mock')
        self.assertIsNotNone(resultado['pagamento'])
        self.assertTrue(resultado['client_secret'].startswith('mock_pi_'))

        pagamento = resultado['pagamento']
        self.assertEqual(pagamento.status, 'pendente')
        self.assertEqual(pagamento.gateway, 'mock')
        self.assertEqual(pagamento.valor, Decimal('47.35'))

    @override_settings(PAYMENT_GATEWAY='mock')
    def test_confirmar_pagamento_mock(self):
        resultado = criar_pagamento(self.pedido)
        pagamento = resultado['pagamento']

        confirmar_pagamento_mock(pagamento)

        pagamento.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(pagamento.status, 'aprovado')
        self.assertTrue(self.pedido.pago)
        self.assertEqual(self.pedido.status, 'recebido')

    @override_settings(PAYMENT_GATEWAY='mock')
    def test_criar_pagamento_idempotente(self):
        resultado1 = criar_pagamento(self.pedido)
        resultado2 = criar_pagamento(self.pedido)

        self.assertEqual(resultado1['pagamento'].id, resultado2['pagamento'].id)


class PagamentoStripeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner_stripe', password='123')
        self.restaurante = Restaurante.objects.create(
            nome='Restaurante Stripe',
            subdominio='restaurante-stripe',
            proprietario=self.user,
            endereco='Rua A, 10',
            cidade='Cidade',
            estado='SP',
            cep='01000-000',
            telefone='11999999999',
            email='restaurante@teste.com',
            taxa_entrega=Decimal('5.00'),
            pedido_minimo=Decimal('10.00'),
            taxa_imposto=Decimal('5.00'),
            ativo=True,
        )
        self.pedido = Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='Cliente Stripe',
            cliente_telefone='11911111111',
            cliente_email='cliente@teste.com',
            endereco_entrega='Rua B, 20',
            tipo_entrega='delivery',
            subtotal=Decimal('40.00'),
            taxa_entrega=Decimal('5.00'),
            imposto=Decimal('2.35'),
            total=Decimal('47.35'),
        )

    @override_settings(PAYMENT_GATEWAY='stripe', STRIPE_SECRET_KEY='sk_test_fake123')
    @patch('apps.pagamentos.services.stripe.checkout.Session.create')
    def test_criar_pagamento_stripe_card(self, mock_create):
        mock_session = MagicMock()
        mock_session.id = 'cs_test_abc123'
        mock_session.url = 'https://checkout.stripe.com/pay/cs_test_abc123'
        mock_create.return_value = mock_session

        resultado = criar_pagamento(self.pedido, metodo='card')

        self.assertEqual(resultado['gateway'], 'stripe')
        self.assertEqual(resultado['checkout_url'], 'https://checkout.stripe.com/pay/cs_test_abc123')

        pagamento = resultado['pagamento']
        self.assertEqual(pagamento.status, 'pendente')
        self.assertEqual(pagamento.gateway, 'stripe')
        self.assertEqual(pagamento.dados_resposta['metodo'], 'card')

        # Verifica que payment_method_types=['card']
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs['payment_method_types'], ['card'])

    @override_settings(PAYMENT_GATEWAY='stripe', STRIPE_SECRET_KEY='sk_test_fake123')
    @patch('apps.pagamentos.services.stripe.checkout.Session.create')
    def test_criar_pagamento_stripe_pix(self, mock_create):
        mock_session = MagicMock()
        mock_session.id = 'cs_test_pix456'
        mock_session.url = 'https://checkout.stripe.com/pay/cs_test_pix456'
        mock_create.return_value = mock_session

        resultado = criar_pagamento(self.pedido, metodo='pix')

        self.assertEqual(resultado['gateway'], 'stripe')

        pagamento = resultado['pagamento']
        self.assertEqual(pagamento.dados_resposta['metodo'], 'pix')

        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs['payment_method_types'], ['pix'])
        self.assertIn('pix', call_kwargs['payment_method_options'])

    @override_settings(PAYMENT_GATEWAY='stripe', STRIPE_SECRET_KEY='sk_test_fake123')
    @patch('apps.pagamentos.services.stripe.checkout.Session.create')
    def test_trocar_metodo_cancela_antigo(self, mock_create):
        mock_session_1 = MagicMock()
        mock_session_1.id = 'cs_test_card1'
        mock_session_1.url = 'https://checkout.stripe.com/pay/cs_test_card1'

        mock_session_2 = MagicMock()
        mock_session_2.id = 'cs_test_pix2'
        mock_session_2.url = 'https://checkout.stripe.com/pay/cs_test_pix2'

        mock_create.side_effect = [mock_session_1, mock_session_2]

        resultado1 = criar_pagamento(self.pedido, metodo='card')
        pagamento1 = resultado1['pagamento']

        resultado2 = criar_pagamento(self.pedido, metodo='pix')
        pagamento2 = resultado2['pagamento']

        pagamento1.refresh_from_db()
        self.assertEqual(pagamento1.status, 'recusado')
        self.assertEqual(pagamento2.status, 'pendente')
        self.assertNotEqual(pagamento1.id, pagamento2.id)

    @override_settings(STRIPE_SECRET_KEY='sk_test_fake123')
    @patch('apps.pagamentos.services.stripe.checkout.Session.retrieve')
    def test_confirmar_pagamento_stripe(self, mock_retrieve):
        pagamento = Pagamento.objects.create(
            pedido=self.pedido,
            gateway='stripe',
            stripe_payment_intent_id='cs_test_abc123',
            valor=Decimal('47.35'),
            status='pendente',
        )

        mock_session = MagicMock()
        mock_session.payment_status = 'paid'
        mock_session.payment_intent = 'pi_test_xyz'
        mock_session.customer_details = MagicMock(email='cliente@teste.com')
        mock_retrieve.return_value = mock_session

        confirmar_pagamento_stripe('cs_test_abc123')

        pagamento.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(pagamento.status, 'aprovado')
        self.assertTrue(self.pedido.pago)
        self.assertEqual(self.pedido.status, 'recebido')

    @override_settings(STRIPE_SECRET_KEY='sk_test_fake123')
    @patch('apps.pagamentos.services.stripe.checkout.Session.retrieve')
    def test_confirmar_pagamento_stripe_idempotente(self, mock_retrieve):
        pagamento = Pagamento.objects.create(
            pedido=self.pedido,
            gateway='stripe',
            stripe_payment_intent_id='cs_test_abc123',
            valor=Decimal('47.35'),
            status='aprovado',
        )

        mock_session = MagicMock()
        mock_session.payment_status = 'paid'
        mock_retrieve.return_value = mock_session

        result = confirmar_pagamento_stripe('cs_test_abc123')

        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, 'aprovado')
