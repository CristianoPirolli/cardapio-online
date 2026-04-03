---
phase: "01"
plan: "04"
subsystem: pagamentos
tags: [pix-manual, restaurant-flow, painel, views, templates, context-processor]
dependency_graph:
  requires: [phase-01-plan-03]
  provides: [aceitar_pix-view, rejeitar_pix-view, pix-confirmation-painel-ui, aguardando-confirmacao-nav-badge]
  affects: [apps/pagamentos/views.py, apps/pagamentos/urls.py, apps/restaurantes/views.py, config/context_processors.py, templates/painel/pedido_detalhe.html, templates/painel/pedidos.html, templates/painel/base_painel.html]
tech_stack:
  added: []
  patterns: [login-required-guard, restaurant-ownership-gate, Http404-guard-for-unpaid-orders, context-processor-count]
key_files:
  created: []
  modified:
    - apps/pagamentos/views.py
    - apps/pagamentos/urls.py
    - apps/restaurantes/views.py
    - config/context_processors.py
    - templates/painel/pedido_detalhe.html
    - templates/painel/pedidos.html
    - templates/painel/base_painel.html
decisions:
  - "painel_pedido_detalhe pago=True gate replaced by Http404 guard: pedido must be paid OR status=aguardando_confirmacao"
  - "painel_pedidos shows pendentes_pix always at top (no pagination) while pago=True orders are paginated below"
  - "aguardando_confirmacao_count initialized to 0 before conditional block to avoid UnboundLocalError"
metrics:
  duration_minutes: 5
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_changed: 7
---

# Phase 01 Plan 04: Fluxo restaurante PIX Summary

**One-liner:** Added aceitar_pix/rejeitar_pix views with restaurant-ownership guard, updated painel_pedidos to surface aguardando_confirmacao queue, updated painel_pedido_detalhe to show comprovante + accept/reject buttons, and added nav badge via context processor.

## What Was Done

### Task 1: Add accept/reject views + update painel_pedido_detalhe to allow aguardando_confirmacao

- Added `aceitar_pix` and `rejeitar_pix` views to `apps/pagamentos/views.py`.
  - Both are `@login_required` and verify restaurant ownership via `Restaurante.objects.filter(proprietario=request.user).first()`.
  - `aceitar_pix` calls `confirmar_pix_manual(pagamento)` then redirects to `painel_pedido_detalhe`.
  - `rejeitar_pix` calls `rejeitar_pix_manual(pagamento)` then redirects to `painel_pedidos`.
- Registered URL patterns `<int:pedido_id>/aceitar/` and `<int:pedido_id>/rejeitar/` in `apps/pagamentos/urls.py`.
- Removed `pago=True` gate from `painel_pedido_detalhe` in `apps/restaurantes/views.py`; replaced with Http404 guard for orders that are neither paid nor awaiting PIX confirmation.
- Added `pagamento_pix` to `painel_pedido_detalhe` context when `status=aguardando_confirmacao`.
- Updated `painel_pedidos` to build a separate `pendentes_pix` queryset and pass it (with count) to the template context. Standard pago=True orders remain paginated; PIX pending orders are shown above without pagination.

### Task 2: Update context processor and all painel templates

- `config/context_processors.py`: Added `aguardando_confirmacao_count` (initialized to 0 before the conditional block) queried from `Pedido.objects.filter(status='aguardando_confirmacao')`.
- `templates/painel/base_painel.html`: Added yellow warning badge next to Pedidos nav link displaying `aguardando_confirmacao_count` when > 0.
- `templates/painel/pedido_detalhe.html`:
  - Added `aguardando_confirmacao` case to the status badge block (bg-warning text-dark).
  - Added Comprovante PIX card with link to uploaded file + Aceitar/Rejeitar form buttons (POST to `aceitar_pix`/`rejeitar_pix`).
  - Hid the standard status-update buttons when `status=aguardando_confirmacao`.
- `templates/painel/pedidos.html`:
  - Added "Aguardando PIX" filter tab with count badge.
  - Added a highlighted (border-warning/bg-warning) section above the main table showing all `pendentes_pix` orders.

## New URL Names

| URL Name | Path | View |
|----------|------|------|
| `aceitar_pix` | `/pagamentos/<id>/aceitar/` | `aceitar_pix` |
| `rejeitar_pix` | `/pagamentos/<id>/rejeitar/` | `rejeitar_pix` |

## Context Variables Added

| Variable | Source | Used In |
|----------|--------|---------|
| `aguardando_confirmacao_count` | `context_processors.py` | `base_painel.html` nav badge |
| `pagamento_pix` | `painel_pedido_detalhe` view | `pedido_detalhe.html` comprovante card |
| `pendentes_pix` | `painel_pedidos` view | `pedidos.html` highlighted section |
| `pendentes_pix_count` | `painel_pedidos` view | `pedidos.html` filter tab badge |

## Template Sections Changed

| File | Change | Lines (approx) |
|------|--------|----------------|
| `base_painel.html` | Added aguardando_confirmacao_count warning badge in Pedidos nav item | 28-35 |
| `pedido_detalhe.html` | Added aguardando_confirmacao to status badge block | 110-117 |
| `pedido_detalhe.html` | Added Comprovante PIX card with accept/reject forms | 135-175 |
| `pedido_detalhe.html` | Updated status-update card condition to exclude aguardando_confirmacao | 177 |
| `pedidos.html` | Added Aguardando PIX filter tab | 40-48 |
| `pedidos.html` | Added highlighted pending PIX section above main table | 50-92 |

## Test Suite Result

```
Ran 21 tests in 14.1s
OK
```

All 21 tests across `apps.pagamentos.tests` and `apps.pedidos.tests` pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] aguardando_confirmacao_count unbound without initialization**
- **Found during:** Task 2 implementation
- **Issue:** The plan adds `aguardando_confirmacao_count` inside an `if restaurante:` block but references it in the return dict outside. Without initializing to 0 before the conditional, this would raise `UnboundLocalError` on requests from unauthenticated users or non-painel paths.
- **Fix:** Added `aguardando_confirmacao_count = 0` immediately after `pedidos_abertos_count = 0` initialization.
- **Files modified:** `config/context_processors.py`
- **Commit:** 7120543

## Known Stubs

None — all views fully wired. The comprovante link uses `pagamento_pix.comprovante.url` which is the real uploaded file URL. Accept/reject forms POST to real views calling real service functions.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 6c789c6 | `feat(01-04): add aceitar/rejeitar PIX views, update painel_pedidos and painel_pedido_detalhe` |
| 2 | 7120543 | `feat(01-04): update context processor and painel templates for PIX confirmation flow` |

## Self-Check: PASSED
