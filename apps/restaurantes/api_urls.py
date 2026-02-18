# =============================================================================
# apps/restaurantes/api_urls.py - Rotas da API REST para restaurantes
#
# Registra o ViewSet no router do DRF.
# Incluído em config/urls.py como: path('api/restaurantes/', include(...))
# =============================================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import RestauranteViewSet

router = DefaultRouter()
router.register('', RestauranteViewSet, basename='restaurante')

urlpatterns = [
    path('', include(router.urls)),
]
