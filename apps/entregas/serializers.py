# =============================================================================
# apps/entregas/serializers.py - Serializers REST para entregas e entregadores
# =============================================================================

from rest_framework import serializers
from .models import Entregador, Entrega


class EntregadorSerializer(serializers.ModelSerializer):
    """
    Serializer de Entregador.

    Exemplo de response (GET /api/entregas/entregadores/):
    {
        "id": 1,
        "nome": "João Silva",
        "telefone": "(11) 98888-0000",
        "veiculo": "moto",
        "veiculo_display": "Moto",
        "disponivel": true,
        "ativo": true
    }
    """

    veiculo_display = serializers.CharField(source='get_veiculo_display', read_only=True)

    class Meta:
        model = Entregador
        fields = [
            'id', 'restaurante', 'nome', 'telefone',
            'veiculo', 'veiculo_display', 'disponivel', 'ativo'
        ]
        read_only_fields = ['id']


class EntregaSerializer(serializers.ModelSerializer):
    """
    Serializer de Entrega.

    Exemplo de response (GET /api/entregas/):
    {
        "id": 1,
        "pedido": 5,
        "entregador": 1,
        "entregador_nome": "João Silva",
        "status": "em_transito",
        "status_display": "Em Trânsito",
        "observacoes": "",
        "saiu_em": "2024-01-01T12:00:00Z",
        "entregue_em": null,
        "criado_em": "2024-01-01T11:30:00Z"
    }

    Exemplo de request (POST /api/entregas/):
    {
        "pedido": 5,
        "entregador": 1
    }

    Exemplo de request (PATCH /api/entregas/{id}/atualizar_status/):
    {
        "status": "entregue"
    }
    """

    entregador_nome = serializers.CharField(
        source='entregador.nome', read_only=True, default=''
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Entrega
        fields = [
            'id', 'pedido', 'entregador', 'entregador_nome',
            'status', 'status_display', 'observacoes',
            'saiu_em', 'entregue_em', 'criado_em', 'atualizado_em'
        ]
        read_only_fields = ['id', 'criado_em', 'atualizado_em']
