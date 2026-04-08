---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Phase 01 Complete
stopped_at: Completed 01-05-PLAN.md
last_updated: "2026-04-08T00:15:11.962Z"
progress:
  total_phases: 1
  completed_phases: 1
  total_plans: 5
  completed_plans: 5
---

# State: Cardapio Online

## Current Focus

Phase 01: Pagamento PIX Manual

## Position

Wave 5 — Plan 01-05 (Integracao final, limpeza e validacao E2E)

## Plans

- [x] 01-01: Pre-flight (migracoes pendentes, limpeza de referencias gateway e configuracao PIX_KEY)
- [x] 01-02: Modelo de dados e grafo de status (aguardando_confirmacao + comprovante)
- [x] 01-03: Fluxo cliente PIX manual (pagina, copia, upload)
- [x] 01-04: Fluxo restaurante (filtro, visualizacao comprovante, aceitar/recusar)
- [x] 01-05: Integracao final, limpeza e validacao E2E

## Decisions

- Rewrote services.py as PIX manual only — no external gateway API calls
- Removed mp-webhook and mp-return URL patterns (MP flow eliminated)
- Replaced stale Stripe test_services.py with PIX manual scaffold
- BFS graph: aguardando now routes exclusively through aguardando_confirmacao before recebido
- Pedido.status max_length extended from 10 to 25 to fit aguardando_confirmacao (21 chars)
- mercadopago GATEWAY_CHOICES label changed to descontinuado to preserve existing DB rows
- FileExtensionValidator restricts comprovante to jpg, jpeg, png, webp, pdf only
- services.py replaced with criar_pagamento_pix_manual, confirmar_pix_manual, rejeitar_pix_manual (all idempotent)
- upload_comprovante transitions pedido to aguardando_confirmacao; pago stays False until restaurant confirms
- pagamento_escolher URL name replaced by pagamento_pix_manual
- painel_pedido_detalhe pago=True gate replaced by Http404 guard allowing aguardando_confirmacao orders
- painel_pedidos now shows pendentes_pix section above main table; paginate only pago=True orders
- aguardando_confirmacao_count surfaced via context processor for nav badge
- [Phase 01]: Success page now clarifies aguardando_confirmacao: upload received, restaurant confirms before production.
- [Phase 01]: Checkpoint human-verify approved as blocking gate before phase completion.

## Performance Metrics

| Phase | Plan | Duration (min) | Tasks | Files |
|-------|------|----------------|-------|-------|
| 01 | 01 | 6 | 3 | 10 |
| 01 | 02 | 4 | 2 | 8 |
| 01 | 03 | 9 | 2 | 8 |
| 01 | 04 | 5 | 2 | 7 |
| Phase 01 P05 | 8 | 2 tasks | 4 files |

## Last Session

Stopped at: Completed 01-05-PLAN.md
Date: 2026-04-08
