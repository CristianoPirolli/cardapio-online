# Roadmap: Cardapio Online

## Overview

Evolucao incremental do fluxo de pedidos online com foco em pagamento PIX manual validado pelo restaurante antes da entrada no pipeline de producao.

## Phases

- [ ] **Phase 1: Pagamento PIX Manual** - Remover gateway e implementar confirmacao manual por comprovante

## Phase Details

### Phase 1: Pagamento PIX Manual
**Goal**: Substituir gateway por PIX manual com chave fixa, upload de comprovante e aprovacao manual do restaurante antes do pipeline existente.
**Depends on**: Nothing (first phase)
**Requirements**: [REQ-01, REQ-02, REQ-03, REQ-04, REQ-05, REQ-06, REQ-07, REQ-08, REQ-09, REQ-10, REQ-11, REQ-12, REQ-13, REQ-14]
**Success Criteria** (what must be TRUE):
  1. Cliente consegue copiar chave PIX, retornar ao pedido e enviar comprovante
  2. Restaurante revisa comprovante e aceita/rejeita antes da producao
  3. Pedido aceito entra no fluxo existente e soma no painel
**Plans**: 5 plans

Plans:
- [x] 01-01: Pre-flight (migracoes pendentes, limpeza de referencias gateway e configuracao PIX_KEY)
- [x] 01-02: Modelo de dados e grafo de status (aguardando_confirmacao + comprovante)
- [ ] 01-03: Fluxo cliente PIX manual (pagina, copia, upload)
- [ ] 01-04: Fluxo restaurante (filtro, visualizacao comprovante, aceitar/recusar)
- [ ] 01-05: Integracao final, limpeza e validacao E2E

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Pagamento PIX Manual | 2/5 | In progress | - |
