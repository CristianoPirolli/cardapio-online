# =============================================================================
# apps/pagamentos/services.py - Serviços de pagamento (BB PIX e Mock)
#
# Camada de serviço que abstrai a lógica de pagamento.
# Se USE_PIX_MOCK=True no .env, usa simulação local.
# Se USE_PIX_MOCK=False, usa a API PIX do Banco do Brasil.
#
# ============ COMO ALTERNAR ENTRE PIX REAL E MOCK ============
# No arquivo .env, altere a variável USE_PIX_MOCK:
#   USE_PIX_MOCK=True   -> Usa mock (desenvolvimento)
#   USE_PIX_MOCK=False  -> Usa BB PIX real (produção)
# Também configure as variáveis BB_PIX_* no .env.
# =============================================================================

import uuid
from decimal import Decimal, ROUND_HALF_UP
import ipaddress
from urllib.parse import urlparse
from django.conf import settings
from .models import Pagamento


def criar_pagamento(pedido):
    """
    Cria uma sessão/intent de pagamento para um pedido.
    Reutiliza pagamento pendente existente (idempotencia).

    Se USE_PIX_MOCK=True, simula um pagamento local.
    Se USE_PIX_MOCK=False, cria uma cobrança PIX no Banco do Brasil.

    Returns:
        dict com:
        - 'pagamento': Instância do model Pagamento
        - 'checkout_url': URL de checkout (ou None)
        - 'client_secret': ID técnico para compatibilidade de API
        - 'gateway': 'bb_pix' ou 'mock'
    """
    pagamento_existente = Pagamento.objects.filter(
        pedido=pedido, status='pendente'
    ).first()

    if pagamento_existente:
        dados = pagamento_existente.dados_resposta or {}
        pix_copia_cola = dados.get('pix_copia_cola')

        # Se for gateway real sem payload PIX (fluxo antigo), gera novo PIX.
        if pagamento_existente.gateway == 'bb_pix' and not pix_copia_cola:
            pagamento_existente.status = 'recusado'
            pagamento_existente.save(update_fields=['status', 'atualizado_em'])
        else:
            return {
                'pagamento': pagamento_existente,
                'checkout_url': dados.get('checkout_url'),
                'client_secret': pagamento_existente.stripe_payment_intent_id,
                'gateway': pagamento_existente.gateway,
                'pix_qr_code_base64': dados.get('pix_qr_code_base64'),
                'pix_copia_cola': pix_copia_cola,
                'pix_ticket_url': dados.get('pix_ticket_url'),
                'expira_em': dados.get('expira_em'),
            }

    if settings.USE_PIX_MOCK:
        return _criar_pagamento_mock(pedido)
    else:
        return _criar_pagamento_bb_pix(pedido)


def _build_absolute_url(path):
    base = getattr(settings, 'SITE_URL', '').rstrip('/')
    if base:
        return f'{base}{path}'
    return f'http://localhost{path}'


def _to_money_2(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _is_public_url(url):
    try:
        parsed = urlparse(url or '')
    except Exception:
        return False

    if parsed.scheme not in ('http', 'https'):
        return False

    host = (parsed.hostname or '').lower()
    if not host or host in ('localhost', '127.0.0.1', '::1'):
        return False

    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback:
            return False
    except ValueError:
        pass

    return True


# =============================================================================
# Banco do Brasil PIX
# =============================================================================

def _get_bb_access_token():
    """
    Obtém access token OAuth2 do Banco do Brasil (Client Credentials).

    TODO: Implementar quando as credenciais BB estiverem configuradas.
    Documentação: https://developers.bb.com.br/apis-e-sdks/integracao/oauth-client-credentials

    Variáveis necessárias no .env:
      BB_PIX_CLIENT_ID     - Client ID da aplicação no portal BB Developers
      BB_PIX_CLIENT_SECRET - Client Secret da aplicação
      BB_PIX_ENV           - 'sandbox' ou 'production'
    """
    # TODO: descomentar e implementar quando as credenciais estiverem disponíveis
    # import requests, base64
    # env = settings.BB_PIX_ENV
    # base_url = (
    #     'https://oauth.hm.bb.com.br'
    #     if env == 'sandbox'
    #     else 'https://oauth.bb.com.br'
    # )
    # credentials = base64.b64encode(
    #     f'{settings.BB_PIX_CLIENT_ID}:{settings.BB_PIX_CLIENT_SECRET}'.encode()
    # ).decode()
    # response = requests.post(
    #     f'{base_url}/oauth/token',
    #     headers={
    #         'Authorization': f'Basic {credentials}',
    #         'Content-Type': 'application/x-www-form-urlencoded',
    #     },
    #     data={'grant_type': 'client_credentials', 'scope': 'cob.write cob.read pix.read'},
    # )
    # response.raise_for_status()
    # return response.json()['access_token']
    raise NotImplementedError(
        'Integração BB PIX não implementada. '
        'Configure BB_PIX_* no .env ou ative USE_PIX_MOCK=True.'
    )


def _criar_pagamento_bb_pix(pedido):
    """
    Cria uma cobrança PIX imediata (COB) no Banco do Brasil.

    TODO: Implementar quando as credenciais BB estiverem disponíveis.
    Documentação: https://developers.bb.com.br/apis-e-sdks/api-pix

    Variáveis necessárias no .env:
      BB_PIX_CLIENT_ID     - Client ID da aplicação
      BB_PIX_CLIENT_SECRET - Client Secret da aplicação
      BB_PIX_KEY           - Chave PIX do recebedor (CNPJ, CPF, email, tel. ou aleatória)
      BB_PIX_APP_KEY       - gw-dev-app-key (portal de developers do BB)
      BB_PIX_ENV           - 'sandbox' ou 'production'
    """
    # TODO: descomentar e adaptar quando as credenciais BB estiverem configuradas
    # import requests
    # valor_total = _to_money_2(pedido.total)
    # txid = uuid.uuid4().hex[:35]  # txid: máximo 35 chars alfanumérico
    #
    # access_token = _get_bb_access_token()
    # env = settings.BB_PIX_ENV
    # base_url = (
    #     'https://api.hm.bb.com.br'
    #     if env == 'sandbox'
    #     else 'https://api.bb.com.br'
    # )
    #
    # payload = {
    #     'calendario': {'expiracao': 1800},  # expira em 30 minutos
    #     'valor': {'original': str(valor_total)},
    #     'chave': settings.BB_PIX_KEY,
    #     'solicitacaoPagador': f'Pedido #{pedido.id} - {pedido.restaurante.nome}',
    #     'infoAdicionais': [
    #         {'nome': 'Pedido', 'valor': str(pedido.id)},
    #     ],
    # }
    #
    # webhook_url = _build_absolute_url('/api/pagamentos/webhook/')
    # if _is_public_url(webhook_url):
    #     # Webhook no BB exige certificado mTLS — configurar no portal
    #     payload['webhookUrl'] = webhook_url
    #
    # headers = {
    #     'Authorization': f'Bearer {access_token}',
    #     'Content-Type': 'application/json',
    # }
    # response = requests.put(
    #     f'{base_url}/pix/v2/cob/{txid}?gw-dev-app-key={settings.BB_PIX_APP_KEY}',
    #     json=payload,
    #     headers=headers,
    # )
    # if not response.ok:
    #     raise RuntimeError(f'Falha ao criar cobrança PIX no BB: {response.text}')
    #
    # data = response.json()
    # pix_copia_cola = data.get('pixCopiaECola')
    # pix_ticket_url = data.get('location')
    # expira_em = data.get('calendario', {}).get('criacao')
    #
    # pagamento = Pagamento.objects.create(
    #     pedido=pedido,
    #     gateway='bb_pix',
    #     stripe_payment_intent_id=txid,
    #     valor=valor_total,
    #     status='pendente',
    #     dados_resposta={
    #         'txid': txid,
    #         'pix_copia_cola': pix_copia_cola,
    #         'pix_ticket_url': pix_ticket_url,
    #         'expira_em': expira_em,
    #         'raw': data,
    #     },
    # )
    # pedido.stripe_payment_intent_id = txid
    # pedido.save()
    #
    # return {
    #     'pagamento': pagamento,
    #     'checkout_url': None,
    #     'client_secret': txid,
    #     'gateway': 'bb_pix',
    #     'pix_copia_cola': pix_copia_cola,
    #     'pix_ticket_url': pix_ticket_url,
    #     'expira_em': expira_em,
    # }
    raise NotImplementedError(
        'Integração BB PIX não implementada. '
        'Ative USE_PIX_MOCK=True no .env para usar simulação.'
    )


def processar_webhook_bb(request):
    """
    Processa webhook do Banco do Brasil para confirmar pagamentos PIX.

    TODO: Implementar quando BB PIX estiver configurado.
    O BB envia notificações via POST com lista de PIX confirmados.
    Requer certificado mTLS configurado no servidor para produção.

    Documentação: https://developers.bb.com.br/apis-e-sdks/api-pix#section/Webhooks

    Payload esperado:
    {
      "pix": [
        {
          "endToEndId": "Exxxxxxxxx",
          "txid": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
          "valor": "100.00",
          "horario": "2023-01-01T12:00:00.000Z",
          "infoPagador": "..."
        }
      ]
    }
    """
    # TODO: descomentar e implementar quando BB PIX estiver configurado
    # data = request.data if isinstance(request.data, dict) else {}
    # pix_list = data.get('pix', [])
    #
    # for pix_item in pix_list:
    #     txid = pix_item.get('txid')
    #     if not txid:
    #         continue
    #
    #     pagamento = Pagamento.objects.filter(
    #         stripe_payment_intent_id=txid
    #     ).first()
    #     if not pagamento:
    #         continue
    #
    #     pagamento.status = 'aprovado'
    #     pagamento.dados_resposta = {
    #         **(pagamento.dados_resposta or {}),
    #         'bb_pix_confirmado': pix_item,
    #     }
    #     pagamento.save()
    #
    #     pedido = pagamento.pedido
    #     pedido.pago = True
    #     if pedido.status == 'aguardando':
    #         pedido.status = 'recebido'
    #     pedido.save()

    return {'status': 200, 'message': 'Webhook BB PIX recebido (implementação pendente)'}


# =============================================================================
# Mock (simulação para desenvolvimento)
# =============================================================================

def _criar_pagamento_mock(pedido):
    """
    Simula um pagamento para desenvolvimento/testes.
    Gera um ID fictício e retorna imediatamente.
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
    Usado na view de confirmação quando USE_PIX_MOCK=True.
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
