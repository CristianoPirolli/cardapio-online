# =============================================================================
# apps/pagamentos/serializers.py - Serializers REST para pagamentos
# =============================================================================

from rest_framework import serializers
from .models import Pagamento


class PagamentoSerializer(serializers.ModelSerializer):
    """
    Serializer de Pagamento.

    Exemplo de response (GET /api/pagamentos/{id}/):
    {
        "id": 1,
        "pedido": 1,
        "gateway": "pix_manual",
        "external_payment_id": "",
        "valor": "91.79",
        "status": "aprovado",
        "criado_em": "2024-01-01T10:00:00Z"
    }
    """

    class Meta:
        model = Pagamento
        fields = [
            'id', 'pedido', 'gateway', 'external_payment_id',
            'valor', 'status', 'criado_em', 'atualizado_em'
        ]
        read_only_fields = ['id', 'criado_em', 'atualizado_em']
