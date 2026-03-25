# =============================================================================
# apps/pagamentos/views.py - Views HTML para pagamento
#
# Views para:
# - Página de escolha de método (Cartão / PIX / Mock)
# - Iniciar pagamento Stripe (cria session e redireciona)
# - Retorno do Stripe Checkout
# - Webhook do Stripe
# - Confirmação de pagamento mock
# - Página de sucesso/erro
# =============================================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.pedidos.models import Pedido
from .models import Pagamento
from .services import (
    criar_pagamento,
    confirmar_pagamento_mock,
    confirmar_pagamento_stripe,
    processar_webhook_stripe,
)


def pagamento_escolher(request, pedido_id):
    """
    Página de escolha do método de pagamento.

    - stripe: Mostra opções Cartão e PIX
    - mock: Mostra botão de simulação
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if pedido.pago:
        messages.info(request, 'Este pedido já foi pago.')
        return redirect('acompanhar_pedido', pedido_id=pedido.id)

    gateway = settings.PAYMENT_GATEWAY

    if gateway == 'mock':
        try:
            resultado = criar_pagamento(pedido)
        except Exception as exc:
            messages.error(request, f'Não foi possível iniciar o pagamento: {exc}')
            return redirect('pagamento_erro', pedido_id=pedido.id)

        context = {
            'pedido': pedido,
            'restaurante': pedido.restaurante,
            'pagamento': resultado['pagamento'],
            'gateway': 'mock',
        }
    else:
        # Stripe: apenas mostra a página de escolha (sem criar session ainda)
        context = {
            'pedido': pedido,
            'restaurante': pedido.restaurante,
            'gateway': 'stripe',
        }

    return render(request, 'pagamentos/pagamento.html', context)


@require_POST
def iniciar_pagamento_stripe(request, pedido_id):
    """
    Cria a Stripe Checkout Session com o método escolhido e redireciona.

    POST com campo 'metodo': 'card' ou 'pix'
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if pedido.pago:
        messages.info(request, 'Este pedido já foi pago.')
        return redirect('acompanhar_pedido', pedido_id=pedido.id)

    metodo = request.POST.get('metodo', 'card')
    if metodo not in ('card', 'pix'):
        metodo = 'card'

    try:
        resultado = criar_pagamento(pedido, metodo=metodo)
    except Exception as exc:
        messages.error(request, f'Não foi possível iniciar o pagamento: {exc}')
        return redirect('pagamento_erro', pedido_id=pedido.id)

    checkout_url = resultado.get('checkout_url')
    if checkout_url:
        return redirect(checkout_url)

    messages.error(request, 'Não foi possível criar a sessão de pagamento.')
    return redirect('pagamento_erro', pedido_id=pedido.id)


def stripe_checkout_return(request, pedido_id):
    """
    Retorno do Stripe Checkout após pagamento.

    Verifica o status direto na API do Stripe e confirma.
    Funciona mesmo sem webhook (ideal para desenvolvimento local).
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)
    session_id = request.GET.get('session_id')

    if not session_id:
        messages.error(request, 'Sessão de pagamento não encontrada.')
        return redirect('pagamento_erro', pedido_id=pedido.id)

    try:
        confirmar_pagamento_stripe(session_id)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning('stripe_checkout_return: %s', exc)

    pedido.refresh_from_db()

    if pedido.pago:
        messages.success(request, 'Pagamento confirmado com sucesso!')
        return redirect('pagamento_sucesso', pedido_id=pedido.id)

    messages.error(request, 'Não foi possível confirmar o pagamento.')
    return redirect('pagamento_erro', pedido_id=pedido.id)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Webhook do Stripe para confirmar pagamentos automaticamente.

    Em desenvolvimento local, use o Stripe CLI:
        stripe listen --forward-to localhost:8081/pagamentos/stripe-webhook/
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    resultado = processar_webhook_stripe(payload, sig_header)

    return JsonResponse(
        {'message': resultado.get('message', resultado.get('error'))},
        status=resultado.get('status', 200)
    )


def pagamento_confirmar_mock(request, pagamento_id):
    """
    Confirma um pagamento mock (simulação).
    """
    if settings.PAYMENT_GATEWAY != 'mock':
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
