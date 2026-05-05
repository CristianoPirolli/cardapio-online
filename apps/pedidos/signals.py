# =============================================================================
# apps/pedidos/signals.py - Sinais Django para notificação de status
#
# Quando um Pedido é salvo com status alterado, emite notificação WebSocket
# para todos os clientes conectados ao grupo daquele pedido.
# =============================================================================

import logging

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Pedido
from .notifications import NotificationService

logger = logging.getLogger(__name__)

# Cache do status anterior para comparação em post_save
_pedido_status_anterior = {}


@receiver(pre_save, sender=Pedido)
def capturar_status_anterior(sender, instance, **kwargs):
    """
    Signal que dispara ANTES de salvar.
    Captura o status anterior para comparação.
    """
    if instance.pk:
        try:
            old_pedido = Pedido.objects.get(pk=instance.pk)
            _pedido_status_anterior[instance.pk] = old_pedido.status
        except Pedido.DoesNotExist:
            _pedido_status_anterior[instance.pk] = None
    else:
        _pedido_status_anterior[instance.pk] = None


@receiver(post_save, sender=Pedido)
def pedido_status_changed(sender, instance, created, **kwargs):
    """
    Signal que dispara quando um Pedido é salvo.
    Se o status foi alterado, notifica via WebSocket.
    """
    if created:
        # Pedido novo - não notifica
        if instance.pk in _pedido_status_anterior:
            del _pedido_status_anterior[instance.pk]
        return

    # Pega o status anterior do cache
    old_status = _pedido_status_anterior.get(instance.pk)
    if instance.pk in _pedido_status_anterior:
        del _pedido_status_anterior[instance.pk]

    # Se status não mudou, não faz nada
    if old_status == instance.status:
        return

    # Status mudou - emite notificação WebSocket
    try:
        channel_layer = get_channel_layer()
        group_name = f'pedido_{instance.pk}_status'

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'status_update',
                'status': instance.status,
                'status_display': instance.get_status_display(),
                'customer_status': instance.customer_status,
                'customer_status_display': instance.customer_status_display,
                'terminal': instance.customer_status_terminal,
                'timestamp': instance.atualizado_em.isoformat(),
            }
        )
    except Exception as e:
        # Não falha se o channel layer não estiver disponível
        print(f'Erro ao enviar notificação WebSocket: {e}')


@receiver(post_save, sender=Pedido)
def pedido_salvo(sender, instance, created, **kwargs):
    """
    Dispara NotificationService para restaurante (novo pedido) e cliente (mudança de status).

    Detecta mudança de status via instance._status_anterior capturado no __init__,
    evitando query extra ao banco.
    """
    try:
        if created:
            NotificationService.novo_pedido(instance)
        elif hasattr(instance, '_status_anterior') and instance._status_anterior != instance.status:
            NotificationService.status_mudou(instance, instance._status_anterior)
    except Exception as exc:
        logger.error('Erro ao processar notificação para pedido %s: %s', instance.pk, exc)
