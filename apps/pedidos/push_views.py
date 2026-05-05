from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import PushSubscription


@api_view(['POST'])
@permission_classes([AllowAny])
def push_subscribe(request):
    """
    Registra ou atualiza uma Web Push subscription.

    Body JSON:
    {
        "endpoint": "https://fcm.googleapis.com/...",
        "keys": {"p256dh": "...", "auth": "..."},
        "tipo": "painel" | "pedido",
        "restaurante_id": 5,   // obrigatório se tipo == "painel"
        "pedido_id": 42        // obrigatório se tipo == "pedido"
    }
    """
    data = request.data
    endpoint = data.get('endpoint')
    keys = data.get('keys') or {}
    tipo = data.get('tipo')

    if not endpoint or not keys.get('p256dh') or not keys.get('auth'):
        return Response(
            {'error': 'endpoint, keys.p256dh e keys.auth são obrigatórios'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    defaults = {
        'p256dh': keys['p256dh'],
        'auth': keys['auth'],
        'user_agent': (request.META.get('HTTP_USER_AGENT') or '')[:255],
    }

    if tipo == 'painel':
        restaurante_id = data.get('restaurante_id')
        if not restaurante_id:
            return Response(
                {'error': 'restaurante_id é obrigatório para tipo painel'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.restaurantes.models import Restaurante
        try:
            restaurante = Restaurante.objects.get(id=restaurante_id)
        except Restaurante.DoesNotExist:
            return Response({'error': 'Restaurante não encontrado'}, status=status.HTTP_404_NOT_FOUND)

        PushSubscription.objects.update_or_create(
            restaurante=restaurante,
            endpoint=endpoint,
            defaults=defaults,
        )

    elif tipo == 'pedido':
        pedido_id = data.get('pedido_id')
        if not pedido_id:
            return Response(
                {'error': 'pedido_id é obrigatório para tipo pedido'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .models import Pedido
        try:
            pedido = Pedido.objects.get(id=pedido_id)
        except Pedido.DoesNotExist:
            return Response({'error': 'Pedido não encontrado'}, status=status.HTTP_404_NOT_FOUND)

        PushSubscription.objects.update_or_create(
            pedido=pedido,
            endpoint=endpoint,
            defaults=defaults,
        )

    else:
        return Response(
            {'error': 'tipo deve ser "painel" ou "pedido"'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({'status': 'ok'}, status=status.HTTP_201_CREATED)
