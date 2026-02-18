# =============================================================================
# apps/pagamentos/views.py - Views HTML para pagamento
#
# Views para:
# - Escolha de método de pagamento
# - Página de pagamento Stripe (com Stripe.js)
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
    Página para escolher o método de pagamento.

    Se USE_STRIPE_MOCK=True, mostra botão de simulação.
    Se USE_STRIPE_MOCK=False, mostra formulário Stripe.
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if pedido.pago:
        messages.info(request, 'Este pedido já foi pago.')
        return redirect('acompanhar_pedido', pedido_id=pedido.id)

    # Cria o pagamento (Stripe ou mock)
    resultado = criar_pagamento(pedido)

    context = {
        'pedido': pedido,
        'restaurante': pedido.restaurante,
        'pagamento': resultado['pagamento'],
        'client_secret': resultado['client_secret'],
        'gateway': resultado['gateway'],
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'use_mock': settings.USE_STRIPE_MOCK,
    }

    return render(request, 'pagamentos/pagamento.html', context)


def pagamento_confirmar_mock(request, pagamento_id):
    """
    Confirma um pagamento mock (simulação).

    Redireciona para a página de sucesso após "pagamento".
    """
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
