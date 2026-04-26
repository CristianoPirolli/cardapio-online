# Roadmap: Cardapio Online

## Overview

Roadmap ativo para o proximo milestone. Milestones concluidos foram arquivados em `.planning/milestones/`.

## Milestones

- ✅ **v1.0 milestone** — Phase 1 (shipped 2026-04-08)
- ✅ **v1.1 Operacao Manual PIX** — Phases 2-3 (completed 2026-04-11)
- 🔄 **v1.2 Acompanhamento de Pedido** — Phases 4-6 (active)

## Phases

<details>
<summary>✅ v1.0 milestone (Phase 1) — SHIPPED 2026-04-08</summary>

- [x] Phase 1: Pagamento PIX Manual (5/5 plans)

</details>

<details>
<summary>✅ v1.1 Operacao Manual PIX (Phases 2-3) — SHIPPED 2026-04-11</summary>

- [x] Phase 2: Gestao de Chaves PIX (2/2 plans)
- [x] Phase 3: Revisao Manual e Auditoria (2/2 plans)
- Archive: `.planning/milestones/v1.1-ROADMAP.md`

</details>

## Active Milestone: v1.2 Acompanhamento de Pedido

- [ ] **Phase 4: Status Visual Core** — Barra de progresso com 4 estados e polling correto
- [ ] **Phase 5: Link Surfacing** — Link de acompanhamento visivel antes e apos o pagamento
- [ ] **Phase 6: Cancellation UX** — Comunicacao clara de rejeicao com motivo e opcao de reenvio

## Phase Details

### Phase 4: Status Visual Core
**Goal:** Cliente ve o estado real do seu pedido na pagina de acompanhamento, com barra de 4 estados corretamente mapeada, visual distinto para comprovante em analise, polling que para em estados terminais e titulo de pagina refletindo o status atual.
**Depends on:** Phase 3
**Requirements:** TRACK-01, TRACK-02, TRACK-03, TRACK-04
**Success criteria:**
1. Cliente que acabou de subir comprovante ve "Comprovante recebido, aguardando verificacao" com visual diferente de quem ainda nao pagou
2. A barra de progresso avanca por 4 etapas visiveis — Aguardando PIX, Confirmado, Pronto, Entregue — sem pular nem repetir estados
3. Polling cessa automaticamente quando o pedido e concluido ou cancelado, sem que o JS continue fazendo requisicoes em background
4. A aba do navegador exibe o estado atual do pedido no titulo da pagina (ex: "Pedido Confirmado — Cardapio Online")
**Plans:** TBD
**UI hint:** yes

### Phase 5: Link Surfacing
**Goal:** Cliente encontra o link de acompanhamento do proprio pedido nos momentos certos da jornada — antes de subir o comprovante, na tela de confirmacao, e ao ser redirecionado em caso de cancelamento.
**Depends on:** Phase 4
**Requirements:** TRACK-05, TRACK-06, TRACK-07
**Success criteria:**
1. Na pagina da chave PIX (antes de subir comprovante), cliente ve um link visivel que leva direto a pagina de acompanhamento do pedido atual
2. Na tela de confirmacao apos subir comprovante, cliente ve a URL de acompanhamento de forma copiavel ou bookmarkavel, alem do botao existente
3. Pedido cancelado exibe link do WhatsApp do restaurante com numero do pedido pre-preenchido na mensagem
**Plans:** TBD
**UI hint:** yes

### Phase 6: Cancellation UX
**Goal:** Cliente cujo pedido foi rejeitado entende exatamente o motivo e sabe qual caminho seguir — reenviar comprovante ou contatar o restaurante.
**Depends on:** Phase 5
**Requirements:** TRACK-08, TRACK-09
**Success criteria:**
1. Pagina de acompanhamento de pedido cancelado exibe o motivo de rejeicao registrado pelo restaurante (proveniente de PagamentoRevisaoHistorico), nao uma mensagem generica
2. Apos rejeicao de PIX, cliente ve opcao clara para reenviar o comprovante sem precisar recomecar o pedido do zero
**Plans:** TBD
**UI hint:** yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Pagamento PIX Manual | v1.0 | 5/5 | Complete | 2026-04-08 |
| 2. Gestão de Chaves PIX | v1.1 | 2/2 | Complete | 2026-04-10 |
| 3. Revisão Manual e Auditoria | v1.1 | 2/2 | Complete | 2026-04-11 |
| 4. Status Visual Core | v1.2 | 0/? | Not started | - |
| 5. Link Surfacing | v1.2 | 0/? | Not started | - |
| 6. Cancellation UX | v1.2 | 0/? | Not started | - |
