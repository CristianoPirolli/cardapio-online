# =============================================================================
# apps/pagamentos/urls.py - URLs para pagamento PIX Manual
# =============================================================================

from django.urls import path
from . import views

urlpatterns = [
    path('<int:pedido_id>/', views.pagamento_pix_manual, name='pagamento_pix_manual'),
    path('<int:pedido_id>/upload/', views.upload_comprovante, name='upload_comprovante'),
    path('sucesso/<int:pedido_id>/', views.pagamento_sucesso, name='pagamento_sucesso'),
    path('erro/<int:pedido_id>/', views.pagamento_erro, name='pagamento_erro'),
    path('<int:pedido_id>/aceitar/', views.aceitar_pix, name='aceitar_pix'),
    path('<int:pedido_id>/rejeitar/', views.rejeitar_pix, name='rejeitar_pix'),
]
