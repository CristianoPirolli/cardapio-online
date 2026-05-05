import json
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings

from pywebpush import webpush, WebPushException

from .whatsapp import get_whatsapp_adapter

logger = logging.getLogger(__name__)


class WebPushService:
    """Envia Web Push notifications via VAPID (pywebpush)."""

    @staticmethod
    def send(subscription, payload: dict) -> bool:
        """
        Envia uma notificação push para a subscription informada.

        Deleta automaticamente subscriptions expiradas (HTTP 404/410).
        """
        try:
            webpush(
                subscription_info={
                    'endpoint': subscription.endpoint,
                    'keys': {
                        'p256dh': subscription.p256dh,
                        'auth': subscription.auth,
                    },
                },
                data=json.dumps(payload),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={'sub': f'mailto:{settings.VAPID_ADMIN_EMAIL}'},
            )
            return True
        except WebPushException as exc:
            logger.error('Web Push falhou para endpoint %s: %s', subscription.endpoint[:60], exc)
            if exc.response and exc.response.status_code in (404, 410):
                subscription.delete()
            return False
        except Exception as exc:
            logger.error('Erro inesperado ao enviar Web Push: %s', exc)
            return False


class NotificationService:
    """
    Orquestra todos os canais de notificação.

    - novo_pedido: notifica o restaurante via WebSocket (painel aberto) e Web Push (offline).
    - status_mudou: notifica o cliente via Web Push + WhatsApp (só em entrega/pronto_retirada).
    """

    @classmethod
    def novo_pedido(cls, pedido):
        """Notifica o restaurante sobre um novo pedido."""
        from .models import PushSubscription

        payload = {
            'type': 'novo_pedido',
            'title': f'Novo pedido #{pedido.id}',
            'body': (
                f'{pedido.cliente_nome} — '
                f'R$ {pedido.total:.2f} — '
                f'{pedido.get_tipo_entrega_display()}'
            ),
            'url': f'/painel/pedidos/{pedido.id}/',
            'pedido_id': pedido.id,
            'cliente_nome': pedido.cliente_nome,
            'total': str(pedido.total),
            'tipo_entrega': pedido.tipo_entrega,
        }

        # WebSocket: entrega ao browser se o painel estiver aberto
        channel_layer = get_channel_layer()
        group_name = f'painel_{pedido.restaurante_id}'
        try:
            async_to_sync(channel_layer.group_send)(group_name, {
                'type': 'novo_pedido',
                **payload,
            })
        except Exception as exc:
            logger.error('Erro no channel layer para painel %s: %s', pedido.restaurante_id, exc)

        # Web Push: entrega ao browser mesmo se o painel estiver fechado
        for sub in PushSubscription.objects.filter(restaurante_id=pedido.restaurante_id):
            WebPushService.send(sub, payload)

    @classmethod
    def status_mudou(cls, pedido, status_anterior):
        """Notifica o cliente sobre mudança de status do pedido."""
        from .models import PushSubscription

        push_payload = {
            'type': 'status_update',
            'title': f'Pedido #{pedido.id} atualizado',
            'body': pedido.customer_status_display,
            'url': f'/pedidos/{pedido.id}/acompanhar/',
            'status': pedido.status,
        }

        # Web Push para o cliente (se tiver subscription registrada)
        for sub in PushSubscription.objects.filter(pedido_id=pedido.id):
            WebPushService.send(sub, push_payload)

        # WhatsApp apenas para entrega ou pronto_retirada
        if pedido.status not in ('entrega', 'pronto_retirada'):
            return
        if not pedido.cliente_telefone:
            return

        site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
        acompanhar_url = f'{site_url}/pedidos/{pedido.id}/acompanhar/'

        if pedido.status == 'entrega':
            mensagem = (
                f'Olá {pedido.cliente_nome}! Seu pedido #{pedido.id} '
                f'saiu para entrega!!! 😋🍕 Acompanhe em: {acompanhar_url}'
            )
        else:
            mensagem = (
                f'Olá {pedido.cliente_nome}! Seu pedido #{pedido.id} '
                f'está pronto para retirada!!! 😋🍕 Acompanhe em: {acompanhar_url}'
            )

        try:
            adapter = get_whatsapp_adapter()
            adapter.send(pedido.cliente_telefone, mensagem)
        except Exception as exc:
            logger.error('Erro ao enviar WhatsApp para pedido %s: %s', pedido.id, exc)
