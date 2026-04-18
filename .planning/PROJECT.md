# Cardapio Online

## What This Is

Sistema de pedidos online para restaurantes com pagamento via PIX e operação assistida pelo painel do estabelecimento. O produto prioriza simplicidade operacional para o restaurante e uma jornada de pagamento clara para o cliente.

## Core Value

Receber pedidos pagos com segurança e baixo atrito operacional, sem quebrar o fluxo de produção do restaurante.

## Current Milestone: v1.2 Acompanhamento de Pedido

**Goal:** Cliente acompanha o status do proprio pedido em tempo real sem precisar entrar em contato com o restaurante.

**Target features:**
- Pagina publica de status por pedido com URL persistente (/pedido/<id>/status)
- Atualizacao automatica via polling (sem reload manual, sem WebSocket)
- 4 estados visiveis: Aguardando PIX → Confirmado → Pronto → Entregue
- Transicoes de status atreladas a acoes ja existentes no painel (sem novos botoes de avanco manual)
- Link de acompanhamento exibido na tela de confirmacao do pedido

## Requirements

### Validated

- ✓ Cliente copia chave PIX e envia comprovante — v1.0 / Phase 1
- ✓ Restaurante valida pagamento e decide aceitar/rejeitar antes da produção — v1.0 / Phase 1
- ✓ Pipeline existente segue intacto após confirmação — v1.0 / Phase 1
- ✓ Cadastro e gestão de múltiplas chaves PIX por restaurante — v1.1 / Phase 2
- ✓ Regras para escolher chave PIX por contexto de pedido/canal — v1.1 / Phase 2
- ✓ Tratamento de revisao manual com fila, justificativa e historico operacional — v1.1 / Phase 3

### Active

- [ ] Cliente acessa pagina publica de status do proprio pedido via URL persistente — v1.2
- [ ] Status atualiza automaticamente via polling sem reload manual — v1.2
- [ ] 4 estados de pedido visiveis: Aguardando PIX, Confirmado, Pronto, Entregue — v1.2
- [ ] Transicoes de status atreladas a acoes ja existentes no painel — v1.2
- [ ] Link de acompanhamento exibido na confirmacao do pedido — v1.2

### Out of Scope

- Confirmacao automatica por webhook/gateway — fora do escopo do produto atual
- Reembolso automatizado — ainda fora do escopo por impacto operacional/financeiro
- Split de pagamento entre múltiplos recebedores — dependência de regras contábeis não definidas

## Context

Milestone v1.0 entregou fluxo PIX manual completo com upload de comprovante e aprovacao no painel. O ciclo v1.1 foi concluido com suporte a multiplas chaves PIX por restaurante e revisao manual operacional com filtros, justificativa obrigatoria e trilha auditavel.

## Current State

- v1.1 concluido e arquivado em `.planning/milestones/v1.1-ROADMAP.md` e `.planning/milestones/v1.1-REQUIREMENTS.md`.
- Fluxo manual PIX consolidado sem gateway/webhook.
- Proximo passo de produto: abrir novo milestone e definir requisitos futuros.

## Constraints

- **Tech stack**: Django monolito atual — manter consistência com arquitetura existente.
- **Backward compatibility**: Fluxo manual atual deve continuar operando enquanto as melhorias entram em producao.
- **No gateway/no webhook**: Confirmacao continua manual; nao introduzir integracao externa de pagamento.
- **Operational safety**: Toda aprovacao/rejeicao manual deve deixar trilha auditavel.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| PIX manual como base inicial | Reduzir custo e complexidade de gateway | ✓ Good |
| `pago=True` como gate do painel/produção | Reaproveitar pipeline já estável | ✓ Good |
| Manter modelo sem gateway no v1.1 | Preservar simplicidade operacional e evitar complexidade externa | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition**:
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone**:
1. Full review of all sections
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-17 — milestone v1.2 started*
