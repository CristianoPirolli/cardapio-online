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

from django.db import transaction

from .models import ChavePix
from .models import Pagamento

logger = logging.getLogger(__name__)


def selecionar_chave_pix_checkout(restaurante):
    """
    Resolve a chave PIX para checkout de forma deterministica.

    Regra:
    1. chave padrao ativa do restaurante
    2. fallback pela menor prioridade ativa
    3. desempate por id
    """
    chaves_ativas = ChavePix.objects.filter(
        restaurante=restaurante,
        ativo=True,
    ).order_by('prioridade', 'id')

    chave_padrao = chaves_ativas.filter(padrao=True).first()
    if chave_padrao:
        return chave_padrao

    fallback = chaves_ativas.first()
    if fallback:
        return fallback

    raise ValueError('Nenhuma chave PIX ativa para este restaurante.')


def _snapshot_presente(pagamento):
    return bool(pagamento.pix_chave_id_snapshot and pagamento.pix_chave_valor_snapshot)


def _aplicar_snapshot_chave(pagamento, chave):
    dados_resposta = dict(pagamento.dados_resposta or {})
    dados_resposta['pix_key'] = {
        'id': chave.id,
        'tipo': chave.tipo,
        'valor': chave.valor_normalizado or chave.valor,
    }
    pagamento.dados_resposta = dados_resposta
    pagamento.pix_chave_id_snapshot = chave.id
    pagamento.pix_chave_tipo_snapshot = chave.tipo
    pagamento.pix_chave_valor_snapshot = chave.valor_normalizado or chave.valor


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
    with transaction.atomic():
        existente = Pagamento.objects.select_for_update().filter(
            pedido=pedido,
            status='pendente',
            gateway='pix_manual',
        ).first()

        if existente:
            if not _snapshot_presente(existente):
                chave = selecionar_chave_pix_checkout(pedido.restaurante)
                _aplicar_snapshot_chave(existente, chave)
                existente.save(update_fields=[
                    'dados_resposta',
                    'pix_chave_id_snapshot',
                    'pix_chave_tipo_snapshot',
                    'pix_chave_valor_snapshot',
                    'atualizado_em',
                ])

            logger.debug(
                "criar_pagamento_pix_manual: reusing existing pagamento %s for pedido %s",
                existente.id, pedido.id
            )
            return existente

        chave = selecionar_chave_pix_checkout(pedido.restaurante)
        pagamento = Pagamento(
            pedido=pedido,
            gateway='pix_manual',
            valor=pedido.total,
            status='pendente',
        )
        _aplicar_snapshot_chave(pagamento, chave)
        pagamento.save()

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
