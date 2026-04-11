# =============================================================================
# apps/restaurantes/admin.py - Configuração do admin para restaurantes
#
# Customiza a interface do Django Admin para gestão de restaurantes.
# Inclui filtros, busca, e organização em fieldsets.
# =============================================================================

from django.contrib import admin
from .models import Restaurante, TamanhoPizza, ZonaEntrega


class TamanhoPizzaInline(admin.TabularInline):
    model = TamanhoPizza
    extra = 1
    fields = ('nome', 'fatias', 'diametro_cm', 'max_sabores', 'preco_base', 'ordem', 'ativo')


class ZonaEntregaInline(admin.TabularInline):
    model = ZonaEntrega
    extra = 1
    fields = ('nome', 'raio_max_km', 'taxa_entrega', 'ativo')
    ordering = ('raio_max_km',)


@admin.register(Restaurante)
class RestauranteAdmin(admin.ModelAdmin):
    """
    Admin customizado para o model Restaurante.

    Funcionalidades:
    - Lista com colunas relevantes e filtros por status/cidade
    - Busca por nome, subdomínio e email
    - Fieldsets organizados por categoria
    - Campos read-only para timestamps
    """

    list_display = (
        'nome', 'subdominio', 'cidade', 'estado',
        'taxa_entrega', 'ativo', 'criado_em'
    )
    list_filter = ('ativo', 'estado', 'cidade')
    search_fields = ('nome', 'subdominio', 'email', 'endereco')
    list_editable = ('ativo',)
    prepopulated_fields = {'subdominio': ('nome',)}
    readonly_fields = ('criado_em', 'atualizado_em')
    inlines = [TamanhoPizzaInline, ZonaEntregaInline]

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'subdominio', 'proprietario', 'descricao', 'logo')
        }),
        ('Localização', {
            'fields': ('endereco', 'cidade', 'estado', 'cep', 'latitude', 'longitude'),
            'description': 'As coordenadas (latitude/longitude) são necessárias para calcular zonas de entrega por raio. '
                           'Você pode obtê-las no Google Maps clicando com o botão direito sobre o endereço do restaurante.'
        }),
        ('Contato', {
            'fields': ('telefone', 'email')
        }),
        ('Configurações de Entrega', {
            'fields': ('taxa_entrega', 'pedido_minimo', 'raio_entrega_km')
        }),
        ('Configurações Fiscais', {
            'fields': ('taxa_imposto',)
        }),
        ('Funcionamento', {
            'fields': (
                'funciona_segunda', 'funciona_terca', 'funciona_quarta',
                'funciona_quinta', 'funciona_sexta', 'funciona_sabado', 'funciona_domingo',
                'horario_abertura', 'horario_fechamento', 'ativo'
            )
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )
