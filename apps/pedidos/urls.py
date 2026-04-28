# =============================================================================
# apps/pedidos/urls.py - URLs para carrinho e pedidos (views HTML)
#
# Incluído em config/urls.py como: path('pedidos/', include(...))
# =============================================================================

from django.urls import path
from . import views

urlpatterns = [
    # Carrinho
    path('carrinho/', views.ver_carrinho, name='ver_carrinho'),
    path('carrinho/adicionar/', views.adicionar_ao_carrinho, name='adicionar_ao_carrinho'),
    path('carrinho/remover/', views.remover_do_carrinho, name='remover_do_carrinho'),
    path('carrinho/atualizar/', views.atualizar_carrinho, name='atualizar_carrinho'),
    path('upsell-bebidas/', views.upsell_bebidas, name='upsell_bebidas'),

    # Checkout
    path('checkout/', views.checkout, name='checkout'),

    # Reverse geocoding (Nominatim proxy com cache)
    path('api/geocode/', views.geocode, name='geocode'),

    # Acompanhamento
    path('<int:pedido_id>/acompanhar/', views.acompanhar_pedido, name='acompanhar_pedido'),
    path('<int:pedido_id>/status/', views.acompanhar_pedido_status, name='acompanhar_pedido_status'),
    path('<int:pedido_id>/concluir/', views.concluir_pedido_cliente, name='concluir_pedido_cliente'),
]
