---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Operacao Manual PIX
status: Phase 2 complete
last_updated: "2026-04-10T23:56:30.000Z"
last_activity: 2026-04-10
progress:
  total_phases: 2
  completed_phases: 1
  total_plans: 2
  completed_plans: 2
---

# State: Cardapio Online

## Current Focus

Phase 3: Revisão Manual e Auditoria

## Position

Phase: 02-gest-o-de-chaves-pix (completed)
Plan: 02-02 completed
Status: Phase 2 concluida com CRUD/historico de chaves PIX no painel
Last activity: 2026-04-10

## Plans

- [x] 01-01: Pre-flight (migracoes pendentes, limpeza de referencias gateway e configuracao PIX_KEY)
- [x] 01-02: Modelo de dados e grafo de status (aguardando_confirmacao + comprovante)
- [x] 01-03: Fluxo cliente PIX manual (pagina, copia, upload)
- [x] 01-04: Fluxo restaurante (filtro, visualizacao comprovante, aceitar/recusar)
- [x] 01-05: Integracao final, limpeza e validacao E2E
- [x] 02-01: Base de dados/servicos para chaves PIX por restaurante
- [x] 02-02: Gestao no painel (CRUD + historico) e integracao de navegacao/regressao

## Decisions

- v1.0 consolidado com fluxo PIX manual estável.
- v1.1 mantera fluxo manual (sem gateway/webhook) com multiplas chaves PIX.
- Revisao manual tera trilha auditavel e justificativas operacionais.
- [Phase 02]: Constraints condicionais por restaurante para chave PIX padrao/prioridade ativa.
- [Phase 02]: Checkout passa a usar snapshot persistido de chave PIX por pagamento, sem fallback global.
- [Phase 02-gest-o-de-chaves-pix]: Tela principal de chaves PIX em /painel/chaves-pix/ com mutacoes via endpoints dedicados.
- [Phase 02-gest-o-de-chaves-pix]: Historico operacional restrito a mutacoes de painel, sem incluir eventos de selecao no checkout.

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-10)

**Core value:** Receber pedidos pagos com segurança e baixo atrito operacional.
**Current focus:** Phase 03 — revisao manual e auditoria
