# =============================================================================
# apps/pagamentos/admin.py - Configuração do admin para pagamentos
# =============================================================================

from django.contrib import admin
from .models import Pagamento


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    """Admin para registros de pagamento."""

    list_display = ('id', 'pedido', 'gateway', 'valor', 'status', 'criado_em')
    list_filter = ('gateway', 'status', 'criado_em')
    search_fields = ('pedido__cliente_nome', 'stripe_payment_intent_id')
    readonly_fields = ('criado_em', 'atualizado_em', 'dados_resposta')

    fieldsets = (
        ('Pedido', {
            'fields': ('pedido',)
        }),
        ('Pagamento', {
            'fields': ('gateway', 'valor', 'status', 'stripe_payment_intent_id')
        }),
        ('Dados do Gateway', {
            'fields': ('dados_resposta',),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )
