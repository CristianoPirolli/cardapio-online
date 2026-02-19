# =============================================================================
# apps/pedidos/api_views.py - Views da API REST para pedidos
#
# Endpoints:
# GET    /api/pedidos/                → Lista pedidos (filtro por restaurante)
# POST   /api/pedidos/               → Cria novo pedido com itens
# GET    /api/pedidos/{id}/           → Detalhe de pedido
# PATCH  /api/pedidos/{id}/status/    → Atualiza status do pedido
# =============================================================================

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch

from apps.restaurantes.models import Restaurante
from apps.produtos.models import Produto
from .models import Pedido, ItemPedido
from .serializers import PedidoSerializer, CriarPedidoSerializer


class PedidoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para pedidos via API.

    Endpoints:
    - GET    /api/pedidos/              → Listar pedidos
    - POST   /api/pedidos/              → Criar pedido
    - GET    /api/pedidos/{id}/         → Detalhe
    - PATCH  /api/pedidos/{id}/status/  → Atualizar status

    Filtros: ?restaurante=1&status=recebido
    """

    queryset = Pedido.objects.prefetch_related(
        Prefetch('itens', queryset=ItemPedido.objects.select_related('produto'))
    ).all()
    serializer_class = PedidoSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['restaurante', 'status', 'pago', 'tipo_entrega']
    ordering_fields = ['criado_em', 'total']

    def get_queryset(self):
        queryset = super().get_queryset()
        estabelecimento_id = self.request.query_params.get('estabelecimento')
        if estabelecimento_id and not self.request.query_params.get('restaurante'):
            queryset = queryset.filter(restaurante_id=estabelecimento_id)
        return queryset

    def create(self, request, *args, **kwargs):
        """
        Cria um novo pedido com itens.

        Fluxo:
        1. Valida os dados do pedido e dos itens
        2. Verifica se todos os produtos existem e estão disponíveis
        3. Cria o pedido e os itens (preço unitário = preço atual do produto)
        4. Calcula totais (subtotal + taxa + imposto)
        5. Retorna o pedido completo
        """
        serializer = CriarPedidoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        # Busca o restaurante
        restaurante = get_object_or_404(
            Restaurante, id=dados['restaurante_id'], ativo=True
        )

        # Verifica se o restaurante esta aberto
        if not restaurante.esta_aberto:
            return Response(
                {'error': 'O restaurante está fechado no momento.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        itens_data = dados['itens']

        # Cria o pedido
        pedido = Pedido.objects.create(
            restaurante=restaurante,
            cliente_nome=dados['cliente_nome'],
            cliente_telefone=dados['cliente_telefone'],
            cliente_email=dados.get('cliente_email', ''),
            endereco_entrega=dados.get('endereco_entrega', ''),
            tipo_entrega=dados.get('tipo_entrega', 'delivery'),
            observacoes=dados.get('observacoes', ''),
        )

        produto_ids = list({item['produto_id'] for item in itens_data})
        produtos = Produto.objects.filter(
            id__in=produto_ids,
            restaurante=restaurante,
            disponivel=True
        ).select_related('categoria')
        produtos_por_id = {produto.id: produto for produto in produtos}

        ids_invalidos = [pid for pid in produto_ids if pid not in produtos_por_id]
        if ids_invalidos:
            pedido.delete()
            return Response(
                {'error': f'Produto(s) inválido(s) ou indisponível(is): {ids_invalidos}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        itens_pedido = []
        for item_data in itens_data:
            produto = produtos_por_id[item_data['produto_id']]
            itens_pedido.append(ItemPedido(
                pedido=pedido,
                produto=produto,
                quantidade=item_data['quantidade'],
                preco_unitario=produto.preco,
                observacao=item_data.get('observacao', ''),
            ))
        ItemPedido.objects.bulk_create(itens_pedido)

        # Calcula os totais
        pedido.calcular_totais()

        # Valida pedido mínimo
        if pedido.subtotal < restaurante.pedido_minimo:
            pedido.delete()
            return Response(
                {
                    'error': f'Pedido mínimo é R$ {restaurante.pedido_minimo:.2f}. '
                             f'Seu subtotal: R$ {pedido.subtotal:.2f}'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cria registro de entrega para pedidos delivery
        if pedido.tipo_entrega == 'delivery':
            from apps.entregas.models import Entrega
            Entrega.objects.create(pedido=pedido, status='aguardando')

        # Retorna o pedido criado
        pedido = self.get_queryset().get(pk=pedido.pk)
        return Response(PedidoSerializer(pedido).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'])
    def status(self, request, pk=None):
        """
        PATCH /api/pedidos/{id}/status/

        Atualiza o status de um pedido.

        Exemplo de request:
        {"status": "preparo"}

        Exemplo de response:
        {"id": 1, "status": "preparo", "status_display": "Em Preparo"}
        """
        pedido = self.get_object()
        novo_status = request.data.get('status')

        if novo_status not in dict(Pedido.STATUS_CHOICES):
            return Response(
                {'error': f'Status inválido. Opções: {list(dict(Pedido.STATUS_CHOICES).keys())}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        valido, msg = pedido.validar_transicao_status(novo_status)
        if not valido:
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

        pedido.status = novo_status
        pedido.save()

        return Response({
            'id': pedido.id,
            'status': pedido.status,
            'status_display': pedido.get_status_display(),
        })
