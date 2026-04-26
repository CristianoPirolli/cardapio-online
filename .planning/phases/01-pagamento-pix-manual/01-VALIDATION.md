---
phase: 1
slug: pagamento-pix-manual
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-02
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Django TestCase (built-in `unittest`) |
| **Config file** | none — uses `python manage.py test` |
| **Quick run command** | `python manage.py test apps.pagamentos.tests --verbosity=1` |
| **Full suite command** | `python manage.py test --verbosity=1` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python manage.py test apps.pagamentos.tests --verbosity=1`
- **After every plan wave:** Run `python manage.py test --verbosity=1`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-02-01 | 02 | 2 | REQ-08 | unit | `python manage.py test apps.pedidos.tests.test_status.StatusGraphTest.test_aguardando_confirmacao_transitions --verbosity=1` | ✅ | ⬜ pending |
| 1-02-02 | 02 | 2 | REQ-03 | unit | `python manage.py test apps.pagamentos.tests.test_services.PixManualServiceTest.test_upload_comprovante --verbosity=1` | ✅ | ⬜ pending |
| 1-03-01 | 03 | 3 | REQ-01, REQ-02, REQ-07 | integration | `python manage.py test apps.pagamentos.tests.test_views --verbosity=1` | ✅ | ⬜ pending |
| 1-04-01 | 04 | 4 | REQ-04, REQ-05, REQ-06 | integration | `python manage.py test apps.pagamentos.tests.test_services apps.pagamentos.tests.test_views --verbosity=1` | ✅ | ⬜ pending |
| 1-05-01 | 05 | 5 | REQ-11, REQ-12, REQ-13, REQ-14 | e2e/regression | `python manage.py test --verbosity=1` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `apps/pagamentos/tests/test_services.py` — scaffold exists for REQ-03/04/05
- [x] `apps/pagamentos/tests/test_views.py` — scaffold exists for REQ-01/02/07
- [x] `apps/pedidos/tests/test_status.py` — scaffold exists for REQ-08

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Copy PIX key and leave to bank app, then return to order page | REQ-01, REQ-02 | Cross-app navigation depends on real browser/user behavior | Open checkout, copy PIX key, switch app/tab, return to `/pedidos/<id>/acompanhar/`, confirm order state preserved |
| Restaurant views uploaded comprovante before accepting/rejecting | REQ-04, REQ-05 | Requires visual file inspection in admin/painel UI | Upload image/PDF comprovante, open pending order in painel/admin, confirm file is viewable, then accept and reject in separate test orders |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-02
