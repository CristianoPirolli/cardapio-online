# Phase 4: Status Visual Core - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Atualizar a página pública `acompanhar.html` para exibir os estados internos do pedido como 5 passos visuais do cliente, com polling que para em estados terminais e badge diferenciado para "comprovante em análise". Nenhuma nova funcionalidade além do mapeamento e da barra de progresso.

</domain>

<decisions>
## Implementation Decisions

### Mapeamento customer_status

**D-01:** A barra de progresso terá **5 passos visíveis** (não 4 como no requisito original do v1.2). Decisão tomada para preservar a granularidade `entrega` como passo próprio.

**D-02:** Mapeamento interno → customer_status:

| Estado interno | customer_status | Label visível |
|---|---|---|
| `aguardando` | `aguardando_pix` | Aguardando PIX |
| `aguardando_confirmacao` | `aguardando_pix` | Aguardando PIX (+ badge distinto) |
| `recebido` | `confirmado` | Pedido Confirmado |
| `preparo` | `em_preparo` | Em Preparo |
| `entrega` | `saiu_entrega` | Saiu p/ Entrega |
| `concluido` | `entregue` | Entregue |
| `cancelado` | `cancelado` | (fora da barra) |

**D-03:** O mapeamento vive como **property no model `Pedido`** — `pedido.customer_status` — reutilizável na view, no endpoint JSON e no template. Padrão estabelecido pelo próprio model com `proximo_passo` e `passos_para_concluir`.

### Visual "Comprovante em Análise"

**D-04:** Quando `status == 'aguardando_confirmacao'`, a barra permanece no passo 1 (Aguardando PIX), mas um **badge/alerta abaixo da barra** exibe: `"Comprovante recebido — aguardando verificação do restaurante"`. Usar cor/ícone de "informação" (azul ou laranja, não verde).

### Polling e Endpoint

**D-05:** O endpoint `acompanhar_pedido_status` deve retornar **ambos**:
```json
{
  "status": "preparo",
  "customer_status": "em_preparo",
  "terminal": false
}
```

**D-06:** Estados **terminais** (param o polling): `entregue` e `cancelado`. O JS para o timer quando `terminal == true`. Comportamento de retomada de foco de aba permanece igual.

**D-07:** O título da aba deve refletir o customer_status label atual, ex: `"Pedido Confirmado — Cardapio Online"`. Usar o display do customer_status, não o status interno.

### Labels dos 5 Passos

**D-08:** Texto exato dos 5 passos da barra:
1. **Aguardando PIX**
2. **Pedido Confirmado**
3. **Em Preparo**
4. **Saiu p/ Entrega**
5. **Entregue**

### Claude's Discretion

- Ícone exato e tom de cor do badge "comprovante em análise" — usar Bootstrap classes consistentes com o restante da página.
- Estrutura exata da property `customer_status` no model (dict lookup vs. if/elif) — preferir dict para consistência com `VALID_TRANSITIONS`.
- Ordem e agrupamento das respostas do endpoint de polling (além dos campos obrigatórios de D-05).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above e nos arquivos abaixo.

### Código existente (MUST read antes de modificar)
- `templates/pedidos/acompanhar.html` — Template completo com barra de progresso e polling JS existente. Modificar, não substituir.
- `apps/pedidos/models.py` — Model `Pedido` com STATUS_CHOICES (7 estados), propriedades BFS, e padrão de properties existente (`proximo_passo`, `passos_para_concluir`). Adicionar `customer_status` seguindo esse padrão.
- `apps/pedidos/views.py` — `acompanhar_pedido_status()` (endpoint de polling atual) e `acompanhar_pedido()` (view principal). Ambas precisam de atualização.

### Requisitos do milestone
- `.planning/PROJECT.md` §"Current Milestone: v1.2" — Success criteria TRACK-01 a TRACK-04 relevantes a esta fase.
- `.planning/ROADMAP.md` §"Phase 4" — Goals e success criteria canônicos.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`acompanhar.html` — barra de progresso Bootstrap**: Já tem 4 círculos de passo com `bg-success`/`bg-light`, linha de progresso e labels. Adaptar para 5 passos usando a mesma estrutura.
- **`acompanhar.html` — polling JS**: `setInterval` de 30s com `visibilitychange`, `fetch()` para `/acompanhar/<id>/status/`, reload na mudança de status. Ajustar apenas a condição terminal (`data.terminal == true` em vez de `data.status == 'concluido' || ...`).
- **`Pedido.VALID_TRANSITIONS` (dict)**: Padrão de dict lookup O(1) já estabelecido — usar o mesmo padrão para o mapeamento `customer_status`.
- **`Pedido.proximo_passo` e `passos_para_concluir`**: Properties no model que servem de template para adicionar `customer_status`.

### Established Patterns
- **Status display**: Template usa `pedido.get_status_display()` e `pedido.status` direto — customer_status seguirá o mesmo padrão via property.
- **Endpoint JSON**: `acompanhar_pedido_status` usa `.only('id', 'status')` para eficiência — preservar essa otimização ao adicionar `customer_status` (a property não precisa de campos extras além de `status`).
- **Bootstrap + Bootstrap Icons**: Todo o visual usa Bootstrap 5 com `bi-*` icons. Badge de comprovante deve seguir o mesmo padrão.

### Integration Points
- `apps/pedidos/models.py` → adicionar property `customer_status` ao model `Pedido`
- `apps/pedidos/views.py` → atualizar `acompanhar_pedido_status()` para incluir `customer_status` e `terminal`; atualizar `acompanhar_pedido()` para passar customer_status ao contexto do template
- `templates/pedidos/acompanhar.html` → refatorar barra de 4 para 5 passos; adicionar badge condicional para `aguardando_confirmacao`; atualizar condição de polling no JS; atualizar `{% block title %}`

</code_context>

<specifics>
## Specific Ideas

- O badge de "comprovante em análise" deve aparecer entre a barra de progresso e os cards de detalhes do pedido — mesma área do card de status existente.
- O título da aba deve usar o label do passo visível (ex: "Pedido Confirmado"), não o status interno (ex: "recebido").

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-status-visual-core*
*Context gathered: 2026-04-17*
