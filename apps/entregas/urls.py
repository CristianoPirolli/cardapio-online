# =============================================================================
# apps/entregas/urls.py - URLs para gestão de entregas (views HTML)
#
# Incluído em config/urls.py como: path('entregas/', include(...))
# =============================================================================

from django.urls import path
from . import views

urlpatterns = [
    # Painel do entregador
    path('minhas/', views.entregador_entregas, name='entregador_entregas'),

    # Entregas
    path('painel/', views.painel_entregas, name='painel_entregas'),
    path('painel/atribuir/<int:entrega_id>/', views.atribuir_entregador, name='atribuir_entregador'),
    path('painel/entregas/<int:entrega_id>/status/', views.atualizar_status_entrega, name='atualizar_status_entrega'),

    # Entregadores CRUD
    path('painel/entregadores/', views.painel_entregadores, name='painel_entregadores'),
    path('painel/entregadores/criar/', views.painel_entregador_criar, name='painel_entregador_criar'),
    path('painel/entregadores/<int:entregador_id>/editar/', views.painel_entregador_editar, name='painel_entregador_editar'),
    path('painel/entregadores/<int:entregador_id>/excluir/', views.painel_entregador_excluir, name='painel_entregador_excluir'),
]
