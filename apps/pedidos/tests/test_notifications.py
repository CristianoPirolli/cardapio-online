from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.test import TestCase
from decimal import Decimal

from apps.pedidos.models import Pedido, PushSubscription
from apps.restaurantes.models import Restaurante
from apps.pedidos.whatsapp import LogWhatsAppAdapter, get_whatsapp_adapter


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


class WhatsAppAdapterTests(TestCase):
    def test_log_adapter_retorna_true(self):
        adapter = LogWhatsAppAdapter()
        resultado = adapter.send('11999999999', 'Mensagem de teste')
        self.assertTrue(resultado)

    def test_get_whatsapp_adapter_retorna_instancia_configurada(self):
        with self.settings(WHATSAPP_ADAPTER='apps.pedidos.whatsapp.LogWhatsAppAdapter'):
            adapter = get_whatsapp_adapter()
        self.assertIsInstance(adapter, LogWhatsAppAdapter)


from unittest.mock import patch, MagicMock
from apps.pedidos.notifications import NotificationService, WebPushService


class WebPushServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner2', password='123')
        self.restaurante = Restaurante.objects.create(
            nome='Teste Push',
            subdominio='teste-push',
            proprietario=self.user,
            endereco='Rua B', cidade='SP', estado='SP', cep='01000-000',
            telefone='11888888888', email='push@test.com',
            taxa_entrega=Decimal('0'), pedido_minimo=Decimal('0'),
            taxa_imposto=Decimal('0'), ativo=True,
        )
        self.sub = PushSubscription.objects.create(
            restaurante=self.restaurante,
            endpoint='https://fcm.example.com/sub1',
            p256dh='pubkey123',
            auth='authkey123',
        )

    @patch('apps.pedidos.notifications.webpush')
    def test_webpush_send_retorna_true_em_sucesso(self, mock_webpush):
        mock_webpush.return_value = None
        resultado = WebPushService.send(self.sub, {'title': 'Teste', 'body': 'Corpo'})
        self.assertTrue(resultado)

    @patch('apps.pedidos.notifications.webpush')
    def test_webpush_send_deleta_subscription_em_410(self, mock_webpush):
        from pywebpush import WebPushException
        response_mock = MagicMock()
        response_mock.status_code = 410
        exc = WebPushException('Gone', response=response_mock)
        mock_webpush.side_effect = exc

        resultado = WebPushService.send(self.sub, {'title': 'Teste', 'body': 'Corpo'})

        self.assertFalse(resultado)
        self.assertFalse(PushSubscription.objects.filter(pk=self.sub.pk).exists())


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner3', password='123')
        self.restaurante = Restaurante.objects.create(
            nome='Notif Teste',
            subdominio='notif-teste',
            proprietario=self.user,
            endereco='Rua C', cidade='SP', estado='SP', cep='01000-000',
            telefone='11777777777', email='notif@test.com',
            taxa_entrega=Decimal('0'), pedido_minimo=Decimal('0'),
            taxa_imposto=Decimal('0'), ativo=True,
        )
        self.pedido = Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='Maria',
            cliente_telefone='11966666666',
            status='recebido',
            pago=True,
        )

    @patch('apps.pedidos.notifications.WebPushService.send')
    @patch('apps.pedidos.notifications.async_to_sync')
    @patch('apps.pedidos.notifications.get_channel_layer')
    def test_novo_pedido_envia_push_para_restaurante(self, mock_layer, mock_sync, mock_push):
        PushSubscription.objects.create(
            restaurante=self.restaurante,
            endpoint='https://fcm.example.com/rest1',
            p256dh='pk1', auth='ak1',
        )
        NotificationService.novo_pedido(self.pedido)
        mock_push.assert_called_once()

    @patch('apps.pedidos.notifications.WebPushService.send')
    @patch('apps.pedidos.notifications.get_whatsapp_adapter')
    @patch('apps.pedidos.notifications.async_to_sync')
    @patch('apps.pedidos.notifications.get_channel_layer')
    def test_status_mudou_envia_whatsapp_em_entrega(self, mock_layer, mock_sync, mock_wpp, mock_push):
        mock_adapter = MagicMock()
        mock_wpp.return_value = mock_adapter
        self.pedido.status = 'entrega'
        self.pedido._skip_status_validation = True
        self.pedido.save()

        NotificationService.status_mudou(self.pedido, 'preparo')

        mock_adapter.send.assert_called_once()
        args = mock_adapter.send.call_args[0]
        self.assertIn('11966666666', args[0])
        self.assertIn('saiu para entrega', args[1])

    @patch('apps.pedidos.notifications.WebPushService.send')
    @patch('apps.pedidos.notifications.get_whatsapp_adapter')
    @patch('apps.pedidos.notifications.async_to_sync')
    @patch('apps.pedidos.notifications.get_channel_layer')
    def test_status_mudou_nao_envia_whatsapp_em_preparo(self, mock_layer, mock_sync, mock_wpp, mock_push):
        mock_adapter = MagicMock()
        mock_wpp.return_value = mock_adapter
        self.pedido.status = 'preparo'
        self.pedido._skip_status_validation = True
        self.pedido.save()

        NotificationService.status_mudou(self.pedido, 'recebido')

        mock_adapter.send.assert_not_called()
