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
from .services import (
    PedidoCheckoutError,
    validar_dados_checkout,
    criar_pedido_do_carrinho,
)


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
        # Regra de negócio: operações de consulta do estabelecimento só enxergam pedidos pagos.
        if self.action in ('list', 'retrieve', 'status', 'partial_update', 'update'):
            queryset = queryset.filter(pago=True)
        estabelecimento_id = self.request.query_params.get('estabelecimento')
        if estabelecimento_id and not self.request.query_params.get('restaurante'):
            queryset = queryset.filter(restaurante_id=estabelecimento_id)
        return queryset

    def create(self, request, *args, **kwargs):
        """
        Cria um novo pedido com itens.

        Fluxo:
        1. Valida os dados do pedido
        2. Busca o restaurante e verifica se está aberto
        3. Converte itens da API para formato de sessão
        4. Usa criar_pedido_do_carrinho que:
           - Valida produtos
           - Calcula distância e taxa de zona se applicable
           - Cria pedido e itens em transação atômica
           - Valida pedido mínimo
        5. Retorna o pedido completo
        """
        serializer = CriarPedidoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        # Busca o restaurante
        restaurante = get_object_or_404(
            Restaurante, id=dados['restaurante_id'], ativo=True
        )

        # Verifica se o restaurante está aberto
        if not restaurante.esta_aberto:
            return Response(
                {'error': 'O restaurante está fechado no momento.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Converte itens para formato esperado por criar_pedido_do_carrinho
        itens_sessao = {}
        for idx, item_data in enumerate(dados['itens']):
            item_key = f"{item_data['produto_id']}:{idx}"
            itens_sessao[item_key] = {
                'produto_id': item_data['produto_id'],
                'quantidade': item_data['quantidade'],
                'observacao': item_data.get('observacao', ''),
            }

        # Prepara dados do cliente
        dados_cliente = {
            'cliente_nome': dados['cliente_nome'],
            'cliente_telefone': dados['cliente_telefone'],
            'cliente_email': dados.get('cliente_email', ''),
            'endereco_entrega': dados.get('endereco_entrega', ''),
            'tipo_entrega': dados.get('tipo_entrega', 'delivery'),
            'forma_pagamento': dados.get('forma_pagamento', 'pix'),
            'observacoes': dados.get('observacoes', ''),
            'lat_cliente': dados.get('lat_cliente'),
            'lng_cliente': dados.get('lng_cliente'),
        }

        try:
            pedido = criar_pedido_do_carrinho(restaurante, itens_sessao, dados_cliente)
        except PedidoCheckoutError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Retorna o pedido criado com itens prefetched
        pedido = Pedido.objects.prefetch_related(
            Prefetch('itens', queryset=ItemPedido.objects.select_related('produto'))
        ).get(pk=pedido.pk)
        return Response(PedidoSerializer(pedido).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'])
    def status(self, request, pk=None):
        """
        PATCH /api/pedidos/{id}/status/

        Atualiza o status de um pedido.

        Normaliza automaticamente:
        - Retirada no local: 'entrega' → 'pronto_retirada'
        - Delivery: 'pronto_retirada' → 'entrega'

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

        # Normaliza o status baseado no tipo de entrega
        novo_status = pedido.normalizar_status_por_tipo_entrega(novo_status)

        valido, msg = pedido.validar_transicao_status(novo_status)
        if not valido:
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

        pedido.status = novo_status
        pedido.save()

        # BFS (Cap. 6): inclui informações de navegação do grafo de status
        nomes = dict(Pedido.STATUS_CHOICES)
        return Response({
            'id': pedido.id,
            'status': pedido.status,
            'status_display': pedido.get_status_display(),
            'proximo_passo': pedido.proximo_passo,
            'passos_para_concluir': pedido.passos_para_concluir,
            'caminho_ate_conclusao': [
                nomes.get(s, s) for s in pedido.caminho_ate_status('concluido')
            ],
        })
