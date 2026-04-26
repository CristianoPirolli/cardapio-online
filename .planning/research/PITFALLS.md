# Pitfalls Research: Order Status Tracking

**Domain:** Polling-based order status tracking on a Django monolith with manual PIX payment
**Researched:** 2026-04-17
**Codebase version:** v1.2 milestone start — polling skeleton already exists in views.py and acompanhar.html

---

## Context: What Already Exists

The following is already implemented and must be preserved:

- `acompanhar_pedido` (GET `/<id>/acompanhar/`) — renders the HTML tracking page
- `acompanhar_pedido_status` (GET `/<id>/status/`) — returns `{status, status_display, proximo_passo, passos_para_concluir}` as JSON
- `acompanhar.html` — has a `setInterval(checkStatus, 30000)` that reloads on status change, plus `visibilitychange` pause/resume
- `concluir_pedido_cliente` (POST `/<id>/concluir/`) — client can mark order as concluded when status is `entrega`
- Status graph: `aguardando → aguardando_confirmacao → recebido → preparo → entrega → concluido` (or `cancelado` from any)

The milestone work is integration, not greenfield. Pitfalls below are specific to completing and wiring this correctly.

---

## Pitfall List

---

### 1. Status Mismatch: Internal States vs. Customer-Visible States

- **Risk:** The model has 7 internal states (`aguardando`, `aguardando_confirmacao`, `recebido`, `preparo`, `entrega`, `concluido`, `cancelado`) but the milestone spec defines 4 customer-visible states (`Aguardando PIX`, `Confirmado`, `Pronto`, `Entregue`). If the polling endpoint returns raw internal status values and the template renders them directly, the customer sees confusing internal names like `aguardando_confirmacao` or `recebido` that mean nothing to them. Currently `acompanhar_pedido_status` returns `status_display` from `Pedido.STATUS_CHOICES`, which maps `recebido` to "Recebido" — not the customer-facing "Confirmado".

- **Warning sign:** The progress bar in `acompanhar.html` hardcodes steps as `recebido`, `preparo`, `entrega`, `concluido`. The `aguardando` and `aguardando_confirmacao` states are invisible in the progress visualization — the bar stays at 0% for both, with no distinction shown to the customer.

- **Prevention:** Define an explicit mapping layer, not inline template conditionals. Create a `customer_status()` method or property on `Pedido` that collapses the 7 internal states into the 4 customer-visible ones. Example: `aguardando` and `aguardando_confirmacao` both map to "Aguardando PIX"; `recebido` and `preparo` both map to "Confirmado" (payment confirmed, in kitchen); `entrega` maps to "Pronto"; `concluido` maps to "Entregue". The polling JSON endpoint must return this customer label, not the raw `status`. The template must consume `customer_status` for display, while the progress bar percentage is driven by this collapsed mapping.

- **Phase to address:** Phase 1 (status model and endpoint definition) — must be decided before any template or JS is written, because it affects what the JSON endpoint returns and how the progress bar renders.

---

### 2. Public URL Exposes Order Data Without Access Control

- **Risk:** `/<pedido_id>/acompanhar/` and `/<pedido_id>/status/` are fully public. Any person who guesses or enumerates an integer `pedido_id` can view another customer's full order: name, phone, email, address, items, totals. The current `acompanhar_pedido` view uses `get_object_or_404(Pedido, id=pedido_id)` with no ownership check. The `id` field is a sequential auto-increment integer starting from 1 — trivially enumerable.

- **Warning sign:** You can open `/pedidos/1/acompanhar/`, `/pedidos/2/acompanhar/` in sequence and see every order in the database. The customer data fields `cliente_nome`, `cliente_telefone`, `cliente_email`, `endereco_entrega` are all rendered in the template with no masking.

- **Prevention:** Two complementary mitigations, apply both. First: add a UUID token field to `Pedido` (e.g., `token = models.UUIDField(default=uuid.uuid4, unique=True)`), change the tracking URL to `/pedidos/<uuid:token>/acompanhar/`, and stop using the integer ID in the public URL. Second: limit what is rendered on the page — show only first name, masked phone (e.g., `(11) ****-5678`), and items list; do not render full address or email. Do not remove the integer-ID endpoint without a redirect for any existing links. The polling JSON endpoint (`/status/`) should also move to the UUID-based URL. The `pagamento_sucesso` template already links to `acompanhar_pedido` by integer ID — that link must be updated when the URL changes.

- **Phase to address:** Phase 1 (URL and model design) — the token field requires a migration. The URL change must happen before the tracking link is exposed to customers. Retrofitting this after release creates broken links already shared by customers.

---

### 3. Polling Hitting the Database on Every Request Without Caching

- **Risk:** `acompanhar_pedido_status` uses `Pedido.objects.only('id', 'status')` which is a DB query on every poll. With 30-second intervals and one customer per order this is negligible. The risk becomes real if: (a) the interval is shortened (e.g., 10s for impatient UX), (b) multiple tabs are open, or (c) someone uses the polling endpoint as a status API and calls it faster. There is a `HashCache` class in `apps/core/algorithms.py` with configurable TTL already available in the project.

- **Warning sign:** `setInterval(checkStatus, 30000)` in `acompanhar.html` is the only throttle. If the interval is reduced during UX testing without adding server-side rate limiting or caching, DB load increases proportionally. The `visibilitychange` handler pauses polling when the tab is hidden — this helps but does not protect against multiple open tabs.

- **Prevention:** Keep the 30-second interval as the default. Do not reduce below 15 seconds without adding a per-order status cache with TTL matching the interval. The existing `HashCache` in `algorithms.py` can serve this: cache key `status:{pedido_id}`, TTL 15s, invalidate on every `Pedido.save()` that changes `status`. Add a `max_age` header (`Cache-Control: max-age=25`) to the JSON response to allow browser-level caching and prevent duplicate requests from re-renders. Do not add rate limiting via Django middleware unless traffic justifies it — the current scale does not.

- **Phase to address:** Phase 1 (endpoint implementation) for the Cache-Control header; Phase 2 (load testing) if interval is reduced.

---

### 4. Polling Continues After Terminal States (Concluido / Cancelado)

- **Risk:** The JS in `acompanhar.html` stops polling with `{% if pedido.status != 'concluido' and pedido.status != 'cancelado' %}` — but this check runs at initial page render. If the page loaded when status was `preparo` and the order later reaches `concluido`, the JS reloads the page (`window.location.reload()`), which re-renders with the terminal status, and the JS block is no longer emitted. This flow is correct. The hidden risk is: if `window.location.reload()` is called but the status endpoint returns an intermediate state due to a read-committed isolation quirk, the reload may happen in a loop (status shows `preparo`, reload, still `preparo`, reload again). This is unlikely with PostgreSQL default isolation but possible under heavy write load.

- **Warning sign:** Rapid consecutive reloads visible in browser network tab when status transitions happen. The JSON `data.status !== currentStatus` comparison is strict-equal — any case mismatch or whitespace in the API response would prevent the reload from triggering at all.

- **Prevention:** After reload, the template should show a clear terminal state message (the `cancelado` alert is already there; the `concluido` state needs an equivalent final message). Add `stopped: true` to the JSON response when `status` is in `['concluido', 'cancelado']`, and check it in the JS: if `data.stopped`, clear the interval and do a final reload instead of relying on the status comparison. This decouples the "stop polling" logic from the template-side conditional.

- **Phase to address:** Phase 1 (JS polling logic) — simple addition to the existing `checkStatus` function.

---

### 5. Rejected PIX Leaves Customer Stranded on Tracking Page

- **Risk:** When the restaurant rejects a PIX comprovante, `rejeitar_pix_manual` sets `pedido.status = 'cancelado'`. The customer is on the `acompanhar_pedido` page (or the `pagamento_sucesso` page). On next poll, the page reloads and renders the generic "Pedido Cancelado — Entre em contato com o restaurante" message. The customer has no context: is it a payment issue? Did they pay the wrong amount? Can they resubmit? Currently there is no explanation surface for cancellation reason on the customer-facing tracking page.

- **Warning sign:** The `PagamentoRevisaoHistorico` model stores the rejection `motivo` and `justificativa` — this information exists in the DB but is never surfaced on the customer-facing page. The `painel_pedido_detalhe` view loads `historico_revisao_pagamento` but `acompanhar_pedido` does not.

- **Prevention:** When `pedido.status == 'cancelado'`, query `PagamentoRevisaoHistorico` for the most recent `REJEITADO` entry and surface a customer-friendly version of the reason (e.g., "Seu comprovante não foi reconhecido — valor incorreto" instead of raw `justificativa`). Add a "Tentar novamente" button that links to the `pagamento_pix_manual` page — but only if the order is cancelado due to payment rejection (not due to a restaurant operational cancellation). Distinguish these two cancellation causes by checking if a `PagamentoRevisaoHistorico` with `acao=REJEITADO` exists for the order. Do not expose the raw internal `justificativa` text to the customer.

- **Phase to address:** Phase 2 (UX edge cases) — not blocking for the first working version, but must be addressed before the feature is considered production-ready.

---

### 6. Tracking Link Not Shown After Comprovante Upload

- **Risk:** After uploading the comprovante, the customer is redirected to `pagamento_sucesso` (via `redirect('pagamento_sucesso', pedido_id=pedido.id)`). The `sucesso.html` template already contains a "Acompanhar meu pedido" button linking to `acompanhar_pedido`. This link uses the integer `pedido.id`. If the URL is later changed to use a UUID token (Pitfall 2), this link breaks silently — the template renders a 404 URL without any error at template compile time.

- **Warning sign:** The `sucesso.html` template hardcodes `{% url 'acompanhar_pedido' pedido.id %}`. If `acompanhar_pedido` URL pattern changes signature (from `int:pedido_id` to `uuid:token`), the `{% url %}` tag will raise `NoReverseMatch` at runtime.

- **Prevention:** When changing the URL signature in Pitfall 2, update both `sucesso.html` and the checkout flow that redirects after order creation simultaneously. The `checkout` view redirects to `pagamento_pix_manual` — that view must also pass the token if the confirmation page needs to link forward. Do a project-wide search for `acompanhar_pedido` URL references before changing the URL signature: currently appears in `sucesso.html`, `pagamento_pix_manual` view redirect (line 64 of `views.py`), and `acompanhar.html` footer link.

- **Phase to address:** Phase 1 (URL design) — resolve at the same time as Pitfall 2. Never change a URL signature without auditing all usages first.

---

### 7. `_skip_status_validation` Flag Bypasses BFS Guard in Client Conclude

- **Risk:** `concluir_pedido_cliente` sets `pedido._skip_status_validation = True` before saving with `status = 'concluido'`. This was used to bypass the BFS transition validation in `Pedido.save()`. The BFS graph has `'entrega': ['concluido', 'cancelado']` — so `entrega → concluido` is a valid transition and the flag is unnecessary. More dangerously: if `_skip_status_validation` pattern is cargo-culted into new views for the v1.2 milestone, it can silently allow invalid transitions (e.g., `aguardando → concluido`) with no error.

- **Warning sign:** Any new view that sets `pedido._skip_status_validation = True` is a red flag. The BFS validation in `Pedido.save()` exists precisely to prevent impossible transitions — bypassing it should require explicit justification.

- **Prevention:** Remove `_skip_status_validation = True` from `concluir_pedido_cliente` since `entrega → concluido` is already a valid BFS transition. Do not introduce this pattern in any new v1.2 views. The only legitimate use would be for admin/data-repair scripts outside normal user flows.

- **Phase to address:** Phase 1 (code review of existing skeleton before adding new flows) — fix the existing misuse before writing new code that might copy it.

---

### 8. The `aguardando` State Is Invisible in the Progress Bar

- **Risk:** A customer places an order and is redirected to the PIX payment page. Before uploading the comprovante, `pedido.status == 'aguardando'`. If they open the tracking URL at this point, the progress bar renders with 0% and all steps greyed out, with no badge distinguishing "waiting for payment" from "something went wrong". The `{% if pedido.status != 'cancelado' %}` guard shows the bar, but the bar gives no visual feedback for the payment-waiting phase.

- **Warning sign:** The progress bar in `acompanhar.html` has 4 steps (`recebido`, `preparo`, `entrega`, `concluido`). States `aguardando` and `aguardando_confirmacao` produce identical visual output: empty bar, all circles grey. A customer who uploaded the comprovante (`aguardando_confirmacao`) sees the same bar as one who hasn't uploaded anything (`aguardando`).

- **Prevention:** The customer-visible 4 states (Pitfall 1) must drive the progress bar, not the internal 7. Add a pre-step visual indicator for "Aguardando PIX" and "Comprovante enviado, aguardando confirmação" — these can be the same first step in the progress bar but with different text labels and icons. At minimum, distinguish `aguardando` (show "Envie o comprovante" with a link to the upload page) from `aguardando_confirmacao` (show "Comprovante em análise, aguardando restaurante").

- **Phase to address:** Phase 1 (template redesign) — the progress bar must be rewritten to reflect the customer-visible state model before the feature is shipped.

---

### 9. Polling Endpoint Returns Data That Doesn't Map to What the Template Renders

- **Risk:** `acompanhar_pedido_status` returns `proximo_passo` and `passos_para_concluir` computed from `pedido.proximo_passo` (a BFS property). On status change, the JS does `window.location.reload()` — so these fields are never actually used by the current JS. They are dead payload. If a future iteration tries to do DOM updates instead of full reload (to avoid flash), this payload would need to be consumed. But the mismatch between what the template renders (progress bar based on status string comparison) and what the JSON returns (BFS step counts) makes partial DOM updates hard to implement correctly later.

- **Warning sign:** The JS `checkStatus()` function only uses `data.status` for comparison. `data.proximo_passo` and `data.passos_para_concluir` are fetched but never consumed.

- **Prevention:** Either use the richer data or remove it from the response for now. If the reload approach is kept (simplest), strip the JSON to only `{status, customer_status, stopped}` — the minimum needed. If partial DOM update is planned for a later phase (replacing reload to avoid flash), keep the richer fields but document them as "for future use" and ensure the template's progress logic can be reproduced in JS using the same data.

- **Phase to address:** Phase 1 (endpoint response design) — decide reload-only vs. DOM-update before finalizing the JSON schema.

---

### 10. Introducing New URL Patterns That Conflict With Existing Pedidos Routing

- **Risk:** The current `apps/pedidos/urls.py` uses `path('<int:pedido_id>/.../')` patterns. Adding a UUID-based route like `path('<uuid:token>/acompanhar/')` in the same `urlpatterns` list requires care: Django matches patterns in order, and if a UUID pattern is placed after an int pattern with the same path structure, it may never be reached. Worse, if both the old integer URL and the new UUID URL coexist during a transition period, the same `name='acompanhar_pedido'` cannot be used for both, creating broken `{% url %}` tags.

- **Warning sign:** Adding a second URL with the same `name` parameter in the same `urlpatterns` list — Django uses the last definition, silently breaking `{% url %}` references to the first.

- **Prevention:** When introducing the UUID-based URL, rename the view and URL name simultaneously (e.g., `name='acompanhar_pedido_v2'`), keep the old integer URL as a redirect to the new UUID URL for backward compatibility (any shared links from v1.0/v1.1 still work), then remove the old integer-based name after confirming no templates or views reference it. Never have two URL patterns with the same `name` in the same namespace.

- **Phase to address:** Phase 1 (URL migration) — plan the transition before writing any code, not after.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| Status model / mapping | Pitfall 1 (internal vs. customer states) | Define `customer_status` mapping before writing any template or JS |
| URL design | Pitfall 2 + 10 (public ID enumeration, URL conflicts) | Add UUID token field and migrate URL in a single atomic change |
| Polling endpoint | Pitfall 3 + 9 (load, dead payload) | Keep 30s interval, add Cache-Control header, trim JSON to what JS consumes |
| JS polling logic | Pitfall 4 (loop on terminal state) | Add `stopped` flag to JSON, clear interval on receipt |
| UX for rejected PIX | Pitfall 5 (stranded customer) | Surface rejection reason from `PagamentoRevisaoHistorico`, show retry link |
| Tracking link in sucesso.html | Pitfall 6 (broken link on URL change) | Audit all `acompanhar_pedido` references before changing URL signature |
| Existing code review | Pitfall 7 (`_skip_status_validation` misuse) | Remove flag from `concluir_pedido_cliente`, never copy to new views |
| Progress bar template | Pitfall 8 (invisible pre-payment state) | Redesign bar to show customer-visible 4-state model, not internal 7 |
