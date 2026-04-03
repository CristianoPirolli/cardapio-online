---
phase: "01"
plan: "03"
subsystem: pagamentos
tags: [pix-manual, customer-flow, views, templates, tdd, services]
dependency_graph:
  requires: [phase-01-plan-01, phase-01-plan-02]
  provides: [pix-manual-services, customer-pix-page, comprovante-upload-view, pix-upload-template]
  affects: [apps/pagamentos/services.py, apps/pagamentos/views.py, apps/pagamentos/urls.py, apps/pagamentos/api_views.py, templates/pagamentos/pagamento.html, templates/pagamentos/pix_upload.html, apps/pedidos/views.py]
tech_stack:
  added: []
  patterns: [tdd-red-green, idempotent-service, bfs-safe-status-transition, file-size-validation, multipart-form-upload]
key_files:
  created:
    - templates/pagamentos/pix_upload.html
  modified:
    - apps/pagamentos/services.py
    - apps/pagamentos/views.py
    - apps/pagamentos/urls.py
    - apps/pagamentos/api_views.py
    - apps/pagamentos/tests/test_services.py
    - apps/pagamentos/tests/test_views.py
    - templates/pagamentos/pagamento.html
    - apps/pedidos/views.py
decisions:
  - "services.py replaced with three focused functions: criar_pagamento_pix_manual, confirmar_pix_manual, rejeitar_pix_manual — all idempotent"
  - "upload_comprovante transitions pedido to aguardando_confirmacao; pago stays False until restaurant confirms"
  - "File validation: size (10MB) checked before extension to give most relevant error first"
  - "override_settings(STORAGES=StaticFilesStorage) applied to view tests to bypass CompressedManifestStaticFilesStorage in test env"
  - "pagamento_escolher URL name replaced by pagamento_pix_manual in apps/pedidos/views.py redirect"
metrics:
  duration_minutes: 9
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_changed: 8
---

# Phase 01 Plan 03: Fluxo cliente PIX manual Summary

**One-liner:** Replaced old MP-era service functions with criar_pagamento_pix_manual/confirmar_pix_manual/rejeitar_pix_manual, rewrote views.py to pagamento_pix_manual + upload_comprovante, cleaned url patterns, and created pagamento.html (PIX key + copy button) and pix_upload.html (multipart file upload with 10MB + extension validation).

## What Was Done

### Task 1: Replace services.py with PIX manual service functions (TDD)

- Wrote 5 failing tests in `apps/pagamentos/tests/test_services.py` (RED), confirming ImportError on missing functions.
- Replaced `apps/pagamentos/services.py` entirely: removed `criar_pagamento`, `confirmar_pagamento_mock`, `_criar_pagamento_pix_manual` (old internal) and all helper functions.
- Implemented three exported functions:
  - `criar_pagamento_pix_manual(pedido)` — idempotent, reuses existing pendente record, creates new if none exists
  - `confirmar_pix_manual(pagamento)` — idempotent, sets pagamento.status='aprovado', pedido.pago=True, pedido.status='recebido' (via BFS-validated save)
  - `rejeitar_pix_manual(pagamento)` — sets pagamento.status='recusado', pedido.status='cancelado', pedido.pago stays False
- All 8 service tests pass (3 model + 5 service).

### Task 2: Rewrite views, urls, and customer-facing templates (TDD)

- Wrote 5 failing view tests in `apps/pagamentos/tests/test_views.py` (RED).
- Replaced `apps/pagamentos/views.py` with four views: `pagamento_pix_manual`, `upload_comprovante`, `pagamento_sucesso`, `pagamento_erro`.
- Replaced `apps/pagamentos/urls.py` with clean URL patterns: `pagamento_pix_manual`, `upload_comprovante`, `pagamento_sucesso`, `pagamento_erro`.
- Rewrote `templates/pagamentos/pagamento.html`: PIX key display with `id="pix-code"` input and `id="btn-copiar"` button; no `{% load static %}` dependency.
- Created `templates/pagamentos/pix_upload.html`: multipart/form-data file upload form with `hx-boost="false"`, file size and extension help text.
- All 5 view tests pass; 13 total pagamentos tests pass.

## Service Function Signatures

```python
# apps/pagamentos/services.py

def criar_pagamento_pix_manual(pedido) -> Pagamento:
    """Creates or reuses a Pagamento(gateway='pix_manual', status='pendente') for the pedido."""

def confirmar_pix_manual(pagamento) -> Pagamento:
    """Sets pagamento.status='aprovado', pedido.pago=True, pedido.status='recebido'. Idempotent."""

def rejeitar_pix_manual(pagamento) -> Pagamento:
    """Sets pagamento.status='recusado', pedido.status='cancelado', pedido.pago stays False."""
```

## New URL Names

| URL Name | Path | View |
|----------|------|------|
| `pagamento_pix_manual` | `/pagamentos/<id>/` | `pagamento_pix_manual` |
| `upload_comprovante` | `/pagamentos/<id>/upload/` | `upload_comprovante` |
| `pagamento_sucesso` | `/pagamentos/sucesso/<id>/` | `pagamento_sucesso` |
| `pagamento_erro` | `/pagamentos/erro/<id>/` | `pagamento_erro` |

## pagamento_escolher References Updated

| File | Old Reference | New Reference |
|------|---------------|---------------|
| `apps/pedidos/views.py:475` | `redirect('pagamento_escolher', pedido_id=pedido.id)` | `redirect('pagamento_pix_manual', pedido_id=pedido.id)` |

Remaining references in templates (`pix.html`, `mock_cartao.html`, `erro.html`) are in templates that are being phased out in plan 01-05 (final cleanup). These templates are not referenced by the new URL patterns.

## Test Coverage

| Module | Test Class | Tests | Result |
|--------|------------|-------|--------|
| `test_services.py` | `PagamentoModelTest` | 3 | PASS |
| `test_services.py` | `PixManualServiceTest` | 5 | PASS |
| `test_views.py` | `PixManualViewTest` | 5 | PASS |
| **Total** | | **13** | **All pass** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] api_views.py imported criar_pagamento from old services**
- **Found during:** Task 1 (services.py replacement broke api_views import)
- **Issue:** `apps/pagamentos/api_views.py` imported `criar_pagamento` which was removed from services.py.
- **Fix:** Updated import to `criar_pagamento_pix_manual` and simplified response dict (removed dict-return pattern, now returns Pagamento object directly).
- **Files modified:** `apps/pagamentos/api_views.py`
- **Commit:** 3b27048

**2. [Rule 3 - Blocking] views.py imported confirmar_pagamento_mock from old services**
- **Found during:** Task 1 (services.py replacement broke views import at module load time, which blocked URL routing and system check)
- **Issue:** Old `views.py` imported `confirmar_pagamento_mock` and `criar_pagamento` — both removed from services.py.
- **Fix:** Applied full Task 2 view rewrite early to unblock Task 1 tests. This consolidated Tasks 1 and 2 execution but did not change what was delivered.
- **Files modified:** `apps/pagamentos/views.py`, `apps/pagamentos/urls.py`
- **Commit:** 3b27048 (views/urls staged with Task 2 commit 6bdd257)

**3. [Rule 3 - Blocking] pedidos/views.py referenced pagamento_escolher URL name**
- **Found during:** Task 2 cleanup
- **Issue:** `apps/pedidos/views.py:475` redirected to `pagamento_escolher` which no longer exists in urls.py.
- **Fix:** Updated to `pagamento_pix_manual`.
- **Files modified:** `apps/pedidos/views.py`
- **Commit:** 3b27048

**4. [Rule 1 - Bug] View tests failed due to CompressedManifestStaticFilesStorage requiring manifest**
- **Found during:** Task 2 TDD RED verification
- **Issue:** `base.html` uses `{% static %}` and the project's `STORAGES['staticfiles']` is `CompressedManifestStaticFilesStorage` which raises `ValueError: Missing staticfiles manifest entry` when no `collectstatic` has been run.
- **Fix:** Added `@override_settings(STORAGES=...)` to `PixManualViewTest` class to use simple `StaticFilesStorage` during tests.
- **Files modified:** `apps/pagamentos/tests/test_views.py`
- **Commit:** 6bdd257

## Known Stubs

None — all views are fully wired. The `PIX_KEY` setting falls back to empty string if env var not set; this is by design (gracefully warns user in template rather than crashing).

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 3b27048 | `feat(01-03): replace services.py with PIX manual service functions` |
| 2 | 6bdd257 | `feat(01-03): rewrite views, urls, and customer-facing templates for PIX manual flow` |

## Self-Check: PASSED
