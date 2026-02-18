# Cardápio Online SaaS

Sistema profissional SaaS de cardápio digital e pedidos online para restaurantes.
Desenvolvido com Django, PostgreSQL, Docker, Bootstrap 5 e integração Stripe.

---

## Funcionalidades

- **Multi-tenant**: Cada restaurante opera com subdomínio próprio (ex: `pizzaria1.meusistema.com`)
- **Cardápio digital responsivo**: Interface mobile-first com Bootstrap 5
- **Carrinho e pedidos**: Carrinho com sessão, checkout com cálculo automático (subtotal + taxa + imposto)
- **Pagamentos**: Integração com Stripe e mock para desenvolvimento
- **Painel administrativo**: Dashboard com métricas, gestão de produtos/categorias/pedidos
- **API REST**: Endpoints completos com autenticação JWT (DRF + SimpleJWT)
- **Entregas**: Cadastro de entregadores, atribuição e rastreio de entregas
- **Upload de imagens**: Fotos de produtos com preview responsivo

---

## Tecnologias

| Componente | Tecnologia |
|---|---|
| Backend | Django 4.2 |
| Banco de dados | PostgreSQL 15 |
| API REST | Django REST Framework |
| Autenticação API | JWT (SimpleJWT) |
| Frontend | Django Templates + Bootstrap 5 |
| Pagamentos | Stripe (com mock fallback) |
| Servidor | Gunicorn |
| Proxy reverso | Nginx |
| Containerização | Docker + docker-compose |
| Processamento de imagens | Pillow |

---

## Estrutura do Projeto

```
cardapio-online/
├── docker-compose.yml          # Orquestração dos serviços
├── Dockerfile                  # Imagem Docker da aplicação
├── .env                        # Variáveis de ambiente (NÃO commitar)
├── .env.example                # Exemplo de variáveis
├── requirements.txt            # Dependências Python
├── manage.py                   # CLI do Django
├── README.md                   # Este arquivo
│
├── config/                     # Configuração do projeto Django
│   ├── settings.py             # Settings principal
│   ├── urls.py                 # Roteamento de URLs
│   ├── wsgi.py                 # WSGI (Gunicorn)
│   ├── asgi.py                 # ASGI (futuro)
│   ├── middleware.py           # Middleware multi-tenant
│   └── context_processors.py   # Context processors
│
├── apps/                       # Apps Django
│   ├── restaurantes/           # Gestão de restaurantes (tenants)
│   ├── produtos/               # CRUD produtos e categorias
│   ├── pedidos/                # Pedidos e carrinho
│   ├── pagamentos/             # Stripe e mock de pagamento
│   └── entregas/               # Entregadores e rastreio
│
├── templates/                  # Templates HTML
│   ├── base.html               # Template base
│   ├── home.html               # Landing page
│   ├── auth/                   # Login e registro
│   ├── produtos/               # Cardápio público
│   ├── pedidos/                # Carrinho e checkout
│   ├── pagamentos/             # Pagamento e confirmação
│   ├── painel/                 # Painel administrativo
│   └── entregas/               # Gestão de entregas
│
├── static/                     # Arquivos estáticos
│   ├── css/style.css
│   └── js/carrinho.js
│
├── media/                      # Uploads (imagens de produtos)
│
└── nginx/
    └── nginx.conf              # Configuração do Nginx
```

---

## Instalação Local (sem Docker)

### Pré-requisitos
- Python 3.11+
- PostgreSQL 15+
- pip

### Passos

```bash
# 1. Clonar o repositório
git clone <url-do-repo> cardapio-online
cd cardapio-online

# 2. Criar e ativar virtualenv
python -m venv venv
source venv/bin/activate        # Linux/Mac
# ou: venv\Scripts\activate     # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Edite o .env com suas configurações (banco, chaves, etc.)
# Para desenvolvimento local, altere POSTGRES_HOST para 'localhost'

# 5. Criar o banco de dados no PostgreSQL
# psql -U postgres
# CREATE DATABASE cardapio_db;
# CREATE USER cardapio_user WITH PASSWORD 'cardapio_pass_dev';
# GRANT ALL PRIVILEGES ON DATABASE cardapio_db TO cardapio_user;

# 6. Rodar migrations
python manage.py migrate

# 7. Popular com dados de teste (seed)
python manage.py seed

# 8. Coletar arquivos estáticos
python manage.py collectstatic --noinput

# 9. Rodar o servidor de desenvolvimento
python manage.py runserver
```

Acesse: http://localhost:8000

---

## Ambiente com Docker

### Pré-requisitos
- Docker e docker-compose instalados

### Passos

```bash
# 1. Configurar variáveis de ambiente
cp .env.example .env
# Edite o .env conforme necessário

# 2. Subir os containers
docker-compose up --build -d

# 3. Rodar migrations (primeira vez)
docker-compose exec web python manage.py migrate

# 4. Popular com dados de teste
docker-compose exec web python manage.py seed

# 5. Coletar estáticos
docker-compose exec web python manage.py collectstatic --noinput
```

Acesse: http://localhost

### Comandos úteis Docker

```bash
# Ver logs
docker-compose logs -f web

# Abrir shell no container
docker-compose exec web bash

# Parar containers
docker-compose down

# Parar e remover volumes (CUIDADO: apaga dados do banco)
docker-compose down -v

# Rebuild após mudanças
docker-compose up --build -d
```

---

## Deploy na VPS (Hostinger)

### 1. Preparar o servidor

```bash
# Conectar via SSH
ssh root@seu-ip-da-vps

# Atualizar pacotes
apt update && apt upgrade -y

# Instalar Docker e docker-compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
apt install docker-compose -y
```

### 2. Enviar o projeto

```bash
# No seu computador local:
scp -r cardapio-online/ root@seu-ip:/opt/cardapio-online/

# Ou usando git no servidor:
cd /opt
git clone <url-do-repo> cardapio-online
```

### 3. Configurar variáveis de produção

```bash
cd /opt/cardapio-online
cp .env.example .env
nano .env
```

Configure no `.env`:
```
DEBUG=False
SECRET_KEY=<gere-uma-chave-forte>
ALLOWED_HOSTS=meusistema.com,.meusistema.com,seu-ip
BASE_DOMAIN=meusistema.com
POSTGRES_PASSWORD=<senha-forte>
STRIPE_PUBLIC_KEY=pk_live_xxx
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
USE_STRIPE_MOCK=False
```

Para gerar uma SECRET_KEY forte:
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4. Subir os serviços

```bash
docker-compose up --build -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic --noinput
docker-compose exec web python manage.py createsuperuser
```

---

## Configuração de Domínio

### No painel da Hostinger (ou seu registrador DNS)

Crie os seguintes registros DNS apontando para o IP da sua VPS:

| Tipo | Nome | Valor |
|---|---|---|
| A | @ | `seu-ip-da-vps` |
| A | * | `seu-ip-da-vps` |
| CNAME | www | `meusistema.com` |

O registro `*` (wildcard) é essencial para que subdomínios como `pizzaria1.meusistema.com` funcionem.

### No nginx.conf

Edite `nginx/nginx.conf` e substitua `meusistema.com` pelo seu domínio real.

---

## Habilitar HTTPS com Certbot (Let's Encrypt)

### 1. Instalar Certbot

```bash
apt install certbot python3-certbot-nginx -y
```

### 2. Obter certificado wildcard

```bash
# Certificado wildcard para suportar subdomínios
certbot certonly --manual --preferred-challenges=dns \
  -d meusistema.com -d "*.meusistema.com"
```

Siga as instruções para adicionar o registro TXT no DNS.

### 3. Ou certificado simples (sem wildcard)

```bash
# Primeiro, pare o Nginx temporariamente
docker-compose stop nginx

# Obter certificado
certbot certonly --standalone -d meusistema.com -d www.meusistema.com

# Reiniciar Nginx
docker-compose start nginx
```

### 4. Configurar Nginx para HTTPS

No arquivo `nginx/nginx.conf`, descomente o bloco HTTPS (server 443) e atualize os caminhos dos certificados.

### 5. Renovação automática

```bash
# Testar renovação
certbot renew --dry-run

# Adicionar ao crontab para renovação automática
echo "0 3 * * * certbot renew --quiet && docker-compose -f /opt/cardapio-online/docker-compose.yml restart nginx" | crontab -
```

---

## Variáveis do .env

| Variável | Descrição | Exemplo |
|---|---|---|
| `SECRET_KEY` | Chave secreta do Django | `django-insecure-xxx` |
| `DEBUG` | Modo debug (True/False) | `False` |
| `ALLOWED_HOSTS` | Hosts permitidos (vírgula) | `meusistema.com,.meusistema.com` |
| `POSTGRES_DB` | Nome do banco | `cardapio_db` |
| `POSTGRES_USER` | Usuário do banco | `cardapio_user` |
| `POSTGRES_PASSWORD` | Senha do banco | `senha_segura` |
| `POSTGRES_HOST` | Host do banco | `db` (Docker) ou `localhost` |
| `POSTGRES_PORT` | Porta do banco | `5432` |
| `STRIPE_PUBLIC_KEY` | Chave pública Stripe | `pk_test_xxx` |
| `STRIPE_SECRET_KEY` | Chave secreta Stripe | `sk_test_xxx` |
| `STRIPE_WEBHOOK_SECRET` | Secret do webhook Stripe | `whsec_xxx` |
| `USE_STRIPE_MOCK` | Usar mock em vez do Stripe | `True` |
| `BASE_DOMAIN` | Domínio base do sistema | `meusistema.com` |

---

## Criar Superusuário

```bash
# Com Docker
docker-compose exec web python manage.py createsuperuser

# Sem Docker
python manage.py createsuperuser
```

Acesse o admin em: `/admin/`

---

## Migrations e Seed

### Criar e aplicar migrations

```bash
# Gerar migrations após alterar models
python manage.py makemigrations

# Aplicar migrations no banco
python manage.py migrate
```

### Popular dados de teste (seed)

```bash
python manage.py seed
```

O seed cria:
- **Superusuário**: `admin` / `admin123`
- **Pizzaria do João**: user `pizzaria` / `pizza123` (subdomínio: `pizzaria1`)
- **Burger da Maria**: user `hamburgueria` / `burger123` (subdomínio: `hamburgueria2`)
- Categorias e produtos de exemplo
- Entregadores de teste

---

## Endpoints da API REST

### Autenticação JWT

```
POST /api/auth/token/           → Obter tokens (access + refresh)
POST /api/auth/token/refresh/   → Renovar token de acesso
```

### Restaurantes

```
GET    /api/restaurantes/           → Listar restaurantes
POST   /api/restaurantes/           → Criar restaurante
GET    /api/restaurantes/{id}/      → Detalhe
PUT    /api/restaurantes/{id}/      → Atualizar
DELETE /api/restaurantes/{id}/      → Remover
GET    /api/restaurantes/{id}/metricas/ → Métricas do restaurante
```

### Produtos

```
GET    /api/produtos/               → Listar produtos (?restaurante=1&categoria=2)
POST   /api/produtos/               → Criar produto
GET    /api/produtos/{id}/          → Detalhe
PUT    /api/produtos/{id}/          → Atualizar
DELETE /api/produtos/{id}/          → Remover
GET    /api/produtos/categorias/    → Listar categorias
POST   /api/produtos/categorias/    → Criar categoria
```

### Pedidos

```
GET    /api/pedidos/                → Listar pedidos (?restaurante=1&status=recebido)
POST   /api/pedidos/                → Criar pedido com itens
GET    /api/pedidos/{id}/           → Detalhe do pedido
PATCH  /api/pedidos/{id}/status/    → Atualizar status
```

### Pagamentos

```
GET    /api/pagamentos/             → Listar pagamentos
POST   /api/pagamentos/criar/      → Criar pagamento para pedido
POST   /api/pagamentos/webhook/    → Webhook do Stripe
```

### Entregas

```
GET    /api/entregas/                           → Listar entregas
POST   /api/entregas/                           → Criar entrega
PATCH  /api/entregas/{id}/atualizar_status/     → Atualizar status
GET    /api/entregas/entregadores/              → Listar entregadores
POST   /api/entregas/entregadores/              → Criar entregador
```

---

## Multi-Tenant por Subdomínio

O sistema identifica o restaurante automaticamente pelo subdomínio:

- `pizzaria1.meusistema.com` → Restaurante com `subdominio='pizzaria1'`
- `hamburgueria2.meusistema.com` → Restaurante com `subdominio='hamburgueria2'`
- `meusistema.com` → Landing page (sem restaurante específico)

**Em desenvolvimento local**, como subdomínios não funcionam em `localhost`, use o parâmetro GET:
```
http://localhost:8000/cardapio/?restaurante=pizzaria1
```

---

## Stripe vs Mock

O sistema suporta dois modos de pagamento:

### Mock (desenvolvimento)
- Defina `USE_STRIPE_MOCK=True` no `.env`
- Pagamentos são simulados localmente
- Botão "Simular Pagamento" no checkout

### Stripe (produção)
- Defina `USE_STRIPE_MOCK=False` no `.env`
- Configure `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY` e `STRIPE_WEBHOOK_SECRET`
- Formulário Stripe Elements no checkout
- Configure o webhook no dashboard Stripe apontando para:
  `https://meusistema.com/api/pagamentos/webhook/`

---

## Licença

Projeto privado. Todos os direitos reservados.
