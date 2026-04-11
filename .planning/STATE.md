---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Operacao Manual PIX
status: Milestone v1.1 arquivado; aguardando definicao do proximo milestone
last_updated: "2026-04-11T12:50:56.492Z"
last_activity: 2026-04-11
progress:
  total_phases: 2
  completed_phases: 2
  total_plans: 4
  completed_plans: 4
---

# State: Cardapio Online

## Current Focus

Planejar proximo milestone

## Position

Phase: 03
Plan: Complete
Status: Milestone v1.1 arquivado; aguardando definicao do proximo milestone
Last activity: 2026-04-11

## Plans

- [x] 01-01: Pre-flight (migracoes pendentes, limpeza de referencias gateway e configuracao PIX_KEY)
- [x] 01-02: Modelo de dados e grafo de status (aguardando_confirmacao + comprovante)
- [x] 01-03: Fluxo cliente PIX manual (pagina, copia, upload)
- [x] 01-04: Fluxo restaurante (filtro, visualizacao comprovante, aceitar/recusar)
- [x] 01-05: Integracao final, limpeza e validacao E2E
- [x] 02-01: Base de dados/servicos para chaves PIX por restaurante
- [x] 02-02: Gestao no painel (CRUD + historico) e integracao de navegacao/regressao
- [x] 03-01: Contrato de decisao manual com justificativa obrigatoria e persistencia auditavel por pedido
- [x] 03-02: Fila operacional com filtro por periodo e exibicao da trilha no detalhe do pedido

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

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-11)

**Core value:** Receber pedidos pagos com segurança e baixo atrito operacional.
**Current focus:** iniciar novo milestone com `$gsd-new-milestone`
