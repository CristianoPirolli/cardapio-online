# Technology Stack

**Analysis Date:** 2026-04-02

## Languages

**Primary:**
- Python 3.12.10 — All backend logic, Django application, services, models
  - Runtime: CPython (local venv at `venv/`)
  - Docker container uses Python 3.11 (Dockerfile: `python:3.11-slim-bookworm`)

**Secondary:**
- JavaScript (ES6, no build step) — Frontend interactivity via HTMX and vanilla JS
- HTML/Jinja2 (Django Templates) — Server-rendered pages in `templates/`
- CSS — Custom styles in `static/css/style.css`

## Runtime

**Environment:**
- Python 3.11 (production Docker container)
- Python 3.12.10 (local development venv)

**Package Manager:**
- pip — no Pipfile or pyproject.toml, lockfile is `requirements.txt`
- Lockfile: present (`requirements.txt` with pinned versions)

## Frameworks

**Core:**
- Django 4.2.28 — Primary web framework (LTS release), server-rendered templates + REST API
- Django REST Framework 3.16.1 — REST API layer under `/api/`
- Gunicorn 25.1.0 — WSGI production server (3 workers, 120s timeout)

**Authentication:**
- djangorestframework_simplejwt 5.5.1 — JWT auth for API (`/api/auth/token/`)
- Django built-in session auth — Used for browser-based painel (dashboard) views

**Forms:**
- django-crispy-forms 2.5 + crispy-bootstrap5 2025.6 — Styled form rendering with Bootstrap 5

**Filtering:**
- django-filter 25.1 — DRF filter backend for API querysets

**Frontend (vendored, no npm/build step):**
- HTMX 2.0.4 — SPA-like navigation (`hx-boost`) and partial updates; bundled at `static/vendor/htmx.min.js`
- Bootstrap 5 — CSS framework; bundled at `static/vendor/bootstrap/`
- Bootstrap Icons — Icon set; bundled at `static/vendor/bootstrap-icons/`
- instant.page 5.2.0 — Prefetch on hover; bundled at `static/vendor/instantpage.js`
- Custom cart logic at `static/js/carrinho.js`

**Build/Dev:**
- No build pipeline (Webpack, Vite, etc.) — all assets are vendored static files
- WhiteNoise 6.11.0 — Serves compressed/hashed static files in production without Nginx for statics; uses `CompressedManifestStaticFilesStorage`
- python-dotenv 1.2.1 — Loads `.env` into environment at startup

## Key Dependencies

**Critical:**
- `mercadopago==2.3.0` — Official Mercado Pago Python SDK; used exclusively in `apps/pagamentos/services.py` for Checkout Pro and PIX payments
- `psycopg==3.3.2` + `psycopg-binary==3.3.2` — PostgreSQL async-compatible driver (psycopg3)
- `Pillow==12.1.1` — Image processing for product/restaurant logo uploads
- `python-slugify==8.0.4` + `text-unidecode==1.3` — Slug generation for restaurant subdomains
- `requests==2.32.5` — HTTP client (used for outgoing calls if needed)
- `PyJWT==2.11.0` — JWT support (pulled by simplejwt)

**Infrastructure:**
- `whitenoise==6.11.0` — Static file serving in production (configured as STORAGES backend)
- `gunicorn==25.1.0` — Production WSGI server
- `django-cors-headers==4.9.0` — CORS middleware; permissive in DEBUG, restricted to `https://meusistema.com` in production

## Configuration

**Environment:**
- All secrets and runtime config loaded from `.env` via `python-dotenv`
- See `.env.example` for all required variables
- `DJANGO_SETTINGS_MODULE=config.settings` (single settings file, no split dev/prod)

**Key configs driven by env vars:**
- `SECRET_KEY` — Django secret (required)
- `DEBUG` — Toggles dev mode, CORS, ALLOWED_HOSTS wildcard
- `PAYMENT_GATEWAY` — `mercadopago` or `mock` (selects payment backend in `apps/pagamentos/services.py`)
- `MP_ACCESS_TOKEN` — Mercado Pago credentials
- `POSTGRES_*` — Database connection
- `BASE_DOMAIN` / `SITE_URL` — Multi-tenant subdomain routing and absolute URL building

**Build:**
- `Dockerfile` — Single-stage build from `python:3.11-slim-bookworm`; runs `collectstatic` at image build time
- `docker-compose.yml` — Orchestrates three services: `db` (PostgreSQL 15-alpine), `web` (Gunicorn), `nginx` (nginx:1.25-alpine)
- Static files collected to `staticfiles/` (gitignored, served by WhiteNoise or Nginx volume)

## Platform Requirements

**Development:**
- Python 3.11+ or 3.12
- PostgreSQL 15 (or Docker Compose)
- `.env` file populated from `.env.example`

**Production:**
- Docker + Docker Compose
- Nginx 1.25 as reverse proxy (config at `nginx/nginx.conf`)
- PostgreSQL 15 (managed via Docker volume `postgres_data`)
- HTTPS via Let's Encrypt / Certbot (nginx HTTPS block commented out in `nginx/nginx.conf`, certbot directory at `nginx/certbot/`)
- `PAYMENT_GATEWAY=mercadopago` with valid `MP_ACCESS_TOKEN`
- `SITE_URL` must be set to the public URL for Mercado Pago webhook and redirect URLs to resolve correctly

---

*Stack analysis: 2026-04-02*
