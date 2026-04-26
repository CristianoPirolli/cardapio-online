# Phase 2: Gestao de Chaves PIX - Research

**Researched:** 2026-04-10  
**Domain:** Django monolith (multi-tenant restaurant panel) + manual PIX checkout key selection  
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Gestão no Painel
- **D-01:** O painel de chaves PIX será **completo** nesta fase (cadastro, edicao, ativacao/desativacao, definicao de padrao, prioridade e historico na mesma tela).
- **D-02:** Validacao avancada por tipo e obrigatoria no cadastro/edicao: CPF, CNPJ, e-mail, telefone e chave aleatoria (UUID).
- **D-03:** Historico operacional na tela deve mostrar no minimo: **quem alterou**, **quando**, **acao** e **antes/depois**.

### Compatibilidade de Fluxo
- **D-04:** Nao introduzir gateway nem webhook nesta fase; confirmacao continua manual pelo restaurante.
- **D-05:** Pedidos em andamento devem permanecer consistentes quando chaves forem ativadas/desativadas.

### Claude's Discretion
- Regra exata de selecao de chave no checkout (padrao vs prioridade/fallback) pode ser detalhada no planejamento, respeitando as decisoes D-01..D-05.
- Estrutura de UX (componentizacao da tela e ordem de blocos) fica a criterio do planner, desde que mantenha operacao clara para o restaurante.

### Deferred Ideas (OUT OF SCOPE)
- Conciliacao automatica por webhook/gateway (fora do escopo desta fase).
- Reembolso automatico e split de pagamento (fora do escopo do milestone atual).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PAY-15 | Restaurante cadastra multiplas chaves PIX ativas no painel | Novo modelo `ChavePix` por restaurante, CRUD no painel, constraints de tenant |
| PAY-16 | Restaurante define chave padrao e prioridade de uso no checkout | Constraint de "uma padrao ativa por restaurante" + ordenacao por prioridade |
| PAY-17 | Checkout seleciona e exibe a chave PIX correta conforme regra configurada | Service de selecao deterministica usada em `pagamento_pix_manual` |
| PAY-18 | Restaurante consegue ativar/desativar chaves sem quebrar pedidos em andamento | Snapshot da chave usada no momento da criacao do `Pagamento` + nao depender de chave global |
</phase_requirements>

## Summary

O estado atual usa `settings.PIX_KEY` global no checkout (`apps/pagamentos/views.py`), o que impede multi-chave por restaurante e nao atende PAY-15..PAY-18. A fase precisa migrar de configuracao global para modelo por tenant com selecao deterministica em runtime e historico auditavel no painel.

O caminho de menor risco e maior aderencia ao codigo existente e: (1) criar entidade de chave PIX por restaurante com ativacao/prioridade/padrao; (2) mover a selecao de chave para um service transacional; (3) salvar snapshot da chave escolhida no pagamento para manter consistencia de pedidos em andamento; (4) expor CRUD + historico na mesma tela do painel, sem alterar o fluxo manual de comprovante/aceite/rejeicao.

As validacoes por tipo podem ser implementadas com regras oficiais de formato do DICT/Pix (CPF/CNPJ/PHONE/EMAIL/EVP) e validacao adicional de digito para CPF/CNPJ. O planejamento deve incluir testes novos para PAY-15..PAY-18; hoje os testes cobrem apenas o fluxo manual de pagamento e nao cobrem gestao de chaves.

**Primary recommendation:** Implementar `ChavePix` + `ChavePixHistorico` por restaurante e um `selecionar_chave_pix_checkout(restaurante)` com fallback deterministico e snapshot no `Pagamento`.

## Project Constraints (from CLAUDE.md)

`CLAUDE.md` nao existe no workspace. Nenhuma diretiva adicional de projeto foi encontrada fora dos artefatos `.planning/*`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2.28 | ORM, views, forms, migrations | Ja e o framework base do monolito; reduz risco de regressao |
| PostgreSQL | 18.2 (client detectado) | Persistencia e constraints | Necessario para integridade (unique/partial constraints) |
| Bootstrap templates | Existing project | Tela unica de gestao no painel | Padrao atual do painel e consistente com UX existente |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django.core.validators + custom validators | Django 4.2.28 | Validacao por tipo de chave PIX | Cadastro/edicao de chave PIX |
| `transaction.atomic()` + `select_for_update()` | Django 4.2 docs | Evitar corrida ao trocar padrao/prioridade | Atualizacoes concorrentes de chaves no painel |
| Django TestCase | Django 4.2.28 | Testes de unit/integration da fase | Cobrir PAY-15..PAY-18 antes de merge |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Modelo dedicado de chaves PIX | Guardar lista JSON em `Restaurante` | JSON dificulta constraints, consulta e historico auditavel |
| Snapshot da chave em pagamento | Resolver chave "ao vivo" sempre | Quebra consistencia de pedidos em andamento ao desativar chave |
| Constraint em banco para padrao unico | Regra apenas em view/form | Maior chance de race condition e dados inconsistentes |

**Installation:**
```bash
pip install -r requirements.txt
```

**Version verification (workspace):**
```bash
venv\Scripts\python -c "import django; print(django.get_version())"   # 4.2.28
psql --version                                                         # PostgreSQL 18.2 client
```

## Architecture Patterns

### Recommended Project Structure
```
apps/pagamentos/
├── models.py          # ChavePix, ChavePixHistorico e ajustes em Pagamento
├── services.py        # seletor de chave + regras de ativacao/padrao/prioridade
├── views.py           # checkout consome service de selecao
├── tests/
│   ├── test_pix_keys_models.py
│   ├── test_pix_keys_services.py
│   └── test_pix_keys_views.py
templates/painel/
└── pix_keys.html      # tela unica com CRUD + historico
```

### Pattern 1: Tenant-Scoped PIX Key Entity
**What:** Model `ChavePix` com `restaurante`, `tipo`, `valor`, `valor_normalizado`, `ativo`, `padrao`, `prioridade`, timestamps e operador.  
**When to use:** Sempre que for persistir chave PIX por restaurante (PAY-15/PAY-16).  
**Example:**
```python
class ChavePix(models.Model):
    restaurante = models.ForeignKey("restaurantes.Restaurante", on_delete=models.CASCADE, related_name="chaves_pix")
    tipo = models.CharField(max_length=16, choices=TIPO_CHOICES)
    valor = models.CharField(max_length=120)
    valor_normalizado = models.CharField(max_length=120)
    ativo = models.BooleanField(default=True)
    padrao = models.BooleanField(default=False)
    prioridade = models.PositiveIntegerField(default=100)
```

### Pattern 2: Deterministic Selection Service
**What:** Service unico para escolher chave no checkout: primeiro `padrao` ativa; fallback por menor `prioridade` ativa; empate por `id` crescente.  
**When to use:** Em `pagamento_pix_manual` e qualquer endpoint que precise exibir chave (PAY-17).  
**Example:**
```python
def selecionar_chave_pix_checkout(restaurante):
    qs = restaurante.chaves_pix.filter(ativo=True)
    return qs.filter(padrao=True).order_by("prioridade", "id").first() or qs.order_by("prioridade", "id").first()
```

### Pattern 3: Snapshot for In-Flight Consistency
**What:** Persistir no `Pagamento` a chave selecionada no momento da criacao (`pix_key_id`, `pix_key_tipo`, `pix_key_valor_snapshot`).  
**When to use:** Na criacao/reuso de pagamento pendente (PAY-18).  
**Example:**
```python
pagamento.dados_resposta = {
    **(pagamento.dados_resposta or {}),
    "pix_key_id": chave.id,
    "pix_key_tipo": chave.tipo,
    "pix_key_valor": chave.valor,
}
```

### Pattern 4: Append-Only Operational History
**What:** Modelo `ChavePixHistorico` registrando `acao`, `ator`, `antes`, `depois`, `criado_em`.  
**When to use:** Toda mudanca de chave no painel (PAY-15/PAY-16 + D-03).  
**Example:**
```python
ChavePixHistorico.objects.create(
    chave=chave, ator=request.user, acao="ativacao", antes={"ativo": False}, depois={"ativo": True}
)
```

### Anti-Patterns to Avoid
- **Usar `settings.PIX_KEY` global no checkout:** quebra multi-tenant; substituir por consulta por restaurante.
- **Excluir fisicamente chaves para "desativar":** perde rastreabilidade; usar `ativo=False`.
- **Regra de padrao sem constraint de banco:** permite mais de uma chave padrao em concorrencia.
- **Nao persistir snapshot da chave no pagamento:** pedidos antigos podem passar a exibir outra chave.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Integridade de "uma chave padrao ativa" | Check manual apenas em view | `UniqueConstraint(condition=...)` + transacao | Evita race conditions |
| Concorrencia na troca de prioridade/padrao | Atualizacao sem lock | `transaction.atomic()` + `select_for_update()` | Evita gravações intercaladas |
| Regras de formato PIX | Regex inventada ad hoc | Padroes oficiais DICT/BCB para CPF/CNPJ/PHONE/EMAIL/EVP | Alinha com especificacao oficial |
| Auditoria de alteracao | Log textual solto | Tabela de historico com antes/depois estruturado | Facilita tela e rastreabilidade |

**Key insight:** A fase parece CRUD simples, mas sem constraints + snapshot + historico ela gera inconsistencias operacionais e regressao em pedidos em andamento.

## Common Pitfalls

### Pitfall 1: Fallback nao deterministico
**What goes wrong:** Checkout escolhe chaves diferentes em condicoes iguais.  
**Why it happens:** Ordenacao incompleta (sem critero de empate).  
**How to avoid:** Ordenar sempre por `prioridade`, `id`.  
**Warning signs:** Testes flakey em PAY-17.

### Pitfall 2: Duas chaves padrao ativas
**What goes wrong:** Regras de selecao ficam ambiguas.  
**Why it happens:** Atualizacao em paralelo sem lock/constraint.  
**How to avoid:** Constraint parcial + bloco atomico para troca de padrao.  
**Warning signs:** Duas linhas `padrao=True` para mesmo restaurante.

### Pitfall 3: Pedidos em andamento quebrando apos desativacao
**What goes wrong:** Pedido ja criado passa a exibir chave diferente ou inexistente.  
**Why it happens:** Checkout consulta chave sempre "ao vivo", sem snapshot no pagamento.  
**How to avoid:** Snapshot da chave no momento do pagamento pendente.  
**Warning signs:** Pedido antigo sem chave resolvida apos manutencao no painel.

### Pitfall 4: Validacao incompleta de CPF/CNPJ
**What goes wrong:** Chaves sintaticamente plausiveis mas invalidas entram no sistema.  
**Why it happens:** Apenas regex, sem digito verificador.  
**How to avoid:** Validacao por formato + digito verificador para CPF/CNPJ.  
**Warning signs:** Alta taxa de erro operacional em comprovacao.

## Code Examples

Verified patterns from official sources:

### Model Validation Entry Point
```python
from django.core.exceptions import ValidationError

obj.full_clean()  # roda clean_fields + clean + unique + constraints
```
Source: https://docs.djangoproject.com/en/4.2/ref/models/instances/

### Conditional Unique Constraint
```python
from django.db import models
from django.db.models import Q

models.UniqueConstraint(
    fields=["restaurante"],
    condition=Q(padrao=True, ativo=True),
    name="uq_chave_pix_padrao_ativa_por_restaurante",
)
```
Source: https://docs.djangoproject.com/en/4.2/ref/models/constraints/

### Transaction Block for Critical Updates
```python
from django.db import transaction

with transaction.atomic():
    # atualiza padrao/prioridade de forma consistente
    ...
```
Source: https://docs.djangoproject.com/en/4.2/topics/db/transactions/

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `settings.PIX_KEY` global | Chaves por tenant com selecao deterministica | Phase 2 (planejado) | Resolve multi-tenant real e PAY-15..18 |
| Sem trilha estruturada de alteracao de chave | Historico antes/depois por operador | Phase 2 (planejado) | Atende D-03 e auditoria operacional |
| Chave resolvida em tempo de render | Snapshot no pagamento pendente | Phase 2 (planejado) | Preserva consistencia de pedidos em andamento |

**Deprecated/outdated:**
- Uso de `PIX_KEY` global para checkout multi-restaurante.

## Open Questions

1. **Empate de prioridade: qual UX no painel?**
   - What we know: precisa haver prioridade e fallback.
   - What's unclear: prioridade deve ser unica por restaurante ou pode repetir com desempate tecnico.
   - Recommendation: permitir repeticao e aplicar desempate por `id`; opcionalmente alertar visualmente no painel.

2. **Historico deve incluir eventos de leitura/selecao no checkout?**
   - What we know: D-03 exige historico operacional de alteracoes.
   - What's unclear: registrar apenas mutacoes de chave ou tambem "chave selecionada no pedido".
   - Recommendation: manter historico de mutacoes na tela e snapshot no pagamento para rastreio por pedido.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Django app/tests | ✓ | 3.14.2 (global), 3.12.10 (venv) | — |
| Django (venv) | Models/views/migrations/tests | ✓ | 4.2.28 | — |
| PostgreSQL | Dev/test DB | ✓ | Port 5432 open; client 18.2 | SQLite somente para dev isolado (nao recomendado para paridade) |
| Docker daemon | Fluxo containerizado | ✗ | CLI 5.1.1, daemon indisponivel | Executar local via venv + Postgres local |
| ripgrep (`rg`) | Busca rapida no planejamento/implementacao | ✓ | Installed | `Select-String` |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- Docker daemon indisponivel no momento; fallback local funcional (venv + Postgres localhost).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Django `TestCase` (Django 4.2.28) |
| Config file | none (default `manage.py test`) |
| Quick run command | `venv\Scripts\python manage.py test apps.pagamentos.tests --keepdb --noinput --verbosity 1` |
| Full suite command | `venv\Scripts\python manage.py test --keepdb --noinput --verbosity 1` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PAY-15 | CRUD de multiplas chaves PIX por restaurante | integration + model | `venv\Scripts\python manage.py test apps.pagamentos.tests.test_pix_keys_views --keepdb --noinput` | ❌ Wave 0 |
| PAY-16 | Definir padrao e prioridade com integridade | unit + model | `venv\Scripts\python manage.py test apps.pagamentos.tests.test_pix_keys_services --keepdb --noinput` | ❌ Wave 0 |
| PAY-17 | Checkout exibe chave correta conforme regra | integration | `venv\Scripts\python manage.py test apps.pagamentos.tests.test_pix_key_selection --keepdb --noinput` | ❌ Wave 0 |
| PAY-18 | Ativar/desativar sem quebrar pedidos em andamento | integration + regression | `venv\Scripts\python manage.py test apps.pagamentos.tests.test_pix_key_consistency --keepdb --noinput` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `venv\Scripts\python manage.py test apps.pagamentos.tests --keepdb --noinput --verbosity 1`
- **Per wave merge:** `venv\Scripts\python manage.py test --keepdb --noinput --verbosity 1`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/pagamentos/tests/test_pix_keys_models.py` — constraints/validacoes de chave (PAY-15/16)
- [ ] `apps/pagamentos/tests/test_pix_keys_services.py` — regra de selecao/fallback/snapshot (PAY-16/17/18)
- [ ] `apps/pagamentos/tests/test_pix_keys_views.py` — fluxo painel CRUD + checkout exibicao (PAY-15/17)
- [ ] `apps/pagamentos/tests/factories.py` (ou helpers) — fixtures reutilizaveis de chave/pedido/restaurante

## Sources

### Primary (HIGH confidence)
- Internal codebase:
  - `apps/pagamentos/views.py` (uso atual de `settings.PIX_KEY`)
  - `apps/pagamentos/services.py` (fluxo manual e idempotencia)
  - `apps/restaurantes/views.py` (padroes de painel e autorizacao)
  - `apps/pedidos/views.py` (handoff checkout -> pagamento)
  - `.planning/phases/02-gest-o-de-chaves-pix/02-CONTEXT.md` (decisoes lockadas)
- Banco Central (PIX/DICT):
  - https://aprendervalor.bcb.gov.br/content/estabilidadefinanceira/pix/API-DICT.html
  - https://www.bcb.gov.br/content/estabilidadefinanceira/pix/Regulamento_Pix/versoes_futuras/X_ManualOperacionaldoDICT-versao8-1.pdf

### Secondary (MEDIUM confidence)
- Django documentation (version-matched to project major):
  - https://docs.djangoproject.com/en/4.2/ref/models/instances/
  - https://docs.djangoproject.com/en/4.2/ref/models/constraints/
  - https://docs.djangoproject.com/en/4.2/topics/db/transactions/
  - https://docs.djangoproject.com/en/4.2/ref/models/querysets/#select-for-update

### Tertiary (LOW confidence)
- Nenhuma fonte terciaria nao verificada foi usada para recomendacao principal.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - derivado do workspace real (`requirements.txt`, venv, comandos locais)
- Architecture: HIGH - alinhada ao codigo existente e a docs oficiais Django/BCB
- Pitfalls: HIGH - baseados em comportamento atual observado e riscos classicos de concorrencia/integridade

**Research date:** 2026-04-10  
**Valid until:** 2026-05-10
