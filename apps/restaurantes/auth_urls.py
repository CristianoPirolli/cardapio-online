# =============================================================================
# apps/restaurantes/auth_urls.py - URLs de autenticação (login/logout/registro)
#
# Incluído em config/urls.py como: path('auth/', include(...))
# =============================================================================

from django.urls import path
from . import auth_views

urlpatterns = [
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
    path('registro/', auth_views.registro_view, name='registro'),
]
