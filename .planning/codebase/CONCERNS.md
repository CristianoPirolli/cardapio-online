# Codebase Concerns

**Analysis Date:** 2026-04-02

---

## Migration State: Stripe → Mercado Pago (UNCOMMITTED)

**Two migrations are unapplied and uncommitted:**
- `apps/pagamentos/migrations/0006_switch_to_mercadopago.py`
- `apps/pedidos/migrations/0008_rename_payment_field.py`

Both rename `stripe_payment_intent_id` → `external_payment_id` at the database level. Until these are applied (`python manage.py migrate`), any production database still has the old column name. The Django models and application code already reference `external_payment_id`, so **the app is currently broken on any environment where migrations have not been run**.

Risk: Deploying the code without running migrations will cause `django.db.ProgrammingError` on any query touching `Pedido.external_payment_id` or `Pagamento.external_payment_id`.

Fix: Apply both migrations before or immediately after deploying:
```
python manage.py migrate pedidos 0008_rename_payment_field
python manage.py migrate pagamentos 0006_switch_to_mercadopago
```

---

## Tech Debt: Test Suite Still References Stripe

**Files:**
- `apps/pagamentos/tests/test_services.py`

The entire test class `PagamentoStripeTests` (lines 82–221) imports and calls `confirmar_pagamento_stripe`, patches `apps.pagamentos.services.stripe.checkout.Session`, and creates `Pagamento` objects with `gateway='stripe'` and `stripe_payment_intent_id=...`. None of these exist in `services.py` anymore.

**Consequence:** Running `python manage.py test` will fail at import time with `ImportError: cannot import name 'confirmar_pagamento_stripe' from 'apps.pagamentos.services'`. The mock test class `PagamentoMockTests` also asserts `resultado['client_secret']` (line 54), a key that no longer exists in the `_criar_pagamento_mock` return dict (the field is now `checkout_url`/`gateway` only).

**Impact:** The test suite is effectively broken. No CI gate is enforcing payment correctness.

**Fix:** Delete or rewrite `PagamentoStripeTests` with Mercado Pago equivalents. Update `PagamentoMockTests.test_criar_pagamento_mock` to assert `resultado['gateway'] == 'mock'` and remove the `client_secret` assertion.

---

## Tech Debt: Stale Stripe References in Non-Migration Code

**Files:**
- `apps/pedidos/admin.py` line 53: `'stripe_payment_intent_id'` is referenced in a `fieldsets` tuple. This field no longer exists on `Pedido` after migration 0008. The Django admin will raise `ImproperlyConfigured` when loading the Pedido change form.
- `apps/pagamentos/serializers.py` lines 18, 28: The docstring example and `fields` list reference `stripe_payment_intent_id`. After migration 0006 the field is `external_payment_id`. The serializer's `fields` list will cause a `django.core.exceptions.ImproperlyConfigured` or silent field omission.
- `apps/pagamentos/api_views.py` line 25 (comment) and line 43 (docstring): Refer to `gateway=stripe` as an example filter value. Minor documentation rot, not a runtime error.

**Fix:**
- `apps/pedidos/admin.py`: Replace `'stripe_payment_intent_id'` with `'external_payment_id'` in `fieldsets`.
- `apps/pagamentos/serializers.py`: Replace `stripe_payment_intent_id` with `external_payment_id` in both `fields` list and docstring example.

---

## Security: Webhook Endpoint Has No Signature Verification

**File:** `apps/pagamentos/views.py` lines 185–207 (`mp_webhook`)

The Mercado Pago webhook endpoint is decorated with `@csrf_exempt` (required for external webhooks) but performs **no signature or authenticity check** on the incoming request. Any party that knows the webhook URL can POST a fabricated `{"type": "payment", "data": {"id": "123"}}` payload and trigger payment confirmation logic.

Mercado Pago provides a request signature header (`x-signature` + `x-request-id`) that should be validated using the MP webhook secret. The project has no `MP_WEBHOOK_SECRET` env var defined anywhere (not in `settings.py`, not in `.env.example`).

**Current mitigation:** The `confirmar_pagamento_mp` function re-queries the MP API before marking a payment approved, so a spoofed payment ID pointing to a non-approved payment will not confirm. However, this still allows DoS-style hammering of the MP API with arbitrary IDs.

**Risk level:** Medium. Direct financial fraud is blocked by the re-query, but forged webhooks waste MP API quota and may trigger rate limiting.

**Recommendation:** Implement MP webhook signature validation. Add `MP_WEBHOOK_SECRET` to `.env.example` and `settings.py`. Validate `x-signature` header in `mp_webhook` before calling `processar_webhook_mp`.

---

## Security: API Endpoint Creates Payments Without Authentication

**File:** `apps/pagamentos/api_views.py` line 35–36

```python
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def criar_pagamento_api(request):
```

Any unauthenticated caller can POST `{"pedido_id": N}` to `/api/pagamentos/criar/` and create a Mercado Pago preference for any order ID they can guess. This also exposes the `checkout_url` (Mercado Pago Checkout Pro link) for any order.

**File:** `apps/pedidos/api_views.py` line 40

```python
permission_classes = [permissions.AllowAny]
```

The `PedidoViewSet` also uses `AllowAny`, meaning any anonymous caller can create orders via `POST /api/pedidos/` and update order status via `PATCH /api/pedidos/{id}/status/`. There is no restaurant-scoped authorization: any actor can change the status of any order in the system.

**Risk level:** High. Order status manipulation allows anyone to mark arbitrary orders as delivered or cancelled.

**Fix:** Apply `IsAuthenticated` or a custom `IsRestauranteProprietario` permission to write operations on `PedidoViewSet` and `criar_pagamento_api`. Public order creation for customers needs careful scoping (separate public vs. admin endpoints).

---

## Security: Admin Panel References Non-Existent Field (Runtime Error)

**File:** `apps/pedidos/admin.py` line 53

```python
'fields': ('status', 'pago', 'stripe_payment_intent_id')
```

Once migration 0008 is applied, attempting to open any `Pedido` in the Django admin will raise a field configuration error because `stripe_payment_intent_id` no longer exists. This could lock out admin users from managing orders via the admin panel.

**Fix:** Change `stripe_payment_intent_id` → `external_payment_id` in `apps/pedidos/admin.py`.

---

## Security: Hardcoded Fallback Credentials in Settings

**File:** `config/settings.py` lines 27, 134–138

```python
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-TROQUE-ESTA-CHAVE')
'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'cardapio_pass_dev'),
```

If `SECRET_KEY` or `POSTGRES_PASSWORD` are not set in the environment, Django will silently use the insecure fallback values. There is no startup check that enforces these are set in production.

**File:** `.env.example` line 47: The example superuser password is `admin123mudar` — this is a common default that may be used verbatim in staging environments.

**Fix:** Add a startup assertion in `settings.py` that raises `ImproperlyConfigured` if `SECRET_KEY` contains `insecure` when `DEBUG=False`. Consider using `django-environ` or a secrets validation pattern.

---

## Security: CORS Allows All Origins in DEBUG Mode

**File:** `config/settings.py` line 221

```python
CORS_ALLOW_ALL_ORIGINS = DEBUG
```

When `DEBUG=True`, all cross-origin requests are permitted. If a staging environment runs with `DEBUG=True` (a common mistake), any external site can make credentialed API calls to it.

**Fix:** Set `CORS_ALLOW_ALL_ORIGINS = False` unconditionally and manage `CORS_ALLOWED_ORIGINS` via an env var list, even in development.

---

## Security: ALLOWED_HOSTS Becomes Wildcard in DEBUG Mode

**File:** `config/settings.py` lines 34–36

```python
if DEBUG and '*' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('*')
```

A wildcard `ALLOWED_HOSTS` bypasses Django's HTTP Host header validation. This is safe only in a controlled local dev environment, but creates risk on misconfigured staging servers running `DEBUG=True`.

---

## Incomplete Feature: PIX Expiry Not Enforced Server-Side

**File:** `apps/pagamentos/views.py` (`pagamento_pix`, `verificar_status_pagamento`)
**File:** `templates/pagamentos/pix.html` (JavaScript countdown, line 147)

The frontend displays a 30-minute countdown timer, but the server never cancels a pending PIX payment after expiry. A `Pagamento` with `status='pendente'` and a PIX payment method will remain permanently in the database with no cleanup. If someone pays after the timer expires (the MP PIX QR codes expire per MP's own rules, not the UI timer), the webhook will still confirm it.

There is no scheduled task or management command to expire stale PIX payments.

**Fix:** Add a Celery beat task or Django management command to expire `Pagamento` records where `status='pendente'`, `gateway='mercadopago'`, and `criado_em` is older than 35 minutes (slightly beyond MP's 30-min PIX expiry).

---

## Incomplete Feature: PIX Polling Ignores Network Errors Silently

**File:** `templates/pagamentos/pix.html` lines 178–179

```javascript
.catch(function () {});
```

The polling fetch call swallows all errors silently. If the status endpoint is temporarily down, the user sees no indication and will wait until the countdown expires.

**Fix:** Add error feedback to the UI (e.g., update `status-text` to show "Aguardando conexão...") in the catch handler.

---

## Incomplete Feature: API Response References `client_secret` That No Longer Exists

**File:** `apps/pagamentos/api_views.py` line 70

```python
'client_secret': resultado['client_secret'],
```

The `criar_pagamento` service (`services.py`) no longer returns a `client_secret` key in any code path (Mercado Pago uses `checkout_url`, mock uses `checkout_url: None`). This will raise a `KeyError` at runtime when the `/api/pagamentos/criar/` endpoint is called with `PAYMENT_GATEWAY=mercadopago`.

**Fix:** Remove the `client_secret` field from the API response in `api_views.py` and update any API consumers.

---

## Tech Debt: Admin Bulk Status Actions Bypass Transition Validation

**File:** `apps/pedidos/admin.py` lines 63–76

```python
def marcar_preparo(self, request, queryset):
    queryset.update(status='preparo')
```

The three bulk admin actions use `queryset.update()` which bypasses the `Pedido.save()` override that enforces valid status transitions via BFS graph validation. An admin could move a `cancelado` order back to `preparo` using a bulk action, corrupting the status graph invariant.

**Fix:** Replace `queryset.update()` with a loop calling `pedido.save()`, or add transition validation logic before the bulk update.

---

## Tech Debt: `_skip_status_validation` Flag is Fragile

**File:** `apps/pedidos/views.py` line 569
**File:** `apps/pedidos/models.py` line 203

```python
pedido._skip_status_validation = True
pedido.status = 'concluido'
pedido.save()
```

The `concluir_pedido_cliente` view bypasses the model's BFS transition guard using an undocumented private attribute flag. This pattern is fragile: any future refactor that adds a pre-save signal or other save hook may not respect this flag. The manual `entrega → concluido` transition check at line 565 (`if pedido.status != 'entrega'`) duplicates logic that already exists in the validated graph.

**Fix:** Add `'entrega' → 'concluido'` as an explicit valid transition in `GRAFO_STATUS_PEDIDO` in `apps/core/algorithms.py` and remove the `_skip_status_validation` pattern entirely.

---

## Tech Debt: MP_PIX_PAYER_EMAIL is a Shared Stub

**File:** `apps/pagamentos/services.py` line 172
**File:** `config/settings.py` line 245

```python
payer_email = getattr(settings, 'MP_PIX_PAYER_EMAIL', 'cliente@cardapio.com')
```

The Mercado Pago PIX API requires a payer email, but the system uses a single shared stub email (`cliente@cardapio.com`) for all PIX transactions because customers order without a mandatory account/email. This means all PIX payments appear under the same payer identity in the MP dashboard, making reconciliation and dispute resolution difficult.

**Risk:** At scale, Mercado Pago may flag or rate-limit accounts where all payments share the same payer email.

**Fix:** Use the customer's `cliente_email` from the order if provided; fall back to the stub only when blank.

---

## Test Coverage Gaps

**What's not tested:**
- `confirmar_pagamento_mp` — no test covers the Mercado Pago payment confirmation path.
- `processar_webhook_mp` — no test verifies webhook payload parsing for either the Webhook JSON format or IPN query-param format.
- `_criar_pagamento_mp_cartao` / `_criar_pagamento_mp_pix` — no tests for the actual MP SDK calls.
- `mp_checkout_return` view — return URL handling with `payment_id` query param is untested.
- `verificar_status_pagamento` — the polling endpoint is untested.
- All Stripe-based tests in `PagamentoStripeTests` will fail at import, meaning the test runner exits before running any tests in that file (including the valid mock tests).

**Files:** `apps/pagamentos/tests/test_services.py`

**Priority:** High. Payment processing is the most critical path in the application and has zero working tests covering the active (Mercado Pago) gateway.

---

## Scaling Concern: No Rate Limiting on Polling Endpoint

**File:** `apps/pagamentos/urls.py`
**File:** `apps/pagamentos/views.py` (`verificar_status_pagamento`)

The PIX status polling endpoint at `GET /pagamentos/verificar/<pagamento_id>/` makes a live API call to Mercado Pago on every request (when payment is pending). The frontend polls this every 10 seconds. If many users have open PIX pages simultaneously, this multiplies API calls to MP proportionally.

There is no rate limiting, caching layer, or request throttling on this endpoint.

**Fix:** Cache the payment status in Django's cache backend (Redis) for 8–9 seconds between polling intervals. Only hit the MP API when the cache is stale.

---

*Concerns audit: 2026-04-02*
