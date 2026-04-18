---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Acompanhamento de Pedido
status: active
last_updated: "2026-04-17T00:00:00.000Z"
last_activity: 2026-04-17
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# State: Cardapio Online

## Current Focus

Phase 4: Status Visual Core — definir mapeamento customer_status e corrigir barra de progresso

## Position

Phase: 4 — Status Visual Core
Plan: —
Status: Not started
Last activity: 2026-04-17 — Phase 4 context gathered

## Plans

_(nenhum plano ainda — Phase 4 aguarda planejamento)_

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
- [v1.2]: Mapeamento customer_status (7 estados internos → 4 estados visiveis) deve ser decidido em Phase 4 antes de qualquer trabalho em template ou JS.
- [v1.2]: Nenhuma dependencia nova — Django built-ins e vanilla JS ja presentes em acompanhar.html.

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-17)

**Core value:** Receber pedidos pagos com segurança e baixo atrito operacional.
**Current focus:** Phase 4 — Status Visual Core (v1.2)
