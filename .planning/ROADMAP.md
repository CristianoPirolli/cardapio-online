# Roadmap: Cardapio Online

## Overview

Roadmap do v1.1 focado em reduzir confirmação manual de pagamento e ampliar flexibilidade de cobrança com múltiplas chaves PIX por restaurante.

## Milestones

- ✅ **v1.0 milestone** — Phase 1 (shipped 2026-04-08)
- 🚧 **v1.1 Conciliação PIX** — Phases 2-3 (in progress)

## Phases

<details>
<summary>✅ v1.0 milestone (Phase 1) — SHIPPED 2026-04-08</summary>

- [x] Phase 1: Pagamento PIX Manual (5/5 plans)

</details>

- [ ] **Phase 2: Conciliação Automática PIX** - Integrar webhooks e validação automática com trilha de auditoria
- [ ] **Phase 3: Múltiplas Chaves e Fila de Divergências** - Gestão de chaves PIX e operação assistida para exceções

## Phase Details

### Phase 2: Conciliação Automática PIX
**Goal**: Confirmar pagamentos automaticamente a partir de eventos PIX válidos sem quebrar o fluxo atual.
**Depends on**: Phase 1
**Requirements**: [PAY-15, PAY-16, PAY-17]
**Success Criteria** (what must be TRUE):
  1. Pagamento válido conciliado atualiza pedido para pago sem ação manual
  2. Divergência de valor/identificador não confirma automaticamente
  3. Toda conciliação gera histórico auditável de evento e decisão
**Plans**: TBD

### Phase 3: Múltiplas Chaves e Fila de Divergências
**Goal**: Permitir múltiplas chaves PIX por restaurante e operar exceções de conciliação no painel.
**Depends on**: Phase 2
**Requirements**: [PAY-18, PAY-19, PAY-20, OPS-01, OPS-02]
**Success Criteria** (what must be TRUE):
  1. Restaurante cadastra e gerencia chaves PIX ativas/inativas
  2. Checkout usa chave correta conforme regra configurada
  3. Divergências aparecem em fila com ação de aprovação/rejeição registrada
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Pagamento PIX Manual | v1.0 | 5/5 | Complete | 2026-04-08 |
| 2. Conciliação Automática PIX | v1.1 | 0/TBD | Not started | - |
| 3. Múltiplas Chaves e Fila de Divergências | v1.1 | 0/TBD | Not started | - |
