import json
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.test import TestCase, override_settings

from apps.pedidos.consumers import PainelConsumer


@override_settings(CHANNEL_LAYERS={
    'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
})
class PainelConsumerTests(TestCase):

    async def _connect(self, restaurante_id):
        app = PainelConsumer.as_asgi()
        communicator = WebsocketCommunicator(app, f'/ws/painel/{restaurante_id}/')
        communicator.scope['url_route'] = {'kwargs': {'restaurante_id': str(restaurante_id)}}
        connected, _ = await communicator.connect()
        return communicator, connected

    def test_consumer_aceita_conexao(self):
        async def run():
            communicator, connected = await self._connect(1)
            self.assertTrue(connected)
            await communicator.disconnect()
        async_to_sync(run)()

    def test_consumer_recebe_evento_novo_pedido(self):
        async def run():
            communicator, _ = await self._connect(1)
            channel_layer = get_channel_layer()
            await channel_layer.group_send('painel_1', {
                'type': 'novo_pedido',
                'title': 'Novo pedido #99',
                'body': 'Cliente — R$ 50,00',
                'url': '/painel/pedidos/99/',
                'pedido_id': 99,
                'cliente_nome': 'Cliente',
                'total': '50.00',
                'tipo_entrega': 'delivery',
            })
            response = await communicator.receive_json_from(timeout=3)
            self.assertEqual(response['type'], 'novo_pedido')
            self.assertEqual(response['pedido_id'], 99)
            await communicator.disconnect()
        async_to_sync(run)()
