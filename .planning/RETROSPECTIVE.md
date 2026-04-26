# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.1 — Operacao Manual PIX

**Shipped:** 2026-04-11  
**Phases:** 2 | **Plans:** 4 | **Sessions:** 1

### What Was Built
- Gestao de multiplas chaves PIX por restaurante com selecao deterministica no checkout.
- Snapshot de chave PIX por pagamento para preservar consistencia de pedidos em andamento.
- Revisao manual com justificativa obrigatoria, filtro por periodo e trilha auditavel no detalhe do pedido.

### What Worked
- Decomposicao por fases com contexto travado antes de planejamento reduziu retrabalho.
- Estrategia TDD por plano ajudou a manter regressao controlada no fluxo PIX.

### What Was Inefficient
- Ausencia de milestone audit formal antes do fechamento.
- Divergencia temporaria entre comportamento de views e testes legados de fase anterior.

### Patterns Established
- Fluxo sem gateway/webhook com confirmacao manual baseada em comprovante permanece o padrao.
- Contratos de painel devem ser validados por testes de view com `follow=True` quando ha redirect.

### Key Lessons
1. Fechar milestone sem auditoria formal cria risco de drift documental, mesmo com verificacao de fase aprovada.
2. Alteracoes de UX de painel devem incluir atualizacao imediata dos testes de regressao da fase anterior.

### Cost Observations
- Model mix: predominio de sonnet para pesquisa/execucao/verificacao
- Sessions: 1
- Notable: alto reaproveitamento de estrutura existente do Django monolito reduziu custo de implementacao

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.1 | 1 | 2 | Consolidação do fluxo PIX manual com governança operacional no painel |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.1 | suites de pagamentos/restaurantes verdes | n/a | 0 |

### Top Lessons (Verified Across Milestones)

1. Manter o `pago=True` como gate central simplifica integração entre fases.
2. Contratos de contexto antes do plano aumentam previsibilidade da execução.
