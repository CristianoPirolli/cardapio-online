# =============================================================================
# apps/restaurantes/api_views.py - Views da API REST para restaurantes
#
# Endpoints:
# GET    /api/restaurantes/            → Lista todos os restaurantes ativos
# POST   /api/restaurantes/            → Cria novo restaurante (autenticado)
# GET    /api/restaurantes/{id}/       → Detalhe de um restaurante
# PUT    /api/restaurantes/{id}/       → Atualiza restaurante (proprietário)
# DELETE /api/restaurantes/{id}/       → Remove restaurante (proprietário)
# =============================================================================

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Restaurante
from .serializers import RestauranteSerializer


class IsProprietarioOrReadOnly(permissions.BasePermission):
    """
    Permissão customizada: apenas o proprietário pode editar.
    Leitura é permitida para qualquer usuário.
    """

    def has_object_permission(self, request, view, obj):
        # Leitura permitida para todos
        if request.method in permissions.SAFE_METHODS:
            return True
        # Escrita apenas para o proprietário
        return obj.proprietario == request.user


class RestauranteViewSet(viewsets.ModelViewSet):
    """
    ViewSet completo para CRUD de restaurantes via API REST.

    Endpoints gerados automaticamente:
    - GET    /api/restaurantes/          → list
    - POST   /api/restaurantes/          → create
    - GET    /api/restaurantes/{id}/     → retrieve
    - PUT    /api/restaurantes/{id}/     → update
    - PATCH  /api/restaurantes/{id}/     → partial_update
    - DELETE /api/restaurantes/{id}/     → destroy

    Exemplo de request (POST /api/restaurantes/):
    {
        "nome": "Pizzaria do João",
        "endereco": "Rua das Flores, 123",
        "cidade": "São Paulo",
        "estado": "SP",
        "cep": "01234-567",
        "telefone": "(11) 99999-9999",
        "email": "contato@pizzariadojoao.com",
        "taxa_entrega": "8.00"
    }

    Exemplo de response (201 Created):
    {
        "id": 1,
        "nome": "Pizzaria do João",
        "subdominio": "pizzaria-do-joao",
        ...
    }
    """

    queryset = Restaurante.objects.filter(ativo=True)
    serializer_class = RestauranteSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsProprietarioOrReadOnly]
    filterset_fields = ['cidade', 'estado', 'ativo']
    search_fields = ['nome', 'descricao', 'cidade']
    ordering_fields = ['nome', 'criado_em']

    def perform_create(self, serializer):
        """Ao criar, define o proprietário como o usuário autenticado."""
        serializer.save(proprietario=self.request.user)

    @action(detail=True, methods=['get'])
    def metricas(self, request, pk=None):
        """
        GET /api/restaurantes/{id}/metricas/

        Retorna métricas básicas do restaurante (total de pedidos, faturamento).

        Exemplo de response:
        {
            "total_pedidos": 150,
            "pedidos_hoje": 12,
            "faturamento_total": "15420.50",
            "faturamento_hoje": "1230.00",
            "ticket_medio": "102.80"
        }
        """
        restaurante = self.get_object()
        from apps.pedidos.models import Pedido
        from django.db.models import Sum, Count
        from django.utils import timezone

        hoje = timezone.localdate()
        # Regra de negócio: métricas operacionais consideram apenas pedidos pagos.
        pedidos = Pedido.objects.filter(restaurante=restaurante, pago=True)
        pedidos_hoje = pedidos.filter(criado_em__date=hoje)

        total_pedidos = pedidos.count()
        faturamento_total = pedidos.filter(
            status='concluido'
        ).aggregate(total=Sum('total'))['total'] or 0

        pedidos_hoje_count = pedidos_hoje.count()
        faturamento_hoje = pedidos_hoje.filter(
            status='concluido'
        ).aggregate(total=Sum('total'))['total'] or 0

        ticket_medio = faturamento_total / total_pedidos if total_pedidos > 0 else 0

        return Response({
            'total_pedidos': total_pedidos,
            'pedidos_hoje': pedidos_hoje_count,
            'faturamento_total': f'{faturamento_total:.2f}',
            'faturamento_hoje': f'{faturamento_hoje:.2f}',
            'ticket_medio': f'{ticket_medio:.2f}',
        })
