# =============================================================================
# config/wsgi.py - Ponto de entrada WSGI para o servidor Gunicorn
#
# Expõe a variável 'application' que o Gunicorn usa para servir o Django.
# Uso: gunicorn config.wsgi:application --bind 0.0.0.0:8000
# =============================================================================

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()
