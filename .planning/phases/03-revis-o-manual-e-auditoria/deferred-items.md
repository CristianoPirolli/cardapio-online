# Deferred Items - Phase 03

## 2026-04-11 - Plan 03-02 execution

- Full suite regression (`venv\Scripts\python manage.py test --verbosity=1 --keepdb --noinput`) failed in pre-existing PIX keys panel tests:
  - `apps.pagamentos.tests.test_views_chaves_pix.PainelPixKeysViewTest.test_painel_pix_keys_nao_exibe_historico_antes_depois`
  - `apps.pagamentos.tests.test_views_chaves_pix.PainelPixKeysViewTest.test_prioridade_ativa_duplicada_por_restaurante_e_rejeitada`
  - `apps.pagamentos.tests.test_views_chaves_pix.PainelPixKeysViewTest.test_validacao_por_tipo_rejeita_cpf_cnpj_email_telefone_e_uuid_invalidos`
- Symptom: expected `200`, received `302`.
- Scope decision: not fixed in Plan 03-02 because failures are in unrelated PIX keys management flow and existed outside the manual-review queue/audit-detail changes.
