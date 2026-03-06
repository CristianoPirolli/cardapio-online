# =============================================================================
# apps/pagamentos/api_urls.py - Rotas da API REST para pagamentos
#
# Incluído em config/urls.py como: path('api/pagamentos/', include(...))
# =============================================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import PagamentoViewSet, criar_pagamento_api, pix_webhook

router = DefaultRouter()
router.register('', PagamentoViewSet, basename='pagamento')

urlpatterns = [
    # Criar pagamento para um pedido
    path('criar/', criar_pagamento_api, name='api_criar_pagamento'),
    # Webhook PIX (Banco do Brasil)
    path('webhook/', pix_webhook, name='pix_webhook'),
    # CRUD (somente leitura)
    path('', include(router.urls)),
]
