# Codebase Structure

**Analysis Date:** 2026-04-02

## Directory Layout

```
cardapio-online/
├── apps/                        # All Django applications
│   ├── core/                    # Shared algorithms and utilities (no models/views)
│   ├── restaurantes/            # Tenant root: restaurants, auth, painel
│   ├── produtos/                # Product catalog: categories and products
│   ├── pedidos/                 # Cart, checkout, and order management
│   └── pagamentos/              # Payment gateway abstraction
├── config/                      # Django project configuration
│   ├── settings.py              # Central settings (all envs)
│   ├── urls.py                  # Root URL configuration
│   ├── middleware.py            # TenantMiddleware + HtmxMiddleware
│   ├── context_processors.py    # Template context globals
│   ├── wsgi.py                  # WSGI entry point
│   └── asgi.py                  # ASGI entry point (if present)
├── templates/                   # All HTML templates (global)
│   ├── base.html                # Root base template
│   ├── home.html                # Landing page
│   ├── auth/                    # Login/registro templates
│   ├── painel/                  # Operator dashboard templates
│   ├── pedidos/                 # Cart and checkout templates
│   ├── produtos/                # Public cardápio templates
│   ├── pagamentos/              # Payment flow templates
│   └── partials/                # HTMX partial templates
├── static/                      # Source static files (committed)
│   ├── css/                     # Custom stylesheets
│   ├── js/                      # Custom JavaScript
│   ├── img/                     # Images
│   └── vendor/                  # Third-party libraries (Bootstrap etc.)
├── staticfiles/                 # Collected static files (generated, not committed)
├── media/                       # User-uploaded files (not committed)
│   ├── produtos/                # Product images
│   └── restaurantes/logos/      # Restaurant logo uploads
├── nginx/                       # Nginx reverse-proxy config
│   ├── nginx.conf               # Nginx configuration
│   └── certbot/                 # SSL certificate management
├── services/                    # Supporting services (e.g., go-notify)
├── manage.py                    # Django management entry point
├── Dockerfile                   # Multi-stage Docker image (Python 3.11-slim)
├── docker-compose.yml           # Local dev orchestration
├── requirements.txt             # Python dependencies
├── gunicorn.ctl                 # Gunicorn supervisor config
└── .env.example                 # Environment variable template
```

## Django App Internal Structure

Every app follows this consistent layout:

```
apps/<appname>/
├── __init__.py
├── apps.py                  # AppConfig
├── models.py                # Data models
├── views.py                 # HTML views (template rendering)
├── urls.py                  # HTML URL patterns (included under prefix)
├── api_views.py             # DRF ViewSets for REST API
├── api_urls.py              # REST URL patterns (included under /api/)
├── serializers.py           # DRF serializers
├── admin.py                 # Django admin registrations
├── services.py              # Business logic layer (pedidos, pagamentos)
├── forms.py                 # Django forms (restaurantes, produtos)
├── migrations/              # Database migrations
└── tests/                   # Test suite
```

**Exceptions to the pattern:**
- `apps/core/`: only `algorithms.py` — no models, views, urls, or admin.
- `apps/restaurantes/`: additionally has `auth_views.py` and `auth_urls.py` for the login/logout flow.

## Key File Locations

**Entry Points:**
- `manage.py`: Django CLI entry point
- `config/wsgi.py`: WSGI application (used by Gunicorn in production)
- `config/urls.py`: Root URL dispatcher — all URL prefixes defined here

**Configuration:**
- `config/settings.py`: All Django settings; reads env vars via `os.getenv()`
- `.env.example`: Documents required environment variables
- `docker-compose.yml`: Local development service orchestration
- `Dockerfile`: Production container definition
- `nginx/nginx.conf`: Reverse proxy and SSL termination config

**Core Business Logic:**
- `apps/core/algorithms.py`: `HashCache`, BFS status graph, binary search, memoized subtotal
- `apps/pedidos/services.py`: Cart assembly (`montar_resumo_carrinho`), order creation (`criar_pedido_do_carrinho`), checkout validation
- `apps/pagamentos/services.py`: Gateway abstraction (`criar_pagamento`, `confirmar_pagamento_mp`, `processar_webhook_mp`)

**Data Models:**
- `apps/restaurantes/models.py`: `Restaurante`, `TamanhoPizza`
- `apps/produtos/models.py`: `Categoria`, `Produto`, `ProdutoTamanho`
- `apps/pedidos/models.py`: `Pedido`, `ItemPedido`
- `apps/pagamentos/models.py`: `Pagamento`

**Middleware and Context:**
- `config/middleware.py`: `TenantMiddleware`, `HtmxMiddleware`
- `config/context_processors.py`: `estabelecimento_context` — injects tenant, cart count, open orders count

**Templates:**
- `templates/base.html`: Root layout, extended by all pages
- `templates/painel/base_painel.html`: Painel-specific layout extending `base.html`
- `templates/pagamentos/pagamento.html`: Payment method selection
- `templates/pagamentos/pix.html`: PIX QR code display with polling
- `templates/pagamentos/mock_cartao.html`: Mock card checkout simulation

**Testing:**
- `apps/pedidos/tests/`: Order and cart tests
- `apps/pagamentos/tests/`: Payment flow tests

## Template Organization

Templates live in `templates/` at the project root (configured in `settings.py` as `BASE_DIR / 'templates'`). Apps do NOT have their own `templates/` subdirectories — all templates are centralized.

**Template → View mapping:**
| Template Path | Rendered By |
|---|---|
| `templates/home.html` | `restaurantes.views.home` |
| `templates/auth/login.html` | `restaurantes.auth_views.login_view` |
| `templates/painel/dashboard.html` | `restaurantes.views.painel_dashboard` |
| `templates/painel/pedidos.html` | `restaurantes.views.painel_pedidos` |
| `templates/painel/pedido_detalhe.html` | `restaurantes.views.painel_pedido_detalhe` |
| `templates/painel/configuracoes.html` | `restaurantes.views.painel_configuracoes` |
| `templates/painel/pizzas.html` | `restaurantes.views.painel_pizzas` |
| `templates/painel/produtos.html` | `produtos.views.painel_produtos` |
| `templates/painel/produto_form.html` | `produtos.views.painel_produto_criar/editar` |
| `templates/painel/categorias.html` | `produtos.views.painel_categorias` |
| `templates/painel/categoria_form.html` | `produtos.views.painel_categoria_criar/editar` |
| `templates/produtos/cardapio.html` | `produtos.views.cardapio_publico` |
| `templates/produtos/produto_detalhe.html` | `produtos.views.produto_detalhe` |
| `templates/pedidos/carrinho.html` | `pedidos.views.ver_carrinho` |
| `templates/pedidos/checkout.html` | `pedidos.views.checkout` |
| `templates/pedidos/acompanhar.html` | `pedidos.views.acompanhar_pedido` |
| `templates/pagamentos/pagamento.html` | `pagamentos.views.pagamento_escolher` |
| `templates/pagamentos/pix.html` | `pagamentos.views.pagamento_pix` |
| `templates/pagamentos/mock_cartao.html` | `pagamentos.views.mock_cartao_checkout` |
| `templates/pagamentos/sucesso.html` | `pagamentos.views.pagamento_sucesso` |
| `templates/pagamentos/erro.html` | `pagamentos.views.pagamento_erro` |

## Static Files

**Source:** `static/` — committed to git
- `static/css/`: Custom CSS
- `static/js/`: Custom JavaScript (includes HTMX interactions and PIX polling)
- `static/img/`: Images
- `static/vendor/`: Third-party assets (Bootstrap 5, etc.)

**Collected:** `staticfiles/` — generated by `python manage.py collectstatic`, not committed
- Served by WhiteNoise in production (`whitenoise.storage.CompressedManifestStaticFilesStorage`)
- WhiteNoise is injected as middleware (`whitenoise.middleware.WhiteNoiseMiddleware`) so static files are served directly without Nginx needing to handle them

## Media Files

**Location:** `media/` — not committed (user uploads)
- `media/produtos/`: Product photos (uploaded via `Produto.imagem`)
- `media/restaurantes/logos/`: Restaurant logos (uploaded via `Restaurante.logo`)
- In development: served by Django when `DEBUG=True` (configured in `config/urls.py`)
- In production: should be served by Nginx or object storage (not currently abstracted)

## Naming Conventions

**Files:**
- Snake_case for all Python files: `auth_views.py`, `api_urls.py`, `context_processors.py`
- Template filenames mirror their purpose: `pagamento.html`, `pix.html`, `mock_cartao.html`

**Directories:**
- App directories: lowercase plural noun (`restaurantes`, `produtos`, `pedidos`, `pagamentos`)
- Template subdirectories match app names or functional areas (`painel/`, `auth/`, `partials/`)

**Python identifiers:**
- Models: PascalCase (`Restaurante`, `ItemPedido`, `TamanhoPizza`)
- Functions/views: snake_case (`criar_pagamento`, `painel_pedidos`, `cardapio_publico`)
- URL names: snake_case (`painel_dashboard`, `pagamento_escolher`, `mp_webhook`)
- Portuguese throughout: models, field names, view names, URL names, templates

## Where to Add New Code

**New Django app:**
- Create under `apps/<nome>/` following the standard internal structure above
- Register in `INSTALLED_APPS` in `config/settings.py` as `'apps.<nome>'`
- Add HTML URLs in `config/urls.py` under an appropriate prefix
- Add API URLs in `config/urls.py` under `/api/<nome>/`

**New HTML view:**
- Add function to the relevant app's `views.py`
- Add URL pattern to the app's `urls.py`
- Add template to `templates/<appname>/<template>.html`

**New API endpoint:**
- Add action to the relevant app's `api_views.py` (ViewSet action or standalone `@api_view`)
- Add URL to the app's `api_urls.py`

**New model:**
- Add to the relevant app's `models.py`
- Run `python manage.py makemigrations <appname>` and `python manage.py migrate`
- Register in `apps/<appname>/admin.py`

**New business logic:**
- Place in `apps/<appname>/services.py` (not in views)
- Shared algorithms/data structures belong in `apps/core/algorithms.py`

**New template partial (HTMX):**
- Add to `templates/partials/`

**New static asset:**
- Add to `static/css/`, `static/js/`, or `static/img/` as appropriate

## Special Directories

**`staticfiles/`:**
- Purpose: WhiteNoise-served collected static assets
- Generated: Yes (`python manage.py collectstatic`)
- Committed: No

**`media/`:**
- Purpose: User-uploaded files (product images, logos)
- Generated: Yes (by Django file upload handling)
- Committed: No

**`venv/`:**
- Purpose: Python virtual environment
- Generated: Yes
- Committed: No

**`.planning/`:**
- Purpose: GSD planning documents and codebase analysis
- Generated: Yes (by GSD tooling)
- Committed: Yes (planning artifacts)

**`nginx/certbot/`:**
- Purpose: SSL certificate management for production HTTPS
- Generated: Yes (by certbot)
- Committed: Partially (config only, not certs)

---

*Structure analysis: 2026-04-02*
