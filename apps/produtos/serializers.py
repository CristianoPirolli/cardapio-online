# =============================================================================
# apps/produtos/serializers.py - Serializers REST para produtos e categorias
#
# Serializam/deserializam dados para a API REST de produtos.
# =============================================================================

from rest_framework import serializers
from .models import Categoria, Produto


class CategoriaSerializer(serializers.ModelSerializer):
    """
    Serializer para Categoria.

    Exemplo de response (GET /api/produtos/categorias/):
    {
        "id": 1,
        "nome": "Pizzas Tradicionais",
        "descricao": "Nossas pizzas clássicas",
        "ordem": 1,
        "ativo": true,
        "quantidade_produtos": 8
    }
    """

    quantidade_produtos = serializers.SerializerMethodField()

    class Meta:
        model = Categoria
        fields = [
            'id', 'restaurante', 'nome', 'descricao', 'ordem',
            'adicional_sabor', 'eh_pizza', 'ativo', 'quantidade_produtos'
        ]
        read_only_fields = ['id']

    def get_quantidade_produtos(self, obj):
        """Retorna a quantidade de produtos ativos nesta categoria."""
        return getattr(
            obj,
            'quantidade_produtos',
            obj.produtos.filter(disponivel=True).count()
        )


class ProdutoSerializer(serializers.ModelSerializer):
    """
    Serializer completo de Produto.

    Exemplo de response (GET /api/produtos/):
    {
        "id": 1,
        "restaurante": 1,
        "categoria": 1,
        "categoria_nome": "Pizzas Tradicionais",
        "nome": "Pizza Margherita",
        "descricao": "Molho de tomate, mussarela e manjericão fresco",
        "preco": "39.90",
        "imagem": "/media/produtos/margherita.jpg",
        "disponivel": true,
        "destaque": true,
        "criado_em": "2024-01-01T10:00:00Z",
        "atualizado_em": "2024-01-01T10:00:00Z"
    }

    Exemplo de request (POST /api/produtos/):
    {
        "restaurante": 1,
        "categoria": 1,
        "nome": "Pizza Calabresa",
        "descricao": "Calabresa, cebola e azeitonas",
        "preco": "35.90"
    }
    """

    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)
    preco = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )

    class Meta:
        model = Produto
        fields = [
            'id', 'restaurante', 'categoria', 'categoria_nome',
            'nome', 'descricao', 'preco', 'imagem',
            'disponivel', 'destaque', 'criado_em', 'atualizado_em'
        ]
        read_only_fields = ['id', 'criado_em', 'atualizado_em']
