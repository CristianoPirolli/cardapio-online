# =============================================================================
# apps/pagamentos/urls.py - URLs para pagamento (views HTML)
#
# Incluido em config/urls.py como: path('pagamentos/', include(...))
# =============================================================================

from django.urls import path

from . import views

urlpatterns = [
    path('<int:pedido_id>/', views.pagamento_escolher, name='pagamento_escolher'),
    path('<int:pedido_id>/pix/', views.pagamento_pix, name='pagamento_pix'),
    path('verificar/<int:pagamento_id>/', views.verificar_status_pagamento, name='verificar_status_pagamento'),
    path('<int:pedido_id>/mock-cartao/', views.mock_cartao_checkout, name='mock_cartao_checkout'),
    path('confirmar-mock/<int:pagamento_id>/', views.pagamento_confirmar_mock, name='pagamento_confirmar_mock'),
    path('sucesso/<int:pedido_id>/', views.pagamento_sucesso, name='pagamento_sucesso'),
    path('erro/<int:pedido_id>/', views.pagamento_erro, name='pagamento_erro'),
]
