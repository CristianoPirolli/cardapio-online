# =============================================================================
# apps/produtos/apps.py - Configuração do app produtos
# =============================================================================

from django.apps import AppConfig


class ProdutosConfig(AppConfig):
    """Configuração do app de produtos e categorias."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.produtos'
    verbose_name = 'Produtos'
