import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from apps.pedidos.models import Pedido, PushSubscription
from apps.restaurantes.models import Restaurante


VALID_SUBSCRIPTION = {
    'endpoint': 'https://fcm.googleapis.com/fcm/send/abc123',
    'keys': {
        'p256dh': 'pubkeyabc',
        'auth': 'authkeyabc',
    },
}


class PushSubscribeAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='api_owner', password='123')
        self.restaurante = Restaurante.objects.create(
            nome='API Restaurante',
            subdominio='api-rest',
            proprietario=self.user,
            endereco='Rua E', cidade='SP', estado='SP', cep='01000-000',
            telefone='11444444444', email='api@test.com',
            taxa_entrega=Decimal('0'), pedido_minimo=Decimal('0'),
            taxa_imposto=Decimal('0'), ativo=True,
        )
        self.pedido = Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='API Cliente',
            cliente_telefone='11333333333',
            status='recebido',
            pago=True,
        )

    def _post(self, data):
        return self.client.post(
            '/api/pedidos/push/subscribe/',
            data=json.dumps(data),
            content_type='application/json',
        )

    def test_subscribe_painel_cria_subscription(self):
        data = {**VALID_SUBSCRIPTION, 'tipo': 'painel', 'restaurante_id': self.restaurante.id}
        response = self._post(data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            PushSubscription.objects.filter(
                restaurante=self.restaurante,
                endpoint=VALID_SUBSCRIPTION['endpoint'],
            ).exists()
        )

    def test_subscribe_pedido_cria_subscription(self):
        data = {**VALID_SUBSCRIPTION, 'tipo': 'pedido', 'pedido_id': self.pedido.id}
        response = self._post(data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            PushSubscription.objects.filter(
                pedido=self.pedido,
                endpoint=VALID_SUBSCRIPTION['endpoint'],
            ).exists()
        )

    def test_subscribe_sem_endpoint_retorna_400(self):
        data = {'tipo': 'painel', 'restaurante_id': self.restaurante.id, 'keys': {'p256dh': 'k', 'auth': 'a'}}
        response = self._post(data)
        self.assertEqual(response.status_code, 400)

    def test_subscribe_tipo_invalido_retorna_400(self):
        data = {**VALID_SUBSCRIPTION, 'tipo': 'invalido'}
        response = self._post(data)
        self.assertEqual(response.status_code, 400)

    def test_subscribe_idempotente_atualiza_sem_duplicar(self):
        data = {**VALID_SUBSCRIPTION, 'tipo': 'painel', 'restaurante_id': self.restaurante.id}
        self._post(data)
        self._post(data)
        count = PushSubscription.objects.filter(
            restaurante=self.restaurante,
            endpoint=VALID_SUBSCRIPTION['endpoint'],
        ).count()
        self.assertEqual(count, 1)
