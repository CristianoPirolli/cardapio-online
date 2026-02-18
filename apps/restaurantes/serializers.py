# =============================================================================
# apps/restaurantes/serializers.py - Serializers REST para restaurantes
#
# Define a serialização/deserialização de dados dos restaurantes para a API.
# =============================================================================

from rest_framework import serializers
from .models import Restaurante


class RestauranteSerializer(serializers.ModelSerializer):
    """
    Serializer completo do Restaurante.

    Exemplo de response (GET /api/restaurantes/):
    {
        "id": 1,
        "nome": "Pizzaria do João",
        "subdominio": "pizzaria-do-joao",
        "descricao": "A melhor pizza da cidade",
        "endereco": "Rua das Flores, 123",
        "cidade": "São Paulo",
        "estado": "SP",
        "cep": "01234-567",
        "telefone": "(11) 99999-9999",
        "email": "contato@pizzariadojoao.com",
        "logo": "/media/restaurantes/logos/logo.jpg",
        "taxa_entrega": "8.00",
        "pedido_minimo": "25.00",
        "raio_entrega_km": "15.0",
        "taxa_imposto": "5.00",
        "horario_abertura": "11:00:00",
        "horario_fechamento": "23:00:00",
        "esta_aberto": true,
        "ativo": true
    }
    """

    esta_aberto = serializers.BooleanField(read_only=True)
    proprietario = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Restaurante
        fields = [
            'id', 'nome', 'subdominio', 'proprietario', 'descricao',
            'endereco', 'cidade', 'estado', 'cep', 'telefone', 'email',
            'logo', 'taxa_entrega', 'pedido_minimo', 'raio_entrega_km',
            'taxa_imposto', 'horario_abertura', 'horario_fechamento',
            'esta_aberto', 'ativo', 'criado_em', 'atualizado_em'
        ]
        read_only_fields = ['id', 'criado_em', 'atualizado_em']


class RestauranteResumoSerializer(serializers.ModelSerializer):
    """
    Serializer resumido para listagens e referências.

    Exemplo de response:
    {
        "id": 1,
        "nome": "Pizzaria do João",
        "subdominio": "pizzaria-do-joao",
        "logo": "/media/restaurantes/logos/logo.jpg",
        "esta_aberto": true
    }
    """

    esta_aberto = serializers.BooleanField(read_only=True)

    class Meta:
        model = Restaurante
        fields = ['id', 'nome', 'subdominio', 'logo', 'esta_aberto']
