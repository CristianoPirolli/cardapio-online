# =============================================================================
# apps/restaurantes/urls.py - URLs do painel do restaurante (views HTML)
#
# Incluído em config/urls.py como: path('painel/', include(...))
# =============================================================================

from django.urls import path
from . import views

urlpatterns = [
    # Dashboard principal do painel
    path('', views.painel_dashboard, name='painel_dashboard'),
    # Configurações do restaurante
    path('configuracoes/', views.painel_configuracoes, name='painel_configuracoes'),
    # Configurações específicas de pizzas
    path('pizzas/', views.painel_pizzas, name='painel_pizzas'),
    # Lista de pedidos no painel
    path('pedidos/', views.painel_pedidos, name='painel_pedidos'),
    # Contador de pedidos em aberto (notificação do menu)
    path('pedidos/abertos/count/', views.painel_pedidos_abertos_count, name='painel_pedidos_abertos_count'),
    # Detalhe de pedido no painel
    path('pedidos/<int:pedido_id>/', views.painel_pedido_detalhe, name='painel_pedido_detalhe'),
]
