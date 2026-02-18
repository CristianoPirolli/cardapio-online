# =============================================================================
# apps/restaurantes/apps.py - Configuração do app restaurantes
# =============================================================================

from django.apps import AppConfig


class RestaurantesConfig(AppConfig):
    """Configuração do app de restaurantes (tenants do sistema SaaS)."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.restaurantes'
    verbose_name = 'Restaurantes'
