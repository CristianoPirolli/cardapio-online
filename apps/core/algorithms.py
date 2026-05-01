# =============================================================================
# apps/core/algorithms.py - Algoritmos e Estruturas de Dados
#
# Implementações baseadas no livro "Entendendo Algoritmos"
# (Grokking Algorithms) de Aditya Y. Bhargava.
#
# Estruturas implementadas:
# 1. Tabelas Hash (Cap. 5) - Cache O(1) para lookups frequentes
# 2. Pesquisa em Largura / BFS (Cap. 6) - Grafo de status de pedidos
# 3. Dijkstra (Cap. 7) - Seleção otimizada de entregadores
# 4. Pesquisa Binária (Cap. 1) - Busca em faixas de preço
# 5. Recursão + Memoização (Cap. 3/8) - Cache de cálculos
# =============================================================================

import time
import bisect
from collections import deque
from decimal import Decimal
from heapq import heappush, heappop


# =============================================================================
# 1. TABELAS HASH (Cap. 5) - Cache com dicionários para lookup O(1)
#
# Livro: "Uma tabela hash mapeia chaves a valores... a busca é O(1)"
# Uso: Cache de restaurante, cardápio e lookups de produtos
# =============================================================================

class HashCache:
    """
    Cache em memória usando tabela hash (dicionário Python).

    Complexidade:
    - get: O(1) amortizado
    - set: O(1) amortizado
    - invalidate: O(1)

    Sem tabela hash: cada busca seria O(n) varrendo a lista.
    Com tabela hash: busca direta pela chave em O(1).

    O TTL (time-to-live) evita dados obsoletos sem precisar
    de invalidação manual.
    """

    def __init__(self, ttl_seconds=60):
        self._store = {}       # {chave: (valor, timestamp)}
        self._ttl = ttl_seconds

    def get(self, key):
        """Busca O(1). Retorna None se expirou ou não existe."""
        entry = self._store.get(key)
        if entry is None:
            return None
        value, timestamp = entry
        if time.time() - timestamp > self._ttl:
            del self._store[key]
            return None
        return value

    def set(self, key, value):
        """Inserção O(1)."""
        self._store[key] = (value, time.time())

    def invalidate(self, key):
        """Remoção O(1)."""
        self._store.pop(key, None)

    def invalidate_prefix(self, prefix):
        """Remove todas as chaves que começam com o prefixo. O(n) no pior caso."""
        keys_to_delete = [k for k in self._store if str(k).startswith(prefix)]
        for k in keys_to_delete:
            del self._store[k]

    def clear(self):
        """Limpa todo o cache."""
        self._store.clear()


# Instâncias globais de cache (uma por domínio de dados)
# TTL de 30s para dados que mudam pouco (cardápio, config)
# TTL de 10s para dados mais voláteis (status, disponibilidade)
cache_restaurante = HashCache(ttl_seconds=30)
cache_cardapio = HashCache(ttl_seconds=30)
cache_produtos = HashCache(ttl_seconds=10)


# =============================================================================
# 2. PESQUISA EM LARGURA / BFS (Cap. 6) - Grafo de transição de status
#
# Livro: "A pesquisa em largura encontra o caminho mais curto entre dois nós"
# Uso: Validar transições de status e encontrar caminho até status final
# =============================================================================

# Grafo de transições de pedido (lista de adjacência)
GRAFO_STATUS_PEDIDO = {
    'aguardando': ['aguardando_confirmacao', 'cancelado'],
    'aguardando_confirmacao': ['recebido', 'cancelado'],
    'recebido': ['preparo', 'cancelado'],
    'preparo': ['entrega', 'pronto_retirada', 'cancelado'],
    'entrega': ['concluido', 'cancelado'],
    'pronto_retirada': ['concluido', 'cancelado'],
    'concluido': [],
    'cancelado': [],
}

# Grafo de transições de entrega
GRAFO_STATUS_ENTREGA = {
    'aguardando': ['coletado', 'cancelado'],
    'coletado': ['em_transito', 'cancelado'],
    'em_transito': ['entregue', 'cancelado'],
    'entregue': [],
    'cancelado': [],
}


def bfs_caminho_mais_curto(grafo, origem, destino):
    """
    Pesquisa em Largura (BFS) para encontrar o caminho mais curto
    entre dois status no grafo de transições.

    Livro Cap. 6: "Primeiro, adicione todos os vizinhos à fila.
    Depois, para cada vizinho, adicione os vizinhos dele..."

    Complexidade: O(V + E) onde V = vértices, E = arestas
    Sem BFS: teríamos que testar todos os caminhos possíveis O(V!)

    Args:
        grafo: dict representando lista de adjacência
        origem: status atual
        destino: status desejado

    Returns:
        list: caminho mais curto [origem, ..., destino] ou [] se impossível
    """
    if origem == destino:
        return [origem]

    # Fila FIFO (First In, First Out) - essencial para BFS
    fila = deque()
    fila.append([origem])

    # Conjunto de visitados para evitar ciclos - lookup O(1)
    visitados = {origem}

    while fila:
        caminho = fila.popleft()
        nodo_atual = caminho[-1]

        for vizinho in grafo.get(nodo_atual, []):
            if vizinho in visitados:
                continue

            novo_caminho = caminho + [vizinho]

            if vizinho == destino:
                return novo_caminho

            visitados.add(vizinho)
            fila.append(novo_caminho)

    return []  # Não há caminho possível


def bfs_status_alcancaveis(grafo, origem):
    """
    Retorna todos os status alcançáveis a partir do status atual.
    Útil para mostrar ao usuário quais são os próximos passos possíveis.

    Complexidade: O(V + E)

    Returns:
        dict: {status: distância_em_passos}
    """
    distancias = {origem: 0}
    fila = deque([origem])

    while fila:
        atual = fila.popleft()
        for vizinho in grafo.get(atual, []):
            if vizinho not in distancias:
                distancias[vizinho] = distancias[atual] + 1
                fila.append(vizinho)

    return distancias




def proximo_status_para_concluir(status_atual):
    """
    Usa BFS para descobrir qual é o próximo passo no caminho mais curto
    até 'concluido'. Útil para sugerir a próxima ação ao restaurante.

    Returns:
        str ou None: próximo status ou None se impossível
    """
    caminho = bfs_caminho_mais_curto(GRAFO_STATUS_PEDIDO, status_atual, 'concluido')
    if len(caminho) >= 2:
        return caminho[1]
    return None


# =============================================================================
# 3. PESQUISA BINÁRIA (Cap. 1) - Busca eficiente em faixas de preço
#
# Livro: "Com a pesquisa binária, você chuta o meio... elimina metade"
# Busca linear: O(n) - Pesquisa binária: O(log n)
# =============================================================================



def produtos_na_faixa_preco(produtos_ordenados, preco_min, preco_max):
    """
    Encontra todos os produtos em uma faixa de preço usando pesquisa binária.

    Duas pesquisas binárias: uma para achar o início e outra para o fim.
    Complexidade: O(log n) para encontrar + O(k) para retornar k resultados.
    Busca linear seria O(n) sempre.
    """
    precos = [float(p.preco or 0) for p in produtos_ordenados]

    idx_inicio = bisect.bisect_left(precos, float(preco_min))
    idx_fim = bisect.bisect_right(precos, float(preco_max))

    return produtos_ordenados[idx_inicio:idx_fim]


# =============================================================================
# 5. RECURSÃO + MEMOIZAÇÃO (Cap. 3 e 8)
#
# Livro Cap. 3: "Recursão é quando uma função chama a si mesma"
# Livro Cap. 8: "Programação dinâmica: resolver subproblemas e cachear"
# =============================================================================



def calcular_subtotal_otimizado(itens_queryset):
    """
    Calcula o subtotal usando acumulação O(n) ao invés de múltiplas queries.

    Antes: self.itens.all() fazia uma query → O(n) no banco + O(n) no Python
    Agora: recebe queryset já carregado → O(n) apenas no Python (sem query extra)
    """
    return sum(
        (item.quantidade * item.preco_unitario for item in itens_queryset),
        Decimal('0.00')
    )


# =============================================================================
# 6. HAVERSINE - Distância geodésica entre dois pontos (coordenadas GPS)
#
# Fórmula de Haversine: calcula a distância em linha reta sobre a superfície
# da Terra usando latitudes e longitudes.
# Complexidade: O(1) — operações trigonométricas constantes.
# =============================================================================

import math


def calcular_distancia_km(lat1, lon1, lat2, lon2):
    """
    Calcula a distância em quilômetros entre dois pontos geográficos
    usando a fórmula de Haversine.

    Args:
        lat1, lon1: Latitude e longitude do ponto de origem (restaurante)
        lat2, lon2: Latitude e longitude do ponto de destino (cliente)

    Returns:
        float: Distância em quilômetros
    """
    R = 6371.0  # Raio médio da Terra em km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def zona_entrega_para_distancia(zonas, distancia_km):
    """
    Encontra a zona de entrega adequada para uma dada distância.

    As zonas devem estar ordenadas por raio_max_km crescente.
    Usa pesquisa linear (O(n)), geralmente ≤ 5 zonas por restaurante.

    Args:
        zonas: QuerySet ou lista de ZonaEntrega ordenadas por raio_max_km
        distancia_km: Distância calculada do cliente ao restaurante

    Returns:
        ZonaEntrega ou None se fora da área de entrega
    """
    for zona in zonas:
        if distancia_km <= float(zona.raio_max_km):
            return zona
    return None


def agrupar_por_categoria_hash(produtos):
    """
    Agrupa produtos por categoria usando tabela hash (dicionário).

    Complexidade: O(n) - uma passada pela lista
    Sem hash: agrupamento por nested loops seria O(n²)

    Retorna dict onde:
    - chave = categoria_id (lookup O(1))
    - valor = {'categoria': obj, 'produtos': [lista]}
    """
    agrupados = {}
    for produto in produtos:
        cat_id = produto.categoria_id or 0
        if cat_id not in agrupados:
            agrupados[cat_id] = {
                'categoria': produto.categoria,
                'produtos': [],
            }
        agrupados[cat_id]['produtos'].append(produto)
    return agrupados
