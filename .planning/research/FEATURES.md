# Features Research: Order Status Tracking

**Domain:** Customer-facing order status page for restaurant ordering with manual PIX confirmation
**Researched:** 2026-04-17
**Milestone scope:** v1.2 — customer tracks their own order without contacting the restaurant

---

## Context: What Already Exists

A codebase audit reveals that substantial infrastructure was built in v1.0/v1.1 that
directly affects what needs to be built vs. what is already done:

| Component | Status | Location |
|-----------|--------|----------|
| `acompanhar_pedido` view (HTML page) | EXISTS | `apps/pedidos/views.py` |
| `acompanhar_pedido_status` endpoint (JSON poll) | EXISTS | `apps/pedidos/views.py` |
| `concluir_pedido_cliente` action (client confirms receipt) | EXISTS | `apps/pedidos/views.py` |
| URL `/<pedido_id>/acompanhar/` | EXISTS | `apps/pedidos/urls.py` |
| URL `/<pedido_id>/status/` (poll endpoint) | EXISTS | `apps/pedidos/urls.py` |
| Progress bar (recebido/preparo/entrega/concluido) | EXISTS | `templates/pedidos/acompanhar.html` |
| Polling JS (30s interval, pauses on tab hide) | EXISTS | `templates/pedidos/acompanhar.html` |
| "Acompanhar meu pedido" link from sucesso.html | EXISTS | `templates/pagamentos/sucesso.html` |

**Critical gap identified:** The tracking page progress bar only renders
`recebido → preparo → entrega → concluido`. The states `aguardando` (waiting for PIX
upload) and `aguardando_confirmacao` (waiting for manual restaurant approval) are not
represented in the customer-visible flow. A customer who just submitted their comprovante
and clicks "Acompanhar meu pedido" sees a progress bar with no active step — the order
appears stalled.

The PROJECT.md milestone defines 4 customer-visible states:
`Aguardando PIX → Confirmado → Pronto → Entregue`, which maps internal model states as:

| Customer label | Internal status(es) | Trigger |
|----------------|--------------------|---------| 
| Aguardando PIX | `aguardando`, `aguardando_confirmacao` | Customer has not yet uploaded comprovante, or has uploaded and waiting for manual approval |
| Confirmado | `recebido` | Restaurant approves PIX in the review panel — existing action |
| Pronto | `preparo` | Restaurant moves order to preparo — existing action |
| Entregue | `entrega`, `concluido` | Restaurant dispatches, customer confirms receipt |

---

## Table Stakes (must-have for v1.2)

These are features a customer unambiguously expects when following a tracking link.
Missing any of these makes the page feel broken or untrustworthy.

### 1. Correct 4-state progress bar matching the manual-confirmation flow

**Why essential:** The current progress bar skips the waiting-for-payment-confirmation
state entirely. A customer who just uploaded their comprovante and opens the tracking link
sees a blank/inactive progress bar with zero indication that anything is happening. This is
the core customer anxiety the feature is supposed to eliminate. The mapping must be:
`Aguardando PIX → Confirmado → Pronto → Entregue` using the labels defined in PROJECT.md.

**Complexity:** Low — the template logic already exists; this is a label and step-mapping
change plus adding the two waiting states to the render path.

**Dependency:** Existing `Pedido.STATUS_CHOICES` model — no model change needed. The
`acompanhar.html` template needs a conditional render update.

### 2. Automatic status update without manual page reload

**Why essential:** A static page forces the customer to refresh to know if anything has
changed. The whole point of this feature is eliminating the "did it work?" phone call to
the restaurant. Polling is the correct implementation for this monolith — WebSockets add
operational complexity for marginal benefit.

**Complexity:** Low — the polling JS is already implemented (30s interval, pauses on tab
hidden). The endpoint `acompanhar_pedido_status` already exists. This is already done for
states after `recebido`; it needs to also work for `aguardando_confirmacao`.

**Gap:** The current polling JS compares `data.status !== currentStatus` and reloads the
full page on any change. This works. The only gap is that the rendered page for
`aguardando` / `aguardando_confirmacao` must not show the polling-disabled condition
(`{% if pedido.status != 'concluido' and pedido.status != 'cancelado' %}`). The current
template does include these states in polling scope, so this is already correct.

### 3. Persistent tracking URL accessible after the payment flow

**Why essential:** The tracking URL must work even if the customer closes their browser
and returns hours later. It must not depend on session state.

**Complexity:** None — already implemented. The URL `/pedidos/<id>/acompanhar/` uses only
the `pedido_id` from the path and does a `get_object_or_404` — no session required.

**Note:** The URL uses a sequential integer ID. This is a security concern (see
Anti-Features and Pitfalls), but it is the existing design and not a blocker for v1.2.

### 4. Tracking link surfaced immediately after order placement

**Why essential:** The customer must know the link exists before they need it. If the link
only appears after PIX confirmation, the customer has no way to check status during the
waiting period — which is exactly when anxiety is highest.

**Complexity:** Low — the `sucesso.html` template already has this link. The PIX payment
page (`pagamento.html`) does NOT have the link. The link should be surfaced from the
moment the order is created, not just after comprovante upload.

**Gap to close:** Add the tracking link to `pagamento.html` (the PIX key display page)
so the customer can bookmark it before uploading their comprovante.

### 5. Unambiguous status message in the "waiting for confirmation" state

**Why essential:** In a manual-confirmation model, there is a latency gap between the
customer uploading the comprovante and the restaurant reviewing it. If the tracking page
shows no clear explanation of this gap, the customer assumes something went wrong.

**Complexity:** Low — adding a contextual message card for `aguardando_confirmacao`:
"Comprovante recebido. Aguardando verificação pelo restaurante."

**Dependency:** No new data required — `pedido.status` is already available on the
tracking page.

### 6. Cancelled order handling with clear explanation

**Why essential:** If a PIX is rejected (`cancelado`), the customer needs to know why
(at least at a summary level) and what to do next. A bare "Pedido Cancelado" with no
context creates support burden.

**Complexity:** Low — the template already renders a cancellation alert. The gap is that
no reason is shown. The `PagamentoRevisaoHistorico` model contains `motivo` and
`justificativa` fields that could be surfaced (redacted or summarized).

**Decision note:** Surfacing the operator's verbatim justificativa is a moderate privacy
and support risk. The safe v1.2 approach is to show the pre-defined `motivo` label
(e.g., "Pagamento inválido") without the free-text justificativa, plus restaurant contact
options.

---

## Differentiators (nice-to-have)

These features add meaningful value but are not required for the tracking page to fulfill
its core promise of "customer knows their order status without calling the restaurant."

### 1. Page title / tab title reflects current status

**Value:** When a customer has the tracking page open in a background tab, a dynamic
`<title>` like "[Em Preparo] Pedido #42 — Restaurante X" lets them glance at the tab bar.

**Complexity:** Low — set on page load via the template; update via JS after each
successful poll that triggers a reload.

### 2. Faster poll interval when order is in active transition states

**Value:** The 30-second interval is appropriate for stable states (awaiting confirmation).
During `preparo` or `entrega`, a 10–15s interval provides a noticeably more "live" feel
without meaningful server load increase for typical restaurant volumes.

**Complexity:** Low — the existing polling JS can adapt the interval based on the current
status value returned by the poll endpoint.

**Tradeoff:** Increases database read frequency by 2–3x during peak states. Negligible at
restaurant scale (tens of concurrent active orders), but worth noting.

### 3. Estimated preparation time display

**Value:** Reduces anxiety. "Seu pedido deve ficar pronto em aproximadamente 30 minutos"
(static text configured per restaurant) anchors expectations.

**Complexity:** Medium — requires a new field on `Restaurante` (tempo_preparo_estimado in
minutes). No per-order dynamic estimation — just the restaurant's configured average.
Frontend reads it from the existing page context; no new endpoint needed.

**Limitation:** This is a fixed estimate, not a real ETA. For a manual-confirmation model
with no kitchen display system, real ETAs are not feasible.

### 4. WhatsApp deep-link to contact restaurant

**Value:** When the order is cancelled or delayed, a one-tap link to WhatsApp with the
restaurant's number pre-fills the context. Reduces friction for the customer AND reduces
unstructured inbound messages to the restaurant (the customer opens WhatsApp vs. calling).

**Complexity:** Low — WhatsApp URL scheme is `https://wa.me/<number>?text=<text>`. The
`Restaurante` model likely has `telefone`. The text could pre-fill "Olá, tenho uma dúvida
sobre o Pedido #42."

**Condition:** Only show in cancelled or anomalous states, not during normal flow.

### 5. Order items summary collapsed by default

**Value:** On mobile, the current tracking page renders the full items list and customer
data inline, pushing the status indicator down. Collapsing the items list behind a toggle
improves the visual hierarchy on small screens.

**Complexity:** Low — CSS/JS toggle, no backend change.

---

## Anti-Features (explicitly out of scope for v1.2)

### 1. WebSocket / Server-Sent Events (SSE) real-time push

**Why wrong for this product:** The existing 30-second polling is sufficient for a
manual-confirmation model where status transitions happen on human timescales (minutes, not
seconds). WebSockets introduce persistent connection management, Django Channels (ASGI
upgrade), and operational overhead that the monolith does not need. The product constraint
"Django monolith — manter consistência" makes this explicitly wrong. The PROJECT.md
already specifies "polling (sem WebSocket)."

### 2. Push notifications (browser, SMS, email)

**Why wrong:** Push channels require opt-in consent flows, infrastructure (FCM, Twilio,
SendGrid), and ongoing costs. For a product where the customer is typically waiting nearby
and actively monitoring their order (or has a tab open), push is over-engineering. The
manual-confirmation model has inherent latency (restaurant operator must act) that makes
sub-minute notifications meaningless. Defer to a future milestone if adoption data
supports it.

### 3. Customer account / order history

**Why wrong:** The system has no customer login. Orders are anonymous (customer submits
name + phone, no auth). Adding auth to serve an order history page is a separate product
decision that spans the entire checkout flow. v1.2 scope is a single-order status page.

### 4. Automatic payment confirmation (webhook)

**Why wrong:** Explicitly listed as out of scope in both PROJECT.md and v1.1-REQUIREMENTS.
The entire system is built around manual PIX confirmation. Introducing a webhook path
bypasses the existing review queue and audit trail built in v1.1.

### 5. Delivery map / GPS tracking

**Why wrong:** There is no delivery driver management in the system. The restaurant
operates delivery manually. Showing a map requires driver-side location reporting (a
separate app surface) and real-time data that does not exist. This is a fundamentally
different product scope.

### 6. Order modification or cancellation by the customer

**Why wrong:** Once a PIX comprovante is submitted, the restaurant must manually review it.
Allowing customer-side cancellation after PIX submission creates a reconciliation problem
— the restaurant may have already confirmed the payment. The existing flow correctly places
all approval/rejection decisions in the restaurant panel with mandatory justificativa.

### 7. Sequential order ID obfuscation (UUID-based tracking URL)

**Why deferred (not wrong in principle, wrong for v1.2):** The current URL is
`/pedidos/<int>/acompanhar/` which exposes sequential integer order IDs — any user can
increment the ID and view another customer's order. This is a genuine privacy issue.
However, changing the URL scheme requires a migration and redirect strategy across the
existing payment success page, the painel links, and any bookmarked URLs. Scoping this
into v1.2 would expand the milestone beyond its stated goal. Flag for v1.3 or a security
hardening phase.

---

## Feature Dependencies

| New Feature | Depends On | Existing System Hook |
|-------------|-----------|----------------------|
| 4-state progress bar | `Pedido.status` field | `STATUS_CHOICES` in `apps/pedidos/models.py`; no model change |
| Waiting state message | `Pedido.status == 'aguardando_confirmacao'` | Set by `confirmar_upload_comprovante` in `apps/pagamentos/services.py` |
| Cancellation reason display | `PagamentoRevisaoHistorico.motivo` | OPS-02/03 from v1.1; `historico_revisao_pagamento` reverse relation on `Pedido` |
| Faster poll on active states | Poll endpoint response (`status` field) | `acompanhar_pedido_status` view already returns `status` |
| Tracking link on PIX page | `pedido.id` in template context | `pagamento_pix_manual` view already passes `pedido` in context |
| WhatsApp deep-link | `restaurante.telefone` | `Restaurante` model; verify field exists before implementing |
| Estimated prep time | New `Restaurante` field | Requires model migration — only needed for the differentiator, not table stakes |

---

## Status Mapping Clarification

The gap between the model's 7 internal states and the 4 customer-visible labels in
PROJECT.md must be explicit in the implementation:

```
Internal state          Customer sees
─────────────────────   ──────────────────────────────────────────────
aguardando              "Aguardando PIX" (customer has not yet paid)
aguardando_confirmacao  "Aguardando PIX" (comprovante sent, review pending)
recebido                "Confirmado" (restaurant approved PIX)
preparo                 "Pronto" (restaurant is preparing)
entrega                 "Entregue" (saiu para entrega — in transit)
concluido               "Entregue" (cliente confirmou recebimento)
cancelado               "Cancelado" (special case with explanation)
```

The `entrega` and `concluido` states both render as the final "Entregue" step because from
the customer's perspective, once the order is dispatched the journey is complete. The
"Confirmar Recebimento" button (already in `acompanhar.html`) handles the
`entrega → concluido` transition.

Note that PROJECT.md uses "Pronto" for the preparo stage — this label means "being
prepared / ready soon" in the restaurant context, not that the order is ready to pick up.
If retirada (takeout) is a delivery type, "Pronto" should be re-evaluated: for retirada,
"Pronto para retirada" is more accurate than "Em Preparo" once the order is actually
ready. This is a label decision for the implementation phase.
