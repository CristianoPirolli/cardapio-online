# External Integrations

**Analysis Date:** 2026-04-02

## Payment Gateway — Mercado Pago

**Purpose:** Primary payment processor for the Brazilian market. Supports two payment flows.

**SDK/Client:** `mercadopago==2.3.0` (official Python SDK)

**Implementation:** `apps/pagamentos/services.py`

**Payment methods supported:**
- **Checkout Pro (cartao/card):** Creates a Mercado Pago preference, redirects the customer to MP-hosted checkout page. Returns a `sandbox_init_point` (DEBUG mode) or `init_point` (production) URL.
- **PIX:** Creates a MP payment with `payment_method_id=pix`, returns a `qr_code` string (also usable as "PIX Copia e Cola") and a `qr_code_base64` image for display. Status confirmed via polling endpoint.

**API calls made:**
- `sdk.preference().create(preference_data)` — Checkout Pro card flow
- `sdk.payment().create(payment_data)` — PIX flow
- `sdk.payment().get(payment_id)` — Status polling and webhook confirmation

**Auth:**
- `MP_ACCESS_TOKEN` env var — Set to `TEST-...` for sandbox, `APP_USR-...` for production

**Webhook / IPN:**
- Incoming endpoint: `POST /pagamentos/mp-webhook/` (`apps/pagamentos/views.mp_webhook`)
- CSRF exempt, handles both JSON body (Webhook) and query string (IPN) formats
- Must be registered in Mercado Pago developer panel: `https://www.mercadopago.com.br/developers/panel/app`
- Triggers `processar_webhook_mp()` → `confirmar_pagamento_mp()` → marks order as paid

**Return URLs (MP redirects back to app):**
- Success/pending: `{SITE_URL}/pagamentos/mp-return/{pedido_id}/`
- Failure: `{SITE_URL}/pagamentos/erro/{pedido_id}/`

**Sandbox behavior:**
- When `DEBUG=True`, uses `sandbox_init_point` for card checkout
- `MP_PIX_PAYER_EMAIL` must be set to a valid MP test account email for PIX in sandbox

**Required env vars:**
```
PAYMENT_GATEWAY=mercadopago
MP_ACCESS_TOKEN=TEST-<your-sandbox-token>   # or APP_USR- for production
MP_PIX_PAYER_EMAIL=cliente@seudominio.com.br
SITE_URL=https://yourdomain.com              # Must be publicly reachable for webhook
```

---

## Payment Gateway — Mock (Local Simulation)

**Purpose:** Development-only payment simulation. No external calls.

**Activation:** `PAYMENT_GATEWAY=mock` in `.env`

**Behavior:**
- Generates a fake `mock_pi_<uuid>` payment ID
- Card flow redirects to `GET /pagamentos/<pedido_id>/mock-cartao/` (rendered from `templates/pagamentos/mock_cartao.html`)
- PIX flow goes to `GET /pagamentos/<pedido_id>/pix/` with an `is_mock=True` flag
- Confirmation via `POST /pagamentos/confirmar-mock/<pagamento_id>/` — immediately marks as `aprovado`

**Implementation:** `apps/pagamentos/services._criar_pagamento_mock()`, `apps/pagamentos/services.confirmar_pagamento_mock()`

---

## Data Storage — PostgreSQL

**Provider:** Self-hosted via Docker (image `postgres:15-alpine`)

**ORM:** Django ORM with psycopg3 (`psycopg==3.3.2`)

**Connection:**
```
POSTGRES_DB=cardapio_db
POSTGRES_USER=cardapio_user
POSTGRES_PASSWORD=<secret>
POSTGRES_HOST=db          # Docker service name; use localhost for local dev
POSTGRES_PORT=5432
```

**Volumes:** Persistent via Docker named volume `postgres_data`

**Migrations:** Run automatically on container startup via `python manage.py migrate --noinput` in `docker-compose.yml`

---

## File Storage — Local Filesystem

**Type:** Django default `FileSystemStorage`

**Media uploads:**
- Product images: `media/produtos/`
- Restaurant logos: `media/restaurantes/logos/`
- Served at `/media/` (by Django in DEBUG, by Nginx volume mount in production)

**No cloud file storage** (S3, GCS, etc.) is configured. Uploads are stored on the local container filesystem and shared with Nginx via a Docker named volume (`media_volume`).

---

## Caching — In-Process Dictionary

**Type:** Custom in-memory cache (not Redis, Memcached, or Django's cache framework)

**Implementation:** `apps/core/algorithms.cache_restaurante` — a simple Python object used as a hash table/dict

**Scope:** Per-process, non-shared across Gunicorn workers, does not survive restarts

**Used by:** `config/middleware.TenantMiddleware` to cache tenant (restaurant) lookups by subdomain

**Key pattern:** `"tenant:{subdominio}"` → `Restaurante` model instance or `False` (for cache miss)

---

## Authentication & Identity

**Provider:** Django built-in auth (`django.contrib.auth`)

**Browser sessions:** Standard Django session middleware (`SESSION_COOKIE_SECURE` set based on `SECURE_SSL_REDIRECT`)

**API tokens:** JWT via `djangorestframework_simplejwt 5.5.1`
- Access token lifetime: 1 hour
- Refresh token lifetime: 7 days
- Rotation: enabled (`ROTATE_REFRESH_TOKENS=True`)
- Endpoints: `POST /api/auth/token/` and `POST /api/auth/token/refresh/`

**Authorization model:** Restaurant owners are Django `User` objects with a `OneToOneField` to `Restaurante`. Customers order without authentication.

---

## Email (Optional / Not Active)

**Config defined in `.env.example` but not referenced in `config/settings.py`:**
```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu-email@gmail.com
EMAIL_HOST_PASSWORD=sua-senha-de-app
```

No email sending is observed in app code (no `send_mail` or similar calls found). The configuration is scaffolded but not wired up.

---

## Web Server & Proxy

**Application server:** Gunicorn 25.1.0 (WSGI)
- Bind: `0.0.0.0:8000`
- Workers: 3
- Timeout: 120s

**Reverse proxy:** Nginx 1.25-alpine
- Config: `nginx/nginx.conf`
- Listens on port `${NGINX_PORT:-8081}` (mapped to container port 80)
- Serves `/static/` and `/media/` directly from Docker volumes
- Proxies all other traffic to Gunicorn at `http://web:8000`
- Supports wildcard subdomains: `*.meusistema.com` for multi-tenancy
- HTTPS block present but commented out; Certbot integration scaffolded at `nginx/certbot/`

---

## Multi-Tenant Routing

**Mechanism:** Subdomain-based tenant identification via `config/middleware.TenantMiddleware`

**How it works:**
1. Reads `HTTP_HOST` from the request
2. Strips `BASE_DOMAIN` suffix to extract subdomain
3. Looks up active `Restaurante` with matching `subdominio` field (cached in-process)
4. Sets `request.restaurante` and `request.estabelecimento` for downstream views

**Dev override:** In `DEBUG=True`, the subdomain can be passed as a query parameter: `?estabelecimento=<subdominio>` or `?restaurante=<subdominio>`

**Required env vars:**
```
BASE_DOMAIN=meusistema.com
SITE_URL=https://meusistema.com
```

---

## CORS

**Library:** `django-cors-headers==4.9.0`

**Development:** `CORS_ALLOW_ALL_ORIGINS=True` (when `DEBUG=True`)

**Production:** Only `https://meusistema.com` is in `CORS_ALLOWED_ORIGINS`

---

## Security / HTTPS

**HSTS:** Configured via env vars (`SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`) — defaults to disabled

**SSL redirect:** `SECURE_SSL_REDIRECT` env var — defaults to disabled

**Session/CSRF cookie security:** Enabled only when `SECURE_SSL_REDIRECT=True`

**CSRF trusted origins:** Configurable via `CSRF_TRUSTED_ORIGINS` env var; localhost variants auto-added in DEBUG mode

---

## Summary of All Required Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | Yes | Django cryptographic key |
| `DEBUG` | Yes | Development mode toggle |
| `ALLOWED_HOSTS` | Yes | Django ALLOWED_HOSTS |
| `CSRF_TRUSTED_ORIGINS` | Prod | CSRF validation for proxied origins |
| `POSTGRES_DB` | Yes | Database name |
| `POSTGRES_USER` | Yes | Database user |
| `POSTGRES_PASSWORD` | Yes | Database password |
| `POSTGRES_HOST` | Yes | Database host (`db` in Docker, `localhost` locally) |
| `POSTGRES_PORT` | No | Database port (default: 5432) |
| `PAYMENT_GATEWAY` | Yes | `mercadopago` or `mock` |
| `MP_ACCESS_TOKEN` | If MP | Mercado Pago API token |
| `MP_PIX_PAYER_EMAIL` | If MP+PIX | Payer email required by MP PIX API |
| `BASE_DOMAIN` | Yes | Root domain for subdomain routing |
| `SITE_URL` | Yes | Public base URL (used for MP webhook/return URLs) |
| `NGINX_PORT` | No | Host port for Nginx (default: 8081) |
| `SECURE_HSTS_SECONDS` | Prod | HSTS max-age (default: 0 = disabled) |
| `SECURE_SSL_REDIRECT` | Prod | Force HTTPS redirect (default: False) |

---

*Integration audit: 2026-04-02*
