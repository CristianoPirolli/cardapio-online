# =============================================================================
# config/routing.py - Roteamento de WebSocket para Django Channels
#
# Define as rotas de WebSocket da aplicação.
# =============================================================================

from django.urls import re_path
from apps.pedidos.consumers import PedidoStatusConsumer, PainelConsumer

websocket_urlpatterns = [
    re_path(r'ws/pedidos/(?P<pedido_id>\d+)/status/$', PedidoStatusConsumer.as_asgi()),
    re_path(r'ws/painel/(?P<restaurante_id>\d+)/$', PainelConsumer.as_asgi()),
]
