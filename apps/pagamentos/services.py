# =============================================================================
# apps/pagamentos/services.py - Serviços de pagamento (Stripe e Mock)
#
# Configure PAYMENT_GATEWAY no .env:
#   PAYMENT_GATEWAY=stripe  -> Stripe Checkout (cartão + PIX)
#   PAYMENT_GATEWAY=mock    -> Simulação local (desenvolvimento)
# =============================================================================

import uuid
from decimal import Decimal, ROUND_HALF_UP

import stripe
from django.conf import settings

from .models import Pagamento

STRIPE_METODOS_VALIDOS = ('card', 'pix')


def criar_pagamento(pedido, metodo='card'):
    """
    Cria uma sessão/intent de pagamento para um pedido.
    Reutiliza pagamento pendente existente se for o mesmo método.

    Args:
        pedido: instância de Pedido
        metodo: 'card' ou 'pix' (usado apenas para gateway Stripe)
    """
    pagamento_existente = Pagamento.objects.filter(
        pedido=pedido, status='pendente'
    ).first()

    if pagamento_existente:
        dados = pagamento_existente.dados_resposta or {}
        metodo_existente = dados.get('metodo')

        # Mesmo gateway e mesmo método → reutiliza
        if metodo_existente == metodo or pagamento_existente.gateway == 'mock':
            return {
                'pagamento': pagamento_existente,
                'checkout_url': dados.get('checkout_url'),
                'client_secret': pagamento_existente.stripe_payment_intent_id,
                'gateway': pagamento_existente.gateway,
            }

        # Método diferente → cancela o antigo e cria novo
        pagamento_existente.status = 'recusado'
        pagamento_existente.save(update_fields=['status', 'atualizado_em'])

    gateway = settings.PAYMENT_GATEWAY

    if gateway == 'stripe':
        return _criar_pagamento_stripe(pedido, metodo)
    else:
        return _criar_pagamento_mock(pedido)


def _build_absolute_url(path):
    base = getattr(settings, 'SITE_URL', '').rstrip('/')
    if base:
        return f'{base}{path}'
    return f'http://localhost{path}'


def _to_money_2(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# =============================================================================
# Stripe Checkout
# =============================================================================

def _criar_pagamento_stripe(pedido, metodo='card'):
    """
    Cria uma Stripe Checkout Session para o pedido.

    Args:
        metodo: 'card' (cartão de crédito/débito) ou 'pix'
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY

    if not stripe.api_key or stripe.api_key.startswith('sk_test_COLOQUE'):
        raise RuntimeError(
            'STRIPE_SECRET_KEY não configurada. '
            'Obtenha sua chave em https://dashboard.stripe.com/test/apikeys '
            'e configure no .env'
        )

    if metodo not in STRIPE_METODOS_VALIDOS:
        metodo = 'card'

    valor_total = _to_money_2(pedido.total)
    valor_centavos = int(valor_total * 100)

    success_url = _build_absolute_url(
        f'/pagamentos/stripe-return/{pedido.id}/'
    ) + '?session_id={CHECKOUT_SESSION_ID}'

    cancel_url = _build_absolute_url(f'/pagamentos/{pedido.id}/')

    descricao_itens = ', '.join(
        f'{item.quantidade}x {item.produto.nome}'
        for item in pedido.itens.all()[:10]
    )

    session_params = dict(
        payment_method_types=[metodo],
        line_items=[{
            'price_data': {
                'currency': 'brl',
                'product_data': {
                    'name': f'Pedido #{pedido.id} - {pedido.restaurante.nome}',
                    'description': descricao_itens or 'Pedido do cardápio',
                },
                'unit_amount': valor_centavos,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            'pedido_id': str(pedido.id),
            'restaurante': pedido.restaurante.nome,
            'metodo': metodo,
        },
    )

    # PIX: expiração de 30 minutos
    if metodo == 'pix':
        session_params['payment_method_options'] = {
            'pix': {'expires_after_seconds': 1800},
        }

    session = stripe.checkout.Session.create(**session_params)

    pagamento = Pagamento.objects.create(
        pedido=pedido,
        gateway='stripe',
        stripe_payment_intent_id=session.id,
        valor=valor_total,
        status='pendente',
        dados_resposta={
            'session_id': session.id,
            'checkout_url': session.url,
            'metodo': metodo,
        },
    )

    pedido.stripe_payment_intent_id = session.id
    pedido.save()

    return {
        'pagamento': pagamento,
        'checkout_url': session.url,
        'client_secret': session.id,
        'gateway': 'stripe',
    }


def confirmar_pagamento_stripe(session_id):
    """
    Verifica o status de uma Stripe Checkout Session e confirma o pagamento.
    Idempotente: se já confirmado, não faz nada.
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.retrieve(session_id)

    if session.payment_status != 'paid':
        return None

    pagamento = Pagamento.objects.filter(
        stripe_payment_intent_id=session_id,
        gateway='stripe',
    ).first()

    if not pagamento or pagamento.status != 'pendente':
        return pagamento

    pagamento.status = 'aprovado'
    pagamento.dados_resposta = {
        **(pagamento.dados_resposta or {}),
        'payment_status': session.payment_status,
        'payment_intent': session.payment_intent,
        'customer_email': (
            session.customer_details.email
            if session.customer_details else None
        ),
    }
    pagamento.save()

    pedido = pagamento.pedido
    pedido.pago = True
    if pedido.status == 'aguardando':
        pedido.status = 'recebido'
    pedido.save()

    return pagamento


def processar_webhook_stripe(payload, sig_header):
    """
    Processa webhook do Stripe para confirmar pagamentos.

    Em desenvolvimento (DEBUG=True) sem STRIPE_WEBHOOK_SECRET configurado,
    aceita o evento sem verificar assinatura — útil sem o Stripe CLI.

    Em produção (DEBUG=False), o STRIPE_WEBHOOK_SECRET é obrigatório.
    Para registrar o endpoint: https://dashboard.stripe.com/webhooks
    Para dev local com assinatura: stripe listen --forward-to localhost:8081/pagamentos/stripe-webhook/
    """
    import json
    import logging

    logger = logging.getLogger(__name__)
    stripe.api_key = settings.STRIPE_SECRET_KEY

    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if webhook_secret:
        # Verifica assinatura (dev com Stripe CLI ou produção)
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except ValueError:
            return {'status': 400, 'error': 'Payload inválido'}
        except stripe.error.SignatureVerificationError:
            return {'status': 400, 'error': 'Assinatura inválida'}
    elif settings.DEBUG:
        # Dev sem Stripe CLI: aceita sem assinatura, loga aviso
        logger.warning(
            'STRIPE_WEBHOOK_SECRET não configurado. '
            'Processando webhook sem verificação de assinatura (apenas em DEBUG).'
        )
        try:
            event = json.loads(payload)
        except (ValueError, TypeError):
            return {'status': 400, 'error': 'Payload inválido'}
    else:
        # Produção sem secret: bloqueia
        return {'status': 400, 'error': 'STRIPE_WEBHOOK_SECRET não configurado'}

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        confirmar_pagamento_stripe(session['id'])

    return {'status': 200, 'message': 'Webhook processado'}


# =============================================================================
# Mock (simulação para desenvolvimento)
# =============================================================================

def _criar_pagamento_mock(pedido):
    """
    Simula um pagamento para desenvolvimento/testes.
    """
    mock_id = f'mock_pi_{uuid.uuid4().hex[:16]}'
    valor_total = _to_money_2(pedido.total)

    pagamento = Pagamento.objects.create(
        pedido=pedido,
        gateway='mock',
        stripe_payment_intent_id=mock_id,
        valor=valor_total,
        status='pendente',
        dados_resposta={'mock_id': mock_id, 'mensagem': 'Pagamento simulado'},
    )

    pedido.stripe_payment_intent_id = mock_id
    pedido.save()

    return {
        'pagamento': pagamento,
        'checkout_url': None,
        'client_secret': mock_id,
        'gateway': 'mock',
    }


def confirmar_pagamento_mock(pagamento):
    """
    Confirma um pagamento mock (simula sucesso).
    """
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
