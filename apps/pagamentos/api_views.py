# =============================================================================
# apps/pagamentos/api_views.py - Views da API REST para pagamentos
#
# Endpoints:
# GET    /api/pagamentos/              → Lista pagamentos
# POST   /api/pagamentos/criar/        → Cria pagamento para um pedido
# GET    /api/pagamentos/{id}/         → Detalhe de um pagamento
# =============================================================================

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.pedidos.models import Pedido
from .models import Pagamento
from .serializers import PagamentoSerializer
from .services import criar_pagamento


class PagamentoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet somente leitura para consultar pagamentos.

    Filtros: ?pedido=1&status=aprovado&gateway=stripe
    """

    queryset = Pagamento.objects.all()
    serializer_class = PagamentoSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['pedido', 'status', 'gateway']


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def criar_pagamento_api(request):
    """
    POST /api/pagamentos/criar/

    Cria um pagamento para um pedido existente.

    Request:  {"pedido_id": 1}
    Response: {"pagamento_id": 1, "gateway": "stripe", "checkout_url": "..."}
    """
    pedido_id = request.data.get('pedido_id')
    if not pedido_id:
        return Response(
            {'error': 'pedido_id é obrigatório'},
            status=status.HTTP_400_BAD_REQUEST
        )

    pedido = get_object_or_404(Pedido, id=pedido_id)

    if pedido.pago:
        return Response(
            {'error': 'Este pedido já foi pago'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        resultado = criar_pagamento(pedido)
    except Exception as exc:
        return Response(
            {'error': str(exc)},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response({
        'pagamento_id': resultado['pagamento'].id,
        'gateway': resultado['gateway'],
        'valor': str(resultado['pagamento'].valor),
    }, status=status.HTTP_201_CREATED)
