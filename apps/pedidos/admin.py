# =============================================================================
# apps/pedidos/admin.py - Configuração do admin para pedidos
#
# Exibe pedidos com itens inline, filtros por status e restaurante,
# e ações em lote para atualizar status.
# =============================================================================

from django.contrib import admin
from .models import Pedido, ItemPedido


class ItemPedidoInline(admin.TabularInline):
    """Exibe itens do pedido como tabela inline no formulário do pedido."""
    model = ItemPedido
    extra = 0
    readonly_fields = ('subtotal',)
    fields = (
        'produto', 'quantidade', 'preco_unitario',
        'tamanho_nome', 'sabores_descricao', 'observacao', 'subtotal'
    )


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    """
    Admin para pedidos com:
    - Itens inline
    - Filtros por status, restaurante, data e pagamento
    - Ações em lote para atualizar status
    """

    list_display = (
        'id', 'cliente_nome', 'restaurante', 'status',
        'total', 'pago', 'tipo_entrega', 'criado_em'
    )
    list_filter = ('status', 'pago', 'tipo_entrega', 'restaurante', 'criado_em')
    search_fields = ('cliente_nome', 'cliente_telefone', 'cliente_email')
    readonly_fields = ('subtotal', 'taxa_entrega', 'imposto', 'total', 'criado_em', 'atualizado_em')
    inlines = [ItemPedidoInline]
    date_hierarchy = 'criado_em'

    fieldsets = (
        ('Cliente', {
            'fields': ('cliente_nome', 'cliente_telefone', 'cliente_email')
        }),
        ('Pedido', {
            'fields': ('restaurante', 'tipo_entrega', 'endereco_entrega', 'observacoes')
        }),
        ('Valores', {
            'fields': ('subtotal', 'taxa_entrega', 'imposto', 'total')
        }),
        ('Status e Pagamento', {
            'fields': ('status', 'pago', 'external_payment_id')
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    actions = ['marcar_preparo', 'marcar_entrega', 'marcar_concluido']

    @admin.action(description='Marcar como Em Preparo')
    def marcar_preparo(self, request, queryset):
        """Ação em lote: muda status para 'preparo'."""
        queryset.update(status='preparo')

    @admin.action(description='Marcar como Saiu para Entrega')
    def marcar_entrega(self, request, queryset):
        """Ação em lote: muda status para 'entrega'."""
        queryset.update(status='entrega')

    @admin.action(description='Marcar como Concluído')
    def marcar_concluido(self, request, queryset):
        """Ação em lote: muda status para 'concluido'."""
        queryset.update(status='concluido')
