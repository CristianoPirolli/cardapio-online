# =============================================================================
# apps/pagamentos/api_urls.py - Rotas da API REST para pagamentos
#
# Incluído em config/urls.py como: path('api/pagamentos/', include(...))
# =============================================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import PagamentoViewSet, criar_pagamento_api

router = DefaultRouter()
router.register('', PagamentoViewSet, basename='pagamento')

urlpatterns = [
    path('criar/', criar_pagamento_api, name='api_criar_pagamento'),
    path('', include(router.urls)),
]
