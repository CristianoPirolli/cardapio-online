---
phase: "01"
plan: "02"
subsystem: pagamentos
tags: [bfs-graph, migrations, model-changes, pix-manual, tdd]
dependency_graph:
  requires: [phase-01-plan-01]
  provides: [bfs-graph-aguardando-confirmacao, comprovante-field, pix-manual-gateway]
  affects: [apps/core/algorithms.py, apps/pedidos/models.py, apps/pagamentos/models.py, apps/pagamentos/admin.py]
tech_stack:
  added: []
  patterns: [tdd-red-green, bfs-graph-extension, django-filefield, file-extension-validator]
key_files:
  created:
    - apps/pedidos/migrations/0009_extend_status_length.py
    - apps/pagamentos/migrations/0007_add_pix_manual_fields.py
  modified:
    - apps/core/algorithms.py
    - apps/pedidos/models.py
    - apps/pedidos/tests/test_status.py
    - apps/pagamentos/models.py
    - apps/pagamentos/admin.py
    - apps/pagamentos/tests/test_services.py
decisions:
  - "BFS graph: aguardando now routes exclusively through aguardando_confirmacao before recebido (not directly)"
  - "Pedido.status max_length extended from 10 to 25 to fit aguardando_confirmacao (21 chars)"
  - "mercadopago GATEWAY_CHOICES label changed to descontinuado to preserve existing DB rows"
  - "FileExtensionValidator restricts comprovante to jpg, jpeg, png, webp, pdf only"
metrics:
  duration_minutes: 4
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_changed: 8
---

# Phase 01 Plan 02: Modelo de dados e grafo de status Summary

**One-liner:** Inserted aguardando_confirmacao node into the BFS status graph, extended Pedido.status to max_length=25, added comprovante FileField and pix_manual gateway choice to Pagamento model, generated and applied migrations 0009 (pedidos) and 0007 (pagamentos).

## BFS Graph Final State

```python
GRAFO_STATUS_PEDIDO = {
    'aguardando': ['aguardando_confirmacao', 'cancelado'],
    'aguardando_confirmacao': ['recebido', 'cancelado'],
    'recebido': ['preparo', 'cancelado'],
    'preparo': ['entrega', 'cancelado'],
    'entrega': ['concluido', 'cancelado'],
    'concluido': [],
    'cancelado': [],
}
```

## What Was Done

### Task 1: Update BFS graph and Pedido.STATUS_CHOICES + extend status field length

- Updated `GRAFO_STATUS_PEDIDO` in `apps/core/algorithms.py`: inserted `aguardando_confirmacao` node; `aguardando` now transitions to `aguardando_confirmacao` (not directly to `recebido`); `aguardando_confirmacao` transitions to `recebido` or `cancelado`.
- Added `('aguardando_confirmacao', 'Aguardando Confirmação')` to `Pedido.STATUS_CHOICES` (7 entries total).
- Extended `Pedido.status` `max_length` from 10 to 25 (required to store the 21-char value `aguardando_confirmacao`).
- Generated migration `0009_extend_status_length` for pedidos and applied it.
- Added 5 TDD test cases in `apps/pedidos/tests/test_status.py` — all pass.

### Task 2: Add comprovante FileField and pix_manual gateway to Pagamento, migrate

- Added `from django.core.validators import FileExtensionValidator` import to `apps/pagamentos/models.py`.
- Updated `Pagamento.GATEWAY_CHOICES` to include `('pix_manual', 'PIX Manual')`; relabeled `mercadopago` as `Mercado Pago (descontinuado)` to preserve existing DB rows.
- Added `comprovante = models.FileField(upload_to='comprovantes/%Y/%m/', blank=True, null=True, ...)` with `FileExtensionValidator` allowing jpg, jpeg, png, webp, pdf.
- Generated migration `0007_add_pix_manual_fields` for pagamentos and applied it.
- Updated `PagamentoAdmin` fieldsets to include `comprovante` in the Pagamento fieldset.
- Added 3 TDD test cases in `apps/pagamentos/tests/test_services.py` — all pass.

## Migration Files Created

| Migration | App | Description |
|-----------|-----|-------------|
| `0009_extend_status_length.py` | pedidos | Alters `Pedido.status` max_length from 10 to 25 |
| `0007_add_pix_manual_fields.py` | pagamentos | Adds `comprovante` FileField; alters `gateway` choices |

## Test Cases Added

### apps/pedidos/tests/test_status.py (5 cases)

| Test | Result |
|------|--------|
| `test_aguardando_goes_to_aguardando_confirmacao` | PASS |
| `test_aguardando_confirmacao_goes_to_recebido` | PASS |
| `test_aguardando_confirmacao_goes_to_cancelado` | PASS |
| `test_aguardando_does_not_go_directly_to_recebido` | PASS |
| `test_bfs_can_reach_concluido_from_aguardando_confirmacao` | PASS |

### apps/pagamentos/tests/test_services.py (3 cases)

| Test | Result |
|------|--------|
| `test_can_create_pix_manual_pagamento` | PASS |
| `test_comprovante_is_nullable` | PASS |
| `test_pix_manual_in_gateway_choices` | PASS |

**Total: 8 tests, all passing.**

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None — this plan adds model/schema foundation only. No UI or view logic is wired in this wave; that is the responsibility of plans 01-03 (customer flow) and 01-04 (restaurant flow).

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | b8ca248 | `feat(01-02): update BFS graph and Pedido status choices with aguardando_confirmacao` |
| 2 | ef1605e | `feat(01-02): add comprovante FileField and pix_manual gateway to Pagamento` |

## Self-Check: PASSED
