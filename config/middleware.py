# =============================================================================
# config/middleware.py - Middlewares do projeto
#
# 1. HtmxMiddleware: Garante redirects corretos com HTMX hx-boost.
# 2. TenantMiddleware: Identifica o tenant (restaurante) pelo subdomínio.
# =============================================================================

from django.conf import settings
from django.http import Http404, HttpResponse

from apps.core.algorithms import cache_restaurante


class HtmxMiddleware:
    """
    Converte redirects Django (302) em HX-Redirect para requests HTMX.

    Sem este middleware: HTMX segue o redirect via AJAX mas a URL do browser
    não atualiza corretamente.
    Com este middleware: HTMX recebe HX-Redirect e faz navegação client-side,
    atualizando a URL do browser.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Só intercepta se for request HTMX com redirect (3xx)
        if (
            request.headers.get('HX-Request') == 'true'
            and 300 <= response.status_code < 400
            and 'Location' in response
        ):
            redirect_url = response['Location']
            new_response = HttpResponse(status=200)
            new_response['HX-Redirect'] = redirect_url
            return new_response

        return response


class TenantMiddleware:
    """
    Middleware que extrai o subdomínio da requisição HTTP e associa
    o estabelecimento correspondente ao objeto request.

    Otimização com Tabela Hash (Cap. 5):
    - Cacheia o tenant por subdomínio para evitar query ao banco a cada request.
    - Sem cache: cada requisição = 1 query SQL → O(log n) no banco
    - Com cache: lookup O(1) no dicionário em memória

    Se nenhum subdomínio for encontrado (ex: acesso pelo domínio raiz),
    request.estabelecimento será None (permite acesso a páginas genéricas).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _buscar_tenant(self, subdominio):
        """
        Busca tenant com cache via Tabela Hash (Cap. 5).

        Primeiro tenta o cache O(1). Se miss, busca no banco O(log n)
        e armazena no cache para próximas requisições.
        """
        cache_key = f"tenant:{subdominio}"
        tenant = cache_restaurante.get(cache_key)
        if tenant is not None:
            return tenant

        from apps.restaurantes.models import Restaurante
        try:
            tenant = Restaurante.objects.get(
                subdominio=subdominio,
                ativo=True
            )
            cache_restaurante.set(cache_key, tenant)
            return tenant
        except Restaurante.DoesNotExist:
            # Cacheia o "miss" também para evitar queries repetidas
            cache_restaurante.set(cache_key, False)
            return None

    def __call__(self, request):
        host = request.META.get('HTTP_HOST', '').split(':')[0]
        base_domain = settings.BASE_DOMAIN

        request.restaurante = None
        request.estabelecimento = None

        if host.endswith(f'.{base_domain}'):
            subdominio = host.replace(f'.{base_domain}', '').strip('.')
            if subdominio and subdominio != 'www':
                tenant = self._buscar_tenant(subdominio)
                if tenant:
                    request.restaurante = tenant
                    request.estabelecimento = tenant

        if settings.DEBUG and request.estabelecimento is None:
            sub_param = request.GET.get('estabelecimento') or request.GET.get('restaurante')
            if sub_param:
                tenant = self._buscar_tenant(sub_param)
                if tenant:
                    request.restaurante = tenant
                    request.estabelecimento = tenant

        response = self.get_response(request)
        return response
