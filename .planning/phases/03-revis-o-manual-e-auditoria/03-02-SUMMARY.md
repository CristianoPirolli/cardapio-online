---
phase: 03-revis-o-manual-e-auditoria
plan: 02
subsystem: ui
tags: [django, pix-manual, auditoria, painel, testing]
requires:
  - phase: 03-01
    provides: contrato de decisao manual com historico persistido
provides:
  - filtro operacional por periodo na fila de revisao manual
  - bloco de historico auditavel minimo no detalhe do pedido
  - cobertura de regressao para presets/custom e escopo de exibicao
affects: [painel-pedidos, painel-pedido-detalhe, revisao-manual]
tech-stack:
  added: []
  patterns:
    - fallback para ultimo periodo valido via sessao em filtros operacionais
    - feed auditavel minimizado (acao + data/hora) restrito ao detalhe
key-files:
  created:
    - apps/restaurantes/tests/__init__.py
    - apps/restaurantes/tests/test_painel_revisao.py
  modified:
    - apps/restaurantes/views.py
    - templates/painel/pedidos.html
    - apps/pagamentos/tests/test_auditoria_revisao.py
key-decisions:
  - "Filtro operacional aplicado apenas na fila Aguardando PIX, preservando visao padrao de pedidos."
  - "Historico de revisao permanece visivel somente no detalhe e com campos minimos de exibicao."
patterns-established:
  - "Periodo custom invalido reusa ultima selecao valida e mostra mensagem clara."
  - "Regressoes de auditoria validam ordenacao descrescente e ausencia fora do detalhe."
requirements-completed: [OPS-01, OPS-03]
duration: 9min
completed: 2026-04-11
---

# Phase 3 Plan 2: Revisao Operacional Summary

**Fila de revisao PIX com filtro por periodo (presets + custom validado) e trilha auditavel minima exibida apenas no detalhe do pedido**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-11T11:33:53Z
- **Completed:** 2026-04-11T11:42:37Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Criada suite RED/GREEN para contratos de periodo: `hoje`, `ontem`, `7d`, `30d` e `custom`.
- Implementado filtro operacional por periodo na fila `aguardando_confirmacao`, com fallback para ultima selecao valida em custom invalido.
- Consolidada regressao da trilha auditavel no detalhe com ordem por recencia e visibilidade restrita ao detalhe.

## Task Commits

Each task was committed atomically:

1. **Task 1: Criar testes da fila operacional com filtro por periodo** - `783b31a` (test)
2. **Task 2: Implementar filtro de periodo na fila e UI operacional no painel de pedidos** - `da0b2df` (feat)
3. **Task 3: Exibir trilha auditavel no detalhe e executar regressao integrada** - `f047dba` (feat)

## Files Created/Modified
- `apps/restaurantes/tests/__init__.py` - habilita pacote de testes do app restaurantes.
- `apps/restaurantes/tests/test_painel_revisao.py` - cobre contratos operacionais de filtro por periodo e ordenacao.
- `apps/restaurantes/views.py` - aplica filtro de periodo na fila PIX e torna historico acessivel no detalhe.
- `templates/painel/pedidos.html` - adiciona controles de periodo e reforca copy "Todos os pedidos"/"Aguardando PIX".
- `apps/pagamentos/tests/test_auditoria_revisao.py` - amplia regressao de auditoria (ordem, escopo de exibicao, persistencia no detalhe).

## Decisions Made
- Mantida a regra de UX operacional minima: nenhum novo filtro adicional para fila alem de periodo.
- Historico continuou restrito ao detalhe, mostrando apenas acao e data/hora (D-09/D-10), sem operador/motivo/justificativa na UI.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ajuste de storage estatico nos testes da fila operacional**
- **Found during:** Task 1
- **Issue:** Renderizacao de template falhava em RED por `Missing staticfiles manifest entry`.
- **Fix:** Aplicado `@override_settings(STORAGES=...)` no teste para usar `StaticFilesStorage`.
- **Files modified:** `apps/restaurantes/tests/test_painel_revisao.py`
- **Verification:** Suite focal passou de erro de infraestrutura para falhas funcionais RED esperadas.
- **Committed in:** `783b31a`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Correcao necessaria para executar TDD sem alterar escopo funcional.

## Auth Gates
None.

## Issues Encountered
- Regressao completa (`manage.py test`) permaneceu vermelha em testes preexistentes de chaves PIX (`apps.pagamentos.tests.test_views_chaves_pix` com `302` onde era esperado `200`), fora do escopo deste plano.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None identified in files changed by this plan.

## Next Phase Readiness
- OPS-01 e OPS-03 entregues para operacao no painel.
- Pendencia externa: suite completa depende da estabilizacao dos testes de chaves PIX fora do escopo de 03-02.

---
*Phase: 03-revis-o-manual-e-auditoria*
*Completed: 2026-04-11*

## Self-Check: PASSED
- FOUND: `.planning/phases/03-revis-o-manual-e-auditoria/03-02-SUMMARY.md`
- FOUND commit: `783b31a`
- FOUND commit: `da0b2df`
- FOUND commit: `f047dba`
