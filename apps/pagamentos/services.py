# =============================================================================
# apps/pagamentos/services.py - Serviços de pagamento (Stripe e Mock)
#
# Camada de serviço que abstrai a lógica de pagamento.
# Se USE_STRIPE_MOCK=True no .env, usa simulação local.
# Se USE_STRIPE_MOCK=False, usa a API real do Stripe.
#
# ============ COMO ALTERNAR ENTRE STRIPE E MOCK ============
# No arquivo .env, altere a variável USE_STRIPE_MOCK:
#   USE_STRIPE_MOCK=True   → Usa mock (desenvolvimento)
#   USE_STRIPE_MOCK=False  → Usa Stripe real (produção)
# Também configure STRIPE_SECRET_KEY e STRIPE_PUBLIC_KEY no .env.
# =============================================================================

import uuid
from decimal import Decimal
from django.conf import settings
from .models import Pagamento


def criar_pagamento(pedido):
    """
    Cria uma sessão/intent de pagamento para um pedido.
    Reutiliza pagamento pendente existente (idempotencia).

    Se USE_STRIPE_MOCK=True, simula um pagamento local.
    Se USE_STRIPE_MOCK=False, cria um Payment Intent real no Stripe.

    Args:
        pedido: Instância de Pedido com total calculado.

    Returns:
        dict com:
        - 'pagamento': Instância do model Pagamento
        - 'client_secret': Client secret do Stripe (ou mock ID)
        - 'gateway': 'stripe' ou 'mock'
    """
    # Reutiliza pagamento pendente existente (evita duplicatas ao recarregar pagina)
    pagamento_existente = Pagamento.objects.filter(
        pedido=pedido, status='pendente'
    ).first()

    if pagamento_existente:
        client_secret = pagamento_existente.stripe_payment_intent_id
        if pagamento_existente.gateway == 'stripe':
            client_secret = (pagamento_existente.dados_resposta or {}).get(
                'client_secret', pagamento_existente.stripe_payment_intent_id
            )
        return {
            'pagamento': pagamento_existente,
            'client_secret': client_secret,
            'gateway': pagamento_existente.gateway,
        }

    if settings.USE_STRIPE_MOCK:
        return _criar_pagamento_mock(pedido)
    else:
        return _criar_pagamento_stripe(pedido)


def _criar_pagamento_stripe(pedido):
    """
    Cria um Payment Intent real no Stripe.

    O client_secret retornado é usado pelo frontend (Stripe.js)
    para confirmar o pagamento no lado do cliente.
    """
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Stripe trabalha com centavos (int), então multiplica por 100
    valor_centavos = int(pedido.total * 100)

    # Cria o Payment Intent no Stripe
    intent = stripe.PaymentIntent.create(
        amount=valor_centavos,
        currency='brl',
        metadata={
            'pedido_id': str(pedido.id),
            'restaurante_id': str(pedido.restaurante_id),
            'cliente_nome': pedido.cliente_nome,
        },
    )

    # Registra o pagamento no banco
    pagamento = Pagamento.objects.create(
        pedido=pedido,
        gateway='stripe',
        stripe_payment_intent_id=intent.id,
        valor=pedido.total,
        status='pendente',
        dados_resposta={'payment_intent_id': intent.id, 'client_secret': intent.client_secret},
    )

    # Salva o ID no pedido também
    pedido.stripe_payment_intent_id = intent.id
    pedido.save()

    return {
        'pagamento': pagamento,
        'client_secret': intent.client_secret,
        'gateway': 'stripe',
    }


def _criar_pagamento_mock(pedido):
    """
    Simula um pagamento para desenvolvimento/testes.

    Gera um ID fictício e retorna imediatamente.
    O pagamento pode ser "confirmado" via mock webhook ou
    automaticamente na view de confirmação.
    """
    mock_id = f'mock_pi_{uuid.uuid4().hex[:16]}'

    pagamento = Pagamento.objects.create(
        pedido=pedido,
        gateway='mock',
        stripe_payment_intent_id=mock_id,
        valor=pedido.total,
        status='pendente',
        dados_resposta={'mock_id': mock_id, 'mensagem': 'Pagamento simulado'},
    )

    pedido.stripe_payment_intent_id = mock_id
    pedido.save()

    return {
        'pagamento': pagamento,
        'client_secret': mock_id,
        'gateway': 'mock',
    }


def confirmar_pagamento_mock(pagamento):
    """
    Confirma um pagamento mock (simula sucesso).

    Usado na view de confirmação quando USE_STRIPE_MOCK=True.
    """
    pagamento.status = 'aprovado'
    pagamento.dados_resposta = {
        **(pagamento.dados_resposta or {}),
        'confirmado': True,
        'mensagem': 'Pagamento mock confirmado com sucesso',
    }
    pagamento.save()

    # Marca o pedido como pago
    pedido = pagamento.pedido
    pedido.pago = True
    pedido.save()

    return pagamento


def processar_webhook_stripe(payload, sig_header):
    """
    Processa webhook do Stripe para confirmar pagamentos.

    Chamado pelo endpoint POST /api/pagamentos/webhook/.

    Args:
        payload: Corpo da requisição (bytes)
        sig_header: Header Stripe-Signature

    Returns:
        dict com status do processamento

    Fluxo:
    1. Verifica a assinatura do webhook
    2. Extrai o evento (payment_intent.succeeded, etc.)
    3. Atualiza o pagamento e o pedido correspondente
    """
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return {'error': 'Payload inválido', 'status': 400}
    except stripe.error.SignatureVerificationError:
        return {'error': 'Assinatura inválida', 'status': 400}

    # Processa o evento
    if event['type'] == 'payment_intent.succeeded':
        intent = event['data']['object']
        payment_intent_id = intent['id']

        try:
            pagamento = Pagamento.objects.get(
                stripe_payment_intent_id=payment_intent_id
            )
            pagamento.status = 'aprovado'
            pagamento.dados_resposta = intent
            pagamento.save()

            # Marca pedido como pago
            pedido = pagamento.pedido
            pedido.pago = True
            pedido.save()

            return {'status': 200, 'message': 'Pagamento confirmado'}
        except Pagamento.DoesNotExist:
            return {'error': 'Pagamento não encontrado', 'status': 404}

    elif event['type'] == 'payment_intent.payment_failed':
        intent = event['data']['object']
        payment_intent_id = intent['id']

        try:
            pagamento = Pagamento.objects.get(
                stripe_payment_intent_id=payment_intent_id
            )
            pagamento.status = 'recusado'
            pagamento.dados_resposta = intent
            pagamento.save()

            return {'status': 200, 'message': 'Pagamento marcado como recusado'}
        except Pagamento.DoesNotExist:
            return {'error': 'Pagamento não encontrado', 'status': 404}

    return {'status': 200, 'message': f'Evento {event["type"]} recebido'}
