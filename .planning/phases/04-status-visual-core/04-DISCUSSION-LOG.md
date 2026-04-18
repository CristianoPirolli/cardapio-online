# Phase 4: Status Visual Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 04-status-visual-core
**Areas discussed:** Mapeamento customer_status, Visual 'comprovante em análise', Labels e política de parada do polling, Onde vive o mapeamento no código

---

## Mapeamento customer_status

| Option | Description | Selected |
|--------|-------------|----------|
| preparo=Pronto, entrega=Entregue | 4 passos, entrega já é o estado final visível | |
| preparo=Pronto, entrega=Pronto | 4 passos, Entregue só acende em concluido | |
| Adicionar 5° passo visível | 5 passos: Aguardando PIX / Confirmado / Em Preparo / Saiu p/ Entrega / Entregue | ✓ |

**User's choice:** 5 passos visíveis
**Notes:** Preserva a granularidade de `entrega` como feedback visual para o cliente ("saiu para entrega"). Muda o requisito original de 4 para 5 estados visuais.

---

## Visual "Comprovante em Análise"

| Option | Description | Selected |
|--------|-------------|----------|
| Badge/texto abaixo da barra | Alerta azul/laranja abaixo da barra: "Comprovante recebido — aguardando verificação" | ✓ |
| Passo 1 com ícone diferente + cor | Círculo do passo 1 muda cor/ícone (relógio laranja) | |
| Card substituto no topo da página | Card destacado acima da barra, barra permanece igual | |

**User's choice:** Badge/texto abaixo da barra
**Notes:** A barra de progresso permanece no passo 1, o badge contextualiza o sub-estado sem alterar a progressão visual.

---

## Labels dos passos

| Option | Description | Selected |
|--------|-------------|----------|
| Aguardando PIX / Confirmado / Em Preparo / Saiu p/ Entrega / Entregue | Labels iguais ao get_status_display | |
| Aguardando PIX / Pedido Confirmado / Em Preparo / Saiu p/ Entrega / Entregue | Mais descritivo no passo 2 | ✓ |

**User's choice:** Com "Pedido Confirmado" no passo 2
**Notes:** Deixa explícito que o restaurante aceitou o pedido.

## Polling — endpoint

| Option | Description | Selected |
|--------|-------------|----------|
| Retornar os dois (status + customer_status + terminal) | Endpoint inclui ambos e flag terminal | ✓ |
| Retornar só customer_status | Mais simples, perde status interno no JS | |
| Retornar só status interno (atual) | Mantém como está, template faz mapeamento | |

**User's choice:** Retornar os dois + flag `terminal`

## Polling — estados terminais

| Option | Description | Selected |
|--------|-------------|----------|
| entregue + cancelado | Polling para em ambos os estados finais | ✓ |
| entregue apenas | Cancelado continua fazendo polling | |

**User's choice:** `entregue` e `cancelado` são terminais

---

## Onde vive o mapeamento

| Option | Description | Selected |
|--------|-------------|----------|
| Property no model Pedido | pedido.customer_status — reutilizável em todos os lugares | ✓ |
| Função utilitária em services.py | get_customer_status(pedido) | |
| Lógica no template apenas | Template faz if/elif, não reutilizável | |

**User's choice:** Property no model `Pedido`
**Notes:** Consistente com propriedades existentes `proximo_passo` e `passos_para_concluir`.

---

## Claude's Discretion

- Ícone exato e tom de cor do badge "comprovante em análise"
- Implementação interna da property customer_status (dict lookup recomendado)

## Deferred Ideas

None.
