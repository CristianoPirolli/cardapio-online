# Requirements: Cardapio Online

**Defined:** 2026-04-02
**Core Value:** Restaurante recebe pedidos online com fluxo operacional simples e confiável

## v1 Requirements

### Payments (PIX Manual)

- [x] **REQ-01**: Cliente visualiza chave PIX fixa na etapa de pagamento
- [x] **REQ-02**: Cliente consegue copiar a chave PIX com ação explícita de cópia
- [x] **REQ-03**: Sessão/pedido permanece acessível após cliente sair para app do banco e retornar
- [x] **REQ-04**: Cliente envia comprovante de pagamento em imagem ou PDF
- [x] **REQ-05**: Pedido enviado com comprovante fica em estado aguardando confirmação
- [x] **REQ-06**: Restaurante visualiza pedidos aguardando confirmação antes do pipeline de produção
- [x] **REQ-07**: Restaurante visualiza o arquivo de comprovante para validar pagamento
- [x] **REQ-08**: Restaurante aceita pedido validado e pedido segue para fluxo existente
- [x] **REQ-09**: Restaurante recusa pedido inválido e pedido é cancelado
- [ ] **REQ-10**: Valor de pedidos aceitos compõe totais do painel como no fluxo atual
- [ ] **REQ-11**: Integrações de gateway (Mercado Pago/Stripe) são removidas do fluxo ativo
- [ ] **REQ-12**: Chave PIX é configurável por ambiente/configuração do sistema
- [x] **REQ-13**: Upload aceita apenas jpg/jpeg/png/webp/pdf com limite de tamanho
- [ ] **REQ-14**: Fluxo de produção existente permanece intacto após confirmação manual

## v2 Requirements

### Payments

- **REQ-V2-01**: Validação automática de PIX via webhook/conciliação
- **REQ-V2-02**: Suporte a múltiplas chaves PIX por restaurante

## Out of Scope

| Feature | Reason |
|---------|--------|
| Validação automática de PIX | Fora do escopo da fase 1 |
| Reembolso automatizado | Fora do escopo da fase 1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REQ-01 | Phase 1 | Done (01-03) |
| REQ-02 | Phase 1 | Done (01-03) |
| REQ-03 | Phase 1 | Done (01-03) |
| REQ-04 | Phase 1 | Done (01-03) |
| REQ-05 | Phase 1 | Done (01-03) |
| REQ-06 | Phase 1 | Done (01-04) |
| REQ-07 | Phase 1 | Done (01-04) |
| REQ-08 | Phase 1 | Done (01-04) |
| REQ-09 | Phase 1 | Done (01-04) |
| REQ-10 | Phase 1 | Pending (01-05) |
| REQ-11 | Phase 1 | Done (01-01) |
| REQ-12 | Phase 1 | Done (01-01) |
| REQ-13 | Phase 1 | Done (01-03) |
| REQ-14 | Phase 1 | Pending (01-05) |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-04-02*
*Last updated: 2026-04-02 after phase-1 planning bootstrap*
