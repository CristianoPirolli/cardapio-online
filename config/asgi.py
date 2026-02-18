# =============================================================================
# config/asgi.py - Ponto de entrada ASGI (para uso futuro com WebSockets)
#
# Atualmente não utilizado, mas necessário para compatibilidade futura
# com Django Channels ou servidores ASGI como Uvicorn/Daphne.
# =============================================================================

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_asgi_application()
