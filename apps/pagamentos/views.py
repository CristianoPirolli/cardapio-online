# =============================================================================
# apps/pagamentos/views.py - Views HTML para pagamento
#
# Views para:
# - Página de pagamento PIX (BB PIX ou simulação)
# - Confirmação de pagamento mock
# - Página de sucesso/erro
# =============================================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings

from apps.pedidos.models import Pedido
from .models import Pagamento
from .services import criar_pagamento, confirmar_pagamento_mock


def pagamento_escolher(request, pedido_id):
    """
    Página de pagamento do pedido.

    Se USE_PIX_MOCK=True, mostra botão de simulação.
    Se USE_PIX_MOCK=False, exibe QR Code / PIX copia e cola do BB.
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if pedido.pago:
        messages.info(request, 'Este pedido já foi pago.')
        return redirect('acompanhar_pedido', pedido_id=pedido.id)

    try:
        resultado = criar_pagamento(pedido)
    except Exception as exc:
        messages.error(request, f'Não foi possível iniciar o pagamento: {exc}')
        return redirect('pagamento_erro', pedido_id=pedido.id)

    context = {
        'pedido': pedido,
        'restaurante': pedido.restaurante,
        'pagamento': resultado['pagamento'],
        'checkout_url': resultado.get('checkout_url'),
        'pix_qr_code_base64': resultado.get('pix_qr_code_base64'),
        'pix_copia_cola': resultado.get('pix_copia_cola'),
        'pix_ticket_url': resultado.get('pix_ticket_url'),
        'expira_em': resultado.get('expira_em'),
        'client_secret': resultado['client_secret'],
        'gateway': resultado['gateway'],
        'use_mock': settings.USE_PIX_MOCK,
    }

    return render(request, 'pagamentos/pagamento.html', context)


def pagamento_confirmar_mock(request, pagamento_id):
    """
    Confirma um pagamento mock (simulação).
    Redireciona para a página de sucesso após "pagamento".
    """
    if not settings.USE_PIX_MOCK:
        messages.error(request, 'Modo de pagamento simulado indisponivel neste ambiente.')
        return redirect('home')

    pagamento = get_object_or_404(Pagamento, id=pagamento_id, gateway='mock')

    if pagamento.status == 'aprovado':
        messages.info(request, 'Este pagamento já foi confirmado.')
    else:
        confirmar_pagamento_mock(pagamento)
        messages.success(request, 'Pagamento simulado confirmado com sucesso!')

    return redirect('pagamento_sucesso', pedido_id=pagamento.pedido_id)


def pagamento_sucesso(request, pedido_id):
    """Página de sucesso após pagamento confirmado."""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, 'pagamentos/sucesso.html', {
        'pedido': pedido,
        'restaurante': pedido.restaurante,
    })


def pagamento_erro(request, pedido_id):
    """Página de erro quando o pagamento falha."""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, 'pagamentos/erro.html', {
        'pedido': pedido,
        'restaurante': pedido.restaurante,
    })
