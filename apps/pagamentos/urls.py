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
    path('painel/chaves-pix/criar/', views.painel_pix_keys_create, name='painel_pix_keys_create'),
    path('painel/chaves-pix/<int:chave_id>/editar/', views.painel_pix_keys_edit, name='painel_pix_keys_edit'),
    path('painel/chaves-pix/<int:chave_id>/ativar/', views.painel_pix_keys_activate, name='painel_pix_keys_activate'),
    path('painel/chaves-pix/<int:chave_id>/desativar/', views.painel_pix_keys_deactivate, name='painel_pix_keys_deactivate'),
    path('painel/chaves-pix/<int:chave_id>/padrao/', views.painel_pix_keys_set_default, name='painel_pix_keys_set_default'),
    path('painel/chaves-pix/<int:chave_id>/prioridade/', views.painel_pix_keys_set_priority, name='painel_pix_keys_set_priority'),
]
