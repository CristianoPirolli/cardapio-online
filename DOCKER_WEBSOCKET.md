# Docker Setup com WebSocket

## O que foi alterado

Atualizamos a configuração do Docker para usar **Daphne** (ASGI) em vez de Gunicorn (WSGI):

### Mudanças no Docker

1. **Dockerfile** - Comando alterado de Gunicorn para Daphne
2. **docker-compose.yml** - Adicionado Redis (channel layer)
3. **nginx/nginx.conf** - Adicionado suporte a WebSocket

## Como rodar

### 1. Build e start dos containers

```bash
docker-compose up --build -d
```

Isso inicia:
- PostgreSQL (banco de dados)
- Redis (cache para WebSocket)
- Daphne (aplicação Django com WebSocket)
- Nginx (proxy reverso)

### 2. Verificar se está rodando

```bash
docker-compose ps
```

Deve mostrar todos os 4 serviços como `Up`.

### 3. Verificar logs

```bash
# Logs do Django/Daphne
docker-compose logs -f web

# Logs do Nginx
docker-compose logs -f nginx

# Logs do Redis
docker-compose logs -f redis
```

### 4. Testar a aplicação

Abra: `http://localhost:8081` (porta padrão do Nginx)

Crie um pedido e acompanhe em tempo real via WebSocket!

## Verificação do WebSocket

### No navegador (DevTools)

1. Abra F12 → Console
2. Vá para página de acompanhamento do pedido
3. Você verá: `WebSocket conectado para pedido #123`
4. No terminal, mude o status do pedido (ver abaixo)
5. A página atualizará **instantaneamente**

### Mudar status via Django shell (dentro do container)

```bash
docker-compose exec web python manage.py shell
```

```python
from apps.pedidos.models import Pedido

pedido = Pedido.objects.first()
pedido.status = 'preparo'
pedido.save()
```

A página do cliente atualizará em tempo real!

## Parar os containers

```bash
docker-compose down
```

## Remover volumes (reset completo)

```bash
docker-compose down -v
```

Isso remove banco de dados, arquivos estáticos, etc.

## Troubleshooting

### "WebSocket connection refused"
- Verifique se os containers estão rodando: `docker-compose ps`
- Verifique logs: `docker-compose logs web`
- Certifique-se que Daphne está rodando (não Gunicorn)

### Redis não conecta
- Verifique: `docker-compose logs redis`
- Verifique se Redis está listando: `docker-compose ps redis`

### Nginx não roteia WebSocket
- Verifique se nginx.conf tem os headers corretos
- Rebuild: `docker-compose up --build`

### Porta já em uso
Se a porta 8081 já está em uso, mude no docker-compose.yml:
```yaml
ports:
  - "8082:80"  # Use 8082 em vez de 8081
```

Então acesse: `http://localhost:8082`

## Variáveis de ambiente

Configure no `.env`:
```
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,meusistema.com

POSTGRES_DB=cardapio_db
POSTGRES_USER=cardapio
POSTGRES_PASSWORD=senha_segura

REDIS_HOST=redis
REDIS_PORT=6379

NGINX_PORT=8081
```

## Arquivos modificados

- `Dockerfile` - Usa Daphne em vez de Gunicorn
- `docker-compose.yml` - Adicionado Redis, Daphne
- `nginx/nginx.conf` - Headers para WebSocket upgrade
- Todas as alterações do WebSocket (consumers, signals, etc.)

## Performance

Com Docker:
- **InMemoryChannelLayer** em dev (padrão)
- **RedisChannelLayer** em prod (configurado no settings.py)

Redis oferece melhor escalabilidade em produção com múltiplas instâncias.
