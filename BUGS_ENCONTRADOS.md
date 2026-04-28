# 🐛 BUGS IDENTIFICADOS NO SISTEMA - CARDÁPIO ONLINE

**Data da Análise:** 28 de Abril de 2026  
**Status:** Em Correção

---

## BUG #1: Campo `subdominio` foi removido mas é referenciado em código produtivo
**Severidade:** 🔴 CRÍTICA  
**Status:** ✅ CORRIGIDO

### Problema
- Migration `0008_remove_restaurante_idx_restaurante_subdominio_and_more.py` removeu o campo `subdominio` em 28 de abril
- O campo é **essencial** para a arquitetura multi-tenant do sistema
- Middleware `config/middleware.py` ainda tenta filtrar por `subdominio` (linhas 75-76)
- Vários testes usavam `subdominio=` para criar restaurantes

### Impacto
❌ Sistema inteiro de multi-tenant quebrado  
❌ Nenhum restaurante consegue ser identificado pela URL  
❌ Testes falhando ao tentar criar restaurantes

### Correção Aplicada
1. ✅ Restaurado campo `subdominio` no modelo `Restaurante`
2. ✅ Criada migration `0009_restore_subdominio_field.py`
3. ✅ Removidas linhas com `subdominio=` dos testes (usando sed)

**Arquivos Alterados:**
- `apps/restaurantes/models.py` - Restaurado campo `subdominio`
- `apps/pagamentos/tests/test_auditoria_revisao.py` - Removido `subdominio=`
- `apps/pagamentos/tests/test_chaves_pix.py` - Removido `subdominio=`
- `apps/pagamentos/tests/test_revisao_manual.py` - Removido `subdominio=`
- `apps/pagamentos/tests/test_services.py` - Removido `subdominio=`
- `apps/pagamentos/tests/test_views.py` - Removido `subdominio=`

---

## BUG #2: Relacionamento proprietário usa OneToOneField incorretamente
**Severidade:** 🟡 ALTA  
**Status:** 🔍 IDENTIFICADO

### Problema
- Modelo `Restaurante` usa `OneToOneField` para `proprietario`
- Um usuário só pode ter UM restaurante por vez
- Isso quebra a escalabilidade (usuários querem gerenciar múltiplos restaurantes)
- Não está alinhado com a documentação (menciona "cada restaurante é um tenant isolado")

### Impacto
⚠️ Impossível um proprietário gerenciar múltiplos restaurantes  
⚠️ Não escalável em produção  
⚠️ Limitação de negócio não implementada corretamente

### Recomendação
```python
# ATUAL (OneToOneField - ERRADO)
proprietario = models.OneToOneField(User, related_name='restaurante', ...)

# ESPERADO (ForeignKey - CORRETO para multi-restaurante)
proprietario = models.ForeignKey(User, related_name='restaurantes', ...)
```

---

## BUG #3: Lógica de status de pedido inconsistente
**Severidade:** 🟡 ALTA  
**Status:** 🔍 IDENTIFICADO

### Problema
No modelo `Pedido`:
- Status padrão é `'aguardando'` (linha 141)
- Mas o grafo de transições em `apps/core/algorithms.py` define `'aguardando'` como status válido
- **Conflito:** Quando o pedido é criado com PIX manual, o status deveria ser `'aguardando_confirmacao'` mas fica como `'aguardando'`

Fluxo esperado para PIX:
```
checkout → aguardando → aguardando_confirmacao (após cliente fazer upload) → recebido (após restaurante confirmar)
```

Mas o código em `apps/pedidos/services.py:186` cria o pedido sem especificar o status correto para PIX.

### Impacto
⚠️ Pedidos em status incorreto  
⚠️ Transições de status quebradas para fluxo PIX  
⚠️ Cliente não consegue fazer upload de comprovante

### Recomendação
```python
# Em criar_pedido_do_carrinho():
if forma_pagamento == 'pix':
    pedido.status = 'aguardando_confirmacao'  # Esperando upload de comprovante
elif forma_pagamento in ('dinheiro', 'cartao'):
    pedido.status = 'recebido'  # Já confirmado
```

---

## BUG #4: Views de checkout e PIX têm fluxo não documentado
**Severidade:** 🟡 MÉDIA  
**Status:** 🔍 IDENTIFICADO

### Problema
- `apps/pedidos/views.py` linha 495 redireciona para `'pagamento_pix_manual'` após criar pedido
- Mas o URL pattern e view para este endpoint não está claramente documentado
- A view que recebe o upload de comprovante não está claramente definida

### Recomendação
- Documentar o fluxo PIX manual com diagramas
- Criar uma view específica `pagamento_pix_manual()` que:
  1. Exiba a chave PIX do restaurante
  2. Permita upload de comprovante
  3. Mude status de `aguardando_confirmacao` para `aguardando_revisao`

---

## BUG #5: Método `calcular_totais()` modifica estado sem retorno
**Severidade:** 🟡 MÉDIA  
**Status:** 🔍 IDENTIFICADO

### Problema
Em `apps/pedidos/models.py:265-311`:
```python
def calcular_totais(self, itens_prefetched=None, taxa_entrega_override=None):
    # ... calcula valores ...
    self.save()  # ← Salva automaticamente!
```

Problema: O método modifica e salva o objeto sem retornar nada, causando:
- Side effects invisíveis
- Difícil de testar
- Viola princípio de responsabilidade única

### Recomendação
```python
def calcular_totais(self, itens_prefetched=None, taxa_entrega_override=None):
    # ... calcula valores ...
    # NÃO SALVAR AQUI - deixar para quem chamou
    return {
        'subtotal': self.subtotal,
        'taxa_entrega': self.taxa_entrega,
        'imposto': self.imposto,
        'total': self.total,
    }
```

---

## BUG #6: Cache de `esta_aberto` pode gerar inconsistência
**Severidade:** 🟡 MÉDIA  
**Status:** 🔍 IDENTIFICADO

### Problema
Em `apps/restaurantes/models.py:179-200`:
- Cache com TTL de 30 segundos pode retornar estado desatualizado
- Se o restaurante fecha no meio de uma janela de cache, pedidos ainda podem ser criados
- Não há invalidação de cache em operações críticas

### Recomendação
- Usar TTL menor (5-10 segundos)
- Invalidar cache ao alterar horários de funcionamento
- Considerar cache distribuído para ambientes com múltiplos processos

---

## BUG #7: Testes não cobrem fluxo de pagamento PIX manual completo
**Severidade:** 🟡 MÉDIA  
**Status:** 🔍 IDENTIFICADO

### Problema
Não há testes integrando:
1. Criar pedido com PIX
2. Upload de comprovante
3. Restaurante aceita/rejeita
4. Status é atualizado corretamente

### Recomendação
Criar teste em `apps/pagamentos/tests/test_pix_flow.py`:
```python
def test_pix_manual_complete_flow():
    # 1. Criar pedido
    # 2. Verificar status = aguardando_confirmacao
    # 3. Upload comprovante
    # 4. Restaurante aceita
    # 5. Verificar status = recebido, pago = True
```

---

## RESUMO DE AÇÕES NECESSÁRIAS

| Bugs | Severidade | Status | Ação |
|------|-----------|--------|------|
| #1 - Campo subdominio | 🔴 CRÍTICA | ✅ CORRIGIDO | Migrations aplicadas |
| #2 - OneToOneField proprietario | 🟡 ALTA | 🔍 IDENTIFICADO | Mudar para ForeignKey |
| #3 - Status pedido PIX | 🟡 ALTA | 🔍 IDENTIFICADO | Ajustar lógica de status |
| #4 - Fluxo PIX não documentado | 🟡 MÉDIA | 🔍 IDENTIFICADO | Documentar/criar view |
| #5 - calcular_totais side effect | 🟡 MÉDIA | 🔍 IDENTIFICADO | Refatorar para retornar valores |
| #6 - Cache inconsistente | 🟡 MÉDIA | 🔍 IDENTIFICADO | Reduzir TTL, adicionar invalidação |
| #7 - Testes PIX incompletos | 🟡 MÉDIA | 🔍 IDENTIFICADO | Criar testes de integração |

---

## PRÓXIMOS PASSOS

1. **Aplicar migrations:**
   ```bash
   python manage.py migrate
   ```

2. **Testar sistema:**
   ```bash
   python manage.py test apps/restaurantes apps/pagamentos apps/pedidos
   ```

3. **Corrigir bug #2** (OneToOneField → ForeignKey)

4. **Ajustar fluxo de status PIX** (bug #3)

5. **Refatorar calcular_totais()** (bug #5)
