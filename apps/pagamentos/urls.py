# =============================================================================
# apps/pagamentos/urls.py - URLs para pagamento (views HTML)
#
# Incluído em config/urls.py como: path('pagamentos/', include(...))
# =============================================================================

from django.urls import path
from . import views

urlpatterns = [
    path('<int:pedido_id>/', views.pagamento_escolher, name='pagamento_escolher'),
    path('confirmar-mock/<int:pagamento_id>/', views.pagamento_confirmar_mock, name='pagamento_confirmar_mock'),
    path('sucesso/<int:pedido_id>/', views.pagamento_sucesso, name='pagamento_sucesso'),
    path('erro/<int:pedido_id>/', views.pagamento_erro, name='pagamento_erro'),
]
