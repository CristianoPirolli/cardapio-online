# =============================================================================
# apps/pedidos/serializers.py - Serializers REST para pedidos
#
# Serializa pedidos e itens para a API REST.
# Suporta criação de pedido com itens em uma única requisição (nested).
# =============================================================================

from rest_framework import serializers
from .models import Pedido, ItemPedido
from apps.produtos.models import Produto


class ItemPedidoSerializer(serializers.ModelSerializer):
    """
    Serializer de ItemPedido.

    Exemplo:
    {
        "id": 1,
        "produto": 5,
        "produto_nome": "Pizza Margherita",
        "quantidade": 2,
        "preco_unitario": "39.90",
        "tamanho_nome": "Grande",
        "sabores_descricao": "Calabresa, Frango com Catupiry",
        "observacao": "Sem cebola",
        "subtotal": "79.80"
    }
    """

    produto_nome = serializers.CharField(source='produto.nome', read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = ItemPedido
        fields = [
            'id', 'produto', 'produto_nome', 'quantidade',
            'preco_unitario', 'tamanho_nome', 'sabores_descricao',
            'observacao', 'subtotal'
        ]
        read_only_fields = ['id', 'preco_unitario']


class ItemPedidoCriacaoSerializer(serializers.Serializer):
    """
    Serializer para criação de itens ao criar um pedido.

    O preço unitário é obtido automaticamente do produto.

    Exemplo de input:
    {
        "produto_id": 5,
        "quantidade": 2,
        "observacao": "Sem cebola"
    }
    """

    produto_id = serializers.IntegerField()
    quantidade = serializers.IntegerField(min_value=1)
    observacao = serializers.CharField(required=False, default='')


class PedidoSerializer(serializers.ModelSerializer):
    """
    Serializer completo de Pedido com itens aninhados.

    Exemplo de response (GET /api/pedidos/{id}/):
    {
        "id": 1,
        "restaurante": 1,
        "cliente_nome": "Maria Silva",
        "cliente_telefone": "(11) 99999-0000",
        "cliente_email": "maria@email.com",
        "endereco_entrega": "Rua das Flores, 123",
        "tipo_entrega": "delivery",
        "observacoes": "Tocar a campainha",
        "itens": [
            {
                "id": 1,
                "produto": 5,
                "produto_nome": "Pizza Margherita",
                "quantidade": 2,
                "preco_unitario": "39.90",
                "observacao": "",
                "subtotal": "79.80"
            }
        ],
        "subtotal": "79.80",
        "taxa_entrega": "8.00",
        "imposto": "3.99",
        "total": "91.79",
        "status": "recebido",
        "pago": false,
        "criado_em": "2024-01-01T10:00:00Z"
    }
    """

    itens = ItemPedidoSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Pedido
        fields = [
            'id', 'restaurante', 'cliente_nome', 'cliente_telefone',
            'cliente_email', 'endereco_entrega', 'tipo_entrega',
            'forma_pagamento', 'observacoes', 'itens', 'subtotal', 'taxa_entrega',
            'imposto', 'total', 'status', 'status_display',
            'pago', 'criado_em', 'atualizado_em'
        ]
        read_only_fields = [
            'id', 'subtotal', 'taxa_entrega', 'imposto',
            'total', 'pago', 'criado_em', 'atualizado_em'
        ]


class CriarPedidoSerializer(serializers.Serializer):
    """
    Serializer para criação de um novo pedido via API.

    Exemplo de request (POST /api/pedidos/):
    {
        "restaurante_id": 1,
        "cliente_nome": "Maria Silva",
        "cliente_telefone": "(11) 99999-0000",
        "cliente_email": "maria@email.com",
        "endereco_entrega": "Rua das Flores, 123",
        "tipo_entrega": "delivery",
        "forma_pagamento": "dinheiro",
        "lat_cliente": -23.5505,
        "lng_cliente": -46.6333,
        "observacoes": "Tocar a campainha",
        "itens": [
            {"produto_id": 5, "quantidade": 2, "observacao": "Sem cebola"},
            {"produto_id": 8, "quantidade": 1}
        ]
    }

    Exemplo de response (201 Created):
    {
        "id": 1,
        "total": "91.79",
        "status": "recebido",
        ...
    }
    """

    restaurante_id = serializers.IntegerField()
    cliente_nome = serializers.CharField(max_length=200)
    cliente_telefone = serializers.CharField(max_length=20)
    cliente_email = serializers.EmailField(required=False, default='')
    endereco_entrega = serializers.CharField(required=False, default='')
    tipo_entrega = serializers.ChoiceField(
        choices=Pedido.TIPO_ENTREGA_CHOICES, default='delivery'
    )
    forma_pagamento = serializers.ChoiceField(
        choices=Pedido.FORMA_PAGAMENTO_CHOICES, default='pix'
    )
    lat_cliente = serializers.FloatField(required=False, allow_null=True)
    lng_cliente = serializers.FloatField(required=False, allow_null=True)
    observacoes = serializers.CharField(required=False, default='')
    itens = ItemPedidoCriacaoSerializer(many=True, min_length=1)

    def validate(self, data):
        """Valida que pedidos delivery possuem endereco."""
        if data.get('tipo_entrega') == 'delivery':
            endereco = data.get('endereco_entrega', '').strip()
            if not endereco:
                raise serializers.ValidationError({
                    'endereco_entrega': 'Endereço de entrega é obrigatório para pedidos delivery.'
                })
        return data
