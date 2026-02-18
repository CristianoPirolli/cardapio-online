# =============================================================================
# apps/entregas/apps.py - Configuração do app entregas
# =============================================================================

from django.apps import AppConfig


class EntregasConfig(AppConfig):
    """Configuração do app de entregas e entregadores."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.entregas'
    verbose_name = 'Entregas'
