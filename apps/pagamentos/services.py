# =============================================================================
# apps/pagamentos/services.py - Serviços de pagamento (PIX manual e Mock)
#
# O fluxo de pagamento foi migrado para PIX manual.
# A confirmação do pagamento é feita manualmente pelo restaurante
# após verificação do comprovante enviado pelo cliente.
# =============================================================================

import uuid
import logging
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings

from .models import Pagamento

logger = logging.getLogger(__name__)


def criar_pagamento(pedido, metodo='pix'):
    """
    Cria um registro de pagamento pendente para um pedido (PIX manual).
    Reutiliza pagamento pendente existente se já existir.

    Args:
        pedido: instância de Pedido
        metodo: 'pix' (único método suportado no fluxo manual)
    """
    pagamento_existente = Pagamento.objects.filter(
        pedido=pedido, status='pendente'
    ).first()

    if pagamento_existente:
        return {
            'pagamento': pagamento_existente,
            'gateway': pagamento_existente.gateway,
            'pix_key': getattr(settings, 'PIX_KEY', ''),
        }

    return _criar_pagamento_pix_manual(pedido)


def _to_money_2(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# =============================================================================
# PIX Manual
# =============================================================================

def _criar_pagamento_pix_manual(pedido):
    """
    Cria um registro de pagamento PIX manual.
    Não chama nenhuma API externa — apenas registra a intenção de pagamento.
    O restaurante confirma manualmente ao receber o comprovante.
    """
    valor_total = _to_money_2(pedido.total)
    pix_key = getattr(settings, 'PIX_KEY', '')

    pagamento = Pagamento.objects.create(
        pedido=pedido,
        gateway='pix_manual',
        external_payment_id='',
        valor=valor_total,
        status='pendente',
        dados_resposta={
            'pix_key': pix_key,
            'metodo': 'pix',
        },
    )

    return {
        'pagamento': pagamento,
        'gateway': 'pix_manual',
        'pix_key': pix_key,
    }


# =============================================================================
# Mock (simulação para desenvolvimento)
# =============================================================================

def _criar_pagamento_mock(pedido, metodo='pix'):
    """Simula um pagamento para desenvolvimento/testes."""
    mock_id = f'mock_pi_{uuid.uuid4().hex[:16]}'
    valor_total = _to_money_2(pedido.total)

    pagamento = Pagamento.objects.create(
        pedido=pedido,
        gateway='mock',
        external_payment_id=mock_id,
        valor=valor_total,
        status='pendente',
        dados_resposta={
            'mock_id': mock_id,
            'metodo': metodo,
            'mensagem': 'Pagamento simulado',
        },
    )

    pedido.external_payment_id = mock_id
    pedido.save(update_fields=['external_payment_id'])

    return {
        'pagamento': pagamento,
        'gateway': 'mock',
    }


def confirmar_pagamento_mock(pagamento):
    """Confirma um pagamento mock (simula sucesso)."""
    pagamento.status = 'aprovado'
    pagamento.dados_resposta = {
        **(pagamento.dados_resposta or {}),
        'confirmado': True,
        'mensagem': 'Pagamento mock confirmado com sucesso',
    }
    pagamento.save()

    pedido = pagamento.pedido
    pedido.pago = True
    if pedido.status == 'aguardando':
        pedido.status = 'recebido'
    pedido.save()

    return pagamento
