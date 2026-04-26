# Phase 3: Revisão Manual e Auditoria - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Estruturar a revisao manual de pagamentos PIX com fila operacional no painel, justificativa obrigatoria nas decisoes e trilha auditavel por pedido, mantendo o fluxo manual sem gateway/webhook.

</domain>

<decisions>
## Implementation Decisions

### Fila Operacional
- **D-01:** A fila de revisao manual deve ser ordenada por pedidos mais novos primeiro.
- **D-02:** O unico filtro operacional da fila sera por periodo.
- **D-03:** O filtro de periodo tera as opcoes: Hoje, Ontem, 7 dias, 30 dias e personalizado.
- **D-04:** A tela de pedidos permanece com visao padrao de "Todos os pedidos", mantendo a secao destacada de "Aguardando PIX".

### Justificativa Obrigatoria
- **D-05:** Justificativa sera obrigatoria tanto para aprovar quanto para rejeitar pagamento PIX.
- **D-06:** O texto complementar da justificativa tera minimo de 10 caracteres.
- **D-07:** O formulario de decisao usara motivo estruturado (dropdown) mais texto complementar.
- **D-08:** Dropdown inicial de motivos: valido, invalido e outro.

### Auditoria de Decisoes
- **D-09:** Cada decisao manual (aprovar/rejeitar) registrara no historico apenas acao e data/hora.
- **D-10:** O historico de auditoria sera exibido somente no detalhe do pedido.

### the agent's Discretion
- Definir implementacao tecnica da persistencia de auditoria (modelo dedicado vs reutilizacao de estrutura existente), respeitando D-09 e D-10.
- Definir UX exata do controle de periodo (atalhos, datas e validacao), respeitando D-02 e D-03.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Escopo e Requisitos
- `.planning/ROADMAP.md` — meta da Phase 3 e criterios de sucesso (fila, justificativa, historico).
- `.planning/REQUIREMENTS.md` — requisitos OPS-01, OPS-02 e OPS-03.
- `.planning/PROJECT.md` — restricao de manter fluxo manual sem gateway/webhook.
- `.planning/STATE.md` — estado atual do projeto e decisoes ja consolidadas da fase anterior.

### Fluxo de Revisao Manual Existente
- `apps/restaurantes/views.py` — `painel_pedidos` e `painel_pedido_detalhe` com fila atual por `aguardando_confirmacao`.
- `templates/painel/pedidos.html` — secao destacada de pendentes PIX e filtros atuais.
- `templates/painel/pedido_detalhe.html` — acoes manuais de aceitar/rejeitar e visualizacao de comprovante.

### Servicos e Contratos de Pagamento
- `apps/pagamentos/views.py` — endpoints `aceitar_pix`, `rejeitar_pix` e fluxo de upload.
- `apps/pagamentos/services.py` — `confirmar_pix_manual` e `rejeitar_pix_manual` com efeitos de status/pago.
- `apps/pagamentos/models.py` — modelos `Pagamento` e estruturas relacionadas ao fluxo PIX.
- `apps/pedidos/models.py` — estados de pedido incluindo `aguardando_confirmacao`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/restaurantes/views.py:painel_pedidos` ja separa pendentes PIX e permite filtro por querystring.
- `templates/painel/pedidos.html` ja possui bloco visual dedicado para revisao de pedidos aguardando PIX.
- `templates/painel/pedido_detalhe.html` ja centraliza comprovante e botoes de aprovacao/rejeicao.

### Established Patterns
- Guardas de acesso usam `login_required` + restaurante do usuario logado.
- Pipeline principal continua guiado por `pedido.pago=True` para producao/dashboard.
- Decisoes manuais atuais operam via POST com mensagens de feedback e redirecionamento no painel.

### Integration Points
- Adicionar justificativa obrigatoria no fluxo de `aceitar_pix` e `rejeitar_pix`.
- Enriquecer listagem `painel_pedidos` com filtro de periodo definido em D-03.
- Exibir trilha auditavel no `painel_pedido_detalhe` sem criar nova tela agregada nesta fase.

</code_context>

<specifics>
## Specific Ideas

- Prioridade operacional para pedidos mais recentes na fila de revisao.
- Auditoria propositalmente minima (acao + data/hora) e visivel apenas no detalhe do pedido.

</specifics>

<deferred>
## Deferred Ideas

- Visao agregada de auditoria fora do detalhe do pedido (ex.: tela central de historico) ficou fora das decisoes desta fase.
- Enriquecimento de trilha com operador e motivo completo ficou explicitamente nao adotado nesta rodada.

</deferred>

---

*Phase: 03-revis-o-manual-e-auditoria*
*Context gathered: 2026-04-11*
