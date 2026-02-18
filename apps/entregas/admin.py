# =============================================================================
# apps/entregas/admin.py - Configuração do admin para entregas e entregadores
# =============================================================================

from django.contrib import admin
from .models import Entregador, Entrega


@admin.register(Entregador)
class EntregadorAdmin(admin.ModelAdmin):
    """Admin para entregadores."""

    list_display = ('nome', 'restaurante', 'telefone', 'veiculo', 'disponivel', 'ativo')
    list_filter = ('restaurante', 'veiculo', 'disponivel', 'ativo')
    search_fields = ('nome', 'telefone')
    list_editable = ('disponivel', 'ativo')


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    """Admin para entregas com filtros por status e entregador."""

    list_display = ('id', 'pedido', 'entregador', 'status', 'saiu_em', 'entregue_em')
    list_filter = ('status', 'entregador', 'criado_em')
    search_fields = ('pedido__cliente_nome', 'entregador__nome')
    readonly_fields = ('criado_em', 'atualizado_em')

    fieldsets = (
        ('Pedido', {
            'fields': ('pedido',)
        }),
        ('Entrega', {
            'fields': ('entregador', 'status', 'observacoes')
        }),
        ('Timestamps', {
            'fields': ('saiu_em', 'entregue_em', 'criado_em', 'atualizado_em')
        }),
    )
