# =============================================================================
# apps/produtos/api_urls.py - Rotas da API REST para produtos e categorias
#
# Incluído em config/urls.py como: path('api/produtos/', include(...))
# =============================================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import CategoriaViewSet, ProdutoViewSet

router = DefaultRouter()
router.register('categorias', CategoriaViewSet, basename='categoria')
router.register('', ProdutoViewSet, basename='produto')

urlpatterns = [
    path('', include(router.urls)),
]
