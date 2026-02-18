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
        "gateway": "stripe",
        "stripe_payment_intent_id": "pi_xxx",
        "valor": "91.79",
        "status": "aprovado",
        "criado_em": "2024-01-01T10:00:00Z"
    }
    """

    class Meta:
        model = Pagamento
        fields = [
            'id', 'pedido', 'gateway', 'stripe_payment_intent_id',
            'valor', 'status', 'criado_em', 'atualizado_em'
        ]
        read_only_fields = ['id', 'criado_em', 'atualizado_em']
