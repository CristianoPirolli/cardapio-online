---
phase: 02-gest-o-de-chaves-pix
plan: 02
subsystem: payments
tags: [pix, django, painel, auditoria]
requires:
  - phase: 02-01
    provides: base de dados e selecao deterministica/snapshot por restaurante
provides:
  - CRUD completo de chaves PIX no painel em tela unica
  - historico auditavel de mutacoes com antes/depois
  - navegacao do painel para nova tela de chaves PIX
affects: [checkout-pix-manual, operacao-painel-restaurante, auditoria-operacional]
tech-stack:
  added: []
  patterns:
    - Form ModelForm com validacao de integridade por restaurante
    - Mutacoes de painel com log append-only em ChavePixHistorico
key-files:
  created:
    - apps/pagamentos/forms.py
    - templates/painel/pix_keys.html
  modified:
    - apps/pagamentos/views.py
    - apps/pagamentos/urls.py
    - apps/restaurantes/urls.py
    - templates/painel/base_painel.html
    - apps/pagamentos/tests/test_views_chaves_pix.py
    - apps/pagamentos/tests/test_services.py
    - apps/pagamentos/tests/test_views.py
key-decisions:
  - "Rota principal da tela no namespace do painel (`/painel/chaves-pix/`) e endpoints de mutacao em `/pagamentos/painel/chaves-pix/...`."
  - "Historico operacional limitado a mutacoes do painel; selecao de chave no checkout nao entra no feed."
patterns-established:
  - "Tela unica com bloco de gestao + bloco de historico no mesmo template."
  - "Eventos de mutacao registrados com payload estruturado antes/depois."
requirements-completed: [PAY-15, PAY-16]
duration: 8 min
completed: 2026-04-10
---

# Phase 2 Plan 02: Gestao completa de chaves PIX no painel Summary

**CRUD operacional de chaves PIX em tela unica com regras de padrao/prioridade por restaurante e trilha auditavel de mutacoes**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-10T23:46:24Z
- **Completed:** 2026-04-10T23:54:50Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments
- Entregue fluxo completo no painel para criar, editar, ativar/desativar, definir padrao e ajustar prioridade de chaves PIX.
- Entregue feed de historico no proprio painel com quem/quando/acao/antes/depois, ordenado do mais recente para o mais antigo.
- Integrada navegacao com item "Chaves PIX" e cobertura de regressao/autorizacao em testes de pagamentos.

## Task Commits

1. **Task 1 (RED):** `77b1353` (`test`)  
2. **Task 1 (GREEN):** `119d5b6` (`feat`)  
3. **Task 2 (RED):** `491bf1f` (`test`)  
4. **Task 2 (GREEN):** `9971eb8` (`feat`)  
5. **Task 3:** `df724c8` (`feat`)  

## Files Created/Modified
- `apps/pagamentos/forms.py` - Formulario de cadastro/edicao com validacao de tipo e integridade de prioridade ativa.
- `apps/pagamentos/views.py` - Views de painel para CRUD/mutacoes e registro de historico.
- `apps/pagamentos/urls.py` - Endpoints POST de mutacao do painel.
- `apps/restaurantes/urls.py` - Rota principal `/painel/chaves-pix/`.
- `templates/painel/pix_keys.html` - Tela unica de gestao + historico.
- `templates/painel/base_painel.html` - Item de navegacao "Chaves PIX".
- `apps/pagamentos/tests/test_views_chaves_pix.py` - Cobertura de painel, historico e autorizacao.
- `apps/pagamentos/tests/test_services.py` - Ajuste de baseline para chave ativa por restaurante.
- `apps/pagamentos/tests/test_views.py` - Ajuste de baseline para chave ativa por restaurante.

## Decisions Made
- Manter confirmacao manual inalterada (sem gateway/webhook), adicionando apenas gestao/auditoria de chaves no painel.
- Validacoes de integridade operacional foram aplicadas na camada de formulario/view para feedback imediato no painel.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Atualizacao de baseline de testes legados para multi-chave por restaurante**
- **Found during:** Task 3 (verificacao `apps.pagamentos.tests`)
- **Issue:** Testes antigos de `services`/`views` ainda assumiam criacao de pagamento sem chave ativa, bloqueando a suite focal obrigatoria.
- **Fix:** Adicionada chave PIX ativa por restaurante no `setUp` desses testes para refletir o contrato atual da fase 02.
- **Files modified:** `apps/pagamentos/tests/test_services.py`, `apps/pagamentos/tests/test_views.py`
- **Verification:** `venv\Scripts\python manage.py test apps.pagamentos.tests --verbosity=1 --keepdb --noinput`
- **Committed in:** `df724c8`

---

**Total deviations:** 1 auto-fix (1 blocking)
**Impact on plan:** Correcao de baseline de teste sem alterar escopo funcional; fluxo manual permaneceu intacto.

## Issues Encountered
- Suite de pagamentos falhou inicialmente por incompatibilidade de testes legados com o baseline de multi-chave da fase 02; resolvido com fixture de chave ativa por restaurante.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- PAY-15 e PAY-16 consolidados no painel com historico operacional.
- Base pronta para avancar para verificacao/fase seguinte sem regressao do fluxo PIX manual.

## Self-Check: PASSED
- FOUND: `.planning/phases/02-gest-o-de-chaves-pix/02-02-SUMMARY.md`
- FOUND commits: `77b1353`, `119d5b6`, `491bf1f`, `9971eb8`, `df724c8`

---
*Phase: 02-gest-o-de-chaves-pix*
*Completed: 2026-04-10*
