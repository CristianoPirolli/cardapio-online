# =============================================================================
# apps/pagamentos/api_views.py - Views da API REST para pagamentos
#
# Endpoints:
# GET    /api/pagamentos/              → Lista pagamentos
# POST   /api/pagamentos/criar/        → Cria pagamento para um pedido
# POST   /api/pagamentos/webhook/      → Webhook do Stripe
# GET    /api/pagamentos/{id}/         → Detalhe de um pagamento
# =============================================================================

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from apps.pedidos.models import Pedido
from .models import Pagamento
from .serializers import PagamentoSerializer
from .services import criar_pagamento, processar_webhook_stripe


class PagamentoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet somente leitura para consultar pagamentos.

    Endpoints:
    - GET /api/pagamentos/        → Lista pagamentos
    - GET /api/pagamentos/{id}/   → Detalhe de pagamento

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

    Exemplo de request:
    {
        "pedido_id": 1
    }

    Exemplo de response (201 Created):
    {
        "pagamento_id": 1,
        "client_secret": "pi_xxx_secret_yyy",
        "gateway": "stripe",
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

    resultado = criar_pagamento(pedido)

    return Response({
        'pagamento_id': resultado['pagamento'].id,
        'client_secret': resultado['client_secret'],
        'gateway': resultado['gateway'],
        'valor': str(resultado['pagamento'].valor),
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def stripe_webhook(request):
    """
    POST /api/pagamentos/webhook/

    Endpoint para receber webhooks do Stripe.

    O Stripe envia eventos como:
    - payment_intent.succeeded → Pagamento confirmado
    - payment_intent.payment_failed → Pagamento falhou

    Headers necessários:
    - Stripe-Signature: assinatura para verificação

    Response:
    - 200: Evento processado com sucesso
    - 400: Payload ou assinatura inválidos
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    resultado = processar_webhook_stripe(payload, sig_header)

    return Response(
        {'message': resultado.get('message', resultado.get('error'))},
        status=resultado.get('status', 200)
    )
