# Phase 1: PIX Manual Payment — Research

**Researched:** 2026-04-02
**Domain:** Django payment flow replacement — remove Mercado Pago, implement manual PIX with proof upload
**Confidence:** HIGH (all findings based on direct code inspection)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Replace payment gateway with manual PIX flow (fixed PIX key, no SDK, no webhook)
- Customer copies a fixed PIX key, pays via bank app, then uploads proof (image or PDF)
- Order enters `aguardando confirmacao` state after upload (not yet in production pipeline)
- Restaurant views order + proof, then accepts (enters production) or rejects (cancelled)
- Accepted order amount counts in panel totals
- Remove Mercado Pago integration (gateway, webhooks, SDK)
- PIX key is configurable (env var or admin setting)
- File upload stored with size + type restrictions (image/PDF only)
- Existing production pipeline preserved after acceptance

### Claude's Discretion
- Exact `aguardando_confirmacao` status value string
- Where to store the PIX key (env var vs. restaurant model field vs. Django admin setting)
- File upload field location (on `Pagamento` model or new dedicated model)
- Whether to repurpose the existing `pagamento_pix` view or create a new one
- Template naming strategy (reuse vs. create new)

### Deferred Ideas (OUT OF SCOPE)
- Automated PIX payment verification (no webhook, no QR code generation)
- Multiple PIX keys
- Refund flow
</user_constraints>

---

## Summary

The project is a Django 4.2 monolith using server-rendered templates, Bootstrap 5, HTMX, and PostgreSQL. The payment layer (`apps/pagamentos/`) currently wraps Mercado Pago SDK with a mock fallback. The entire MP integration lives in three tightly bounded files: `services.py`, `views.py`, and `urls.py`. This makes it cleanly replaceable.

The critical pre-condition is that **two migrations are already written but unapplied** (`0006_switch_to_mercadopago.py` and `0008_rename_payment_field.py`). These rename `stripe_payment_intent_id` to `external_payment_id` at the database level. They MUST be applied before any further schema changes. Several existing files still reference the old Stripe field name (`apps/pedidos/admin.py` line 53, `apps/pagamentos/serializers.py`), which will crash after migration.

For the new PIX flow: the order status graph needs one new node (`aguardando_confirmacao`) inserted between `aguardando` and `recebido`. File upload can be added directly to the existing `Pagamento` model as a new `FileField`. Session persistence is already handled correctly — the cart is cleared at checkout time and the `Pedido` ID is the only reference needed; the customer can leave the browser and return via `/pedidos/<id>/acompanhar/`.

**Primary recommendation:** Modify the existing `apps/pagamentos/` app in-place. Do not create a new app. Replace `services.py` content, rewrite `views.py` for the new flow, add a `FileField` to `Pagamento`, add one status to the BFS graph, and update admin for restaurant-side accept/reject. Remove `mercadopago` from `requirements.txt`.

---

## What Needs to Be REMOVED

### 1. The `mercadopago` SDK and all SDK call sites

| File | What to remove |
|------|----------------|
| `requirements.txt` | `mercadopago==2.3.0` |
| `apps/pagamentos/services.py` | Entire file content — `_criar_pagamento_mp`, `_criar_pagamento_mp_cartao`, `_criar_pagamento_mp_pix`, `confirmar_pagamento_mp`, `processar_webhook_mp`, `_get_mp_sdk`, `_criar_pagamento_mock`, `confirmar_pagamento_mock` |
| `config/settings.py` | `MP_ACCESS_TOKEN`, `MP_PIX_PAYER_EMAIL`, `PAYMENT_GATEWAY` settings block (lines 232–245) |
| `.env.example` | `PAYMENT_GATEWAY`, `MP_ACCESS_TOKEN`, `MP_PIX_PAYER_EMAIL` |

### 2. Gateway-specific views and URL patterns

| File | What to remove |
|------|----------------|
| `apps/pagamentos/views.py` | `iniciar_pagamento_mp`, `verificar_status_pagamento`, `mp_checkout_return`, `mp_webhook`, `mock_cartao_checkout`, `pagamento_confirmar_mock` |
| `apps/pagamentos/urls.py` | All paths except `pagamento_escolher`, `pagamento_sucesso`, `pagamento_erro` — and those will be repurposed |

### 3. Gateway-specific templates

| Template | Action |
|----------|--------|
| `templates/pagamentos/pix.html` | Replace entirely (was QR + polling; now static PIX key + upload form) |
| `templates/pagamentos/pagamento.html` | Replace entirely (was card/PIX selection; now PIX-only instructions) |
| `templates/pagamentos/mock_cartao.html` | Delete — no card flow |

### 4. Stale Stripe references that must also be fixed (pre-existing debt)

| File | Issue | Fix |
|------|-------|-----|
| `apps/pedidos/admin.py` line 53 | `'stripe_payment_intent_id'` in fieldsets — crashes after migration 0008 | Replace with `'external_payment_id'` |
| `apps/pagamentos/serializers.py` lines 18, 28 | `stripe_payment_intent_id` in `fields` list — DRF field resolution error after migration 0006 | Replace with `'external_payment_id'` in fields list |
| `apps/pagamentos/api_views.py` line 70 | `resultado['client_secret']` KeyError at runtime | Remove `client_secret` from response dict |

---

## Standard Stack

### Core (already in project — no new installs needed)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| Django | 4.2.28 | FileField, ImageField, ModelAdmin, sessions | All upload infra built-in |
| Pillow | 12.1.1 | Image validation for ImageField | Already installed |
| Bootstrap 5 | (vendored) | Copy-button, file input UI | Already bundled |
| Bootstrap Icons | (vendored) | PIX icon, clipboard icon, upload icon | Already bundled |

### No new packages required
The PIX manual flow uses only Django builtins:
- `django.db.models.FileField` — stores proof file
- Django sessions (`request.session`) — already configured
- Django `FileSystemStorage` — already configured at `MEDIA_ROOT`
- Django admin customization — for accept/reject actions

**PIX key storage:** Simplest approach within project conventions is a new `PIX_KEY` env var read into `settings.py`. This mirrors `MP_ACCESS_TOKEN` pattern and is already documented as the preferred config pattern.

---

## Architecture Patterns

### Recommended Project Structure (changes only)

```
apps/pagamentos/
├── models.py          # ADD: comprovante FileField + status aguardando_confirmacao gateway choice
├── services.py        # REPLACE: pix manual service only (no SDK)
├── views.py           # REPLACE: pix flow views (show key, upload, accept/reject)
├── urls.py            # REPLACE: new URL patterns
├── admin.py           # UPDATE: add accept/reject actions
├── migrations/
│   ├── 0006_switch_to_mercadopago.py   # MUST APPLY FIRST
│   └── 0007_add_pix_manual_fields.py   # NEW: add comprovante field + pix gateway
apps/pedidos/
├── migrations/
│   └── 0008_rename_payment_field.py    # MUST APPLY FIRST
apps/core/
└── algorithms.py      # UPDATE: add aguardando_confirmacao to GRAFO_STATUS_PEDIDO
config/
└── settings.py        # UPDATE: add PIX_KEY env var, remove MP vars
templates/pagamentos/
├── pagamento.html     # REPLACE: PIX instructions + copy button
├── pix_upload.html    # NEW: upload comprovante form
└── sucesso.html       # KEEP: success page (already exists, no changes needed)
```

### Pattern 1: New Status in BFS Graph

The `GRAFO_STATUS_PEDIDO` in `apps/core/algorithms.py` must have `aguardando_confirmacao` inserted:

```python
# Source: apps/core/algorithms.py (direct inspection)
GRAFO_STATUS_PEDIDO = {
    'aguardando': ['aguardando_confirmacao', 'cancelado'],      # changed: was ['recebido', 'cancelado']
    'aguardando_confirmacao': ['recebido', 'cancelado'],        # NEW node
    'recebido': ['preparo', 'cancelado'],
    'preparo': ['entrega', 'cancelado'],
    'entrega': ['concluido', 'cancelado'],
    'concluido': [],
    'cancelado': [],
}
```

**Consequence of this change:** The existing `Pedido.STATUS_CHOICES` list must also gain `('aguardando_confirmacao', 'Aguardando Confirmacao')`. The BFS helpers automatically propagate (they are graph-generic). The painel dashboard currently filters on `pago=True` — orders stay invisible there until restaurant accepts.

**Critical:** `confirmar_pagamento_mp` previously moved `aguardando → recebido` and set `pago=True`. The new PIX service must set `pago=False` when creating the `Pagamento` record. `pago=True` only happens when the restaurant accepts (second step). This preserves the existing "painel only shows `pago=True`" invariant.

### Pattern 2: File Upload on Pagamento Model

Add `comprovante` FileField directly to the existing `Pagamento` model:

```python
# Source: apps/pagamentos/models.py (direct inspection of model structure)
comprovante = models.FileField(
    upload_to='comprovantes/',
    blank=True,
    null=True,
    verbose_name='Comprovante de Pagamento',
)
```

This is preferred over a new model because `Pagamento` already has the FK to `Pedido`, the `status` field, and the `dados_resposta` JSONField. A separate model adds FK joins for no benefit.

### Pattern 3: New Gateway Choice

Add `'pix_manual'` to `Pagamento.GATEWAY_CHOICES`:

```python
# Source: apps/pagamentos/models.py (direct inspection)
GATEWAY_CHOICES = [
    ('mercadopago', 'Mercado Pago'),
    ('mock', 'Mock (Simulacao)'),
    ('pix_manual', 'PIX Manual'),       # NEW
]
```

The `max_length=15` constraint on `gateway` fits `'pix_manual'` (10 chars). No migration needed for the max_length. Migration is needed for the new `comprovante` FileField and the `GATEWAY_CHOICES` update.

### Pattern 4: Customer Flow — Session Handling

**Sessions already work correctly.** The cart is cleared at checkout (line 471 in `pedidos/views.py`):

```python
# Source: apps/pedidos/views.py line 471
request.session['carrinho'] = {'restaurante_id': None, 'itens': {}}
request.session.modified = True
```

After checkout, the customer is redirected to `pagamento_escolher` with only the `pedido_id` in the URL. They can close the browser, leave to the bank app, and return directly to `/pagamentos/<id>/` — no session data is needed. The `Pedido.id` in the URL is the sole state reference.

**Session backend:** Django uses `django.contrib.sessions` with database-backed sessions (default). The session cookie (`SESSION_COOKIE_AGE` defaults to 1209600 seconds = 2 weeks). No `SESSION_EXPIRE_AT_BROWSER_CLOSE` is set, so sessions survive browser close/reopen. **The session will survive leaving the bank app.**

### Pattern 5: Restaurant Accept/Reject Flow

The restaurant accept action must:
1. Set `pagamento.status = 'aprovado'`
2. Set `pedido.pago = True`
3. Transition `pedido.status`: `aguardando_confirmacao → recebido` (valid per new BFS graph)
4. Call `pedido.save()` — BFS validation runs automatically

The restaurant reject action must:
1. Set `pagamento.status = 'recusado'`
2. Transition `pedido.status`: `aguardando_confirmacao → cancelado` (valid per new BFS graph)

These actions belong in `apps/pagamentos/services.py` as `confirmar_pix_manual(pagamento)` and `rejeitar_pix_manual(pagamento)`.

### Anti-Patterns to Avoid

- **Do not add accept/reject to Django admin bulk actions.** Existing bulk actions already bypass BFS validation (`queryset.update()`). New accept/reject should be in the painel HTML view (authenticated, validated through `pedido.save()`).
- **Do not read `request.session` to find the order on the PIX page.** Use `pedido_id` from the URL. The session has no order data after checkout.
- **Do not set `pedido.pago = True` when the customer uploads the comprovante.** That is the restaurant's responsibility on accept. Setting it early would make the order appear in painel counts before confirmation.
- **Do not poll.** There is no webhook, no async status change from an external service. The PIX upload page is a static form — no JavaScript polling needed.
- **Do not use `_skip_status_validation`.** The new `aguardando_confirmacao → recebido` and `aguardando_confirmacao → cancelado` transitions are explicit in the graph, so `pedido.save()` will validate them normally.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File type validation | Custom MIME-type parser | Django `FileField` + `validate_file_extension` validator or accept attribute | Django's upload handler already reads the content type; add `validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf', 'webp'])]` |
| File size limit | Custom middleware | Django `DATA_UPLOAD_MAX_MEMORY_SIZE` setting + view-level check on `request.FILES['comprovante'].size` | One setting covers the global limit; one view check gives a user-friendly error |
| Secure file serving | Custom view with auth checks | Nginx `X-Accel-Redirect` or Django's default media serving in DEBUG | For production: Nginx already serves `/media/` from the `media_volume` Docker volume — no extra auth needed since comprovante paths contain no guessable identifiers if `upload_to` uses `uuid` or `pedido_id` |
| Copy-to-clipboard button | Custom JS | Navigator Clipboard API — already used in `pix.html` line 189 | Same `navigator.clipboard.writeText()` pattern, copy from existing code |
| Status badge colors | Custom CSS | Bootstrap 5 badge classes already mapped per status in `pedido_detalhe.html` lines 111–116 | Add `aguardando_confirmacao` badge variant (e.g., `bg-warning`) to match the template pattern |

---

## Common Pitfalls

### Pitfall 1: Applying Migrations Out of Order

**What goes wrong:** Running `makemigrations` for the new PIX fields before applying the pending `0006` and `0008` migrations creates a dependency chain that Django cannot resolve. The new migration would depend on `0006` (pagamentos) and `0007` (which doesn't exist yet), causing `InconsistentMigrationHistory`.

**Why it happens:** Migration 0006 is created but unapplied. If `makemigrations` runs against an environment that already has `0006` applied in the DB but not in the code state, it will see a mismatch.

**How to avoid:** Apply `0006` and `0008` first (`python manage.py migrate`), then make the new migration for PIX fields.

**Warning signs:** `InconsistentMigrationHistory` or `ProgrammingError: column does not exist` on any query touching `external_payment_id`.

### Pitfall 2: `pago=True` Set Too Early Breaks Painel Filtering

**What goes wrong:** If `pago=True` is set when the customer submits the comprovante, orders appear immediately in `painel_pedidos` and `painel_dashboard` (both filter `pago=True`). The restaurant would see the order in the production pipeline before confirming the payment.

**Why it happens:** The `pago` flag is the gate for all painel visibility. It was designed to be set only when a gateway confirmed payment automatically.

**How to avoid:** Only set `pago=True` in the `confirmar_pix_manual()` service, called from the restaurant's accept action. The `aguardando_confirmacao` state serves as a holding area.

**Warning signs:** Orders with unconfirmed payments appearing in `/painel/pedidos/`.

### Pitfall 3: The `painel_pedidos_abertos_count` Context Processor Misses New Status

**What goes wrong:** The context processor `estabelecimento_context` in `config/context_processors.py` counts "abertos" orders as `pago=True, status NOT IN ['concluido', 'cancelado']`. Orders in `aguardando_confirmacao` have `pago=False`, so they are invisible to the counter. The restaurant's notification badge will not show the pending confirmation queue.

**Why it happens:** The counter was designed around the `pago=True` gate.

**How to avoid:** Add a separate `aguardando_confirmacao_count` to the context processor (or modify the counter to include `status='aguardando_confirmacao'` regardless of `pago`). The painel layout must have a visible notification for "awaiting confirmation" orders.

**Warning signs:** Restaurant has no visual indicator of orders waiting for PIX confirmation.

### Pitfall 4: `admin.py` Crashes on `Pedido` Change Form After Migration 0008

**What goes wrong:** `apps/pedidos/admin.py` line 53 references `'stripe_payment_intent_id'` in the `fieldsets` tuple. Once migration 0008 is applied, the field no longer exists. Opening any `Pedido` in Django Admin raises `django.core.exceptions.FieldError`.

**Why it happens:** This is pre-existing tech debt noted in CONCERNS.md. It was never fixed.

**How to avoid:** Fix `apps/pedidos/admin.py` line 53: replace `'stripe_payment_intent_id'` with `'external_payment_id'` as part of Wave 0 cleanup.

**Warning signs:** `FieldError: Unknown field(s) (stripe_payment_intent_id)` when loading Django Admin for Pedido.

### Pitfall 5: `PagamentoSerializer` Breaks DRF After Migration 0006

**What goes wrong:** `apps/pagamentos/serializers.py` lists `'stripe_payment_intent_id'` in `fields`. After migration 0006 renames it to `external_payment_id`, DRF raises `ImproperlyConfigured` on any request to `/api/pagamentos/`.

**Why it happens:** Pre-existing tech debt (also in CONCERNS.md).

**How to avoid:** Fix serializer as part of Wave 0 cleanup.

### Pitfall 6: `FileField` Requires `MEDIA_ROOT` to Exist at Upload Time

**What goes wrong:** If `media/comprovantes/` directory doesn't exist when a file is first uploaded, Django raises `FileNotFoundError` (on some OS configurations).

**Why it happens:** Django's FileSystemStorage calls `os.makedirs` only if `upload_to` returns a path whose parent directory exists (behavior may differ by OS).

**How to avoid:** Django 4.x `FileSystemStorage` creates intermediate directories automatically for most `upload_to` patterns. Verified: `MEDIA_ROOT = BASE_DIR / 'media'` is already set in `settings.py`. The subdirectory `comprovantes/` will be created on first upload. No extra action needed, but a Wave 0 task should confirm the `media/` directory exists in the Docker volume mount.

### Pitfall 7: HTMX `hx-boost` on Payment Forms

**What goes wrong:** The existing `pagamento.html` has `hx-boost="false"` on forms (lines 114, 130). This is intentional because payment redirects must be hard navigations. The new upload form must also set `hx-boost="false"` or wrap the file input outside an hx-boosted form.

**Why it happens:** HTMX swaps responses in-page; a multipart file upload needs a real form submission. HTMX `hx-boost` does not support `multipart/form-data` without extra config.

**How to avoid:** Always set `hx-boost="false"` or `enctype="multipart/form-data"` on any form with file input. Do not use `hx-post` for the upload.

---

## Code Examples

Verified patterns from existing codebase:

### File Upload Field (verified pattern from `Produto.imagem`)
```python
# Source: apps/produtos/models.py — existing ImageField pattern in project
comprovante = models.FileField(
    upload_to='comprovantes/%Y/%m/',
    blank=True,
    null=True,
    verbose_name='Comprovante de Pagamento',
    validators=[
        FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp', 'pdf'])
    ],
)
```

### New Service Functions (replacing services.py)
```python
# Pattern follows existing confirmar_pagamento_mock() in services.py
def confirmar_pix_manual(pagamento):
    """Restaurante aceita comprovante. Ordem entra no pipeline."""
    pagamento.status = 'aprovado'
    pagamento.save(update_fields=['status', 'atualizado_em'])

    pedido = pagamento.pedido
    pedido.pago = True
    if pedido.status == 'aguardando_confirmacao':
        pedido.status = 'recebido'
    pedido.save()   # BFS validation runs here
    return pagamento


def rejeitar_pix_manual(pagamento):
    """Restaurante rejeita comprovante. Ordem cancelada."""
    pagamento.status = 'recusado'
    pagamento.save(update_fields=['status', 'atualizado_em'])

    pedido = pagamento.pedido
    if pedido.status == 'aguardando_confirmacao':
        pedido.status = 'cancelado'
        pedido.save()   # BFS validation: aguardando_confirmacao -> cancelado is valid
    return pagamento
```

### PIX Key from Settings (mirrors existing MP_ACCESS_TOKEN pattern)
```python
# config/settings.py addition — mirrors existing pattern at line 243
PIX_KEY = os.getenv('PIX_KEY', '')
```

### Copy Button (identical to existing pix.html lines 186-197)
```javascript
// Source: templates/pagamentos/pix.html lines 186-197 — reuse verbatim
function copiarPix() {
    var input = document.getElementById('pix-code');
    navigator.clipboard.writeText(input.value).then(function () {
        var btn = document.getElementById('btn-copiar');
        btn.innerHTML = '<i class="bi bi-check me-1"></i>Copiado!';
        setTimeout(function () {
            btn.innerHTML = '<i class="bi bi-clipboard me-1"></i>Copiar';
        }, 2000);
    });
}
```

### Status Badge for New State (follows pedido_detalhe.html lines 111-116)
```html
<!-- Source: templates/painel/pedido_detalhe.html — existing badge pattern -->
{% if pedido.status == 'aguardando_confirmacao' %}bg-warning text-dark{% endif %}
```

---

## Order Status State Machine — Updated

Current graph (in `apps/core/algorithms.py`):
```
aguardando → recebido → preparo → entrega → concluido
    ↓            ↓         ↓         ↓
 cancelado   cancelado  cancelado  cancelado
```

Required graph after Phase 1:
```
aguardando → aguardando_confirmacao → recebido → preparo → entrega → concluido
    ↓                 ↓                  ↓          ↓         ↓
 cancelado         cancelado          cancelado  cancelado  cancelado
```

**Impact on existing code:**
- `GRAFO_STATUS_PEDIDO` in `apps/core/algorithms.py` — must be updated
- `Pedido.STATUS_CHOICES` in `apps/pedidos/models.py` — must add `('aguardando_confirmacao', 'Aguardando Confirmacao')`
- New migration needed on `pedidos` app (for `STATUS_CHOICES` — Django does NOT enforce choices at DB level, so no schema change; this is a code-only change with no migration required unless the existing app has a migration that hardcodes the choices at the DB level — inspected migrations 0001-0007, none do)
- `painel_pedido_detalhe` view template — must render accept/reject buttons when `status == 'aguardando_confirmacao'`
- `painel_pedidos_abertos_count` context processor — must separately surface the confirmation queue

---

## Migration State Analysis

### Pending (must apply before any new work)

| Migration | App | Status | Blocks |
|-----------|-----|--------|--------|
| `0006_switch_to_mercadopago.py` | pagamentos | Unapplied, uncommitted | Any query on `external_payment_id` in Pagamento |
| `0008_rename_payment_field.py` | pedidos | Unapplied, uncommitted | Any query on `external_payment_id` in Pedido, Django Admin for Pedido |

### New migrations required in Phase 1

| Migration | App | Operation |
|-----------|-----|-----------|
| `0007_add_pix_manual_fields.py` | pagamentos | Add `comprovante FileField`, add `'pix_manual'` to gateway choices, depends on `0006` |

### No migration needed for
- Adding `aguardando_confirmacao` to `Pedido.STATUS_CHOICES` — Django choices are Python-level only; no DB constraint on `status` char field
- Removing `mercadopago` from `GATEWAY_CHOICES` — existing DB rows have `gateway='mercadopago'`; removing from choices only hides from UI, does not break DB. Keep `mercadopago` in choices for now to avoid breaking existing rows, OR keep it but mark display as `'Mercado Pago (descontinuado)'`

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | YES | 3.12.10 | — |
| Pillow | FileField image validation | YES | 12.1.1 | — |
| PostgreSQL | Database | YES (Docker) | 15 (from docker-compose.yml) | — |
| `media/` directory | File uploads | YES (MEDIA_ROOT set) | — | Created on first upload |
| Django sessions | Cart/order persistence | YES (built-in middleware) | 4.2.28 | — |

**No missing dependencies.** Phase 1 requires zero new package installs.

---

## Validation Architecture

No `.planning/config.json` found — treating nyquist_validation as **enabled**.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Django TestCase (built-in) |
| Config file | none — uses `python manage.py test` |
| Quick run command | `python manage.py test apps.pagamentos.tests --verbosity=1` |
| Full suite command | `python manage.py test --verbosity=1` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-01 | PIX page shows fixed key + copy button | smoke | `python manage.py test apps.pagamentos.tests.test_views.PixManualViewTest` | No — Wave 0 |
| REQ-02 | Session survives browser leave/return (pedido survives by ID in URL) | unit | `python manage.py test apps.pagamentos.tests.test_views.PixManualViewTest.test_pix_page_loads_with_pedido_id` | No — Wave 0 |
| REQ-03 | Customer uploads comprovante, order enters aguardando_confirmacao | unit | `python manage.py test apps.pagamentos.tests.test_services.PixManualServiceTest.test_upload_comprovante` | No — Wave 0 |
| REQ-04 | Restaurant accept: pago=True, status=recebido | unit | `python manage.py test apps.pagamentos.tests.test_services.PixManualServiceTest.test_confirmar_pix_manual` | No — Wave 0 |
| REQ-05 | Restaurant reject: status=cancelado | unit | `python manage.py test apps.pagamentos.tests.test_services.PixManualServiceTest.test_rejeitar_pix_manual` | No — Wave 0 |
| REQ-06 | Accepted order amount appears in painel totals (pago=True gate) | integration | `python manage.py test apps.restaurantes.tests.test_dashboard.DashboardTest.test_accepted_pix_order_counted` | No — Wave 0 |
| REQ-07 | File type validation rejects non-image/pdf uploads | unit | `python manage.py test apps.pagamentos.tests.test_views.PixManualViewTest.test_upload_rejects_invalid_type` | No — Wave 0 |
| REQ-08 | BFS graph includes aguardando_confirmacao transitions | unit | `python manage.py test apps.pedidos.tests.test_status.StatusGraphTest.test_aguardando_confirmacao_transitions` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `python manage.py test apps.pagamentos.tests --verbosity=1`
- **Per wave merge:** `python manage.py test --verbosity=1`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/pagamentos/tests/test_services.py` — rewrite (currently broken: imports non-existent `confirmar_pagamento_stripe`)
- [ ] `apps/pagamentos/tests/test_views.py` — create for new PIX views
- [ ] `apps/pedidos/tests/test_status.py` — extend for new `aguardando_confirmacao` node

---

## Open Questions

1. **PIX key storage location**
   - What we know: Two valid options — env var `PIX_KEY` (simple, consistent with `MP_ACCESS_TOKEN` pattern) or a `pix_key` field on the `Restaurante` model (allows per-restaurant customization in the future)
   - What's unclear: Whether the owner wants one global PIX key or per-restaurant PIX keys (SaaS has multiple restaurants)
   - Recommendation: Use `Restaurante.pix_key` CharField (blank=True) with fallback to env var `PIX_KEY`. This costs one migration but enables true multi-tenant use. CONTEXT.md says "PIX key is configurable (env var or admin setting)" — both are satisfied by this pattern (env var as default, admin setting per restaurant).

2. **Where to show "Aguardando Confirmacao" orders in the painel**
   - What we know: Current `painel_pedidos` filters `pago=True` — new status orders won't appear there. A separate UI section or filter tab is needed.
   - What's unclear: Whether a new tab/filter on the existing `painel_pedidos` page suffices, or a dedicated "confirmacoes pendentes" page is needed.
   - Recommendation: Add a filter tab `?status=aguardando_confirmacao` to the existing `painel_pedidos` page, with a badge count in the navigation sidebar. This reuses existing template patterns.

3. **File serving security**
   - What we know: `media/` is served by Nginx directly (no Django auth check). Comprovante files stored under `media/comprovantes/` are publicly accessible if the URL is guessed.
   - What's unclear: Whether direct URL guessing is a real concern for this use case.
   - Recommendation: Use `upload_to='comprovantes/%Y/%m/<uuid>/'` to make paths unguessable. For production serving through Nginx without extra configuration, this is sufficient. Do not implement Django-authenticated file serving (no `X-Accel-Redirect` for now — out of scope complexity).

---

## Sources

### Primary (HIGH confidence)
- Direct file inspection: `apps/pagamentos/models.py`, `services.py`, `views.py`, `urls.py`, `admin.py`
- Direct file inspection: `apps/pedidos/models.py`, `views.py`, `services.py`, `admin.py`
- Direct file inspection: `apps/core/algorithms.py` — BFS graph at lines 95-102
- Direct file inspection: `config/settings.py` — sessions, media, payment gateway config
- Direct file inspection: `config/context_processors.py` — `pago=True` gate at line 52
- Direct file inspection: `apps/restaurantes/views.py` — `painel_pedidos` at line 350-353, `painel_dashboard` at line 72

### Secondary (MEDIUM confidence)
- CONCERNS.md audit (project-generated 2026-04-02) — stale Stripe references and migration state
- STACK.md, INTEGRATIONS.md, ARCHITECTURE.md, STRUCTURE.md (project-generated 2026-04-02)

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- What to remove: HIGH — inspected every referenced file and line
- Session behavior: HIGH — inspected `settings.py`, `pedidos/views.py` checkout, Django built-in session defaults
- Order status machine changes: HIGH — inspected `algorithms.py` graph definition and all consumers
- File upload pattern: HIGH — Pillow present, `MEDIA_ROOT` configured, existing `ImageField` usage in `Produto`
- Migration ordering: HIGH — inspected all six existing pagamentos migrations and both pending ones

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable stack — Django 4.2 LTS, no external services)
