---
status: in_progress
phase: "01"
phase_name: pagamento-pix-manual
last_activity: 2026-04-03
current_focus: "Phase 01: Pagamento PIX Manual"
current_position: "Wave 3 — Plan 01-04 (Fluxo restaurante: filtro, visualizacao comprovante, aceitar/recusar)"
plans_total: 5
plans_complete: 3
---

# State: Cardapio Online

## Current Focus
Phase 01: Pagamento PIX Manual

## Position
Wave 3 — Plan 01-04 (Fluxo restaurante: filtro, visualizacao comprovante, aceitar/recusar)

## Plans
- [x] 01-01: Pre-flight (migracoes pendentes, limpeza de referencias gateway e configuracao PIX_KEY)
- [x] 01-02: Modelo de dados e grafo de status (aguardando_confirmacao + comprovante)
- [x] 01-03: Fluxo cliente PIX manual (pagina, copia, upload)
- [ ] 01-04: Fluxo restaurante (filtro, visualizacao comprovante, aceitar/recusar)
- [ ] 01-05: Integracao final, limpeza e validacao E2E

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

## Performance Metrics

| Phase | Plan | Duration (min) | Tasks | Files |
|-------|------|----------------|-------|-------|
| 01 | 01 | 6 | 3 | 10 |
| 01 | 02 | 4 | 2 | 8 |
| 01 | 03 | 9 | 2 | 8 |

## Last Session
Stopped at: Completed Phase 01 Plan 01-03 (Fluxo cliente PIX manual)
Date: 2026-04-03
