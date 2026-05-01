# =============================================================================
# apps/pedidos/apps.py - Configuração do app pedidos
# =============================================================================

from django.apps import AppConfig


class PedidosConfig(AppConfig):
    """Configuração do app de pedidos e carrinho de compras."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.pedidos'
    verbose_name = 'Pedidos'

    def ready(self):
        """Registra signals quando a app está pronta."""
        import apps.pedidos.signals
