from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from apps.pagamentos.models import Pagamento
from apps.pagamentos.services import processar_webhook_mp
from apps.pedidos.models import Pedido
from apps.restaurantes.models import Restaurante


class PagamentoServicesTests(TestCase):
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
        self.pagamento = Pagamento.objects.create(
            pedido=self.pedido,
            gateway='mp',
            stripe_payment_intent_id='pref_123',
            valor=Decimal('47.35'),
            status='pendente',
            dados_resposta={'preference_id': 'pref_123'},
        )

    def _request_payload(self, payment_id='123456'):
        return SimpleNamespace(
            data={'type': 'payment', 'data': {'id': payment_id}},
            query_params={},
        )

    def test_webhook_aprova_pagamento_quando_valor_confere(self):
        sdk_response = {
            'status': 200,
            'response': {
                'id': 123456,
                'external_reference': str(self.pedido.id),
                'transaction_amount': '47.35',
                'status': 'approved',
            },
        }
        fake_sdk = SimpleNamespace(
            payment=lambda: SimpleNamespace(get=lambda _payment_id: sdk_response)
        )

        with patch('apps.pagamentos.services._get_mp_sdk', return_value=fake_sdk):
            resultado = processar_webhook_mp(self._request_payload())

        self.assertEqual(resultado['status'], 200)
        self.assertIn('aprovado', resultado['message'])

        self.pagamento.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(self.pagamento.status, 'aprovado')
        self.assertEqual(self.pagamento.stripe_payment_intent_id, '123456')
        self.assertTrue(self.pedido.pago)

    def test_webhook_recusa_pagamento_quando_valor_diverge(self):
        sdk_response = {
            'status': 200,
            'response': {
                'id': 123456,
                'external_reference': str(self.pedido.id),
                'transaction_amount': '47.36',
                'status': 'approved',
            },
        }
        fake_sdk = SimpleNamespace(
            payment=lambda: SimpleNamespace(get=lambda _payment_id: sdk_response)
        )

        with patch('apps.pagamentos.services._get_mp_sdk', return_value=fake_sdk):
            resultado = processar_webhook_mp(self._request_payload())

        self.assertEqual(resultado['status'], 400)
        self.assertIn('divergente', resultado['error'])

        self.pagamento.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(self.pagamento.status, 'recusado')
        self.assertFalse(self.pedido.pago)
        self.assertIn('erro_validacao_valor', self.pagamento.dados_resposta)
