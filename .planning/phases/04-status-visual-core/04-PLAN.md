---
phase: 04-status-visual-core
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/pedidos/models.py
  - apps/pedidos/views.py
  - templates/pedidos/acompanhar.html
autonomous: true
requirements: [TRACK-01, TRACK-02, TRACK-03, TRACK-04]

must_haves:
  truths:
    - "Cliente que acabou de subir comprovante vê 'Comprovante recebido — aguardando verificação' com visual distinto (badge azul com ícone de hourglass)"
    - "A barra de progresso mostra exatamente 5 passos — Aguardando PIX, Pedido Confirmado, Em Preparo, Saiu p/ Entrega, Entregue"
    - "Polling cessa automaticamente quando pedido atinge estado terminal (entregue ou cancelado)"
    - "O título da aba reflete o customer_status atual (ex: 'Pedido Confirmado — Cardapio Online')"
    - "Status 'aguardando_confirmacao' permanece no passo 1 mas com badge diferenciado"
    - "Estados internos mapeiam corretamente para 5 passos visuais do cliente sem pular nem repetir"

  artifacts:
    - path: "apps/pedidos/models.py"
      provides: "Property customer_status, customer_status_display e customer_status_terminal"
      min_lines: 10
      patterns: ["CUSTOMER_STATUS_MAP", "@property", "customer_status_terminal"]
    
    - path: "apps/pedidos/views.py"
      provides: "Endpoint acompanhar_pedido_status retornando status, customer_status, e terminal flag"
      min_lines: 10
      exports: ["acompanhar_pedido_status retorna JSON com terminal=true/false"]
    
    - path: "templates/pedidos/acompanhar.html"
      provides: "Barra de 5 passos, badge condicional para aguardando_confirmacao, JS com condição terminal"
      patterns: ["5 passos na barra", "customer_step >= 4", "data.terminal"]

  key_links:
    - from: "Pedido.customer_status property"
      to: "CUSTOMER_STATUS_MAP dict"
      via: "dict lookup pelo status interno"
      pattern: "self.CUSTOMER_STATUS_MAP.get(self.status)"
    
    - from: "acompanhar.html template"
      to: "acompanhar_pedido_status endpoint"
      via: "fetch() a cada 30s, condição terminal para parar"
      pattern: "fetch.*acompanhar_pedido_status.*data.terminal"
    
    - from: "customer_step variable"
      to: "5 passos visuais"
      via: "índice mapeado (0-4) para renderização condicional"
      pattern: "customer_step >= N"

---

<objective>
Implementar o mapeamento dos 7 estados internos do pedido para 5 passos visuais do cliente, com barra de progresso refatorada, badge "comprovante em análise" e polling que para em estados terminais.

**Purpose:** Cliente obtém visibilidade clara e consistente do seu pedido, com feedback visual apropriado em cada etapa, e polling eficiente que não drena bateria após conclusão.

**Output:** 
- Property `customer_status` no model Pedido
- Endpoint `acompanhar_pedido_status` retornando `terminal` flag
- Template `acompanhar.html` com 5 passos + badge + JS inteligente
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@.planning/phases/04-status-visual-core/04-CONTEXT.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/04-status-visual-core/04-CONTEXT.md

## Code Structure Overview

**Model (apps/pedidos/models.py):**
- Status choices: 7 estados internos (`aguardando`, `aguardando_confirmacao`, `recebido`, `preparo`, `entrega`, `concluido`, `cancelado`)
- Properties já existentes: `proximo_passo`, `passos_para_concluir` (padrão a seguir)
- Dict-based lookup estabelecido: `VALID_TRANSITIONS` como O(1)

**Views (apps/pedidos/views.py):**
- `acompanhar_pedido()` — renderiza template, passa `customer_step` e `customer_progress`
- `acompanhar_pedido_status()` — endpoint JSON para polling, atualmente usa `.only('id', 'status')`
- Dict existente: `CUSTOMER_STATUS_STEP_INDEX` — mapeia customer_status para índice 0-4

**Template (templates/pedidos/acompanhar.html):**
- Barra com 4 círculos + linha de progresso (Bootstrap)
- 4 passos atualmente: Aguardando PIX, Pedido Confirmado, Em Preparo, Entregue (FALTAM "Saiu p/ Entrega")
- Badge status no topo (condicional por status)
- Badge "comprovante em análise" já existe (linhas 170-175)
- Polling JS: `checkStatus()` a cada 30s, condiciona reload se status muda
- Título: `{{ pedido.customer_status_display }} - Cardapio Online`

## Decisions to Implement (from 04-CONTEXT.md)

**D-01:** 5 passos na barra (não 4)
**D-02:** Mapeamento 7 internos → 5 customer_status (ver tabela em 04-CONTEXT.md)
**D-03:** Property no model (não vista/template-only)
**D-04:** Badge "comprovante em análise" entre barra e cards
**D-05:** Endpoint retorna `customer_status` + `terminal`
**D-06:** Terminal = `entregue` ou `cancelado`
**D-07:** Título reflete customer_status_display
**D-08:** Labels exatos dos 5 passos

</context>

<tasks>

<task type="auto">
  <name>Task 1: Add customer_status properties to Pedido model</name>
  <files>apps/pedidos/models.py</files>
  <action>
    Adicione ao model `Pedido` (após a propriedade `passos_para_concluir` em torno da linha 218):
    
    1. **Verificar que CUSTOMER_STATUS_MAP existe** (já presente nas linhas 63-71) — contém o mapeamento 7 internos → 5 customer_status exatamente como em D-02.
    
    2. **Adicionar property `customer_status`** (se não existir):
       - Retorna `self.CUSTOMER_STATUS_MAP.get(self.status, 'aguardando_pix')`
       - Referencia D-03: property no model, reutilizável
    
    3. **Adicionar property `customer_status_display`** (se não existir):
       - Busca no dict `CUSTOMER_STATUS_CHOICES` (já presente linhas 72-79)
       - Retorna label humano do customer_status
       - Exemplo: `'aguardando_pix'` → `'Aguardando PIX'`
    
    4. **Adicionar property `customer_status_terminal`** (se não existir):
       - Retorna `self.customer_status in {'entregue', 'cancelado'}`
       - Referencia D-06: termina o polling quando verdadeiro
    
    **Verificação:** O arquivo já contém `customer_status` nas linhas 221-234. Confirmar que:
    - `customer_status` (linha 221-223) retorna o valor correto do mapa
    - `customer_status_display` (linha 226-229) busca no dict CUSTOMER_STATUS_CHOICES
    - `customer_status_terminal` (linha 232-234) retorna True apenas para 'entregue' e 'cancelado'
    
    **Se já existem (caso provável):** Nenhuma modificação necessária. Proceda para Task 2.
  </action>
  <verify>
    <automated>grep -n "def customer_status" apps/pedidos/models.py && grep -n "customer_status_terminal" apps/pedidos/models.py</automated>
  </verify>
  <done>Properties customer_status, customer_status_display e customer_status_terminal existem no model e retornam valores corretos per D-02, D-03, D-06</done>
</task>

<task type="auto">
  <name>Task 2: Update acompanhar_pedido_status endpoint to include terminal flag</name>
  <files>apps/pedidos/views.py</files>
  <action>
    Localize a função `acompanhar_pedido_status()` (linhas 552-572).
    
    **Atualmente retorna:**
    ```json
    {
      "status": "...",
      "status_display": "...",
      "customer_status": "...",
      "customer_status_display": "...",
      "terminal": "...",
      "proximo_passo": "...",
      "passos_para_concluir": "..."
    }
    ```
    
    **Verificação:** Confirme que o JsonResponse já contém:
    - `'terminal': pedido.customer_status_terminal` (per D-05, D-06)
    - `'customer_status': pedido.customer_status`
    - `'customer_status_display': pedido.customer_status_display`
    
    **Se já presente:** Nenhuma modificação. Proceda para Task 3.
    
    **Se ausente:** Adicione os campos ao JsonResponse. O endpoint `.only('id', 'status')` continua válido pois `customer_status` é property (não campo DB).
  </action>
  <verify>
    <automated>grep -A 10 "def acompanhar_pedido_status" apps/pedidos/views.py | grep "terminal"</automated>
  </verify>
  <done>Endpoint retorna JSON com campos obrigatórios: status, customer_status, terminal (per D-05)</done>
</task>

<task type="auto">
  <name>Task 3: Update acompanhar_pedido view to pass correct customer_step for 5 steps</name>
  <files>apps/pedidos/views.py</files>
  <action>
    Localize a função `acompanhar_pedido()` (linhas 522-549).
    
    **Contexto atual:**
    ```python
    customer_step = CUSTOMER_STATUS_STEP_INDEX.get(pedido.customer_status, 0)
    customer_progress = int((customer_step / 4) * 100)
    ```
    
    **Problema:** Usa `/4` (4 passos), mas D-01 define 5 passos. Altere para `/4` (0-4 map para 5 passos: 0%, 25%, 50%, 75%, 100%).
    
    **Verificação do CUSTOMER_STATUS_STEP_INDEX (linhas 28-34):**
    - `'aguardando_pix': 0`
    - `'confirmado': 1`
    - `'em_preparo': 2`
    - `'saiu_entrega': 3`
    - `'entregue': 4`
    
    Confirme que todos os 5 customer_status estão presentes no dict (não 4).
    
    **Cálculo:** `customer_progress = int((customer_step / 4) * 100)` já está correto para 5 passos (0/4=0%, 1/4=25%, ..., 4/4=100%).
    
    **Se CUSTOMER_STATUS_STEP_INDEX estiver incompleto:** Adicione qualquer customer_status faltante. Esperado: 5 entradas (0-4).
  </action>
  <verify>
    <automated>grep -A 2 "CUSTOMER_STATUS_STEP_INDEX" apps/pedidos/views.py && grep -A 2 "customer_progress" apps/pedidos/views.py</automated>
  </verify>
  <done>customer_step range está 0-4 (5 passos) e customer_progress calcula corretamente (0%, 25%, 50%, 75%, 100%)</done>
</task>

<task type="auto">
  <name>Task 4: Refactor acompanhar.html to display 5 steps with correct progression</name>
  <files>templates/pedidos/acompanhar.html</files>
  <action>
    Refatore a barra de progresso (linhas 57-177) para **5 passos** em vez de 4.
    
    **Contexto atual:**
    - Lines 72-168: 5 divs de passo (Aguardando PIX, Confirmado, Em Preparo, Saiu Entrega, Entregue)
    - Lines 63-68: progress-bar com `{{ customer_progress }}`
    - Lines 88, 108, 128, 148, 164: labels dos passos
    
    **Verificação:** O template **já possui 5 passos visíveis**. Confirme:
    - Step 0 (linha 74): "Aguardando PIX" — check icon se customer_step > 0, qr-code se ==0
    - Step 1 (linha 94): "Pedido Confirmado" — check icon se customer_step > 1, inbox se ==1
    - Step 2 (linha 114): "Em Preparo" — check icon se customer_step > 2, fire se ==2
    - Step 3 (linha 134): "Saiu p/ Entrega" — check icon se customer_step > 3, truck se ==3
    - Step 4 (linha 154): "Entregue" — check icon sempre
    
    **Ajustes esperados:**
    - Largura de cada passo: `width: 20%` (5 passos = 100% ÷ 5)
    - Já presente nas linhas 74, 94, 114, 134, 154
    
    **Badge "comprovante em análise":**
    - Já presente (linhas 170-175)
    - Condiciona em `{% if pedido.status == 'aguardando_confirmacao' %}`
    - Mostra alerta azul com mensagem exata de D-04
    
    **Se já estruturado corretamente:** Confirme que cada passo tem seu `style="width: 20%"` (não 25%). Se sim, proceda para Task 5.
  </action>
  <verify>
    <automated>grep -c "width: 20%" templates/pedidos/acompanhar.html</automated>
  </verify>
  <done>Barra exibe 5 passos com width 20% cada, labels exatos de D-08, badge condicional aguardando_confirmacao presente</done>
</task>

<task type="auto">
  <name>Task 5: Update JS polling logic to respect terminal flag and stop on estado terminal</name>
  <files>templates/pedidos/acompanhar.html</files>
  <action>
    Localize o bloco `{% block extra_js %}` (linhas 374-425).
    
    **Lógica atual (linhas 383-405):**
    ```javascript
    if (data.status !== currentStatus) {
        window.location.reload();
    }
    if (data.customer_status !== currentCustomerStatus) {
        window.location.reload();
    }
    if (data.terminal && timer) {
        clearInterval(timer);
    }
    ```
    
    **Verificação:**
    - Linha 397: `if (data.terminal && timer)` — **já existe a condição terminal**
    - Se `data.terminal == true`, para o polling
    - Timer só é zerado se `data.terminal` é verdadeiro (per D-06)
    
    **Se lógica já está correta:** Nenhuma modificação. A condição terminal já implementada.
    
    **Se falta ou está errada:** Corrija para:
    ```javascript
    if (data.terminal) {
        if (timer) {
            clearInterval(timer);
            timer = null;
        }
    }
    ```
    
    **Visibilidade change (linhas 409-421):** Já implementado. Pausa quando aba oculta, retoma ao focar.
    
    **Observação:** Não force reload só por terminal. Se `data.terminal` é true, apenas pare o polling (linha 397-400). O template já mostra o status terminal via `{% if not pedido.customer_status_terminal %}` (linha 363).
  </action>
  <verify>
    <automated>grep -A 5 "if (data.terminal" templates/pedidos/acompanhar.html</automated>
  </verify>
  <done>JS polling cessa quando data.terminal == true (estados 'entregue' ou 'cancelado'), timer cleared corretamente</done>
</task>

<task type="auto">
  <name>Task 6: Verify page title reflects customer_status_display</name>
  <files>templates/pedidos/acompanhar.html</files>
  <action>
    Localize o bloco `{% block title %}` (linha 9).
    
    **Atual:**
    ```django
    {% block title %}{{ pedido.customer_status_display }} - Cardapio Online{% endblock %}
    ```
    
    **Verificação:**
    - Já usa `customer_status_display` (não `status` interno)
    - Per D-07: título reflete customer_status, ex: "Pedido Confirmado — Cardapio Online"
    - Esperado: "Aguardando PIX", "Pedido Confirmado", "Em Preparo", "Saiu p/ Entrega", "Entregue" conforme avança
    
    **Se já correto:** Nenhuma alteração. Proceda para Task 7 (testes).
  </action>
  <verify>
    <automated>grep "block title" templates/pedidos/acompanhar.html</automated>
  </verify>
  <done>Título da aba reflete customer_status_display, exemplo: "Pedido Confirmado — Cardapio Online" per D-07</done>
</task>

<task type="auto">
  <name>Task 7: End-to-end validation of state mapping and polling</name>
  <files>apps/pedidos/models.py, apps/pedidos/views.py, templates/pedidos/acompanhar.html</files>
  <action>
    **Validação de mapeamento (D-02):**
    Confirme que cada estado interno mapeia exatamente para o customer_status esperado:
    
    | Estado Interno | Expected customer_status | Passo Visual | Mapa OK? |
    |---|---|---|---|
    | aguardando | aguardando_pix | 0 | ✓ |
    | aguardando_confirmacao | aguardando_pix | 0 (+ badge) | ✓ |
    | recebido | confirmado | 1 | ✓ |
    | preparo | em_preparo | 2 | ✓ |
    | entrega | saiu_entrega | 3 | ✓ |
    | concluido | entregue | 4 | ✓ |
    | cancelado | cancelado | (fora barra) | ✓ |
    
    **Verificação de propriedades:**
    - `pedido.customer_status` — busca CUSTOMER_STATUS_MAP por status
    - `pedido.customer_status_display` — busca CUSTOMER_STATUS_CHOICES por customer_status
    - `pedido.customer_status_terminal` — True se em {'entregue', 'cancelado'}
    
    **Verificação de template:**
    - 5 passos com width 20%, customer_step range 0-4
    - Badge "Comprovante em Análise" só quando status == 'aguardando_confirmacao'
    - Título usa customer_status_display
    
    **Verificação de endpoint:**
    - `/acompanhar/<id>/status/` retorna `terminal` (boolean)
    - `terminal == true` para customer_status em {'entregue', 'cancelado'}
    
    **Verificação de polling:**
    - JS observa `data.terminal` (linha 397)
    - Se true, clearInterval(timer)
    - Se false, mantém polling a cada 30s
    - Visibilidade change pausar/retomar OK
    
    **Verificação visual:**
    - Quando aguardando_confirmacao: Step 0 ativo, badge azul abaixo da barra
    - Quando recebido: Step 1 ativo
    - Quando preparo: Step 2 ativo
    - Quando entrega: Step 3 ativo
    - Quando concluido: Step 4 ativo, badge de conclusão, polling para
    - Quando cancelado: fora da barra, alert danger, sem barra de progresso
  </action>
  <verify>
    <automated>python manage.py shell -c "from apps.pedidos.models import Pedido; print('Model properties:'); p = Pedido.objects.first(); print(f'customer_status={p.customer_status}'); print(f'customer_status_display={p.customer_status_display}'); print(f'customer_status_terminal={p.customer_status_terminal}')" 2>/dev/null || echo "SKIP: No pedidos in DB, use manual browser testing"</automated>
  </verify>
  <done>Mapeamento 7 internos → 5 visuais completo e correto, properties funcionam, endpoint retorna terminal flag, JS respeita terminal, template mostra 5 passos</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description | Risk |
|----------|-------------|------|
| Client → Server (acompanhar_pedido_status) | Untrusted request for order status | Enumeration: cliente lista pedidos de outros via ID sequencial |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-01 | Information Disclosure | acompanhar_pedido_status endpoint | accept | Phase 4 escopo: display status apenas. Enumeração por ID endereçada em Phase 5 (TRACK-10 com UUID). Atualmente sem autenticação — míngua sem dados sensíveis expostos (apenas status publicamente visível). |
| T-04-02 | Tampering | polling reload logic | accept | Reload desencadeado por mudança de status (servidor valida). Sem inputs do cliente que afetam lógica. |
</threat_model>

<verification>
**Testes manuais obrigatórios:**

1. **Teste de estado aguardando_confirmacao:**
   - Criar pedido novo → status = 'aguardando'
   - Atualizar para 'aguardando_confirmacao' via admin/API
   - Visitar `/acompanhar/<id>/`
   - Verificar: Step 0 ativo, badge "Comprovante em Análise" abaixo da barra, polling ativo (30s)

2. **Teste de transição estados:**
   - Começar em 'aguardando_confirmacao', atualizar para 'recebido'
   - Visitar página → reload automático (JS detecta mudança)
   - Confirmar: Step 1 ativo, badge sumiu, título agora "Pedido Confirmado"

3. **Teste de polling terminal:**
   - Criar pedido em 'preparo'
   - Iniciar acompanhamento, verificar polling a cada 30s via DevTools (Network)
   - Atualizar para 'concluido' via admin
   - Aguardar próxima verificação → JS limpa timer, polling para
   - Verificar: Console sem erros, aba mostra "Entregue", sem requisições posteriores

4. **Teste de cancelamento:**
   - Criar pedido em 'aguardando_confirmacao', atualizar para 'cancelado'
   - Visitar `/acompanhar/<id>/`
   - Verificar: Barra de progresso oculta, alert danger visível, polling para

5. **Teste de visibilidade change:**
   - Abrir acompanhamento em aba
   - Mudar para outra aba → verificar que fetch não ocorre
   - Retornar à aba → fetch ocorre imediatamente, polling retoma

</verification>

<success_criteria>
✓ Todas as 7 transições de status mapeiam corretamente para 5 customer_status (D-02)
✓ Propriedades customer_status, customer_status_display, customer_status_terminal existem e funcionam (D-03)
✓ Barra de progresso exibe 5 passos com width 20% cada (D-01, D-08)
✓ Badge "Comprovante em Análise" aparece quando status == 'aguardando_confirmacao' (D-04)
✓ Endpoint retorna terminal=true para 'entregue' e 'cancelado' (D-05, D-06)
✓ Título da aba reflete customer_status_display (D-07)
✓ Polling JS para quando terminal=true (D-06)
✓ Visibilidade change pausar/retomar polling
✓ Sem erros no console browser durante polling
✓ Teste E2E: aguardando → aguardando_confirmacao → recebido → preparo → entrega → concluido (+ verificação de progresso visual em cada passo)
</success_criteria>

<output>
Após conclusão, criar:
`.planning/phases/04-status-visual-core/04-01-SUMMARY.md`

com seções:
- **What Was Built:** Mapeamento 7→5, propriedades, endpoint com terminal, template 5 passos
- **Files Modified:** models.py, views.py, acompanhar.html
- **Key Decisions Implemented:** D-01 a D-08
- **Test Coverage:** Validação E2E de states, polling, badge
- **Known Limitations:** Enumeração por ID (defer TRACK-10)
- **Next Phase Dependency:** Phase 5 (Link Surfacing) pode ler customer_status_display diretamente
</output>
