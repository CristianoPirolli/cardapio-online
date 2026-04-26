# Requirements: Cardapio Online

**Defined:** 2026-04-17
**Milestone:** v1.2 Acompanhamento de Pedido
**Core Value:** Receber pedidos pagos com segurança e baixo atrito operacional

## v1.2 Requirements

### Status Visual do Pedido

- [ ] **TRACK-01**: Cliente vê barra de progresso com 4 estados — Aguardando PIX, Confirmado, Pronto, Entregue
- [ ] **TRACK-02**: Estado `aguardando_confirmacao` tem visual e mensagem distinto de `aguardando` — "Comprovante recebido, aguardando verificação"
- [ ] **TRACK-03**: Polling para automaticamente quando pedido atinge estado terminal (`concluido` ou `cancelado`)
- [ ] **TRACK-04**: Tag `<title>` da página de acompanhamento reflete o estado atual do pedido

### Acesso ao Rastreamento

- [ ] **TRACK-05**: Cliente vê link de acompanhamento na página da chave PIX (`pagamento.html`) antes de subir comprovante
- [ ] **TRACK-06**: Cliente vê URL copiável/bookmarkável na tela de confirmação (`sucesso.html`) além do botão existente
- [ ] **TRACK-07**: Estado cancelado exibe link para WhatsApp do restaurante com número do pedido pré-preenchido

### Cancelamento / Rejeição

- [ ] **TRACK-08**: Estado cancelado exibe o motivo de rejeição registrado pelo restaurante (de `PagamentoRevisaoHistorico`)
- [ ] **TRACK-09**: Cliente vê opção de reenviar comprovante após rejeição de PIX

## Future Requirements

- **TRACK-10**: URL de rastreamento baseada em UUID em vez de ID inteiro (segurança — enumeração)
- **TRACK-11**: Histórico de pedidos do cliente autenticado
- **TRACK-12**: Notificações push/SMS/email em mudança de status

## Out of Scope

| Feature | Reason |
|---------|--------|
| WebSockets / Django Channels | Polling de 30s é adequado para fluxo manual humano; complexidade desnecessária |
| Notificações push/SMS/email | Requer consentimento e infraestrutura paga; fora do produto atual |
| Autenticação do cliente para acompanhar pedido | Separar milestone — escopo diferente |
| UUID na URL de rastreamento (v1.2) | Real risco de privacidade, mas mudança de URL quebra links compartilhados; defer v1.3 |
| Cancelamento pelo cliente após subir comprovante | Cria problema de conciliação de pagamento |
| Mapa de entrega / GPS | Sem gestão de entregadores no produto |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TRACK-01 | Phase 4 | Pending |
| TRACK-02 | Phase 4 | Pending |
| TRACK-03 | Phase 4 | Pending |
| TRACK-04 | Phase 4 | Pending |
| TRACK-05 | Phase 5 | Pending |
| TRACK-06 | Phase 5 | Pending |
| TRACK-07 | Phase 5 | Pending |
| TRACK-08 | Phase 6 | Pending |
| TRACK-09 | Phase 6 | Pending |

**Coverage:**
- v1.2 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0
