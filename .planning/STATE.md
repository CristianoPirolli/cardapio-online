---
status: in_progress
phase: "01"
phase_name: pagamento-pix-manual
last_activity: 2026-04-03
current_focus: "Phase 01: Pagamento PIX Manual"
current_position: "Wave 1 — Plan 01-02 (Modelo de dados e grafo de status)"
plans_total: 5
plans_complete: 1
---

# State: Cardapio Online

## Current Focus
Phase 01: Pagamento PIX Manual

## Position
Wave 1 — Plan 01-02 (Modelo de dados e grafo de status: aguardando_confirmacao + comprovante)

## Plans
- [x] 01-01: Pre-flight (migracoes pendentes, limpeza de referencias gateway e configuracao PIX_KEY)
- [ ] 01-02: Modelo de dados e grafo de status (aguardando_confirmacao + comprovante)
- [ ] 01-03: Fluxo cliente PIX manual (pagina, copia, upload)
- [ ] 01-04: Fluxo restaurante (filtro, visualizacao comprovante, aceitar/recusar)
- [ ] 01-05: Integracao final, limpeza e validacao E2E

## Decisions
- Rewrote services.py as PIX manual only — no external gateway API calls
- Removed mp-webhook and mp-return URL patterns (MP flow eliminated)
- Replaced stale Stripe test_services.py with PIX manual scaffold

## Last Session
Stopped at: Completed Phase 01 Plan 01-01 (Pre-flight)
Date: 2026-04-03
