# Research Summary: v1.2 Acompanhamento de Pedido

**Synthesized:** 2026-04-17

---

## Key Finding

The tracking feature is structurally complete — views, URLs, polling JS, and template all exist — but the progress bar only represents post-payment states (`recebido → preparo → entrega → concluido`), leaving customers who just submitted a comprovante staring at a blank, inactive bar with no visual feedback. The entire v1.2 milestone is a mapping and UX correction job, not a greenfield build.

---

## Stack Additions

**None.** Zero new packages or infrastructure. All capabilities are covered by Django built-ins and vanilla JS already in `acompanhar.html`. Do not introduce Django Channels, Celery, Redis, htmx, or DRF serializers.

---

## Feature Table Stakes

- **4-state customer progress bar** — `Aguardando PIX → Confirmado → Pronto → Entregue` — replacing the current bar that skips the payment-waiting phase
- **Distinct visual state for `aguardando_confirmacao`** — "Comprovante em análise" — must differ visually from `aguardando`
- **Unambiguous waiting message** — "Comprovante recebido. Aguardando verificação pelo restaurante."
- **Automatic reload on status change** — already wired via 30s polling; must confirm it covers pre-payment states
- **Tracking link on `pagamento.html`** — currently only on `sucesso.html`; customer needs it before uploading comprovante
- **Cancelled order explanation** — surface `motivo` label from `PagamentoRevisaoHistorico` + restaurant contact option
- **`stopped` flag in polling JSON** — add `stopped: true` for `concluido`/`cancelado` to clear JS interval properly

---

## Differentiators

- Dynamic `<title>` tag reflecting current status (visible in background tabs)
- Adaptive poll interval — shorter during active states (`preparo`/`entrega`)
- WhatsApp deep-link on cancelled state — reduces unstructured inbound contact
- Collapsible order items list — CSS/JS only, no backend change

---

## Anti-Features

- WebSockets / Django Channels / SSE — explicitly prohibited; polling is adequate
- Push notifications (browser, SMS, email) — out of scope
- Customer authentication / order history — separate milestone
- UUID-based tracking URL for v1.2 — real security issue but changing URL scheme mid-milestone breaks shared links; defer to v1.3

---

## Watch Out For

**1. Status mapping must be decided before any template or JS is written.**
The model has 7 internal states; define a `customer_status` mapping (method or dict) consumed by both template and endpoint. If they use different label sets, JS comparison will always trigger reload or never trigger.

**2. `aguardando` and `aguardando_confirmacao` are visually identical in the current template.**
Both show blank progress bar. A customer who uploaded their comprovante must see a distinct state from one who hasn't paid yet — this is the highest-anxiety moment in the flow.

**3. Polling interval below 15s needs `Cache-Control` header.**
Add `Cache-Control: max-age=25` to the JSON response before adjusting interval.

**4. Remove `_skip_status_validation = True` from `concluir_pedido_cliente`.**
`entrega → concluido` is already valid; the flag is unnecessary and dangerous as a copy-paste pattern.

**5. Audit all `acompanhar_pedido` URL references before touching URL patterns.**
At least 3 locations: `sucesso.html`, `pagamento_pix_manual` redirect, footer link in `acompanhar.html`.

---

## Build Order

**Phase 1 — Fix the foundation**
1. Define `customer_status` mapping (7 internal → 4 customer states) on `Pedido` model or view
2. Update JSON endpoint: return `customer_status`, add `stopped: true` for terminal states, trim unused payload
3. Rewrite progress bar in `acompanhar.html` for 4 customer states with distinct `aguardando` vs `aguardando_confirmacao` treatment
4. Update JS `checkStatus()`: compare `customer_status`, clear interval on `stopped: true`
5. Remove `_skip_status_validation = True` from `concluir_pedido_cliente`

**Phase 2 — Surface the tracking link**
6. Add tracking link to `pagamento.html` (PIX key page)
7. Verify `sucesso.html` link correct after Phase 1

**Phase 3 — Cancellation UX**
8. Query `PagamentoRevisaoHistorico` in view when `cancelado`; pass `motivo` to template
9. Show motivo label + conditional retry link in cancellation block
