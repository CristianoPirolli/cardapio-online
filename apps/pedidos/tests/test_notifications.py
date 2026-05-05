from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.test import TestCase
from decimal import Decimal

from apps.pedidos.models import Pedido, PushSubscription
from apps.restaurantes.models import Restaurante


class PushSubscriptionModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='123')
        self.restaurante = Restaurante.objects.create(
            nome='Pizzaria Teste',
            subdominio='pizzaria-teste',
            proprietario=self.user,
            endereco='Rua A, 10',
            cidade='Cidade',
            estado='SP',
            cep='01000-000',
            telefone='11999999999',
            email='restaurante@test.com',
            taxa_entrega=Decimal('5.00'),
            pedido_minimo=Decimal('10.00'),
            taxa_imposto=Decimal('0.00'),
            ativo=True,
        )
        self.pedido = Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='João',
            cliente_telefone='11999999999',
            status='recebido',
            pago=True,
        )

    def test_subscription_com_restaurante_e_pedido_invalida(self):
        sub = PushSubscription(
            restaurante=self.restaurante,
            pedido=self.pedido,
            endpoint='https://fcm.example.com/abc',
            p256dh='key123',
            auth='auth123',
        )
        with self.assertRaises(ValidationError):
            sub.full_clean()

    def test_subscription_sem_restaurante_e_sem_pedido_invalida(self):
        sub = PushSubscription(
            endpoint='https://fcm.example.com/abc',
            p256dh='key123',
            auth='auth123',
        )
        with self.assertRaises(ValidationError):
            sub.full_clean()

    def test_subscription_apenas_restaurante_valida(self):
        sub = PushSubscription(
            restaurante=self.restaurante,
            endpoint='https://fcm.example.com/rest',
            p256dh='key123',
            auth='auth123',
        )
        sub.full_clean()  # não deve levantar exceção

    def test_subscription_apenas_pedido_valida(self):
        sub = PushSubscription(
            pedido=self.pedido,
            endpoint='https://fcm.example.com/ped',
            p256dh='key123',
            auth='auth123',
        )
        sub.full_clean()  # não deve levantar exceção

    def test_pedido_status_anterior_snapshot(self):
        """_status_anterior é capturado no momento em que o pedido é carregado."""
        pedido_recarregado = Pedido.objects.get(pk=self.pedido.pk)
        self.assertEqual(pedido_recarregado._status_anterior, 'recebido')

    def test_pedido_status_anterior_reflete_valor_pre_mudanca(self):
        pedido_recarregado = Pedido.objects.get(pk=self.pedido.pk)
        pedido_recarregado.status = 'preparo'
        self.assertEqual(pedido_recarregado._status_anterior, 'recebido')
