# =============================================================================
# config/settings.py - Configurações principais do projeto Cardápio Online SaaS
#
# Este arquivo centraliza todas as configurações do Django, incluindo:
# - Banco de dados PostgreSQL
# - Apps instalados (restaurantes, produtos, pedidos, pagamentos, entregas)
# - Django REST Framework com autenticação JWT
# - Configurações de arquivos estáticos e media
# - Integração com Stripe
# - Middleware multi-tenant por subdomínio
# =============================================================================

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

# Diretório base do projeto (um nível acima de config/)
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Segurança
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-TROQUE-ESTA-CHAVE')
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if host.strip()
]
if DEBUG and '*' not in ALLOWED_HOSTS:
    # Em desenvolvimento local, permite acesso via IP da LAN (ex.: 192.168.x.x).
    ALLOWED_HOSTS.append('*')

# Origens confiáveis para validação CSRF (relevante atrás de proxy/porta diferente).
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]
if DEBUG:
    for origin in (
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'http://localhost:8080',
        'http://127.0.0.1:8080',
        'http://localhost:8081',
        'http://127.0.0.1:8081',
    ):
        if origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)

# ---------------------------------------------------------------------------
# Aplicações instaladas
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    # Apps do Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Bibliotecas de terceiros
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'corsheaders',
    'crispy_forms',
    'crispy_bootstrap5',

    # Apps do projeto
    'apps.restaurantes',
    'apps.produtos',
    'apps.pedidos',
    'apps.pagamentos',
]

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Middleware customizado para identificar o restaurante pelo subdomínio
    'config.middleware.TenantMiddleware',
    # HTMX: converte redirects 302 em HX-Redirect para navegação SPA-like
    'config.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Context processor customizado para dados do estabelecimento
                'config.context_processors.estabelecimento_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ---------------------------------------------------------------------------
# Banco de dados PostgreSQL
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'cardapio_db'),
        'USER': os.getenv('POSTGRES_USER', 'cardapio_user'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'cardapio_pass_dev'),
        'HOST': os.getenv('POSTGRES_HOST', 'db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

# ---------------------------------------------------------------------------
# Validação de senhas
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Internacionalização
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Arquivos estáticos (CSS, JS, imagens do tema)
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise para servir estáticos em produção sem Nginx
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# ---------------------------------------------------------------------------
# Arquivos de media (uploads de imagens de produtos)
# ---------------------------------------------------------------------------
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------------------------------------------------------
# Chave primária padrão
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ---------------------------------------------------------------------------
# Simple JWT (tokens de autenticação)
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ---------------------------------------------------------------------------
# CORS (Cross-Origin Resource Sharing)
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    'https://meusistema.com',
]

# ---------------------------------------------------------------------------
# Crispy Forms (formulários bonitos com Bootstrap 5)
# ---------------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# ---------------------------------------------------------------------------
# PIX Manual
# ---------------------------------------------------------------------------
# Chave PIX fixa do estabelecimento (CNPJ, CPF, email, telefone ou chave aleatória)
PIX_KEY = os.getenv('PIX_KEY', '')

# ---------------------------------------------------------------------------
# Multi-tenant
# ---------------------------------------------------------------------------
BASE_DOMAIN = os.getenv('BASE_DOMAIN', 'localhost')
SITE_URL = os.getenv('SITE_URL', 'http://localhost')

# ---------------------------------------------------------------------------
# Segurança extra para produção
# ---------------------------------------------------------------------------
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", 0))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False") == "True"
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "False") == "True"
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False") == "True"

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

    SESSION_COOKIE_SECURE = SECURE_SSL_REDIRECT
    CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT

# ---------------------------------------------------------------------------
# Login/Logout URLs
# ---------------------------------------------------------------------------
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/painel/'
LOGOUT_REDIRECT_URL = '/'
