---
phase: 01-pagamento-pix-manual
verified: 2026-04-08T00:21:59Z
status: human_needed
score: 3/3 must-haves verified
human_verification:
  - test: "Cópia real da chave PIX no navegador"
    expected: "Botão 'Copiar' copia para clipboard e feedback visual 'Copiado!' aparece"
    why_human: "Clipboard/browser permission e feedback visual não são confirmáveis só por leitura de código"
  - test: "Fluxo E2E real cliente→restaurante no browser"
    expected: "Upload real do comprovante, visualização do arquivo no painel, aceitar/rejeitar com UX correta"
    why_human: "Interação visual e abertura real de arquivo via MEDIA_URL exigem execução manual"
---

# Phase 01: Pagamento PIX Manual Verification Report

**Phase Goal:** Substituir gateway por PIX manual com chave fixa, upload de comprovante e aprovacao manual do restaurante antes do pipeline existente.  
**Verified:** 2026-04-08T00:21:59Z  
**Status:** human_needed  
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Cliente consegue copiar chave PIX, retornar ao pedido e enviar comprovante | ✓ VERIFIED | `pagamento_pix_manual` expõe `pix_key` e cria pagamento idempotente; template mostra `#pix-code` + `#btn-copiar`; upload aceita multipart e salva comprovante com validação de extensão/tamanho em `apps/pagamentos/views.py` e `templates/pagamentos/*` |
| 2 | Restaurante revisa comprovante e aceita/rejeita antes da produção | ✓ VERIFIED | `aceitar_pix`/`rejeitar_pix` existem, exigem login e pedido `aguardando_confirmacao`; detalhe mostra link do comprovante e botões de ação |
| 3 | Pedido aceito entra no fluxo existente e soma no painel | ✓ VERIFIED | `confirmar_pix_manual` define `pedido.pago=True` e `status='recebido'`; dashboard e pedidos do painel usam gate `pago=True`, preservando pipeline existente |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `apps/pagamentos/services.py` | Serviços PIX manual | ✓ VERIFIED | Funções `criar_pagamento_pix_manual`, `confirmar_pix_manual`, `rejeitar_pix_manual` implementadas |
| `apps/pagamentos/views.py` | Fluxo cliente + ações restaurante | ✓ VERIFIED | Views de pagamento/upload/sucesso/erro e aceitar/rejeitar presentes |
| `apps/pagamentos/urls.py` | Rotas PIX manual | ✓ VERIFIED | Rotas `pagamento_pix_manual`, `upload_comprovante`, `aceitar_pix`, `rejeitar_pix` |
| `templates/pagamentos/pagamento.html` | Chave PIX + cópia | ✓ VERIFIED | Input readonly com chave e botão de cópia |
| `templates/pagamentos/pix_upload.html` | Upload multipart | ✓ VERIFIED | Form `multipart/form-data` e `hx-boost="false"` |
| `templates/painel/pedido_detalhe.html` | Revisão comprovante + aceitar/rejeitar | ✓ VERIFIED | Link de comprovante + forms POST para aceitar/rejeitar |
| `templates/painel/pedidos.html` | Fila aguardando confirmação PIX | ✓ VERIFIED | Seção destacada + filtro `aguardando_confirmacao` |
| `config/context_processors.py` | Contador de pendências PIX | ✓ VERIFIED | `aguardando_confirmacao_count` calculado e injetado no contexto |
| `templates/pagamentos/sucesso.html` | Mensagem de aguardando confirmação | ✓ VERIFIED | Condicional para `pedido.status == 'aguardando_confirmacao'` |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `apps/pagamentos/views.py` | `apps/pagamentos/services.py` | `criar_pagamento_pix_manual()` no GET/upload fallback | ✓ WIRED | Chamadas diretas nas linhas 49 e 87 |
| `apps/pagamentos/views.py` | `Pedido.status='aguardando_confirmacao'` | Após upload válido | ✓ WIRED | Atribuição + `pedido.save()` |
| `templates/pagamentos/pix_upload.html` | `upload_comprovante` | `form` POST `multipart/form-data` | ✓ WIRED | Action com URL nomeada e enctype correto |
| `templates/painel/pedido_detalhe.html` | `aceitar_pix/rejeitar_pix` | Forms POST | ✓ WIRED | URLs nomeadas com CSRF |
| `config/context_processors.py` | `Pedido.objects.filter(status='aguardando_confirmacao')` | `aguardando_confirmacao_count` | ✓ WIRED | Query real em runtime |
| `apps/restaurantes/views.py` | `Pagamentos.comprovante` | `pagamento_pix` no contexto do detalhe | ✓ WIRED | Query por pedido/gateway e render em template |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `templates/pagamentos/pagamento.html` | `pix_key` | `settings.PIX_KEY` via `pagamento_pix_manual` | Sim (`config/settings.py`) | ✓ FLOWING |
| `templates/pagamentos/pix_upload.html` | `pedido`, `messages` | `upload_comprovante` + validações | Sim (request + DB) | ✓ FLOWING |
| `templates/painel/pedido_detalhe.html` | `pagamento_pix.comprovante` | Query `Pagamento.objects.filter(...)` | Sim (DB) | ✓ FLOWING |
| `templates/painel/pedidos.html` | `pendentes_pix` | Query `Pedido.objects.filter(status='aguardando_confirmacao')` | Sim (DB) | ✓ FLOWING |
| `templates/painel/base_painel.html` | `aguardando_confirmacao_count` | Context processor com query em `Pedido` | Sim (DB) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Django consistency | `venv\Scripts\python manage.py check` | `System check identified no issues` | ✓ PASS |
| Migrations required by phase | `venv\Scripts\python manage.py showmigrations pagamentos pedidos` | `0007_add_pix_manual_fields` e `0009_extend_status_length` aplicadas | ✓ PASS |
| PIX manual core tests | `venv\Scripts\python manage.py test apps.pagamentos.tests.test_services apps.pagamentos.tests.test_views apps.pedidos.tests.test_status --keepdb --noinput` | 18 testes, `OK` | ✓ PASS |
| Suite regression | `venv\Scripts\python manage.py test --keepdb --noinput` | 21 testes, `OK` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| REQ-01 | 01-03/01-05 | Cliente visualiza chave PIX fixa | ✓ SATISFIED | `pagamento_pix_manual` + template `pagamento.html` |
| REQ-02 | 01-03/01-05 | Cliente copia chave PIX | ? NEEDS HUMAN | JS de cópia existe, mas clipboard real requer browser |
| REQ-03 | 01-03/01-05 | Pedido acessível após sair/voltar | ? NEEDS HUMAN | Fluxo por `pedido_id` (sem sessão obrigatória), validar retorno real no browser |
| REQ-04 | 01-03/01-05 | Upload de comprovante imagem/PDF | ✓ SATISFIED | `upload_comprovante` + `pix_upload.html` |
| REQ-05 | 01-03/01-05 | Status vira aguardando confirmação | ✓ SATISFIED | `pedido.status='aguardando_confirmacao'` após upload |
| REQ-06 | 01-02/01-04/01-05 | Restaurante vê fila antes da produção | ✓ SATISFIED | `pendentes_pix` + badge + filtro específico |
| REQ-07 | 01-03/01-04/01-05 | Restaurante visualiza comprovante | ? NEEDS HUMAN | Link `pagamento_pix.comprovante.url` implementado; abertura real do arquivo é manual |
| REQ-08 | 01-04/01-05 | Aceitar pedido envia ao fluxo existente | ✓ SATISFIED | `confirmar_pix_manual` => `pago=True`, `status='recebido'` |
| REQ-09 | 01-04/01-05 | Rejeitar cancela pedido | ✓ SATISFIED | `rejeitar_pix_manual` => `status='cancelado'` |
| REQ-10 | 01-04/01-05 | Totais do painel incluem aceitos | ✓ SATISFIED | Dashboard opera em `Pedido(pago=True)`; aceitação seta `pago=True` |
| REQ-11 | 01-01/01-05 | Remoção gateway antigo do fluxo ativo | ✓ SATISFIED | Sem referências runtime a MP/Stripe em serviços/views/urls ativos |
| REQ-12 | 01-01/01-05 | PIX key configurável por ambiente | ✓ SATISFIED | `PIX_KEY = os.getenv('PIX_KEY', '')` |
| REQ-13 | 01-02/01-03/01-05 | Tipos e limite de upload | ✓ SATISFIED | Validador de extensão + limite 10MB |
| REQ-14 | 01-02/01-05 | Pipeline existente preservado | ✓ SATISFIED | BFS atualizado com nó intermediário sem quebrar fluxo pago existente |

**Orphaned requirements:** nenhum (REQ-01..REQ-14 estão mapeados nos planos da fase).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `config/context_processors.py` | 26 | `return {}` em `_skip_context` | ℹ️ Info | Comportamento intencional de curto-circuito, não stub |

### Human Verification Required

### 1. Cópia de chave PIX no browser
**Test:** Abrir `/pagamentos/<id>/`, clicar em `Copiar`.  
**Expected:** Texto vai para clipboard e botão muda para `Copiado!`.  
**Why human:** Clipboard API depende de ambiente/navegador.

### 2. E2E completo com arquivo real
**Test:** Cliente envia comprovante real, restaurante abre arquivo e aceita/rejeita no painel.  
**Expected:** Upload real acessível por link; aceitar leva a `recebido` e rejeitar a `cancelado`.  
**Why human:** Verificação visual e abertura real do arquivo não são totalmente cobertas por inspeção estática.

### Gaps Summary

Nenhum gap de implementação foi encontrado nos checks automatizados e no código.  
Status `human_needed` ocorre apenas por itens de UX/comportamento real de navegador.

---

_Verified: 2026-04-08T00:21:59Z_  
_Verifier: Claude (gsd-verifier)_
