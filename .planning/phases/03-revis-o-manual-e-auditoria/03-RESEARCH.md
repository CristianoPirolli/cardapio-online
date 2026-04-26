# Phase 3: Revisao Manual e Auditoria - Research (Forced Refresh)

**Researched:** 2026-04-11  
**Mode:** `--research` (forced re-research)  
**Domain:** Django monolith, painel Bootstrap, fluxo PIX manual sem gateway/webhook  
**Confidence:** HIGH

## Executive Answer

Para planejar a Phase 3 bem, trate a fase como um contrato unico de **revisao manual** com 3 pilares conectados:

1. **Fila operacional filtravel por periodo** no painel de pedidos (OPS-01).  
2. **Decisao com justificativa obrigatoria** para aprovar/rejeitar comprovante (OPS-02).  
3. **Trilha auditavel por pedido** visivel no detalhe (OPS-03).  

Se o plano separar esses pilares sem um contrato de dados comum (acao, motivo, justificativa, timestamp, ator), a implementacao tende a ficar inconsistente.

## Locked Constraints and Decisions

### Must preserve
- Sem gateway/webhook.
- Fluxo manual PIX permanece (upload -> aguardando_confirmacao -> decisao manual).
- Tela de pedidos continua com visao padrao "Todos os pedidos" e secao destacada "Aguardando PIX".

### Context decisions already locked
- Fila por recencia (mais novos primeiro).
- Filtro operacional unico: periodo (hoje, ontem, 7 dias, 30 dias, personalizado).
- Justificativa obrigatoria para aprovar e rejeitar.
- Texto complementar minimo de 10 caracteres.
- Motivos iniciais: `valido`, `invalido`, `outro`.
- Historico mostrado apenas no detalhe do pedido.

## Current System Baseline (What Exists Now)

### Backend
- `apps/restaurantes/views.py::painel_pedidos`:
  - ja separa `pendentes_pix` por `status='aguardando_confirmacao'`
  - ja ordena por `-criado_em`
  - hoje filtra por `status` e `data` simples (nao cobre presets de periodo exigidos).
- `apps/pagamentos/views.py::aceitar_pix` e `rejeitar_pix`:
  - executam decisao manual
  - nao recebem/validam justificativa
  - nao gravam trilha de auditoria de decisao.
- `apps/pagamentos/services.py`:
  - `confirmar_pix_manual` e `rejeitar_pix_manual` alteram estado corretamente
  - sem metadados de justificativa/auditoria.
- `apps/pagamentos/models.py`:
  - `Pagamento` existe e suporta comprovante/status
  - nao ha modelo de auditoria de decisao manual por pedido.

### Frontend
- `templates/painel/pedidos.html`:
  - secao destacada de "Aguardando Confirmacao PIX" ja pronta
  - filtros atuais por status, sem contrato de periodo exigido pela fase.
- `templates/painel/pedido_detalhe.html`:
  - mostra comprovante
  - botoes de aceitar/rejeitar sem campos obrigatorios
  - sem feed de auditoria operacional.

## Requirement Mapping (Explicit)

### OPS-01 — fila de revisao manual com filtros

**Need to implement**
- Filtro de periodo com presets: `hoje`, `ontem`, `7d`, `30d`, `custom`.
- Custom com `data_inicio` e `data_fim`, validacao de intervalo.
- Aplicacao no queryset da fila pendente (`pendentes_pix`), mantendo ordenacao `-criado_em`.
- Manter secao destacada de pendentes dentro da tela de pedidos existente.

**Primary files**
- `apps/restaurantes/views.py`
- `templates/painel/pedidos.html`

### OPS-02 — aprovar/rejeitar com justificativa obrigatoria

**Need to implement**
- Form de revisao com:
  - `motivo` (dropdown: valido/invalido/outro)
  - `justificativa` (min 10 chars)
- Validacao server-side obrigatoria para aceitar e rejeitar.
- Feedback de erro no mesmo detalhe do pedido, sem executar acao.

**Primary files**
- `apps/pagamentos/views.py`
- `apps/pagamentos/forms.py` (novo form de revisao recomendado)
- `templates/painel/pedido_detalhe.html`

### OPS-03 — historico auditavel por pedido

**Need to implement**
- Persistencia append-only de eventos de decisao manual.
- Evento minimo: acao + timestamp (D-09).
- Recomendado incluir `ator`, `motivo`, `justificativa` para auditoria util.
- Exibicao apenas no detalhe do pedido (D-10), ordem mais recente primeiro.

**Primary files**
- `apps/pagamentos/models.py` + migration
- `apps/pagamentos/views.py` (registro da trilha)
- `templates/painel/pedido_detalhe.html`

## Recommended Data Contract

Criar modelo dedicado (ex.: `PagamentoRevisaoHistorico`):
- `pedido` (FK)
- `pagamento` (FK nullable)
- `acao` (`aprovado`/`rejeitado`)
- `motivo` (`valido`/`invalido`/`outro`)
- `justificativa` (TextField)
- `ator` (FK User, nullable)
- `criado_em` (DateTime auto)

Racional:
- evita sobrecarregar `Pagamento` com ultimo evento apenas
- permite rastreabilidade por pedido (OPS-03)
- facilita render no detalhe e testes de ordenacao.

## Interaction and UX Contracts to Respect

1. `pedidos.html` continua sendo a tela principal de operacao.
2. "Aguardando PIX" continua destacado e priorizado visualmente.
3. Acoes de revisar no detalhe exigem motivo + justificativa.
4. Rejeicao continua com confirmacao explicita (destrutiva).
5. Historico aparece no detalhe do pedido e nao em tela global.

## Architecture Options and Tradeoffs

### Option A (recommended)
Registrar auditoria em modelo dedicado e chamar services existentes.
- Pros: baixo risco de regressao, boa rastreabilidade.
- Cons: adiciona migration/modelo novo.

### Option B
Registrar dados em `Pagamento.dados_resposta` (JSON).
- Pros: sem novo modelo.
- Cons: consulta/ordenacao fraca, contrato frouxo, pior auditabilidade.

## Risks and Mitigations

1. **Executar aprovar/rejeitar sem validacao forte**
   - Mitigacao: form unico de revisao com validacao centralizada.

2. **Salvar historico fora de transacao**
   - Mitigacao: transacao atomica para decisao + registro de evento.

3. **Filtro custom ambiguo**
   - Mitigacao: normalizar timezone local e validar `inicio <= fim`.

4. **Regressao no fluxo manual atual**
   - Mitigacao: testes de regressao do upload e status transitions existentes.

## Validation Architecture

As validacoes abaixo devem ser usadas como gate mensuravel para planejamento e execucao.

### Dimension 1: Coverage by Requirement (OPS)
- **Check 1.1:** Cada requisito OPS-01/02/03 mapeado para tasks especificas no PLAN.
- **Check 1.2:** Cada task aponta arquivos-alvo e criterio de pronto verificavel.
- **Pass threshold:** 100% dos OPS mapeados sem lacunas.

### Dimension 2: Behavioral Tests
- **Check 2.1 (OPS-01):** testes de periodo (`hoje`, `ontem`, `7d`, `30d`, `custom`) + invalid custom range.
- **Check 2.2 (OPS-02):** aprovar/rejeitar falha sem justificativa valida; sucesso com dados validos.
- **Check 2.3 (OPS-03):** evento auditavel criado por decisao e exibido no detalhe em ordem desc.
- **Pass threshold:** todos os cenarios criticos verdes no suite focal.

### Dimension 3: Data Integrity
- **Check 3.1:** historico e append-only (sem update/delete via fluxo normal).
- **Check 3.2:** evento sempre vinculado ao `pedido` correto.
- **Check 3.3:** acao e timestamp sempre preenchidos.
- **Pass threshold:** 0 eventos orfaos e 0 eventos sem acao/timestamp em testes.

### Dimension 4: Access and Tenant Isolation
- **Check 4.1:** usuario de outro restaurante nao revisa pedido alheio.
- **Check 4.2:** detalhes/historico visiveis apenas para restaurante dono.
- **Pass threshold:** 100% bloqueios de acesso indevido (404/redirect esperado).

### Dimension 5: UX Contract Conformance
- **Check 5.1:** secao "Aguardando PIX" permanece na tela de pedidos.
- **Check 5.2:** formulario de decisao exige motivo + texto minimo 10.
- **Check 5.3:** historico exibido somente no detalhe do pedido.
- **Pass threshold:** conformidade total com `03-CONTEXT.md` e `03-UI-SPEC.md`.

### Dimension 6: Regression Safety
- **Check 6.1:** fluxo manual legado (upload comprovante + aguardo confirmacao) intacto.
- **Check 6.2:** confirmar/rejeitar continuam atualizando estado do pedido corretamente.
- **Pass threshold:** suite de pagamentos completa verde apos mudancas.

## Planning Blueprint (Suggested Task Sequencing)

1. **Task A:** modelo/migration de auditoria + testes de modelo.  
2. **Task B:** form de revisao (motivo/justificativa) + validacao em aceitar/rejeitar.  
3. **Task C:** filtro de periodo na fila operacional e UI correspondente.  
4. **Task D:** render do historico no detalhe + regressao completa.

## Conclusion

Phase 3 deve ser planejada como evolucao operacional do fluxo manual atual, nao como novo fluxo de pagamento.  
Com modelo auditavel dedicado, validacao obrigatoria de decisao e filtro de periodo na fila, OPS-01/02/03 ficam atendidos sem violar as restricoes de produto.

## RESEARCH COMPLETE
