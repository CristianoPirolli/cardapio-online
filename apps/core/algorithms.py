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
    'recebido': ['preparo', 'cancelado'],
    'preparo': ['entrega', 'cancelado'],
    'entrega': ['concluido', 'cancelado'],
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


def pode_alcancar_status(grafo, origem, destino):
    """
    Verifica se é possível chegar de um status a outro (direta ou indiretamente).

    Exemplo: pode_alcancar_status(GRAFO_STATUS_PEDIDO, 'recebido', 'concluido')
    → True (recebido → preparo → entrega → concluido)

    Exemplo: pode_alcancar_status(GRAFO_STATUS_PEDIDO, 'cancelado', 'concluido')
    → False (cancelado é estado terminal)
    """
    return len(bfs_caminho_mais_curto(grafo, origem, destino)) > 0


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
# 3. DIJKSTRA (Cap. 7) - Seleção otimizada de entregador
#
# Livro: "O algoritmo de Dijkstra encontra o caminho de menor custo"
# Uso: Escolher o melhor entregador baseado em custo ponderado
#      (disponibilidade, veículo, quantidade de entregas ativas)
# =============================================================================

# Pesos por tipo de veículo (menor = mais rápido para entregas curtas)
PESO_VEICULO = {
    'moto': 1.0,       # Mais rápido em cidade
    'carro': 1.5,      # Bom para distâncias maiores
    'bicicleta': 2.0,  # Ecológico mas mais lento
    'a_pe': 3.0,       # Apenas para curtas distâncias
}

# Tempo estimado por km para cada veículo (em minutos)
TEMPO_POR_KM = {
    'moto': 2.5,       # ~24 km/h em cidade
    'carro': 3.0,      # ~20 km/h com trânsito
    'bicicleta': 5.0,  # ~12 km/h
    'a_pe': 12.0,      # ~5 km/h
}


def dijkstra_melhor_entregador(entregadores, entregas_ativas_por_entregador):
    """
    Usa o conceito de Dijkstra para selecionar o entregador com menor
    "custo" ponderado.

    Livro Cap. 7: "Para cada nó, encontre o nó de menor custo...
    atualize os custos dos vizinhos desse nó"

    Aqui adaptamos: cada entregador é um "nó" e o "custo" é calculado
    com base em fatores ponderados:
    - Peso do veículo (moto < carro < bicicleta < a_pe)
    - Número de entregas ativas (menos = melhor)

    Usamos uma min-heap (fila de prioridade) para extrair o menor custo
    em O(log n) ao invés de O(n) com busca linear.

    Complexidade: O(n log n) vs O(n²) sem heap
    """
    if not entregadores:
        return None

    # Min-heap: (custo, entregador_id, entregador)
    heap = []

    for entregador in entregadores:
        peso_veiculo = PESO_VEICULO.get(entregador.veiculo, 2.0)
        entregas_ativas = entregas_ativas_por_entregador.get(entregador.id, 0)

        # Fórmula de custo: peso_veículo + (entregas_ativas * penalidade)
        custo = peso_veiculo + (entregas_ativas * 1.5)

        heappush(heap, (custo, entregador.id, entregador))

    if heap:
        custo, _, melhor = heappop(heap)
        return melhor

    return None


def dijkstra_estimar_tempo_entrega(veiculo, distancia_km, entregas_pendentes=0):
    """
    Estima o tempo de entrega usando pesos de Dijkstra.

    Considera:
    - Tipo de veículo (tempo por km)
    - Distância estimada
    - Entregas pendentes antes desta (cada uma adiciona tempo)

    Returns:
        int: tempo estimado em minutos
    """
    tempo_base = TEMPO_POR_KM.get(veiculo, 5.0) * float(distancia_km)
    tempo_preparo = 15  # média de preparo do restaurante
    tempo_fila = entregas_pendentes * 10  # cada entrega pendente adiciona ~10min

    return int(tempo_preparo + tempo_base + tempo_fila)


def ranking_entregadores(entregadores, entregas_ativas_por_entregador):
    """
    Retorna todos os entregadores rankeados do melhor ao pior custo.
    Usa heap sort implícito via heappush/heappop.

    Complexidade: O(n log n) - mesma que sort, mas com extração incremental
    """
    heap = []
    for entregador in entregadores:
        peso_veiculo = PESO_VEICULO.get(entregador.veiculo, 2.0)
        entregas_ativas = entregas_ativas_por_entregador.get(entregador.id, 0)
        custo = peso_veiculo + (entregas_ativas * 1.5)
        heappush(heap, (custo, entregador.id, entregador))

    ranking = []
    while heap:
        custo, _, entregador = heappop(heap)
        ranking.append({
            'entregador': entregador,
            'custo': round(custo, 2),
            'tempo_estimado': dijkstra_estimar_tempo_entrega(
                entregador.veiculo,
                distancia_km=5,  # média padrão
                entregas_pendentes=entregas_ativas_por_entregador.get(entregador.id, 0),
            ),
        })

    return ranking


# =============================================================================
# 4. PESQUISA BINÁRIA (Cap. 1) - Busca eficiente em faixas de preço
#
# Livro: "Com a pesquisa binária, você chuta o meio... elimina metade"
# Busca linear: O(n) - Pesquisa binária: O(log n)
# =============================================================================

def pesquisa_binaria_preco(produtos_ordenados, preco_alvo):
    """
    Pesquisa binária para encontrar o produto com preço mais próximo.

    Livro Cap. 1: "A cada passo, você elimina metade dos números restantes"

    Requer lista ordenada por preço.
    Complexidade: O(log n) vs O(n) da busca linear.

    Para 1000 produtos:
    - Busca linear: até 1000 comparações
    - Pesquisa binária: até 10 comparações (log2(1000) ≈ 10)
    """
    precos = [float(p.preco or 0) for p in produtos_ordenados]
    preco_float = float(preco_alvo)

    # bisect_left encontra o ponto de inserção em O(log n)
    idx = bisect.bisect_left(precos, preco_float)

    if idx == 0:
        return produtos_ordenados[0] if produtos_ordenados else None
    if idx == len(precos):
        return produtos_ordenados[-1] if produtos_ordenados else None

    # Compara o anterior e o atual para encontrar o mais próximo
    antes = precos[idx - 1]
    depois = precos[idx]
    if preco_float - antes <= depois - preco_float:
        return produtos_ordenados[idx - 1]
    return produtos_ordenados[idx]


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

def calcular_preco_combo_recursivo(itens, idx=0, memo=None):
    """
    Calcula o preço total de um combo/pedido recursivamente com memoização.

    Caso base (Cap. 3): idx == len(itens) → retorna 0
    Caso recursivo: preço do item atual + soma dos restantes

    Memoização (Cap. 8): guarda resultados já calculados para evitar
    recalcular subproblemas. Dict como cache → lookup O(1).

    Sem memoização: O(2^n) no pior caso para combos com descontos
    Com memoização: O(n) - cada subproblema calculado uma vez só
    """
    if memo is None:
        memo = {}

    if idx in memo:
        return memo[idx]

    # Caso base: não há mais itens
    if idx >= len(itens):
        return Decimal('0.00')

    item = itens[idx]
    preco_item = item['quantidade'] * item['preco_unitario']

    # Recursão: preço deste item + preço dos restantes
    total = preco_item + calcular_preco_combo_recursivo(itens, idx + 1, memo)

    # Memoiza o resultado
    memo[idx] = total
    return total


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
