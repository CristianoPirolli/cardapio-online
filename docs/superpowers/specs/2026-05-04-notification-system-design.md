# Sistema de Notificações — Design Spec
**Data:** 2026-05-04  
**Status:** Aprovado  
**Escopo:** Notificações para restaurante (novos pedidos) e cliente (mudança de status)

---

## 1. Visão Geral

Implementar um sistema de notificações em duas camadas para o cardápio-online:

- **Restaurante:** recebe alerta quando um novo pedido chega — em tempo real via WebSocket (painel aberto) e via Web Push nativo do OS (navegador fechado)
- **Cliente:** recebe Web Push quando o status do pedido muda + WhatsApp quando o pedido fica `entrega` ou `pronto_retirada`

A infraestrutura de Django Channels (Daphne + channel layer) já está em produção e será estendida. O provedor de WhatsApp é desacoplado via padrão Adapter/Strategy.

---

## 2. Arquitetura

```
EVENTOS DISPARADORES
  novo pedido criado          status do pedido muda
        │                             │
        ▼                             ▼
  Django Signal post_save     Django Signal post_save
        │                             │
        └──────────┬──────────────────┘
                   ▼
          NotificationService
   (orquestra quem notifica quem e quando)
          │              │                  │
          ▼              ▼                  ▼
  PainelConsumer   WebPushService    WhatsAppAdapter
  (Channels WS)   (pywebpush/VAPID)  (interface pluggável)
  painel aberto   restaurante+cliente  só entrega/pronto
```

### Componentes novos

| Componente | Localização | Responsabilidade |
|---|---|---|
| `PainelConsumer` | `apps/pedidos/consumers.py` | WebSocket do painel do restaurante |
| `NotificationService` | `apps/pedidos/notifications.py` | Orquestra todos os canais de notificação |
| `WebPushService` | `apps/pedidos/notifications.py` | Envia Web Push via `pywebpush` |
| `WhatsAppAdapter` | `apps/pedidos/whatsapp.py` | Interface pluggável de WhatsApp |
| `LogWhatsAppAdapter` | `apps/pedidos/whatsapp.py` | Adapter de desenvolvimento (só loga) |
| `PushSubscription` | `apps/pedidos/models.py` | Armazena subscriptions Web Push por dispositivo |
| Signal `pedido_salvo` | `apps/pedidos/signals.py` | Gatilho para o `NotificationService` |

### O que NÃO muda

- `PedidoStatusConsumer` existente (cliente na página `acompanhar.html`) — sem alterações
- Toda a lógica de negócio de pedidos — sem alterações
- Channel layer e Daphne — já funcionam

---

## 3. Modelo de Dados

### PushSubscription

```
PushSubscription
├── id             BigAutoField (PK)
├── restaurante    FK → Restaurante  (null=True, blank=True)
├── pedido         FK → Pedido       (null=True, blank=True)
├── endpoint       TextField          — URL única do serviço push do browser
├── p256dh         CharField(max=255) — chave pública de criptografia
├── auth           CharField(max=255) — chave de autenticação
├── user_agent     CharField(max=255, blank=True)
└── criado_em      DateTimeField(auto_now_add=True)
```

**Regra de integridade:** ou `restaurante` está preenchido (subscription do painel) ou `pedido` está preenchido (subscription do cliente). Nunca os dois ao mesmo tempo. Validado em `clean()`.

**Unicidade:** `unique_together = [('restaurante', 'endpoint'), ('pedido', 'endpoint')]` — evita duplicatas por dispositivo.

### Alteração em Pedido

Adicionar ao `__init__` do model `Pedido` para detectar mudança de status sem query extra:

```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._status_anterior = self.status
```

---

## 4. Fluxos de Notificação

### 4.1 Novo pedido → Restaurante

```
1. Cliente faz checkout → Pedido criado (post_save, created=True)
2. Signal → NotificationService.novo_pedido(pedido)
3. NotificationService:
   a. channel_layer.group_send('painel_{restaurante_id}', evento)
      → PainelConsumer entrega ao browser (se painel aberto)
      → JS toca som + exibe toast + incrementa badge no título da aba
   b. Busca PushSubscription.objects.filter(restaurante=pedido.restaurante)
      → WebPushService.send(subscription, payload) para cada subscription
      → Browser OS exibe notificação nativa mesmo com aba fechada
```

**Payload Web Push (restaurante):**
```json
{
  "title": "Novo pedido #42",
  "body": "João Silva — R$ 58,00 — Delivery",
  "url": "/painel/pedidos/42/"
}
```

### 4.2 Mudança de status → Cliente

```
1. Restaurante muda status → Pedido salvo (post_save, created=False)
2. Signal detecta _status_anterior != status atual
3. Signal → NotificationService.status_mudou(pedido, status_anterior)
4. NotificationService:
   a. Busca PushSubscription.objects.filter(pedido=pedido)
      → WebPushService.send(subscription, payload com novo status)
   b. Se novo status in ('entrega', 'pronto_retirada'):
      → WhatsAppAdapter.send(pedido.cliente_telefone, mensagem)
```

**Payload Web Push (cliente):**
```json
{
  "title": "Seu pedido #42 foi atualizado",
  "body": "Saiu para entrega!",
  "url": "/pedidos/42/acompanhar/"
}
```

**Mensagens WhatsApp:**

| Status | Mensagem |
|---|---|
| `entrega` | `Olá {nome}! Seu pedido #{id} saiu para entrega. Acompanhe em: {url}` |
| `pronto_retirada` | `Olá {nome}! Seu pedido #{id} está pronto para retirada. Acompanhe em: {url}` |

---

## 5. WhatsApp Adapter

### Interface e provedores

```python
# apps/pedidos/whatsapp.py

class WhatsAppAdapter:
    def send(self, telefone: str, mensagem: str) -> bool:
        raise NotImplementedError

class LogWhatsAppAdapter(WhatsAppAdapter):
    """Desenvolvimento: loga sem enviar."""
    def send(self, telefone, mensagem):
        logger.info(f"[WhatsApp FAKE] {telefone}: {mensagem}")
        return True
```

Novos provedores (Z-API, Twilio, Meta) implementam `WhatsAppAdapter.send()` sem tocar no `NotificationService`.

### Configuração

```python
# settings.py
WHATSAPP_ADAPTER = os.getenv(
    'WHATSAPP_ADAPTER',
    'apps.pedidos.whatsapp.LogWhatsAppAdapter'
)
```

O `NotificationService` instancia o adapter via `import_string(settings.WHATSAPP_ADAPTER)()`.

---

## 6. Web Push / VAPID

### Configuração

```python
# settings.py
VAPID_PUBLIC_KEY  = os.getenv('VAPID_PUBLIC_KEY')
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY')
VAPID_ADMIN_EMAIL = os.getenv('VAPID_ADMIN_EMAIL', 'admin@meusistema.com')
```

Geradas uma única vez com `pywebpush --gen-keys`. As chaves são por domínio e não mudam.

### Endpoint de registro

```
POST /api/push/subscribe/
Body:
{
  "endpoint": "https://fcm.googleapis.com/...",
  "keys": { "p256dh": "...", "auth": "..." },
  "tipo": "painel",       // ou "pedido"
  "restaurante_id": 5,    // obrigatório se tipo == "painel"
  "pedido_id": 42         // obrigatório se tipo == "pedido"
}
Response: 201 Created
```

Cria ou atualiza `PushSubscription` (upsert por endpoint).

---

## 7. PainelConsumer (WebSocket)

Grupo: `painel_{restaurante_id}`

```
ws://host/ws/painel/{restaurante_id}/
```

Eventos recebidos pelo consumer e repassados ao browser:

| Tipo | Disparado por | Dados |
|---|---|---|
| `novo_pedido` | `NotificationService.novo_pedido()` | id, cliente_nome, total, tipo_entrega, url |

O JS do painel ao receber `novo_pedido`:
1. Toca `new_order.mp3`
2. Exibe toast Bootstrap com dados do pedido
3. Incrementa badge no `<title>` da aba: `(N) Pedidos — Restaurante`

---

## 8. Frontend

### Arquivos

| Arquivo | Incluído em | Propósito |
|---|---|---|
| `static/js/sw.js` | registrado globalmente | Service worker: recebe push, exibe notificação OS, deep link ao clicar |
| `static/js/painel_notifications.js` | `base_painel.html` | Registra SW, pede permissão, salva subscription, conecta WS do painel |
| `static/js/pedido_notifications.js` | `acompanhar.html` (pedidos não-terminais) | Registra SW, pede permissão, salva subscription do cliente |

### UX de permissão

Nunca disparar o prompt nativo imediatamente ao carregar. Fluxo:

```
1. Exibir banner contextual próprio: "Ativar notificações de pedidos?"
2. Usuário clica "Ativar"
3. Browser exibe prompt nativo
4. Se aceito → POST /api/push/subscribe/
5. Se negado → continua sem push (WebSocket ainda funciona no painel)
```

---

## 9. Arquivos Afetados

### Criar

- `apps/pedidos/notifications.py`
- `apps/pedidos/whatsapp.py`
- `apps/pedidos/signals.py`
- `apps/pedidos/migrations/XXXX_add_pushsubscription.py`
- `static/js/sw.js`
- `static/js/painel_notifications.js`
- `static/js/pedido_notifications.js`
- `static/sounds/new_order.mp3`

### Modificar

- `apps/pedidos/models.py` — `PushSubscription` model + `__init__` no `Pedido`
- `apps/pedidos/consumers.py` — adiciona `PainelConsumer`
- `apps/pedidos/apps.py` — `ready()` importa signals
- `apps/pedidos/api_urls.py` — endpoint `/api/push/subscribe/`
- `config/routing.py` — rota WS `ws/painel/<id>/`
- `config/settings.py` — VAPID keys + `WHATSAPP_ADAPTER`
- `templates/painel/base_painel.html` — inclui `painel_notifications.js`
- `templates/pedidos/acompanhar.html` — inclui `pedido_notifications.js`

---

## 10. Dependências

```
pywebpush   # Web Push com criptografia VAPID
```

Provedores WhatsApp trazem suas próprias dependências quando implementados.

---

## 11. Fora do Escopo

- Implementação de provedor WhatsApp real (Z-API, Twilio, Meta)
- Painel de gerenciamento de subscriptions
- Notificações por e-mail
- Relatórios de entrega de push (bounce, falha)
- PWA completo (manifest, offline cache)
- Suporte a múltiplos proprietários por restaurante
