# =============================================================================
# apps/produtos/urls.py - URLs para cardápio público e gestão de produtos
#
# Incluído em config/urls.py como: path('cardapio/', include(...))
# =============================================================================

from django.urls import path
from . import views

urlpatterns = [
    # Cardápio público
    path('', views.cardapio_publico, name='cardapio_publico'),
    path('produto/<int:produto_id>/', views.produto_detalhe, name='produto_detalhe'),

    # Painel - Categorias
    path('painel/categorias/', views.painel_categorias, name='painel_categorias'),
    path('painel/categorias/criar/', views.painel_categoria_criar, name='painel_categoria_criar'),
    path('painel/categorias/<int:categoria_id>/editar/', views.painel_categoria_editar, name='painel_categoria_editar'),
    path('painel/categorias/<int:categoria_id>/excluir/', views.painel_categoria_excluir, name='painel_categoria_excluir'),

    # Painel - Produtos
    path('painel/produtos/', views.painel_produtos, name='painel_produtos'),
    path('painel/produtos/criar/', views.painel_produto_criar, name='painel_produto_criar'),
    path('painel/produtos/<int:produto_id>/editar/', views.painel_produto_editar, name='painel_produto_editar'),
    path('painel/produtos/<int:produto_id>/excluir/', views.painel_produto_excluir, name='painel_produto_excluir'),
]
