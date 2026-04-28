# =============================================================================
# apps/pedidos/geocoding.py - Reverse geocoding via Nominatim (OpenStreetMap)
#
# Por que backend (e não fetch direto do navegador)?
# - Política do Nominatim exige User-Agent identificável; navegador manda UA
#   genérico e fica indistinguível de scrapers, levando a IP ban silencioso.
# - Centraliza ponto de cache: requisições repetidas (mesmo prédio, mesmo
#   quarteirão) viram cache hit e não tocam o serviço externo.
# - Permite trocar provedor (Google Maps, Mapbox) no futuro sem mexer no front.
# =============================================================================

import requests
from django.core.cache import cache


NOMINATIM_URL = 'https://nominatim.openstreetmap.org/reverse'
USER_AGENT = 'CardapioOnline/1.0 (contato@cardapio-online.com.br)'
CACHE_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 dias
COORD_PRECISION = 5  # ~1.1 metro — agrupa requests do mesmo prédio


def _validar_coords_brasil(lat, lng):
    """Brasil aproximadamente: lat entre -35 e 6, lng entre -75 e -30."""
    if not (-35 <= lat <= 6):
        return False
    if not (-75 <= lng <= -30):
        return False
    return True


def _cache_key(lat, lng):
    """Arredonda coordenadas para agrupar pontos próximos no mesmo cache key."""
    return f'geocode:{round(lat, COORD_PRECISION)}:{round(lng, COORD_PRECISION)}'


def _consultar_nominatim(lat, lng):
    """Faz a chamada HTTP ao Nominatim. Retorna dict da API ou None em erro."""
    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                'lat': lat,
                'lon': lng,
                'format': 'json',
                'addressdetails': 1,
                'accept-language': 'pt-BR,pt',
            },
            headers={'User-Agent': USER_AGENT},
            timeout=8,
        )
        if response.status_code != 200:
            return None
        return response.json()
    except requests.exceptions.RequestException:
        return None


def formatar_endereco_resposta(address):
    """
    Monta a string de endereço final a partir do dict 'address' do Nominatim.

    Campos disponíveis no Nominatim (nem todos vêm em toda resposta):
    - road             → "Avenida Paulista"
    - house_number     → "1578"  (frequentemente AUSENTE em zonas residenciais)
    - neighbourhood    → "Bela Vista"
    - suburb           → "Bela Vista" (fallback de neighbourhood)
    - quarter          → bairro alternativo
    - city / town / village / municipality
    - state            → "São Paulo"
    - postcode         → "01310-200"
    - country          → "Brasil"

    Trade-off de UX:
    - Endereço LONGO (rua + número + bairro + cidade + estado) → ótimo para
      conferência mas polui a UI do checkout.
    - Endereço CURTO (rua + bairro) → limpo, mas usuário precisa confiar que o
      sistema "entendeu" a localização certa.

    Retorne uma string. Se nada útil for encontrado, retorne string vazia.
    """
    # TODO(usuário): implementar a montagem do endereço aqui (ver bloco abaixo)
    #
    # Sugestão de variáveis úteis já extraídas:
    rua = address.get('road') or ''
    numero = address.get('house_number') or ''
    bairro = address.get('neighbourhood') or address.get('suburb') or address.get('quarter') or ''
    cidade = address.get('city') or address.get('town') or address.get('village') or address.get('municipality') or ''
    estado = address.get('state') or ''

    # ▼▼▼ AJUSTE AQUI conforme a decisão de UX (ver docstring acima) ▼▼▼
    # Default atual: "Rua, Número, Bairro, Cidade" — degrada bem quando
    # number/bairro estão ausentes. Se quiser estado, postcode etc., adicione.
    partes = []
    if rua:
        partes.append(f'{rua}, {numero}' if numero else rua)
    if bairro:
        partes.append(bairro)
    if cidade:
        partes.append(cidade)
    return ', '.join(partes)
    # ▲▲▲ FIM ▲▲▲


def reverse_geocode(lat, lng):
    """
    Converte coordenadas em endereço legível.

    Retorna dict:
        {'valid': bool, 'endereco': str, 'erro': str|None, 'raw': dict|None}

    Estratégia:
    1. Valida que (lat, lng) está dentro do Brasil (evita gastar request).
    2. Consulta cache (chave arredondada para agrupar pontos próximos).
    3. Se cache miss, chama Nominatim e cacheia o resultado por 7 dias.
    4. Formata endereço via formatar_endereco_resposta().
    """
    if not _validar_coords_brasil(lat, lng):
        return {
            'valid': False,
            'endereco': '',
            'erro': 'Coordenadas fora do Brasil.',
            'raw': None,
        }

    key = _cache_key(lat, lng)
    cached = cache.get(key)
    if cached is not None:
        return cached

    data = _consultar_nominatim(lat, lng)
    if not data or 'address' not in data:
        # NÃO cacheia falha (pode ser indisponibilidade temporária do Nominatim)
        return {
            'valid': False,
            'endereco': '',
            'erro': 'Serviço de endereço indisponível. Tente novamente.',
            'raw': None,
        }

    endereco = formatar_endereco_resposta(data['address'])
    if not endereco:
        endereco = data.get('display_name', '')

    resultado = {
        'valid': bool(endereco),
        'endereco': endereco,
        'erro': None if endereco else 'Não foi possível identificar o endereço.',
        'raw': data['address'],
    }
    cache.set(key, resultado, CACHE_TTL_SECONDS)
    return resultado
