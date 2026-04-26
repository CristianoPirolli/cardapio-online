---
phase: 03
slug: revis-o-manual-e-auditoria
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Django TestCase (unittest runner) |
| **Config file** | `manage.py` / `config/settings.py` |
| **Quick run command** | `venv\Scripts\python manage.py test apps.pagamentos.tests.test_revisao_manual apps.pagamentos.tests.test_auditoria_revisao apps.restaurantes.tests.test_painel_revisao --keepdb --noinput` |
| **Full suite command** | `venv\Scripts\python manage.py test --keepdb --noinput` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `venv\Scripts\python manage.py test apps.pagamentos.tests.test_revisao_manual apps.pagamentos.tests.test_auditoria_revisao apps.restaurantes.tests.test_painel_revisao --keepdb --noinput`
- **After every plan wave:** Run `venv\Scripts\python manage.py test --keepdb --noinput`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | OPS-02, OPS-03 | integration (RED) | `venv\Scripts\python manage.py test apps.pagamentos.tests.test_revisao_manual apps.pagamentos.tests.test_auditoria_revisao --keepdb --noinput` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | OPS-02, OPS-03 | unit/integration | `venv\Scripts\python manage.py test apps.pagamentos.tests.test_auditoria_revisao --keepdb --noinput` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | OPS-02, OPS-03 | integration | `venv\Scripts\python manage.py test apps.pagamentos.tests.test_revisao_manual apps.pagamentos.tests.test_auditoria_revisao --keepdb --noinput` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | OPS-01 | integration (RED) | `venv\Scripts\python manage.py test apps.restaurantes.tests.test_painel_revisao --keepdb --noinput` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | OPS-01 | integration | `venv\Scripts\python manage.py test apps.restaurantes.tests.test_painel_revisao --keepdb --noinput` | ❌ W0 | ⬜ pending |
| 03-02-03 | 02 | 2 | OPS-03 | integration/regression | `venv\Scripts\python manage.py test apps.pagamentos.tests.test_auditoria_revisao apps.restaurantes.tests.test_painel_revisao --keepdb --noinput && venv\Scripts\python manage.py test --keepdb --noinput` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/pagamentos/tests/test_revisao_manual.py` — testes de validacao de justificativa/motivo e acoes aprovar/rejeitar
- [ ] `apps/restaurantes/tests/test_painel_revisao.py` — testes de filtro por periodo e exibicao da fila/manual
- [ ] `apps/pagamentos/tests/test_auditoria_revisao.py` — testes de historico auditavel por pedido

Depois de criar esses arquivos no Plan 03-01 Task 1 e Plan 03-02 Task 1, atualizar `wave_0_complete: true`.

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Fluxo visual completo da fila no painel | OPS-01 | Conferencia de UX (hierarquia visual, foco, legibilidade) | Abrir `/painel/pedidos/`, alternar presets de periodo, validar ordenacao por recencia e mensagens de vazio/erro |
| Experiencia de justificativa no detalhe | OPS-02 | Qualidade de copy/estados de erro e confirmacao | Abrir `pedido_detalhe`, tentar enviar sem preencher, validar erro, preencher motivo+texto e confirmar acoes |
| Leitura do historico no detalhe | OPS-03 | Validar clareza de trilha para operador | No detalhe do pedido, verificar bloco de historico com acao e data/hora em ordem mais recente primeiro |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
