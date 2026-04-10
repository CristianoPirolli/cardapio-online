# Requirements: Cardapio Online

**Defined:** 2026-04-10
**Milestone:** v1.1 Conciliação PIX
**Core Value:** Receber pedidos pagos com segurança e baixo atrito operacional

## v1.1 Requirements

### Payments Automation

- [ ] **PAY-15**: Sistema processa webhook PIX válido e marca pedido como pago automaticamente
- [ ] **PAY-16**: Sistema impede confirmação automática quando valor/identificador do pagamento divergir
- [ ] **PAY-17**: Sistema registra trilha de auditoria para cada evento de conciliação

### Multi-Key PIX

- [ ] **PAY-18**: Restaurante cadastra múltiplas chaves PIX ativas no painel
- [ ] **PAY-19**: Checkout seleciona chave PIX conforme regra configurada pelo restaurante
- [ ] **PAY-20**: Restaurante consegue ativar/desativar chaves sem quebrar pedidos em andamento

### Operations

- [ ] **OPS-01**: Divergências de conciliação entram em fila de revisão manual no painel
- [ ] **OPS-02**: Restaurante consegue aprovar/rejeitar divergência com justificativa

## Future Requirements

- **PAY-21**: Reembolso parcial/total com rastreabilidade
- **PAY-22**: Suporte a múltiplos provedores de webhook PIX

## Out of Scope

| Feature | Reason |
|---------|--------|
| Split de pagamento | Regras de negócio e fiscais ainda não definidas |
| Reembolso automático | Exige fluxo financeiro e antifraude não planejados para v1.1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PAY-15 | Phase 2 | Pending |
| PAY-16 | Phase 2 | Pending |
| PAY-17 | Phase 2 | Pending |
| PAY-18 | Phase 3 | Pending |
| PAY-19 | Phase 3 | Pending |
| PAY-20 | Phase 3 | Pending |
| OPS-01 | Phase 3 | Pending |
| OPS-02 | Phase 3 | Pending |

**Coverage:**
- v1.1 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0

---
*Requirements defined: 2026-04-10*
*Last updated: 2026-04-10 after milestone initialization*
