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
    - {{ stripe_public_key }}: chave pública do Stripe para o frontend
    - {{ base_domain }}: domínio base do sistema
    - {{ carrinho_total_itens }}: quantidade total de itens no carrinho da sessão
    """
    tenant = getattr(request, 'estabelecimento', None) or getattr(request, 'restaurante', None)
    carrinho = request.session.get('carrinho', {'itens': {}})
    total_itens = sum(
        int(item.get('quantidade', 0))
        for item in carrinho.get('itens', {}).values()
    )
    return {
        'estabelecimento_atual': tenant,
        'restaurante_atual': tenant,
        'carrinho_total_itens': total_itens,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'base_domain': settings.BASE_DOMAIN,
    }


def restaurante_context(request):
    """Alias legado do context processor para retrocompatibilidade."""
    return estabelecimento_context(request)
