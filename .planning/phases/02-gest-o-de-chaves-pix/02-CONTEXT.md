# Phase 2: Gestão de Chaves PIX - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Suportar multiplas chaves PIX por restaurante e aplicar regras de selecao no checkout, mantendo o fluxo manual de confirmacao de pagamento sem gateway/webhook.

</domain>

<decisions>
## Implementation Decisions

### Gestão no Painel
- **D-01:** O painel de chaves PIX será **completo** nesta fase (cadastro, edicao, ativacao/desativacao, definicao de padrao, prioridade e historico na mesma tela).
- **D-02:** Validacao avancada por tipo e obrigatoria no cadastro/edicao: CPF, CNPJ, e-mail, telefone e chave aleatoria (UUID).
- **D-03:** Historico operacional na tela deve mostrar no minimo: **quem alterou**, **quando**, **acao** e **antes/depois**.

### Compatibilidade de Fluxo
- **D-04:** Nao introduzir gateway nem webhook nesta fase; confirmacao continua manual pelo restaurante.
- **D-05:** Pedidos em andamento devem permanecer consistentes quando chaves forem ativadas/desativadas.

### the agent's Discretion
- Regra exata de selecao de chave no checkout (padrao vs prioridade/fallback) pode ser detalhada no planejamento, respeitando as decisoes D-01..D-05.
- Estrutura de UX (componentizacao da tela e ordem de blocos) fica a criterio do planner, desde que mantenha operacao clara para o restaurante.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and Product Decisions
- `.planning/ROADMAP.md` — define meta da Phase 2 e criterios de sucesso.
- `.planning/REQUIREMENTS.md` — requisitos PAY-15..PAY-18 desta fase.
- `.planning/PROJECT.md` — decisao de manter modelo sem gateway/webhook no v1.1.

### Existing Payment Flow Contracts
- `apps/pagamentos/models.py` — modelo Pagamento atual e campos reutilizaveis.
- `apps/pagamentos/views.py` — fluxo manual atual (pagamento_pix_manual/upload/aceite/rejeicao).
- `apps/pagamentos/services.py` — contratos de confirmacao/rejeicao manual.

### Restaurant Panel Integration Points
- `apps/restaurantes/views.py` — painel/dashboard/pedidos e filtros operacionais.
- `templates/painel/base_painel.html` — navegacao e badges do painel.
- `templates/painel/pedidos.html` — listagem/filtros de pedidos.
- `templates/painel/pedido_detalhe.html` — visualizacao e acoes manuais por pedido.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/pagamentos/models.py`: modelo `Pagamento` ja centraliza informacoes de pagamento por pedido.
- `apps/pagamentos/views.py`: padrao de validacao e mensagens no fluxo manual pode ser reaproveitado para CRUD de chaves.
- `apps/restaurantes/views.py`: estrutura de painel com filtros, paginacao e guardas de acesso ja estabelecida.

### Established Patterns
- Regras operacionais do restaurante usam `login_required` + restaurante do usuario logado.
- Pipeline de producao depende de `pedido.pago=True`; esse gate nao deve ser alterado.
- Status `aguardando_confirmacao` e fluxo de revisao manual ja existem como base de operacao.

### Integration Points
- Nova gestao de chaves deve integrar no painel do restaurante (views/templates existentes).
- Checkout (`pagamento_pix_manual`) deve consumir chave conforme regra configurada no restaurante.
- Historico de alteracoes precisa ficar disponivel no proprio painel para auditoria operacional.

</code_context>

<specifics>
## Specific Ideas

- Tela unica de chaves PIX no painel com tabela principal + trilha de historico na mesma pagina.
- Validacoes por tipo com mensagens objetivas para reduzir erro operacional no cadastro.
- Operacao sem gateway/webhook mantida como regra de negocio do produto.

</specifics>

<deferred>
## Deferred Ideas

- Conciliacao automatica por webhook/gateway (fora do escopo desta fase).
- Reembolso automatico e split de pagamento (fora do escopo do milestone atual).

</deferred>

---

*Phase: 02-gest-o-de-chaves-pix*
*Context gathered: 2026-04-10*
