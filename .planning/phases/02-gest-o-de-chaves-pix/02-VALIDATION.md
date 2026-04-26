---
phase: 2
slug: gest-o-de-chaves-pix
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-10
---

# Phase 2 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Django TestCase (unittest) |
| **Config file** | none — uses `python manage.py test` |
| **Quick run command** | `python manage.py test apps.pagamentos.tests --verbosity=1 --keepdb --noinput` |
| **Full suite command** | `python manage.py test --verbosity=1 --keepdb --noinput` |
| **Estimated runtime** | ~120 seconds |

## Sampling Rate

- After every task commit: run pagamentos-focused tests
- After every wave: run full suite
- Before verify-work: full suite must be green

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | PAY-15, PAY-16 | unit | `python manage.py test apps.pagamentos.tests.test_chaves_pix --verbosity=1 --keepdb --noinput` | ✅ | ⬜ pending |
| 2-01-02 | 01 | 1 | PAY-17, PAY-18 | unit | `python manage.py test apps.pagamentos.tests.test_chaves_pix --verbosity=1 --keepdb --noinput` | ✅ | ⬜ pending |
| 2-02-01 | 02 | 2 | PAY-15..PAY-18 | integration | `python manage.py test apps.pagamentos.tests.test_views_chaves_pix --verbosity=1 --keepdb --noinput` | ✅ | ⬜ pending |

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Validação visual e operação da tela de gestão completa | PAY-15..PAY-18 | UX/human flow | Testar CRUD/ativação/padrão/prioridade e histórico no painel |

## Validation Sign-Off

- [x] All tasks require automated verification
- [x] Wave 0 dependency covered
- [x] nyquist_compliant true

**Approval:** approved 2026-04-10
