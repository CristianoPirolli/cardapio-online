---
phase: 02-gest-o-de-chaves-pix
plan: 01
subsystem: payments
tags: [django, pix, checkout, snapshot, constraints]
requires:
  - phase: 01-pagamento-pix-manual
    provides: fluxo pix manual com confirmacao manual por comprovante
provides:
  - modelos de chave pix por restaurante com constraints de integridade
  - selecao deterministica de chave no checkout
  - snapshot de chave no pagamento pendente para consistencia
affects: [phase-02-plan-02, painel-restaurante, pagamento-manual]
tech-stack:
  added: []
  patterns: [tenant-scoped pix keys, deterministic selection, payment snapshot consistency]
key-files:
  created:
    - apps/pagamentos/migrations/0008_chave_pix_models_and_snapshot.py
    - apps/pagamentos/tests/test_views_chaves_pix.py
  modified:
    - apps/pagamentos/models.py
    - apps/pagamentos/services.py
    - apps/pagamentos/views.py
    - templates/pagamentos/pagamento.html
    - apps/pagamentos/tests/test_chaves_pix.py
key-decisions:
  - "Garantir unicidade de chave padrao/prioridade ativa por restaurante via constraints condicionais em banco."
  - "Persistir snapshot da chave PIX no Pagamento (campos dedicados + dados_resposta.pix_key) para preservar pedidos em andamento."
  - "Remover fallback para PIX global no checkout; ausencia de chave ativa gera falha controlada."
patterns-established:
  - "Chave PIX deve ser resolvida por service unico (selecionar_chave_pix_checkout) e nunca por settings global."
  - "Pedido pendente reutilizado nao pode alterar snapshot de chave apos manutencoes de configuracao."
requirements-completed: [PAY-16, PAY-17, PAY-18]
duration: 29min
completed: 2026-04-10
---

# Phase 2 Plan 1: Base de Chaves PIX Summary

**Selecao de chave PIX por restaurante com regra deterministica e snapshot persistido no pagamento para manter consistencia do fluxo manual.**

## Performance

- **Duration:** 29 min
- **Started:** 2026-04-10T23:33:04Z
- **Completed:** 2026-04-11T00:02:00Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Introduzidos `ChavePix` e `ChavePixHistorico` com constraints por restaurante (padrao ativa unica e prioridade ativa unica).
- Implementado service de selecao deterministica (`padrao` ativa, fallback por prioridade/id) sem `settings.PIX_KEY`.
- Checkout atualizado para usar snapshot da chave no pagamento e manter fluxo manual sem gateway/webhook.

## Task Commits

Each task was committed atomically:

1. **Task 1: Criar contratos de dados e constraints de chave PIX por restaurante**
2. `029f653` (test) RED
3. `22e520f` (feat) GREEN
4. **Task 2: Implementar service de selecao deterministica e snapshot de consistencia**
5. `4e8ae72` (test) RED
6. `d174cf6` (feat) GREEN
7. **Task 3: Integrar checkout para exibir chave selecionada do restaurante**
8. `c49e4e0` (test) RED
9. `87629b7` (feat) GREEN

## Files Created/Modified
- `apps/pagamentos/models.py` - modelos `ChavePix`/`ChavePixHistorico` e campos snapshot em `Pagamento`.
- `apps/pagamentos/migrations/0008_chave_pix_models_and_snapshot.py` - schema para novos modelos/campos/constraints.
- `apps/pagamentos/services.py` - selecao deterministica de chave e persistencia de snapshot em criacao/reuso.
- `apps/pagamentos/views.py` - checkout usando snapshot por pedido e mensagem controlada sem chave ativa.
- `templates/pagamentos/pagamento.html` - exibicao de metadados da chave (tipo e valor mascarado).
- `apps/pagamentos/tests/test_chaves_pix.py` - cobertura de constraints, validacao por tipo, selecao e snapshot.
- `apps/pagamentos/tests/test_views_chaves_pix.py` - cobertura de checkout por restaurante e reapresentacao de snapshot.

## Decisions Made
- Prioridade ativa foi mantida como unica por restaurante em nível de banco, conforme decisão lockada do contexto.
- Snapshot da chave foi salvo em campos dedicados e também em `dados_resposta.pix_key` para compatibilidade retroativa.
- Ausência de chave ativa no checkout passou a ter tratamento explícito via mensagem, sem fallback global.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrigida ordem de validacao do `valor_normalizado` em `ChavePix`**
- **Found during:** Task 1
- **Issue:** `save()` com `full_clean()` falhava antes da normalizacao e impedia cenarios validos.
- **Fix:** `valor_normalizado` passou a aceitar `blank=True` e o `save()` passou a normalizar via `clean()` antes de persistir.
- **Files modified:** `apps/pagamentos/models.py`, `apps/pagamentos/migrations/0008_chave_pix_models_and_snapshot.py`
- **Verification:** `venv\Scripts\python manage.py test apps.pagamentos.tests.test_chaves_pix --verbosity=1 --keepdb --noinput`
- **Committed in:** `22e520f`

---

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** Ajuste necessário para consistência do contrato de validação sem ampliar escopo.

## Issues Encountered
- Nenhum bloqueio externo. Execução ocorreu totalmente no workspace local.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Base transacional e seleção determinística prontas para avançar o painel completo de gestão (CRUD/histórico) no plano 02-02.
- Fluxo manual de confirmação foi preservado, sem introdução de gateway/webhook.

---
*Phase: 02-gest-o-de-chaves-pix*
*Completed: 2026-04-10*

## Self-Check: PASSED
- FOUND: `.planning/phases/02-gest-o-de-chaves-pix/02-01-SUMMARY.md`
- FOUND: `029f653`
- FOUND: `22e520f`
- FOUND: `4e8ae72`
- FOUND: `d174cf6`
- FOUND: `c49e4e0`
- FOUND: `87629b7`
