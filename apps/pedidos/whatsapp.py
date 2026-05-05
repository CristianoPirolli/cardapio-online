import logging
from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class WhatsAppAdapter:
    """
    Interface base para provedores WhatsApp.

    Implementar este contrato para adicionar um novo provedor:
    - ZAPIAdapter: z-api.io
    - TwilioWhatsAppAdapter: twilio.com/whatsapp
    - MetaCloudAdapter: developers.facebook.com/docs/whatsapp

    O provedor ativo é configurado via settings.WHATSAPP_ADAPTER.
    """

    def send(self, telefone: str, mensagem: str) -> bool:
        """
        Envia mensagem WhatsApp.

        Args:
            telefone: Número do destinatário (qualquer formato BR, ex: '11999999999').
            mensagem: Texto da mensagem.

        Returns:
            True se enviado com sucesso, False caso contrário.
        """
        raise NotImplementedError


class LogWhatsAppAdapter(WhatsAppAdapter):
    """Adapter de desenvolvimento — loga a mensagem sem enviar."""

    def send(self, telefone: str, mensagem: str) -> bool:
        logger.info('[WhatsApp FAKE] Para %s: %s', telefone, mensagem)
        return True


def get_whatsapp_adapter() -> WhatsAppAdapter:
    """Retorna a instância do adapter configurado em settings.WHATSAPP_ADAPTER."""
    adapter_class = import_string(
        getattr(settings, 'WHATSAPP_ADAPTER', 'apps.pedidos.whatsapp.LogWhatsAppAdapter')
    )
    return adapter_class()
