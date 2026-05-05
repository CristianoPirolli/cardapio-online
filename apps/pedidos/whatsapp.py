import re
import logging
import requests
from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


def _normalizar_telefone(telefone: str) -> str:
    """Converte qualquer formato BR para E.164 sem '+' (ex: '5511999999999')."""
    digits = re.sub(r'\D', '', telefone)
    if not digits.startswith('55'):
        digits = '55' + digits
    return digits


class WhatsAppAdapter:
    """
    Interface base para provedores WhatsApp.

    O provedor ativo é configurado via settings.WHATSAPP_ADAPTER.
    """

    def send(self, telefone: str, mensagem: str) -> bool:
        raise NotImplementedError


class LogWhatsAppAdapter(WhatsAppAdapter):
    """Adapter de desenvolvimento — loga a mensagem sem enviar."""

    def send(self, telefone: str, mensagem: str) -> bool:
        logger.info('[WhatsApp FAKE] Para %s: %s', telefone, mensagem)
        return True


class EvolutionAPIAdapter(WhatsAppAdapter):
    """
    Envia mensagens via Evolution API (self-hosted, open source).

    Configuração necessária em settings/env:
        EVOLUTION_API_URL   — URL base do servidor (ex: https://minha-api.railway.app)
        EVOLUTION_API_KEY   — Chave de autenticação definida na Evolution API
        EVOLUTION_INSTANCE  — Nome da instância criada ao escanear o QR Code
    """

    def __init__(self):
        self.base_url = getattr(settings, 'EVOLUTION_API_URL', '').rstrip('/')
        self.api_key = getattr(settings, 'EVOLUTION_API_KEY', '')
        self.instance = getattr(settings, 'EVOLUTION_INSTANCE', '')

    def send(self, telefone: str, mensagem: str) -> bool:
        if not all([self.base_url, self.api_key, self.instance]):
            logger.error(
                '[EvolutionAPI] Configuração incompleta. '
                'Verifique EVOLUTION_API_URL, EVOLUTION_API_KEY e EVOLUTION_INSTANCE.'
            )
            return False

        numero = _normalizar_telefone(telefone)
        url = f'{self.base_url}/message/sendText/{self.instance}'

        try:
            response = requests.post(
                url,
                json={'number': numero, 'textMessage': {'text': mensagem}},
                headers={'apikey': self.api_key},
                timeout=10,
            )
            if response.status_code == 201:
                return True
            logger.error(
                '[EvolutionAPI] Erro HTTP %s ao enviar para %s: %s',
                response.status_code, numero, response.text[:200],
            )
            return False
        except requests.Timeout:
            logger.error('[EvolutionAPI] Timeout ao enviar para %s', numero)
            return False
        except requests.RequestException as exc:
            logger.error('[EvolutionAPI] Erro de conexão ao enviar para %s: %s', numero, exc)
            return False


def get_whatsapp_adapter() -> WhatsAppAdapter:
    """Retorna a instância do adapter configurado em settings.WHATSAPP_ADAPTER."""
    adapter_class = import_string(
        getattr(settings, 'WHATSAPP_ADAPTER', 'apps.pedidos.whatsapp.LogWhatsAppAdapter')
    )
    return adapter_class()
