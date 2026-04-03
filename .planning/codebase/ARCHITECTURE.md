# Architecture

**Analysis Date:** 2026-04-02

## Pattern Overview

**Overall:** Multi-tenant SaaS Django monolith with dual interface (HTML templates + REST API)

**Key Characteristics:**
- Tenant isolation via subdomain: each `Restaurante` maps to `<subdominio>.<BASE_DOMAIN>`
- Hybrid rendering: Django template views for the customer-facing frontend; DRF ViewSets for a parallel REST API
- Session-based cart (anonymous checkout — no customer login required)
- Pluggable payment gateway selected by `PAYMENT_GATEWAY` env var (`mercadopago` or `mock`)
- In-process in-memory cache (`HashCache` in `apps/core/algorithms.py`) — no Redis/Memcached
- BFS-validated order status state machine enforced at the model `save()` level

## Django Apps and Their Responsibilities

### `apps.restaurantes`
- **Tenant root.** Owns the `Restaurante` model — the anchor of all multi-tenant data.
- Handles authentication (login/logout at `auth_views.py`, `auth_urls.py`).
- Owns the operator-facing Painel (dashboard, pedidos list, configurações, pizza sizes).
- Provides REST API via `RestauranteViewSet` (`api_views.py`, `api_urls.py`).
- Contains `TamanhoPizza` model for per-restaurant pizza size/price configuration.
- Key files: `apps/restaurantes/models.py`, `apps/restaurantes/views.py`, `apps/restaurantes/auth_views.py`

### `apps.produtos`
- Owns `Categoria` and `Produto` models (scoped per restaurante).
- Serves the public-facing cardápio at `/cardapio/`.
- Provides painel CRUD for categories and products (embedded in `/cardapio/painel/...` URLs).
- `Categoria.eh_pizza` flag enables pizza-mode (tamanho + multiple sabores logic).
- Key files: `apps/produtos/models.py`, `apps/produtos/views.py`, `apps/produtos/urls.py`

### `apps.pedidos`
- Owns `Pedido` and `ItemPedido` models.
- Manages the session-based cart and checkout flow.
- Enforces order status transitions via BFS graph (`GRAFO_STATUS_PEDIDO` in `apps/core/algorithms.py`).
- `ItemPedido` snapshots `preco_unitario` at order time, preserving price history.
- `Pedido.calcular_totais()` computes subtotal, delivery fee, tax, and total.
- No customer login required — customer data (name, phone, address) is stored inline on `Pedido`.
- Key files: `apps/pedidos/models.py`, `apps/pedidos/views.py`, `apps/pedidos/services.py`

### `apps.pagamentos`
- Owns the `Pagamento` model (one record per payment attempt/session).
- Abstracts payment gateway behind `criar_pagamento()` / `confirmar_pagamento_*()` in `services.py`.
- Supports two gateways: `mercadopago` (Checkout Pro for card + PIX via API) and `mock` (local simulation).
- Webhook/IPN endpoint at `POST /pagamentos/mp-webhook/` (CSRF-exempt).
- PIX confirmation uses client-side polling to `GET /pagamentos/verificar/<pagamento_id>/`.
- Key files: `apps/pagamentos/models.py`, `apps/pagamentos/services.py`, `apps/pagamentos/views.py`

### `apps.core`
- Shared algorithms and data structures used across all apps.
- No models, no views — pure Python utility module.
- Provides: `HashCache`, BFS helpers, binary search helpers, memoized subtotal calculation, `agrupar_por_categoria_hash`.
- Global cache instances: `cache_restaurante` (TTL 30s), `cache_cardapio` (TTL 30s), `cache_produtos` (TTL 10s).
- Key file: `apps/core/algorithms.py`

## Layers

**Middleware (config/middleware.py):**
- Purpose: Cross-cutting request concerns
- `TenantMiddleware`: Parses `HTTP_HOST`, extracts subdomain, sets `request.restaurante` and `request.estabelecimento`. Uses `cache_restaurante` to avoid per-request DB lookups. Falls back to `?estabelecimento=` query param in DEBUG.
- `HtmxMiddleware`: Converts 302 redirects into `HX-Redirect` headers for HTMX-boosted navigation.
- Depends on: `apps.core.algorithms.cache_restaurante`

**Context Processors (config/context_processors.py):**
- `estabelecimento_context`: Injects `estabelecimento_atual`, `restaurante_atual`, `carrinho_total_itens`, `painel_pedidos_abertos_count`, `base_domain` into every template context.

**Views (HTML layer):**
- Function-based views using `@login_required` for painel routes.
- Public cardápio and checkout require no authentication.
- Cart is stored in Django sessions (`request.session['carrinho']`).

**API Layer (DRF):**
- Each app exposes a ViewSet registered via `DefaultRouter` in `api_urls.py`.
- Auth: JWT (`SimpleJWT`) or Session. `IsAuthenticatedOrReadOnly` by default.
- Endpoints mirror the HTML routes under `/api/` prefix.

**Service Layer:**
- `apps/pedidos/services.py`: `criar_pedido_do_carrinho()`, `montar_resumo_carrinho()`, `validar_dados_checkout()`
- `apps/pagamentos/services.py`: `criar_pagamento()`, `confirmar_pagamento_mp()`, `confirmar_pagamento_mock()`, `processar_webhook_mp()`
- Services are called by views and contain business logic separate from HTTP concerns.

## Data Models and Relationships

```
User (Django built-in)
 └── Restaurante (1:1 via proprietario)
      ├── TamanhoPizza (1:N — pizza size configs per restaurant)
      ├── Categoria (1:N — scoped product categories)
      │    └── Produto (1:N — menu items)
      └── Pedido (1:N — orders placed at this restaurant)
           ├── ItemPedido (1:N — line items, snapshots preco_unitario)
           └── Pagamento (1:N — payment attempts)
```

**Key field notes:**
- `Restaurante.subdominio`: unique slug, auto-generated from `nome` if blank, indexed.
- `Pedido.status`: enforced state machine — `aguardando → recebido → preparo → entrega → concluido` (or `cancelado` from any state).
- `Pedido.pago`: boolean gate — painel views only show `pago=True` orders.
- `Pedido.external_payment_id`: gateway's reference ID, copied from `Pagamento`.
- `Pagamento.dados_resposta`: JSONField storing full gateway response (QR codes, preference IDs, etc.).
- `ItemPedido.preco_unitario`: price snapshot at order time.
- `ItemPedido.tamanho_nome` / `sabores_descricao`: denormalized pizza configuration strings.

## Order Status State Machine

Defined in `apps/core/algorithms.py` as `GRAFO_STATUS_PEDIDO`:

```
aguardando → recebido → preparo → entrega → concluido
     ↓            ↓         ↓         ↓
  cancelado   cancelado  cancelado  cancelado
```

- Transitions validated in `Pedido.save()` by querying current DB status and running `validar_transicao_status()`.
- `Pedido.proximo_passo` uses BFS to suggest the next action in the painel.
- Payment confirmation (webhook or return URL) moves pedido from `aguardando` → `recebido` and sets `pago=True`.

## Payment Flow

**Mercado Pago — Cartão (Checkout Pro):**
1. Customer at `/pagamentos/<pedido_id>/` selects "Cartão".
2. `POST /pagamentos/<pedido_id>/iniciar/` calls `criar_pagamento(pedido, metodo='card')`.
3. `services.py` creates MP preference via SDK, saves `Pagamento` record, returns `checkout_url`.
4. View redirects customer to Mercado Pago's hosted checkout page.
5. After payment, MP redirects to `GET /pagamentos/mp-return/<pedido_id>/` with `?payment_id=`.
6. View calls `confirmar_pagamento_mp(payment_id)`, marks `pedido.pago=True`, status `recebido`.
7. MP also sends `POST /pagamentos/mp-webhook/` (IPN or webhook JSON) for server-side confirmation.

**Mercado Pago — PIX:**
1. `POST /pagamentos/<pedido_id>/iniciar/` with `metodo='pix'` calls `_criar_pagamento_mp_pix()`.
2. SDK creates a payment with `payment_method_id: pix`, returns QR code data.
3. Customer redirected to `/pagamentos/<pedido_id>/pix/` displaying QR code image + "Pix Copia e Cola".
4. Frontend polls `GET /pagamentos/verificar/<pagamento_id>/` every N seconds.
5. Polling endpoint calls `confirmar_pagamento_mp()`, returns `{pago, status, redirect_url}`.
6. On confirmation, frontend redirects to success page.

**Mock (development):**
1. Same flow, but `_criar_pagamento_mock()` generates a `mock_pi_*` ID — no external calls.
2. Card mock: redirect to `/pagamentos/<pedido_id>/mock-cartao/` with a "Confirm Payment" button.
3. PIX mock: `/pagamentos/<pedido_id>/pix/` shows simulated QR; "Confirm" button POSTs to `confirmar-mock/<pagamento_id>/`.

## Authentication System

- Django's built-in `User` model with session authentication.
- Login at `POST /auth/login/` — uses `AuthenticationForm`.
- Logout at `GET /auth/logout/`.
- Self-registration is **disabled** — `registro_view` immediately redirects with a warning.
- Users and restaurants created by superuser in Django Admin.
- Login redirect: superusers → `/admin/`; restaurant owners → `/painel/`.
- Painel views guard via `@login_required` (redirects to `LOGIN_URL = '/auth/login/'`).
- REST API supports JWT Bearer tokens (via `SimpleJWT`) AND session authentication.
- JWT tokens: access (1h), refresh (7d, rotating).

## URL Routing Map

```
/                              → home (restaurantes.views.home)
/admin/                        → Django Admin
/auth/login/                   → login_view
/auth/logout/                  → logout_view
/auth/registro/                → registro_view (disabled)
/cardapio/                     → cardapio_publico
/cardapio/produto/<id>/        → produto_detalhe
/cardapio/painel/categorias/   → painel CRUD for categorias
/cardapio/painel/produtos/     → painel CRUD for produtos
/pedidos/carrinho/             → ver_carrinho
/pedidos/carrinho/adicionar/   → adicionar_ao_carrinho (POST)
/pedidos/carrinho/remover/     → remover_do_carrinho (POST)
/pedidos/checkout/             → checkout
/pedidos/<id>/acompanhar/      → acompanhar_pedido
/pagamentos/<id>/              → pagamento_escolher
/pagamentos/<id>/iniciar/      → iniciar_pagamento_mp (POST)
/pagamentos/<id>/pix/          → pagamento_pix
/pagamentos/verificar/<id>/    → verificar_status_pagamento (polling JSON)
/pagamentos/mp-return/<id>/    → mp_checkout_return (MP redirect back)
/pagamentos/mp-webhook/        → mp_webhook (CSRF-exempt, POST)
/pagamentos/<id>/mock-cartao/  → mock_cartao_checkout
/pagamentos/confirmar-mock/<id>/ → pagamento_confirmar_mock
/pagamentos/sucesso/<id>/      → pagamento_sucesso
/pagamentos/erro/<id>/         → pagamento_erro
/painel/                       → painel_dashboard (login required)
/painel/configuracoes/         → painel_configuracoes (login required)
/painel/pizzas/                → painel_pizzas (login required)
/painel/pedidos/               → painel_pedidos (login required)
/painel/pedidos/<id>/          → painel_pedido_detalhe (login required)
/painel/pedidos/abertos/count/ → painel_pedidos_abertos_count (JSON)

/api/auth/token/               → JWT TokenObtainPairView
/api/auth/token/refresh/       → JWT TokenRefreshView
/api/restaurantes/             → RestauranteViewSet (DRF)
/api/estabelecimentos/         → RestauranteViewSet (alias)
/api/produtos/                 → ProdutoViewSet (DRF)
/api/pedidos/                  → PedidoViewSet (DRF)
/api/pagamentos/               → PagamentoViewSet (DRF)
/api/pagamentos/criar/         → criar_pagamento_api
```

## Error Handling

**Strategy:** Exception-based with Django messages framework for UI feedback.

**Patterns:**
- Payment errors: `services.py` raises `RuntimeError` on gateway failures; views catch and redirect to `pagamento_erro`.
- Checkout errors: `PedidoCheckoutError` (custom exception in `apps/pedidos/services.py`) caught in `checkout` view.
- Status transition errors: `Pedido.save()` raises `ValueError` on invalid transitions.
- 404 handling: `get_object_or_404()` used consistently across views.
- Webhook errors: logged via `logger.warning()`, always returns HTTP 200 to prevent MP retries from failing.

## Cross-Cutting Concerns

**Multi-tenancy:** `TenantMiddleware` sets `request.restaurante` on every request. Views and services read from this attribute rather than querying by subdomain themselves.

**Caching:** In-process `HashCache` instances in `apps/core/algorithms.py`. Cache is invalidated explicitly on model `save()` for `Restaurante`. No shared cache between workers — each Gunicorn worker has its own cache dict.

**Logging:** Standard Python `logging` via `logger = logging.getLogger(__name__)`. Used in payment services and views. No centralized log aggregation configured.

**Validation:** Model-level (`MinValueValidator`, `MaxValueValidator`, `unique_together`). Business logic validation in service functions. Form validation via Django forms / `crispy_forms`.

**HTMX:** Used for SPA-like navigation. `HtmxMiddleware` converts 302s to `HX-Redirect`. Templates use `hx-boost` and related HTMX attributes.

---

*Architecture analysis: 2026-04-02*
