# =============================================================================
# apps/pagamentos/apps.py - Configuração do app pagamentos
# =============================================================================

from django.apps import AppConfig


class PagamentosConfig(AppConfig):
    """Configuração do app de pagamentos (Mercado Pago e mock)."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.pagamentos'
    verbose_name = 'Pagamentos'
