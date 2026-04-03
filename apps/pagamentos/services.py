# =============================================================================
# apps/pagamentos/services.py - Serviço de pagamento PIX Manual
#
# Fluxo:
# 1. criar_pagamento_pix_manual(pedido) → cria Pagamento pendente
# 2. Cliente envia comprovante → pedido vai para aguardando_confirmacao
# 3. Restaurante aceita → confirmar_pix_manual(pagamento) → pedido.pago=True, recebido
# 4. Restaurante rejeita → rejeitar_pix_manual(pagamento) → cancelado
# =============================================================================

import logging

from .models import Pagamento

logger = logging.getLogger(__name__)


def criar_pagamento_pix_manual(pedido):
    """
    Cria (ou reutiliza) um registro Pagamento pendente para o pedido.

    Idempotente: se já existe um Pagamento pendente para o pedido,
    retorna o existente em vez de criar um duplicado.

    Não altera pedido.pago nem pedido.status — isso é responsabilidade
    do restaurante ao aceitar (confirmar_pix_manual).

    Args:
        pedido: instância de Pedido em status 'aguardando'

    Returns:
        instância de Pagamento com status='pendente'
    """
    existente = Pagamento.objects.filter(
        pedido=pedido,
        status='pendente',
        gateway='pix_manual',
    ).first()

    if existente:
        logger.debug(
            "criar_pagamento_pix_manual: reusing existing pagamento %s for pedido %s",
            existente.id, pedido.id
        )
        return existente

    pagamento = Pagamento.objects.create(
        pedido=pedido,
        gateway='pix_manual',
        valor=pedido.total,
        status='pendente',
    )
    logger.info(
        "criar_pagamento_pix_manual: created pagamento %s for pedido %s",
        pagamento.id, pedido.id
    )
    return pagamento


def confirmar_pix_manual(pagamento):
    """
    Restaurante aceita o comprovante de pagamento PIX.

    Transição: aguardando_confirmacao → recebido
    Efeito:
    - pagamento.status = 'aprovado'
    - pedido.pago = True
    - pedido.status = 'recebido' (via BFS-validated save())

    Idempotente: se pagamento já está aprovado, não faz nada.

    Args:
        pagamento: instância de Pagamento com gateway='pix_manual'

    Returns:
        pagamento (atualizado)
    """
    if pagamento.status == 'aprovado':
        return pagamento

    pagamento.status = 'aprovado'
    pagamento.save(update_fields=['status', 'atualizado_em'])

    pedido = pagamento.pedido
    pedido.pago = True
    if pedido.status == 'aguardando_confirmacao':
        pedido.status = 'recebido'
    pedido.save()  # BFS validation runs here automatically

    logger.info(
        "confirmar_pix_manual: pedido %s confirmado, status=recebido",
        pedido.id
    )
    return pagamento


def rejeitar_pix_manual(pagamento):
    """
    Restaurante rejeita o comprovante de pagamento PIX.

    Transição: aguardando_confirmacao → cancelado
    Efeito:
    - pagamento.status = 'recusado'
    - pedido.status = 'cancelado'
    - pedido.pago permanece False

    Args:
        pagamento: instância de Pagamento com gateway='pix_manual'

    Returns:
        pagamento (atualizado)
    """
    pagamento.status = 'recusado'
    pagamento.save(update_fields=['status', 'atualizado_em'])

    pedido = pagamento.pedido
    if pedido.status == 'aguardando_confirmacao':
        pedido.status = 'cancelado'
        pedido.save()  # BFS validation: aguardando_confirmacao → cancelado is valid

    logger.info(
        "rejeitar_pix_manual: pedido %s rejeitado, status=cancelado",
        pedido.id
    )
    return pagamento
