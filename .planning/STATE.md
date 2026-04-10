---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Conciliação PIX
status: Defining requirements
stopped_at: Milestone v1.1 initialized
last_updated: "2026-04-10T23:02:00.000Z"
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 5
  completed_plans: 5
---

# State: Cardapio Online

## Current Focus

Phase 2: Conciliação Automática PIX

## Position

Phase: Not started (defining requirements)
Plan: -
Status: Defining requirements for v1.1
Last activity: 2026-04-10 — Milestone v1.1 started

## Plans

- [x] 01-01: Pre-flight (migracoes pendentes, limpeza de referencias gateway e configuracao PIX_KEY)
- [x] 01-02: Modelo de dados e grafo de status (aguardando_confirmacao + comprovante)
- [x] 01-03: Fluxo cliente PIX manual (pagina, copia, upload)
- [x] 01-04: Fluxo restaurante (filtro, visualizacao comprovante, aceitar/recusar)
- [x] 01-05: Integracao final, limpeza e validacao E2E

## Decisions

- v1.0 consolidado com fluxo PIX manual estável.
- v1.1 focará em conciliação automática e múltiplas chaves PIX por restaurante.
- Divergências de conciliação seguem para revisão manual (sem auto-aprovação insegura).

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-10)

**Core value:** Receber pedidos pagos com segurança e baixo atrito operacional.
**Current focus:** Phase 2 — Conciliação Automática PIX.
