# =============================================================================
# apps/entregas/api_urls.py - Rotas da API REST para entregas e entregadores
#
# Incluído em config/urls.py como: path('api/entregas/', include(...))
# =============================================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import EntregadorViewSet, EntregaViewSet

router = DefaultRouter()
router.register('entregadores', EntregadorViewSet, basename='entregador')
router.register('', EntregaViewSet, basename='entrega')

urlpatterns = [
    path('', include(router.urls)),
]
