# =============================================================================
# apps/pagamentos/api_views.py - Views da API REST para pagamentos
#
# Endpoints:
# GET    /api/pagamentos/              → Lista pagamentos
# POST   /api/pagamentos/criar/        → Cria pagamento para um pedido
# POST   /api/pagamentos/webhook/      → Webhook PIX (Banco do Brasil)
# GET    /api/pagamentos/{id}/         → Detalhe de um pagamento
# =============================================================================

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.pedidos.models import Pedido
from .models import Pagamento
from .serializers import PagamentoSerializer
from .services import criar_pagamento, processar_webhook_bb


class PagamentoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet somente leitura para consultar pagamentos.

    Endpoints:
    - GET /api/pagamentos/        → Lista pagamentos
    - GET /api/pagamentos/{id}/   → Detalhe de pagamento

    Filtros: ?pedido=1&status=aprovado&gateway=bb_pix
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

    Request:
    {
        "pedido_id": 1
    }

    Response (201 Created):
    {
        "pagamento_id": 1,
        "client_secret": "mock_pi_xxxx",
        "gateway": "mock",
        "valor": "91.79"
    }
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
        'client_secret': resultado['client_secret'],
        'gateway': resultado['gateway'],
        'valor': str(resultado['pagamento'].valor),
        'pix_copia_cola': resultado.get('pix_copia_cola'),
        'pix_ticket_url': resultado.get('pix_ticket_url'),
        'expira_em': resultado.get('expira_em'),
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def pix_webhook(request):
    """
    POST /api/pagamentos/webhook/

    Endpoint para receber webhooks PIX do Banco do Brasil.
    Quando BB PIX estiver implementado, este endpoint será notificado
    automaticamente a cada pagamento confirmado.

    Response:
    - 200: Evento processado
    - 400: Payload inválido
    """
    resultado = processar_webhook_bb(request)

    return Response(
        {'message': resultado.get('message', resultado.get('error'))},
        status=resultado.get('status', 200)
    )
