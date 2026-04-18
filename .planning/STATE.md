---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Acompanhamento de Pedido
status: Defining requirements
last_updated: "2026-04-17T00:00:00.000Z"
last_activity: 2026-04-17
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# State: Cardapio Online

## Current Focus

Definir requisitos e roadmap para milestone v1.2

## Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-17 — Milestone v1.2 started

## Plans

_(nenhum plano ainda — milestone v1.2 em definicao)_

## Decisions

- v1.0 consolidado com fluxo PIX manual estável.
- v1.1 mantera fluxo manual (sem gateway/webhook) com multiplas chaves PIX.
- Revisao manual tera trilha auditavel e justificativas operacionais.
- [Phase 02]: Constraints condicionais por restaurante para chave PIX padrao/prioridade ativa.
- [Phase 02]: Checkout passa a usar snapshot persistido de chave PIX por pagamento, sem fallback global.
- [Phase 02-gest-o-de-chaves-pix]: Tela principal de chaves PIX em /painel/chaves-pix/ com mutacoes via endpoints dedicados.
- [Phase 02-gest-o-de-chaves-pix]: Historico operacional restrito a mutacoes de painel, sem incluir eventos de selecao no checkout.
- [Phase 03-revis-o-manual-e-auditoria]: Contexto decidido com fila por recencia, filtro por periodo, justificativa obrigatoria (aprovar/rejeitar) e auditoria minima (acao + data/hora).
- [Phase 03]: Filtro operacional aplicado apenas na fila Aguardando PIX, preservando visao padrao de pedidos.
- [Phase 03]: Historico de revisao permanece visivel somente no detalhe e com campos minimos de exibicao.
- [Phase 03]: Registro operacional de decisao inclui operador e timestamp para auditoria interna, com feed minimo na interface.
- [v1.2]: Acompanhamento de pedido via polling (sem WebSocket); transicoes automaticas por acoes existentes no painel.

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-17)

**Core value:** Receber pedidos pagos com segurança e baixo atrito operacional.
**Current focus:** definir requisitos e roadmap do milestone v1.2
