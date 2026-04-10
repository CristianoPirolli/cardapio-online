# Roadmap: Cardapio Online

## Overview

Roadmap do v1.1 focado em fortalecer o fluxo PIX manual sem gateway: multiplas chaves por restaurante e operacao de revisao manual com auditoria.

## Milestones

- ✅ **v1.0 milestone** — Phase 1 (shipped 2026-04-08)
- 🚧 **v1.1 Operacao Manual PIX** — Phases 2-3 (in progress)

## Phases

<details>
<summary>✅ v1.0 milestone (Phase 1) — SHIPPED 2026-04-08</summary>

- [x] Phase 1: Pagamento PIX Manual (5/5 plans)

</details>

- [x] **Phase 2: Gestão de Chaves PIX** - Suporte a multiplas chaves PIX e regras de selecao no checkout
- [ ] **Phase 3: Revisão Manual e Auditoria** - Melhorar fila manual, justificativas e historico operacional

## Phase Details

### Phase 2: Gestão de Chaves PIX
**Goal**: Suportar multiplas chaves PIX por restaurante e aplicar regras de selecao no checkout mantendo o fluxo manual atual.
**Depends on**: Phase 1
**Requirements**: [PAY-15, PAY-16, PAY-17, PAY-18]
**Success Criteria** (what must be TRUE):
  1. Restaurante cadastra e gerencia multiplas chaves PIX sem interromper operacao
  2. Checkout mostra a chave correta conforme regra configurada
  3. Pedidos em andamento preservam consistencia mesmo com ativacao/desativacao de chaves
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Base de dados/servicos para chave PIX por restaurante com selecao deterministica e snapshot no pagamento
- [x] 02-02-PLAN.md — Gestao completa no painel (CRUD + historico) e integracao de navegacao/regressao

### Phase 3: Revisão Manual e Auditoria
**Goal**: Estruturar a revisao manual de pagamentos com fila operacional, justificativas e trilha auditavel.
**Depends on**: Phase 2
**Requirements**: [OPS-01, OPS-02, OPS-03]
**Success Criteria** (what must be TRUE):
  1. Painel exibe fila de revisao manual com filtros operacionais
  2. Aprovar/rejeitar exige justificativa e registra operador/data
  3. Historico de decisoes fica acessivel para auditoria interna
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Pagamento PIX Manual | v1.0 | 5/5 | Complete | 2026-04-08 |
| 2. Gestão de Chaves PIX | v1.1 | 2/2 | Complete | 2026-04-10 |
| 3. Revisão Manual e Auditoria | v1.1 | 0/TBD | Not started | - |
