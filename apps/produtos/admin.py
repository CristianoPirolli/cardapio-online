# =============================================================================
# apps/produtos/admin.py - Configuração do admin para produtos e categorias
#
# Interface administrativa para gestão de produtos com filtros,
# busca, edição em massa e preview de imagem.
# =============================================================================

from django.contrib import admin
from django.utils.html import format_html
from .models import Categoria, Produto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    """Admin para categorias de produtos."""

    list_display = ('nome', 'restaurante', 'ordem', 'adicional_sabor', 'ativo')
    list_filter = ('restaurante', 'ativo')
    search_fields = ('nome',)
    list_editable = ('ordem', 'adicional_sabor', 'ativo')


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    """
    Admin para produtos com:
    - Preview de imagem inline
    - Filtros por categoria, restaurante e disponibilidade
    - Busca por nome e descrição
    - Edição rápida de preço e disponibilidade
    """

    list_display = (
        'nome', 'preview_imagem', 'categoria', 'restaurante',
        'preco', 'disponivel', 'destaque'
    )
    list_filter = ('restaurante', 'categoria', 'disponivel', 'destaque')
    search_fields = ('nome', 'descricao')
    list_editable = ('preco', 'disponivel', 'destaque')
    readonly_fields = ('criado_em', 'atualizado_em', 'preview_imagem_grande')

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('restaurante', 'categoria', 'nome', 'descricao', 'preco')
        }),
        ('Imagem', {
            'fields': ('imagem', 'preview_imagem_grande')
        }),
        ('Configurações', {
            'fields': ('disponivel', 'destaque')
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    def preview_imagem(self, obj):
        """Exibe thumbnail da imagem na listagem do admin."""
        if obj.imagem:
            return format_html(
                '<img src="{}" style="width:50px;height:50px;object-fit:cover;border-radius:4px;" />',
                obj.imagem.url
            )
        return '—'
    preview_imagem.short_description = 'Imagem'

    def preview_imagem_grande(self, obj):
        """Exibe imagem maior no formulário de edição."""
        if obj.imagem:
            return format_html(
                '<img src="{}" style="max-width:300px;max-height:300px;border-radius:8px;" />',
                obj.imagem.url
            )
        return 'Sem imagem'
    preview_imagem_grande.short_description = 'Preview'
