# =============================================================================
# apps/pagamentos/views.py - Views HTML para pagamento
#
# Views para:
# - Página de pagamento PIX manual (escolha e exibição da chave PIX)
# - Verificação de status do pagamento
# - Confirmação de pagamento mock (desenvolvimento)
# - Página de sucesso/erro
# =============================================================================

import logging

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.pedidos.models import Pedido

from .models import Pagamento
from .services import (
    confirmar_pagamento_mock,
    criar_pagamento,
)

logger = logging.getLogger(__name__)


def pagamento_escolher(request, pedido_id):
    """
    Página de pagamento PIX manual.
    Exibe a chave PIX do estabelecimento para o cliente realizar o pagamento.
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if pedido.pago:
        messages.info(request, 'Este pedido já foi pago.')
        return redirect('acompanhar_pedido', pedido_id=pedido.id)

    return render(request, 'pagamentos/pagamento.html', {
        'pedido': pedido,
        'restaurante': pedido.restaurante,
        'pix_key': getattr(settings, 'PIX_KEY', ''),
    })


def pagamento_pix(request, pedido_id):
    """
    Página de PIX manual. Exibe a chave PIX e instrucoes para o cliente.
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if pedido.pago:
        return redirect('pagamento_sucesso', pedido_id=pedido.id)

    pagamento = Pagamento.objects.filter(
        pedido=pedido,
        status='pendente',
    ).first()

    if not pagamento:
        # Cria o pagamento pendente se nao existir
        try:
            resultado = criar_pagamento(pedido)
            pagamento = resultado['pagamento']
        except Exception as exc:
            messages.error(request, f'Nao foi possivel iniciar o pagamento: {exc}')
            return redirect('pagamento_escolher', pedido_id=pedido.id)

    pix_key = getattr(settings, 'PIX_KEY', '')

    return render(request, 'pagamentos/pix.html', {
        'pedido': pedido,
        'restaurante': pedido.restaurante,
        'pagamento': pagamento,
        'pix_key': pix_key,
        'is_mock': pagamento.gateway == 'mock',
    })


def verificar_status_pagamento(request, pagamento_id):
    """
    Endpoint de polling para a pagina do PIX.
    Retorna JSON: {pago, status, redirect_url}
    """
    pagamento = get_object_or_404(Pagamento, id=pagamento_id)

    pago = pagamento.status == 'aprovado'
    pedido = pagamento.pedido

    return JsonResponse({
        'pago': pago,
        'status': pagamento.status,
        'redirect_url': (
            reverse('pagamento_sucesso', args=[pedido.id]) if pago else None
        ),
    })


def mock_cartao_checkout(request, pedido_id):
    """
    Pagina de simulacao de checkout para modo mock.
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if pedido.pago:
        return redirect('pagamento_sucesso', pedido_id=pedido.id)

    pagamento = Pagamento.objects.filter(
        pedido=pedido,
        status='pendente',
        gateway='mock',
    ).first()

    if not pagamento:
        messages.error(request, 'Sessao de simulacao nao encontrada.')
        return redirect('pagamento_escolher', pedido_id=pedido.id)

    return render(request, 'pagamentos/mock_cartao.html', {
        'pedido': pedido,
        'restaurante': pedido.restaurante,
        'pagamento': pagamento,
    })


def pagamento_confirmar_mock(request, pagamento_id):
    """Confirma um pagamento mock (simulacao de desenvolvimento)."""
    pagamento = get_object_or_404(Pagamento, id=pagamento_id, gateway='mock')

    if pagamento.status == 'aprovado':
        messages.info(request, 'Este pagamento ja foi confirmado.')
    else:
        confirmar_pagamento_mock(pagamento)
        messages.success(request, 'Pagamento simulado confirmado com sucesso!')

    return redirect('pagamento_sucesso', pedido_id=pagamento.pedido_id)


def pagamento_sucesso(request, pedido_id):
    """Pagina de sucesso apos pagamento confirmado."""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, 'pagamentos/sucesso.html', {
        'pedido': pedido,
        'restaurante': pedido.restaurante,
    })


def pagamento_erro(request, pedido_id):
    """Pagina de erro quando o pagamento falha."""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, 'pagamentos/erro.html', {
        'pedido': pedido,
        'restaurante': pedido.restaurante,
    })
