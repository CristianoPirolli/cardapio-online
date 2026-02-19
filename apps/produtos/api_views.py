# =============================================================================
# apps/produtos/api_views.py - Views da API REST para produtos e categorias
#
# Endpoints:
# GET/POST   /api/produtos/categorias/           → CRUD categorias
# GET/POST   /api/produtos/                      → CRUD produtos
# GET        /api/produtos/?restaurante=1         → Filtrar por restaurante
# GET        /api/produtos/?categoria=2           → Filtrar por categoria
# GET        /api/produtos/?disponivel=true       → Apenas disponíveis
# GET        /api/produtos/?search=pizza          → Busca por nome/descrição
# =============================================================================

from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from .models import Categoria, Produto
from .serializers import CategoriaSerializer, ProdutoSerializer


class CategoriaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de categorias via API.

    Endpoints:
    - GET    /api/produtos/categorias/          → Listar categorias
    - POST   /api/produtos/categorias/          → Criar categoria
    - GET    /api/produtos/categorias/{id}/      → Detalhe
    - PUT    /api/produtos/categorias/{id}/      → Atualizar
    - DELETE /api/produtos/categorias/{id}/      → Remover

    Filtros: ?restaurante=1&ativo=true
    """

    queryset = Categoria.objects.annotate(
        quantidade_produtos=Count(
            'produtos',
            filter=Q(produtos__disponivel=True),
            distinct=True
        )
    )
    serializer_class = CategoriaSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['restaurante', 'ativo']
    search_fields = ['nome']
    ordering_fields = ['ordem', 'nome']

    def get_queryset(self):
        queryset = super().get_queryset()
        estabelecimento_id = self.request.query_params.get('estabelecimento')
        if estabelecimento_id and not self.request.query_params.get('restaurante'):
            queryset = queryset.filter(restaurante_id=estabelecimento_id)
        return queryset


class ProdutoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de produtos via API.

    Endpoints:
    - GET    /api/produtos/          → Listar produtos
    - POST   /api/produtos/          → Criar produto (com imagem via multipart)
    - GET    /api/produtos/{id}/     → Detalhe do produto
    - PUT    /api/produtos/{id}/     → Atualizar produto
    - DELETE /api/produtos/{id}/     → Remover produto

    Filtros disponíveis:
    - ?restaurante=1     → Produtos de um restaurante específico
    - ?categoria=2       → Produtos de uma categoria
    - ?disponivel=true   → Apenas disponíveis
    - ?destaque=true     → Apenas destaques
    - ?search=pizza      → Busca textual no nome e descrição

    Ordenação:
    - ?ordering=preco    → Ordenar por preço (crescente)
    - ?ordering=-preco   → Ordenar por preço (decrescente)
    """

    queryset = Produto.objects.select_related('categoria', 'restaurante').all()
    serializer_class = ProdutoSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['restaurante', 'categoria', 'disponivel', 'destaque']
    search_fields = ['nome', 'descricao']
    ordering_fields = ['preco', 'nome', 'criado_em']

    def get_queryset(self):
        queryset = super().get_queryset()
        estabelecimento_id = self.request.query_params.get('estabelecimento')
        if estabelecimento_id and not self.request.query_params.get('restaurante'):
            queryset = queryset.filter(restaurante_id=estabelecimento_id)
        return queryset
