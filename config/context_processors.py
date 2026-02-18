# =============================================================================
# config/context_processors.py - Context processors customizados
#
# Disponibiliza variáveis globais em todos os templates do projeto.
# =============================================================================

from django.conf import settings


def restaurante_context(request):
    """
    Adiciona o restaurante atual (identificado pelo middleware multi-tenant)
    e configurações úteis ao contexto de todos os templates.

    Variáveis disponíveis nos templates:
    - {{ restaurante_atual }}: instância do Restaurante ou None
    - {{ stripe_public_key }}: chave pública do Stripe para o frontend
    - {{ base_domain }}: domínio base do sistema
    """
    return {
        'restaurante_atual': getattr(request, 'restaurante', None),
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'base_domain': settings.BASE_DOMAIN,
    }
