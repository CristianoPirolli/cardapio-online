---
phase: 02-gest-o-de-chaves-pix
verified: 2026-04-11T00:02:10Z
status: human_needed
score: 6/6 must-haves verified
human_verification:
  - test: "Checkout PIX em navegador com pedido real"
    expected: "Pagina de pagamento exibe a chave snapshot correta do restaurante e o aviso aparece quando nao houver chave ativa."
    why_human: "Fluxo visual e UX de mensagens no template HTML precisam de validacao manual."
  - test: "Gestao de chaves PIX no painel (CRUD completo)"
    expected: "Criar/editar/ativar/desativar/padrao/prioridade funcionam na mesma tela e refletem imediatamente na tabela."
    why_human: "Interacao de formularios e feedback visual (mensagens/estado ativo) nao e totalmente validavel por analise estatica."
  - test: "Historico no painel"
    expected: "Historico mostra quem/quando/acao/antes/depois em ordem do mais recente para o mais antigo."
    why_human: "Apresentacao final dos dados e legibilidade do diff dependem de validacao visual humana."
---

# Phase 2: Gestão de Chaves PIX Verification Report

**Phase Goal:** Suportar multiplas chaves PIX por restaurante e aplicar regras de selecao no checkout mantendo o fluxo manual atual.  
**Verified:** 2026-04-11T00:02:10Z  
**Status:** human_needed  
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Checkout PIX sempre exibe uma chave do proprio restaurante usando regra deterministica. | ✓ VERIFIED | `selecionar_chave_pix_checkout` aplica padrao ativa e fallback por prioridade/id em `apps/pagamentos/services.py:21-43`; `pagamento_pix_manual` usa snapshot no render em `apps/pagamentos/views.py:93-121`; template exibe `pix_key` em `templates/pagamentos/pagamento.html:41-69`. |
| 2 | Mudancas de ativacao/desativacao ou prioridade nao alteram a chave de pedidos ja iniciados. | ✓ VERIFIED | Snapshot persistido em `Pagamento` (`apps/pagamentos/models.py:74-90`) e aplicado/reutilizado em `apps/pagamentos/services.py:46-113` com lock transacional (`select_for_update`). |
| 3 | Existe apenas uma chave padrao ativa por restaurante e prioridades ativas nao conflitam. | ✓ VERIFIED | Constraints condicionais no model e migration: `apps/pagamentos/models.py:149-160`, `apps/pagamentos/migrations/0008_chave_pix_models_and_snapshot.py:77-84`; validacao complementar em `apps/pagamentos/forms.py:56-66`. |
| 4 | Restaurante consegue cadastrar, editar, ativar/desativar e ordenar multiplas chaves PIX no painel. | ✓ VERIFIED | Views de CRUD/mutacao em `apps/pagamentos/views.py:124-389`, rotas em `apps/pagamentos/urls.py:15-20` e `apps/restaurantes/urls.py:25`, formularios no template `templates/painel/pix_keys.html:17-109`. |
| 5 | Somente uma chave padrao ativa e uma prioridade ativa por restaurante sao aceitas. | ✓ VERIFIED | Regras aplicadas por constraints de banco + transacoes de mutacao (`apps/pagamentos/views.py:168-176`, `217-225`, `330-337`, `372-379`) e form (`apps/pagamentos/forms.py:56-66`). |
| 6 | Tela do painel mostra historico de mutacoes com quem/quando/acao/antes/depois. | ✓ VERIFIED | Registro append-only em `apps/pagamentos/views.py:53-60` + `176-182`, `225-231`, `271-277`, `302-308`, `338-344`, `381-387`; exibicao em `templates/painel/pix_keys.html:127-147`. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `apps/pagamentos/models.py` | Modelos/constraints/snapshot | ✓ VERIFIED | Existe, substantivo, usado por forms/services/views/tests. |
| `apps/pagamentos/services.py` | Selecao deterministica + snapshot | ✓ VERIFIED | Existe, substantivo, chamado por views/tests. |
| `apps/pagamentos/views.py` | Checkout + painel CRUD/historico | ✓ VERIFIED | Existe, substantivo, roteado e renderiza templates. |
| `apps/pagamentos/migrations/0008_chave_pix_models_and_snapshot.py` | Schema + constraints | ✓ VERIFIED | Existe e define modelos/campos/constraints esperados. |
| `apps/pagamentos/forms.py` | Form com validacao por tipo/integridade | ✓ VERIFIED | Existe, substantivo, instanciado em views de painel. |
| `templates/painel/pix_keys.html` | Tela unica gestao + historico | ✓ VERIFIED | Existe, substantivo, renderizado por `painel_pix_keys`. |
| `apps/pagamentos/tests/test_views_chaves_pix.py` | Cobertura de painel/checkout | ✓ VERIFIED | Existe, substantivo, executado com sucesso em spot-check. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `apps/pagamentos/views.py` | `apps/pagamentos/services.py` | `pagamento_pix_manual -> criar_pagamento_pix_manual -> selecionar_chave_pix_checkout` | ✓ WIRED | Import e chamada em `apps/pagamentos/views.py:28,93`. |
| `apps/pagamentos/services.py` | `apps/pagamentos/models.py` | persistencia de snapshot no `Pagamento` | ✓ WIRED | `dados_resposta['pix_key']` e campos snapshot em `apps/pagamentos/services.py:50-61`. |
| `apps/pagamentos/models.py` | DB constraints | UniqueConstraint condicional por restaurante | ✓ WIRED | Constraints declaradas em model e migration (`models.py:149-160`, migration `:77-84`). |
| `templates/painel/pix_keys.html` | `apps/pagamentos/views.py` | actions criar/editar/ativar/desativar/padrao/prioridade | ✓ WIRED | Forms POST para URLs de mutacao em `pix_keys.html:18,38,90,95,100,104` + handlers em `views.py:153-389`. |
| `apps/pagamentos/views.py` | `ChavePixHistorico` | registro append-only | ✓ WIRED | `ChavePixHistorico.objects.create` em `apps/pagamentos/views.py:53-60`. |
| `templates/painel/base_painel.html` | `apps/restaurantes/urls.py` | navegacao para `painel_pix_keys` | ✓ WIRED | Link `base_painel.html:52` para rota `apps/restaurantes/urls.py:25`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `apps/pagamentos/views.py` + `templates/pagamentos/pagamento.html` | `pix_key`/`pix_key_tipo` | `criar_pagamento_pix_manual` -> `selecionar_chave_pix_checkout` -> `ChavePix.objects.filter(...)` | Yes | ✓ FLOWING |
| `apps/pagamentos/views.py` + `templates/painel/pix_keys.html` | `chaves` | `ChavePix.objects.filter(restaurante=restaurante).order_by(...)` | Yes | ✓ FLOWING |
| `apps/pagamentos/views.py` + `templates/painel/pix_keys.html` | `historico` | `ChavePixHistorico.objects.filter(...).order_by('-criado_em','-id')` | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Regras de integridade e selecao/snapshot de chave PIX | `venv\Scripts\python manage.py test apps.pagamentos.tests.test_chaves_pix.ChavePixModelTest apps.pagamentos.tests.test_chaves_pix.ChavePixServiceTest --verbosity=1 --keepdb --noinput` | `Ran 7 tests ... OK` | ✓ PASS |
| Checkout + painel CRUD/historico + autorizacao/regressao focal | `venv\Scripts\python manage.py test apps.pagamentos.tests.test_views_chaves_pix.PagamentoPixChaveViewTest apps.pagamentos.tests.test_views_chaves_pix.PainelPixKeysViewTest --verbosity=1 --keepdb --noinput` | `Ran 13 tests ... OK` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| PAY-15 | 02-02-PLAN.md | Restaurante cadastra multiplas chaves PIX ativas no painel | ✓ SATISFIED | CRUD e tela unica em `apps/pagamentos/views.py:124-389`, `templates/painel/pix_keys.html:17-117`; testes `test_views_chaves_pix.py`. |
| PAY-16 | 02-01-PLAN.md, 02-02-PLAN.md | Define chave padrao e prioridade de uso | ✓ SATISFIED | Constraints + mutacoes transacionais (`models.py:149-160`, `views.py:330-337`, `372-379`). |
| PAY-17 | 02-01-PLAN.md | Checkout seleciona/exibe chave correta conforme regra | ✓ SATISFIED | Selecao deterministica em `services.py:21-43`; render de snapshot em `views.py:106-121` e `pagamento.html:41-69`. |
| PAY-18 | 02-01-PLAN.md | Pedidos em andamento mantem consistencia com ativacao/desativacao | ✓ SATISFIED | Snapshot persistido/reutilizado com lock em `services.py:79-113` e campos em `models.py:74-90`. |

### Anti-Patterns Found

No blocker/warning anti-patterns encontrados nos arquivos-chave da fase.  
Nota: hashes de commit citados em SUMMARIES nao foram validados localmente por `gsd-tools verify commits` (informativo; nao bloqueia a verificacao de codigo atual).

### Human Verification Required

### 1. Checkout PIX em navegador com pedido real
**Test:** Abrir `/pagamentos/<pedido_id>/` com restaurante contendo chave ativa e sem chave ativa.  
**Expected:** Com chave ativa, campo exibe snapshot correto; sem chave ativa, aviso de indisponibilidade aparece sem quebrar fluxo.  
**Why human:** Validacao de UX visual e clareza de mensagem.

### 2. Gestao de chaves PIX no painel
**Test:** Em `/painel/chaves-pix/`, executar criar, editar, ativar, desativar, definir padrao e mudar prioridade.  
**Expected:** Tabela atualiza conforme acao, mensagens de sucesso/erro coerentes, navegacao do menu marca item ativo.  
**Why human:** Fluxo de interacao e feedback visual dependem de validacao manual.

### 3. Historico de mutacoes
**Test:** Realizar mutacoes consecutivas e inspecionar bloco "Historico de mutacoes".  
**Expected:** Exibe quem/quando/acao/antes/depois em ordem decrescente de tempo.  
**Why human:** Legibilidade e apresentacao final do diff precisam de avaliacao humana.

### Gaps Summary

Nao foram encontrados gaps de implementacao que bloqueiem o objetivo tecnico da fase.  
Todos os must-haves e requisitos PAY-15/16/17/18 estao implementados e validados por checagens automatizadas; restam validacoes humanas de UX/fluxo visual.

---

_Verified: 2026-04-11T00:02:10Z_  
_Verifier: Claude (gsd-verifier)_
