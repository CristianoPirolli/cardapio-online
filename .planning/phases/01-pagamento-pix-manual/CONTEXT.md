# Phase 1 — PIX Manual Payment Context

## Goal
Replace the existing payment gateway (Mercado Pago/Stripe) with a simpler PIX-only manual flow where customers copy a fixed PIX key, pay via their bank app, upload proof, and the restaurant manually confirms before accepting the order.

## User Requirements (verbatim)
> "quero mudar o jeito que é o pagamento... tiraremos o gateway e deixaremos a chave PIX fixa para copiar... ao copiar o usuário poderá sair para o app do banco (guarda a sessão para o usuário não perder o pedido) e ao realizar o pagamento, ele retorna ao pedido, uma área para o usuário cliente subir um arquivo (imagem ou pdf), comprovante do PIX "pagamento" e então ele finaliza o pedido... o restaurante por sua vez, recebe o pedido e poderá visualizar antes de aceitar ou recusar (uma espécie de filtro)... deverá poder visualizar o arquivo para confirmar que houve um pagamento... só depois o pedido entra para o pipeline de produção... e o valor somado para os pedidos no painel... e segue o fluxo já existente"

## Acceptance Criteria

### Customer Flow
1. Customer sees PIX key (fixed) with a copy button on the payment page
2. Session is preserved when customer leaves to bank app (order not lost)
3. Customer returns and finds their order still pending
4. Customer uploads proof of payment (image or PDF)
5. Customer submits/finalizes the order

### Restaurant Flow
6. Restaurant receives order in "aguardando confirmação" state (not yet in production)
7. Restaurant can view order details + uploaded payment proof file
8. Restaurant can accept → order enters production pipeline
9. Restaurant can reject → order is cancelled
10. Accepted order amount is added to the panel totals

### Technical
11. Remove Mercado Pago integration (gateway, webhooks, SDK)
12. PIX key is configurable (env var or admin setting)
13. File upload stored securely (max size, allowed types: image/pdf)
14. Existing production pipeline flow preserved after acceptance

## Out of Scope
- Automated PIX payment verification (no webhook, no QR code generation)
- Multiple PIX keys
- Refund flow
