# Requirements: Cardapio Online

**Defined:** 2026-04-10
**Milestone:** v1.1 Operacao Manual PIX
**Core Value:** Receber pedidos pagos com segurança e baixo atrito operacional

## v1.1 Requirements

### Multi-Key PIX

- [x] **PAY-15**: Restaurante cadastra multiplas chaves PIX ativas no painel
- [x] **PAY-16**: Restaurante define chave padrao e prioridade de uso no checkout
- [x] **PAY-17**: Checkout seleciona e exibe a chave PIX correta conforme regra configurada
- [x] **PAY-18**: Restaurante consegue ativar/desativar chaves sem quebrar pedidos em andamento

### Operations

- [x] **OPS-01**: Pedidos aguardando confirmacao entram em fila de revisao manual com filtros no painel
- [ ] **OPS-02**: Restaurante consegue aprovar/rejeitar revisao com justificativa obrigatoria
- [x] **OPS-03**: Sistema registra historico auditavel de decisoes manuais por pedido

## Future Requirements

- **PAY-21**: Reembolso parcial/total com rastreabilidade
- **PAY-22**: Integracao futura com provedores externos de conciliacao (se estrategia mudar)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Confirmacao automatica via gateway/webhook | Fora da estrategia do produto no v1.1 |
| Split de pagamento | Regras de negocio e fiscais ainda nao definidas |
| Reembolso automatico | Exige fluxo financeiro e antifraude nao planejados para v1.1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PAY-15 | Phase 2 | Complete |
| PAY-16 | Phase 2 | Complete |
| PAY-17 | Phase 2 | Complete |
| PAY-18 | Phase 2 | Complete |
| OPS-01 | Phase 3 | Complete |
| OPS-02 | Phase 3 | Pending |
| OPS-03 | Phase 3 | Complete |

**Coverage:**
- v1.1 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0

---
*Requirements defined: 2026-04-10*
*Last updated: 2026-04-10 after milestone initialization*
