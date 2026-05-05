# =============================================================================
# apps/pedidos/api_urls.py - Rotas da API REST para pedidos
#
# Incluído em config/urls.py como: path('api/pedidos/', include(...))
# =============================================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api_views import PedidoViewSet
from .push_views import push_subscribe

router = DefaultRouter()
router.register('', PedidoViewSet, basename='pedido')

urlpatterns = [
    path('push/subscribe/', push_subscribe, name='push_subscribe'),
    path('', include(router.urls)),
]
