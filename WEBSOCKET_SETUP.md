# WebSocket Setup - Notificação de Status em Tempo Real

## O que foi implementado

Substituímos o polling de 30 segundos por **WebSocket em tempo real** usando Django Channels.

### Antes (Polling)
- Cliente fazia requisições a cada 30 segundos
- Atraso máximo de 30 segundos para notificar cliente
- Mais requisições HTTP (ineficiente em mobile)

### Depois (WebSocket)
- Conexão persistent entre cliente e servidor
- Notificação instantânea quando status muda
- Uma única conexão WebSocket em vez de N requisições HTTP
- Fallback automático para polling de 60 segundos se WebSocket falhar

## Como Rodar em Desenvolvimento

### 1. Instalar dependências
```bash
pip install channels daphne
```

✅ Já feito!

### 2. Rodar com Daphne (servidor ASGI)
Em vez de usar `python manage.py runserver`, use:

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

Ou com debugging ativo:
```bash
daphne -b 0.0.0.0 -p 8000 -v 2 config.asgi:application
```

### 3. Testar o WebSocket

Abra o navegador em: `http://localhost:8000`

Crie um pedido e vá para a página de acompanhamento (`/pedidos/<id>/acompanhar/`)

Abra o DevTools (F12) → Console

Você verá mensagens como:
```
WebSocket conectado para pedido #123
```

### 4. Simular mudança de status

Abra outro terminal e use a Django shell:

```bash
python manage.py shell
```

```python
from apps.pedidos.models import Pedido

# Encontre um pedido
pedido = Pedido.objects.first()

# Mude o status
pedido.status = 'preparo'
pedido.save()  # Isto dispara o signal que emite WebSocket
```

A página do cliente atualizará **instantaneamente** sem fazer refresh manual!

## Em Produção

Para produção, use **Redis** como channel layer:

```bash
pip install channels-redis
```

Configure no `.env`:
```
REDIS_HOST=localhost
REDIS_PORT=6379
```

O Django automaticamente usará Redis em produção (quando `DEBUG=False`).

Deploy com Daphne:
```bash
daphne -b 0.0.0.0 -p 8000 --asgi-timeout 600 config.asgi:application
```

Ou use com Gunicorn + Daphne:
```bash
gunicorn config.asgi:application \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000
```

## Arquivos Modificados

- `config/settings.py` - Adicionado Daphne, Channels e configuração de channel layer
- `config/asgi.py` - Configurado roteamento de WebSocket
- `config/routing.py` - Novo arquivo com rotas WebSocket
- `apps/pedidos/consumers.py` - Novo consumer WebSocket
- `apps/pedidos/signals.py` - Novo arquivo com signals
- `apps/pedidos/apps.py` - Registrado signals
- `templates/pedidos/acompanhar.html` - Substituído polling por WebSocket

## Troubleshooting

### WebSocket não conecta
- Verifique se está usando Daphne (não runserver)
- Verifique o console do navegador (F12)
- Verifique firewall/proxy (alguns bloqueiam WebSocket)

### Notificação não chega
- Verifique se o signal está registrado: `apps/pedidos/apps.py`
- Verifique se o consumer está no `config/routing.py`
- Procure erros no terminal do Daphne

### Em produção: "channel layer unavailable"
- Instale `channels-redis`
- Configure Redis
- Reinicie a aplicação
