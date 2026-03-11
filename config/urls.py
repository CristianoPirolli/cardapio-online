# =============================================================================
# config/urls.py - Roteamento principal de URLs do projeto Cardápio Online SaaS
#
# Organização:
# - /                  → Página inicial (landing page ou cardápio do restaurante)
# - /api/              → Endpoints REST (DRF)
# - /api/auth/         → Autenticação JWT (obter/renovar token)
# - /admin/            → Painel administrativo do Django
# - /cardapio/         → Views do cardápio público
# - /pedidos/          → Views de pedidos
# - /pagamentos/       → Views de pagamento
# - /painel/           → Painel do restaurante (admin customizado)
# - /auth/             → Login/Logout/Registro
# =============================================================================

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.restaurantes import views as restaurante_views

urlpatterns = [
    # Painel admin nativo do Django
    path('admin/', admin.site.urls),

    # --- API REST ---
    # Autenticação JWT
    # POST /api/auth/token/ → Obtém par de tokens (access + refresh)
    # Exemplo request: {"username": "user", "password": "pass"}
    # Exemplo response: {"access": "eyJ...", "refresh": "eyJ..."}
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain'),

    # POST /api/auth/token/refresh/ → Renova o token de acesso
    # Exemplo request: {"refresh": "eyJ..."}
    # Exemplo response: {"access": "eyJ..."}
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Endpoints REST dos apps
    path('api/restaurantes/', include('apps.restaurantes.api_urls')),
    path('api/estabelecimentos/', include('apps.restaurantes.api_urls')),
    path('api/produtos/', include('apps.produtos.api_urls')),
    path('api/pedidos/', include('apps.pedidos.api_urls')),
    path('api/pagamentos/', include('apps.pagamentos.api_urls')),

    # --- Views HTML (templates) ---
    path('', restaurante_views.home, name='home'),
    path('cardapio/', include('apps.produtos.urls')),
    path('pedidos/', include('apps.pedidos.urls')),
    path('pagamentos/', include('apps.pagamentos.urls')),
    path('painel/', include('apps.restaurantes.urls')),

    # --- Autenticação (login/logout/registro) ---
    path('auth/', include('apps.restaurantes.auth_urls')),
]

# Em desenvolvimento, serve arquivos de media pelo Django
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Customização do admin
admin.site.site_header = 'Cardápio Online - Administração'
admin.site.site_title = 'Cardápio Online Admin'
admin.site.index_title = 'Painel de Administração'
