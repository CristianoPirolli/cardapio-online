---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Operacao Manual PIX
status: Phase 2 in progress
last_updated: "2026-04-11T00:02:00.000Z"
last_activity: 2026-04-11
progress:
  total_phases: 2
  completed_phases: 0
  total_plans: 2
  completed_plans: 1
---

# State: Cardapio Online

## Current Focus

Phase 2: Gestão de Chaves PIX

## Position

Phase: 02-gest-o-de-chaves-pix (in progress)
Plan: 02-02 pending (02-01 completed)
Status: 02-01 concluido e validado
Last activity: 2026-04-11

## Plans

- [x] 01-01: Pre-flight (migracoes pendentes, limpeza de referencias gateway e configuracao PIX_KEY)
- [x] 01-02: Modelo de dados e grafo de status (aguardando_confirmacao + comprovante)
- [x] 01-03: Fluxo cliente PIX manual (pagina, copia, upload)
- [x] 01-04: Fluxo restaurante (filtro, visualizacao comprovante, aceitar/recusar)
- [x] 01-05: Integracao final, limpeza e validacao E2E

## Decisions

- v1.0 consolidado com fluxo PIX manual estável.
- v1.1 mantera fluxo manual (sem gateway/webhook) com multiplas chaves PIX.
- Revisao manual tera trilha auditavel e justificativas operacionais.
- [Phase 02]: Constraints condicionais por restaurante para chave PIX padrao/prioridade ativa.
- [Phase 02]: Checkout passa a usar snapshot persistido de chave PIX por pagamento, sem fallback global.

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-10)

**Core value:** Receber pedidos pagos com segurança e baixo atrito operacional.
**Current focus:** Phase 02 — gest-o-de-chaves-pix
