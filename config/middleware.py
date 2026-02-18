# =============================================================================
# config/middleware.py - Middleware multi-tenant por subdomínio
#
# Identifica o restaurante atual com base no subdomínio da requisição.
# Exemplo: pizzaria1.meusistema.com → restaurante com subdominio="pizzaria1"
# O restaurante identificado fica disponível em request.restaurante.
# =============================================================================

from django.conf import settings
from django.http import Http404


class TenantMiddleware:
    """
    Middleware que extrai o subdomínio da requisição HTTP e associa
    o restaurante correspondente ao objeto request.

    Se nenhum subdomínio for encontrado (ex: acesso pelo domínio raiz),
    request.restaurante será None (permite acesso a páginas genéricas).
    """

    def __init__(self, get_response):
        """Inicializa o middleware com a função de resposta."""
        self.get_response = get_response

    def __call__(self, request):
        """
        Processa cada requisição para identificar o tenant (restaurante).

        Fluxo:
        1. Extrai o host da requisição (ex: 'pizzaria1.meusistema.com')
        2. Remove a porta se houver (ex: 'localhost:8000' → 'localhost')
        3. Verifica se há subdomínio válido
        4. Busca o restaurante no banco pelo subdomínio
        5. Atribui a request.restaurante
        """
        host = request.META.get('HTTP_HOST', '').split(':')[0]
        base_domain = settings.BASE_DOMAIN

        # Inicializa como None (sem restaurante identificado)
        request.restaurante = None

        # Verifica se o host possui subdomínio em relação ao domínio base
        if host.endswith(f'.{base_domain}'):
            subdominio = host.replace(f'.{base_domain}', '').strip('.')
            if subdominio and subdominio != 'www':
                # Importação tardia para evitar importação circular
                from apps.restaurantes.models import Restaurante
                try:
                    request.restaurante = Restaurante.objects.get(
                        subdominio=subdominio,
                        ativo=True
                    )
                except Restaurante.DoesNotExist:
                    pass  # Restaurante não encontrado; request.restaurante = None

        # Para desenvolvimento local, permite identificar via query param
        # Ex: localhost:8000/?restaurante=pizzaria1
        if settings.DEBUG and request.restaurante is None:
            sub_param = request.GET.get('restaurante')
            if sub_param:
                from apps.restaurantes.models import Restaurante
                try:
                    request.restaurante = Restaurante.objects.get(
                        subdominio=sub_param,
                        ativo=True
                    )
                except Restaurante.DoesNotExist:
                    pass

        response = self.get_response(request)
        return response
