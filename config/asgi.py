# =============================================================================
# config/asgi.py - Ponto de entrada ASGI com WebSockets (Django Channels)
#
# Configura o roteamento de HTTP (Django) e WebSocket (Channels).
# Para rodar com Daphne: daphne -b 0.0.0.0 -p 8000 config.asgi:application
# =============================================================================

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Carrega aplicação Django
django_asgi_app = get_asgi_application()

# Importa websocket_urlpatterns após Django estar configurado
from config.routing import websocket_urlpatterns

# Configura roteamento ASGI com suporte a HTTP e WebSocket
application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
