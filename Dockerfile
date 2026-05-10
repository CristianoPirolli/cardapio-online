# =============================================================================
# Dockerfile - Imagem Docker para o projeto Cardápio Online SaaS
# Usa multi-stage build para otimizar o tamanho da imagem final.
# Base: Python 3.11 slim (Debian Bookworm)
# =============================================================================

FROM python:3.11-slim-bookworm AS base

# Previne criação de arquivos .pyc e bufferização do stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Instala dependências do sistema necessárias para psycopg2 e Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Define diretório de trabalho dentro do container
WORKDIR /app

# Copia e instala dependências Python primeiro (aproveita cache de camadas)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o restante do código do projeto
COPY . .

# Coleta arquivos estáticos (sem input interativo)
RUN python manage.py collectstatic --noinput 2>/dev/null || true

# Expõe a porta do Daphne
EXPOSE 8000

# Comando padrão: Daphne servindo o ASGI do Django (com suporte a WebSocket)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
