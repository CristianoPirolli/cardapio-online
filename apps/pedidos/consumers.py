# =============================================================================
# apps/pedidos/consumers.py - WebSocket consumers para notificação de status
#
# Quando o restaurante muda o status de um pedido, notifica o cliente
# conectado via WebSocket para atualização em tempo real.
# =============================================================================

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import Pedido


class PedidoStatusConsumer(AsyncWebsocketConsumer):
    """
    Consumer WebSocket para acompanhamento de status do pedido em tempo real.

    Cliente se conecta em: ws://localhost/ws/pedidos/{pedido_id}/status/
    """

    async def connect(self):
        """Aceita a conexão WebSocket e se inscreve no grupo do pedido."""
        self.pedido_id = self.scope['url_route']['kwargs']['pedido_id']
        self.pedido_group_name = f'pedido_{self.pedido_id}_status'

        # Inscreve no grupo de broadcast
        await self.channel_layer.group_add(
            self.pedido_group_name,
            self.channel_name
        )

        await self.accept()

        # Envia o status atual ao conectar
        pedido = await self.get_pedido()
        if pedido:
            await self.send(text_data=json.dumps({
                'type': 'status_update',
                'status': pedido.status,
                'status_display': pedido.get_status_display(),
                'customer_status': pedido.customer_status,
                'customer_status_display': pedido.customer_status_display,
                'terminal': pedido.customer_status_terminal,
                'timestamp': pedido.atualizado_em.isoformat(),
            }))

    async def disconnect(self, close_code):
        """Remove do grupo ao desconectar."""
        await self.channel_layer.group_discard(
            self.pedido_group_name,
            self.channel_name
        )

    async def status_update(self, event):
        """
        Recebe evento de atualização de status do grupo
        e envia ao cliente WebSocket.
        """
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'status': event['status'],
            'status_display': event['status_display'],
            'customer_status': event['customer_status'],
            'customer_status_display': event['customer_status_display'],
            'terminal': event['terminal'],
            'timestamp': event['timestamp'],
        }))

    @sync_to_async
    def get_pedido(self):
        """Busca o pedido atual do banco."""
        try:
            return Pedido.objects.get(id=self.pedido_id)
        except Pedido.DoesNotExist:
            return None


class PainelConsumer(AsyncWebsocketConsumer):
    """
    WebSocket do painel do restaurante.

    Restaurante conecta em: ws://host/ws/painel/{restaurante_id}/
    Grupo de broadcast: 'painel_{restaurante_id}'

    Eventos recebidos:
    - novo_pedido: novo pedido criado no restaurante
    """

    async def connect(self):
        self.restaurante_id = self.scope['url_route']['kwargs']['restaurante_id']
        self.group_name = f'painel_{self.restaurante_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def novo_pedido(self, event):
        """Recebe evento do NotificationService e repassa ao browser."""
        await self.send(text_data=json.dumps(event))
