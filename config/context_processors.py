# =============================================================================
# config/context_processors.py - Context processors customizados
#
# Disponibiliza variáveis globais em todos os templates do projeto.
# =============================================================================

from django.conf import settings


def estabelecimento_context(request):
    """
    Adiciona o estabelecimento atual (identificado pelo middleware multi-tenant)
    e configurações úteis ao contexto de todos os templates.

    Variáveis disponíveis nos templates:
    - {{ estabelecimento_atual }}: instância do tenant ou None
    - {{ restaurante_atual }}: alias legado para compatibilidade
    - {{ mercadopago_public_key }}: chave pública do Mercado Pago para o frontend
    - {{ base_domain }}: domínio base do sistema
    - {{ carrinho_total_itens }}: quantidade total de itens no carrinho da sessão
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

    return {
        'estabelecimento_atual': tenant,
        'restaurante_atual': tenant,
        'carrinho_total_itens': total_itens,
        'base_domain': settings.BASE_DOMAIN,
    }


def restaurante_context(request):
    """Alias legado do context processor para retrocompatibilidade."""
    return estabelecimento_context(request)
