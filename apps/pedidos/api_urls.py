# =============================================================================
# apps/pedidos/api_urls.py - Rotas da API REST para pedidos
#
# Incluído em config/urls.py como: path('api/pedidos/', include(...))
# =============================================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import PedidoViewSet

router = DefaultRouter()
router.register('', PedidoViewSet, basename='pedido')

urlpatterns = [
    path('', include(router.urls)),
]
