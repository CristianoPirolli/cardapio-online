# =============================================================================
# apps/entregas/api_views.py - Views da API REST para entregas e entregadores
#
# Endpoints:
# GET/POST  /api/entregas/entregadores/                → CRUD entregadores
# GET/POST  /api/entregas/                             → CRUD entregas
# PATCH     /api/entregas/{id}/atualizar_status/       → Atualizar status da entrega
# GET       /api/entregas/entregadores/{id}/entregas/  → Entregas de um entregador
# =============================================================================

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import Entregador, Entrega
from .serializers import EntregadorSerializer, EntregaSerializer


class EntregadorViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de entregadores.

    Endpoints:
    - GET    /api/entregas/entregadores/         → Listar
    - POST   /api/entregas/entregadores/         → Criar
    - GET    /api/entregas/entregadores/{id}/     → Detalhe
    - PUT    /api/entregas/entregadores/{id}/     → Atualizar
    - DELETE /api/entregas/entregadores/{id}/     → Remover

    Filtros: ?restaurante=1&disponivel=true&veiculo=moto
    """

    queryset = Entregador.objects.all()
    serializer_class = EntregadorSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['restaurante', 'disponivel', 'ativo', 'veiculo']
    search_fields = ['nome', 'telefone']

    @action(detail=True, methods=['get'])
    def entregas(self, request, pk=None):
        """
        GET /api/entregas/entregadores/{id}/entregas/

        Lista todas as entregas atribuídas a um entregador.

        Exemplo de response:
        [
            {
                "id": 1,
                "pedido": 5,
                "status": "entregue",
                ...
            }
        ]
        """
        entregador = self.get_object()
        entregas = Entrega.objects.filter(entregador=entregador)
        serializer = EntregaSerializer(entregas, many=True)
        return Response(serializer.data)


class EntregaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de entregas.

    Endpoints:
    - GET    /api/entregas/                  → Listar entregas
    - POST   /api/entregas/                  → Criar entrega
    - GET    /api/entregas/{id}/             → Detalhe
    - PATCH  /api/entregas/{id}/             → Atualizar
    - PATCH  /api/entregas/{id}/atualizar_status/ → Atualizar status

    Filtros: ?status=em_transito&entregador=1
    """

    queryset = Entrega.objects.select_related('pedido', 'entregador').all()
    serializer_class = EntregaSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['status', 'entregador', 'pedido']
    ordering_fields = ['criado_em', 'saiu_em']

    @action(detail=True, methods=['patch'])
    def atualizar_status(self, request, pk=None):
        """
        PATCH /api/entregas/{id}/atualizar_status/

        Atualiza o status de uma entrega.
        Preenche timestamps automaticamente (saiu_em, entregue_em).

        Exemplo de request:
        {"status": "em_transito"}

        Exemplo de response:
        {
            "id": 1,
            "status": "em_transito",
            "status_display": "Em Trânsito",
            "saiu_em": "2024-01-01T12:00:00Z"
        }
        """
        entrega = self.get_object()
        novo_status = request.data.get('status')

        if novo_status not in dict(Entrega.STATUS_CHOICES):
            return Response(
                {'error': f'Status inválido. Opções: {list(dict(Entrega.STATUS_CHOICES).keys())}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        entrega.status = novo_status
        # Timestamps e sincronizacao com pedido sao tratados no model.save()
        entrega.save()

        return Response(EntregaSerializer(entrega).data)
