---
phase: "01"
plan: "01"
subsystem: pagamentos
tags: [migrations, cleanup, pix-manual, pre-flight]
dependency_graph:
  requires: []
  provides: [clean-codebase, pix-key-config, test-scaffold]
  affects: [apps/pagamentos, apps/pedidos, config/settings.py]
tech_stack:
  added: []
  patterns: [pix-manual-payment, no-external-gateway]
key_files:
  created:
    - apps/pagamentos/tests/test_views.py
    - apps/pedidos/tests/test_status.py
  modified:
    - requirements.txt
    - config/settings.py
    - .env.example
    - apps/pedidos/admin.py
    - apps/pagamentos/serializers.py
    - apps/pagamentos/api_views.py
    - apps/pagamentos/services.py
    - apps/pagamentos/views.py
    - apps/pagamentos/urls.py
    - apps/pagamentos/tests/test_services.py
decisions:
  - "Rewrote services.py as PIX manual only — no external gateway calls"
  - "Removed mp-webhook and mp-return URL patterns from urls.py"
  - "Replaced stale Stripe test_services.py with PIX manual scaffold"
metrics:
  duration_minutes: 6
  completed_date: "2026-04-03"
  tasks_completed: 3
  files_changed: 10
---

# Phase 01 Plan 01: Pre-flight (Wave 0) Summary

**One-liner:** Applied pending migrations, purged Mercado Pago SDK and all stale Stripe/MP references, wired PIX_KEY into settings, and created empty test scaffold files for Wave 1+.

## What Was Done

### Task 1: Apply pending migrations and purge Mercado Pago from requirements and settings

- Confirmed migrations `0006_switch_to_mercadopago` (pagamentos) and `0008_rename_payment_field` (pedidos) were already applied to the database.
- Removed `mercadopago==2.3.0` from `requirements.txt`.
- Replaced the `PAYMENT_GATEWAY` / `MP_ACCESS_TOKEN` / `MP_PIX_PAYER_EMAIL` block in `config/settings.py` with `PIX_KEY = os.getenv('PIX_KEY', '')`.
- Updated `.env.example`: removed all MP/gateway vars, added `PIX_KEY=seu_cpf_ou_cnpj_ou_chave_pix`.

### Task 2: Fix stale Stripe/MP field references in admin, serializer, and api_views

- `apps/pedidos/admin.py`: changed `stripe_payment_intent_id` → `external_payment_id` in `PedidoAdmin.fieldsets`.
- `apps/pagamentos/serializers.py`: replaced `stripe_payment_intent_id` with `external_payment_id` in `PagamentoSerializer.fields`.
- `apps/pagamentos/api_views.py`: removed `client_secret` key from the `criar_pagamento_api` Response dict (was causing KeyError).
- `apps/pagamentos/services.py`: rewrote entirely — removed `import mercadopago`, removed all MP SDK calls, implemented PIX manual flow (`_criar_pagamento_pix_manual`).
- `apps/pagamentos/views.py`: removed `confirmar_pagamento_mp` and `processar_webhook_mp` imports; simplified views to PIX manual flow.
- `apps/pagamentos/urls.py`: removed stale MP URL patterns (`mp-webhook/`, `mp-return/`, `iniciar_pagamento_mp`).

### Task 3: Create empty test scaffold packages for pagamentos and pedidos

- `apps/pagamentos/tests/__init__.py`: already existed, left intact.
- `apps/pagamentos/tests/test_services.py`: replaced stale Stripe test file with scaffold containing `_make_restaurante()` and `_make_pedido()` factory functions.
- `apps/pagamentos/tests/test_views.py`: created with minimal imports for view integration tests.
- `apps/pedidos/tests/__init__.py`: already existed, left intact.
- `apps/pedidos/tests/test_status.py`: created with imports for BFS graph tests (`GRAFO_STATUS_PEDIDO`, `bfs_caminho_mais_curto`).

## Stale References Removed

| File | Reference Removed | Replaced With |
|------|-------------------|---------------|
| `requirements.txt` | `mercadopago==2.3.0` | (removed) |
| `config/settings.py` | `PAYMENT_GATEWAY`, `MP_ACCESS_TOKEN`, `MP_PIX_PAYER_EMAIL` | `PIX_KEY` |
| `.env.example` | `PAYMENT_GATEWAY`, `MP_ACCESS_TOKEN`, `MP_PIX_PAYER_EMAIL` | `PIX_KEY` |
| `apps/pedidos/admin.py` | `stripe_payment_intent_id` in fieldsets | `external_payment_id` |
| `apps/pagamentos/serializers.py` | `stripe_payment_intent_id` in fields | `external_payment_id` |
| `apps/pagamentos/api_views.py` | `client_secret` key in Response | (removed) |
| `apps/pagamentos/services.py` | `import mercadopago`, all MP SDK calls | PIX manual flow |
| `apps/pagamentos/views.py` | `confirmar_pagamento_mp`, `processar_webhook_mp` imports | (removed) |
| `apps/pagamentos/urls.py` | `mp-webhook/`, `mp-return/`, `iniciar_pagamento_mp` patterns | (removed) |

## Test Scaffold Available

Factory functions available in `apps/pagamentos/tests/test_services.py`:
- `_make_restaurante()` — creates a `Restaurante` with a linked `User`
- `_make_pedido(restaurante)` — creates a minimal `Pedido` in `'aguardando'` state

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] services.py imported mercadopago SDK at module level**
- **Found during:** Task 2
- **Issue:** `apps/pagamentos/services.py` had `import mercadopago` at the top. Removing the SDK from `requirements.txt` would cause an `ImportError` on every Django startup, blocking all URLs.
- **Fix:** Rewrote `services.py` to implement PIX manual flow without any external SDK. Removed all `_criar_pagamento_mp*`, `confirmar_pagamento_mp`, and `processar_webhook_mp` functions. Added `_criar_pagamento_pix_manual()`.
- **Files modified:** `apps/pagamentos/services.py`
- **Commit:** 6e36606

**2. [Rule 3 - Blocking] views.py imported removed functions from services.py**
- **Found during:** Task 2
- **Issue:** `apps/pagamentos/views.py` imported `confirmar_pagamento_mp` and `processar_webhook_mp` which were removed from services. Also referenced `settings.PAYMENT_GATEWAY` which was removed.
- **Fix:** Rewrote views.py removing all MP-specific views (`iniciar_pagamento_mp`, `mp_checkout_return`, `mp_webhook`). Simplified to PIX manual flow.
- **Files modified:** `apps/pagamentos/views.py`, `apps/pagamentos/urls.py`
- **Commit:** 6e36606

**3. [Rule 3 - Blocking] test_services.py imported confirmar_pagamento_stripe (non-existent)**
- **Found during:** Task 3
- **Issue:** Pre-existing `apps/pagamentos/tests/test_services.py` imported `confirmar_pagamento_stripe` from services — a function that never existed in the codebase. Would cause `ImportError` on test run.
- **Fix:** Replaced the stale file with the scaffold from the plan specification.
- **Files modified:** `apps/pagamentos/tests/test_services.py`
- **Commit:** d9ecec7

## Known Stubs

None — this plan is pre-flight only. The `PIX_KEY` setting returns an empty string by default until the operator sets the env var, but this is by design (documented in `.env.example`).

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 11a4fdb | `chore(01-01): apply pending migrations, remove MP SDK, wire PIX_KEY` |
| 2 | 6e36606 | `fix(01-01): remove stale Stripe/MP field refs, purge MP SDK imports` |
| 3 | d9ecec7 | `test(01-01): create test scaffold packages for pagamentos and pedidos` |

## Self-Check: PASSED
