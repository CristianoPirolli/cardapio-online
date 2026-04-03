# =============================================================================
# config/context_processors.py - Context processors customizados
#
# Disponibiliza variáveis globais em todos os templates do projeto.
# =============================================================================

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist


def estabelecimento_context(request):
    """
    Adiciona o estabelecimento atual (identificado pelo middleware multi-tenant)
    e configurações úteis ao contexto de todos os templates.

    Variáveis disponíveis nos templates:
    - {{ estabelecimento_atual }}: instância do tenant ou None
    - {{ restaurante_atual }}: alias legado para compatibilidade
    - {{ base_domain }}: domínio base do sistema
    - {{ carrinho_total_itens }}: quantidade total de itens no carrinho da sessão
    - {{ aguardando_confirmacao_count }}: pedidos aguardando confirmação PIX (painel)
    - {{ painel_pedidos_abertos_count }}: pedidos em aberto com pago=True (painel)
    """
    # Evita acessar a sessão em requests que não precisam (AJAX de status, etc.)
    if getattr(request, '_skip_context', False):
        return {}

    tenant = getattr(request, 'estabelecimento', None) or getattr(request, 'restaurante', None)

    # Calcula total de itens apenas se houver sessão com carrinho
    total_itens = 0
    if hasattr(request, 'session') and 'carrinho' in request.session:
        itens = request.session['carrinho'].get('itens', {})
        total_itens = sum(int(item.get('quantidade', 0)) for item in itens.values())

    pedidos_abertos_count = 0
    aguardando_confirmacao_count = 0
    if (
        getattr(request, 'user', None)
        and request.user.is_authenticated
        and request.path.startswith('/painel/')
    ):
        restaurante = getattr(request, 'restaurante', None)
        if not restaurante:
            try:
                restaurante = request.user.restaurante
            except ObjectDoesNotExist:
                restaurante = None

        if restaurante:
            # Import local para evitar acoplamento no carregamento inicial.
            from apps.pedidos.models import Pedido

            pedidos_abertos_count = Pedido.objects.filter(
                restaurante=restaurante,
                pago=True,
            ).exclude(
                status__in=['concluido', 'cancelado']
            ).count()

            aguardando_confirmacao_count = Pedido.objects.filter(
                restaurante=restaurante,
                status='aguardando_confirmacao',
            ).count()

    return {
        'estabelecimento_atual': tenant,
        'restaurante_atual': tenant,
        'carrinho_total_itens': total_itens,
        'painel_pedidos_abertos_count': pedidos_abertos_count,
        'aguardando_confirmacao_count': aguardando_confirmacao_count,
        'base_domain': settings.BASE_DOMAIN,
    }


def restaurante_context(request):
    """Alias legado do context processor para retrocompatibilidade."""
    return estabelecimento_context(request)
