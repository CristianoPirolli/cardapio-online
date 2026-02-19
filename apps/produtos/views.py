# =============================================================================
# apps/produtos/views.py - Views HTML para cardápio público e gestão de produtos
#
# Views públicas:
# - Cardápio público do restaurante (acessível sem login)
# - Detalhe de produto
#
# Views do painel (requerem login):
# - CRUD de categorias
# - CRUD de produtos com upload de imagem
# =============================================================================

from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from django.db.models import Prefetch

from apps.restaurantes.models import Restaurante
from apps.core.algorithms import (
    cache_cardapio,
    agrupar_por_categoria_hash,
    produtos_na_faixa_preco,
)
from .models import Categoria, Produto
from .forms import CategoriaForm, ProdutoForm


# ---------------------------------------------------------------------------
# Views públicas (cardápio)
# ---------------------------------------------------------------------------

def cardapio_publico(request):
    """
    Exibe o cardápio público de um restaurante.

    Otimizações aplicadas:
    - Tabela Hash (Cap. 5): cache do cardápio por restaurante (TTL 30s)
    - Big O (Cap. 1): prefetch_related evita N+1 queries
    - Pesquisa Binária (Cap. 1): filtro opcional por faixa de preço

    O restaurante é identificado pelo middleware multi-tenant (subdomínio)
    ou pelo parâmetro GET ?estabelecimento=<subdominio> em desenvolvimento.
    """
    restaurante = request.restaurante

    if request.user.is_authenticated and not request.user.is_superuser:
        restaurante_usuario = Restaurante.objects.filter(
            proprietario=request.user,
            ativo=True
        ).first()
        if restaurante_usuario:
            restaurante = restaurante_usuario
        else:
            messages.warning(request, 'Sua conta ainda não está vinculada a um restaurante.')
            return redirect('home')

    if not restaurante:
        rest_id = request.GET.get('id')
        if rest_id:
            restaurante = get_object_or_404(Restaurante, id=rest_id, ativo=True)
        else:
            return render(request, 'produtos/selecionar_restaurante.html', {
                'restaurantes': Restaurante.objects.filter(ativo=True)
            })

    # -----------------------------------------------------------------------
    # Tabela Hash (Cap. 5): tenta cache primeiro - O(1)
    # Sem cache: cada acesso ao cardápio = 2-3 queries SQL
    # Com cache: lookup O(1) no dicionário em memória (TTL 30s)
    # -----------------------------------------------------------------------
    cache_key = f"cardapio:{restaurante.id}"
    cached = cache_cardapio.get(cache_key)

    if cached is not None:
        cardapio, tamanhos_pizza = cached
    else:
        categorias = Categoria.objects.filter(
            restaurante=restaurante, ativo=True
        ).prefetch_related(
            Prefetch(
                'produtos',
                queryset=Produto.objects.filter(disponivel=True).select_related('categoria'),
                to_attr='produtos_disponiveis',
            )
        )
        tamanhos_pizza = list(restaurante.tamanhos_pizza.filter(ativo=True).order_by('ordem', 'id'))

        cardapio = []
        for cat in categorias:
            produtos = getattr(cat, 'produtos_disponiveis', [])
            if produtos:
                cardapio.append({'categoria': cat, 'produtos': produtos})

        # Armazena no cache (Tabela Hash - inserção O(1))
        cache_cardapio.set(cache_key, (cardapio, tamanhos_pizza))

    # -----------------------------------------------------------------------
    # Pesquisa Binária (Cap. 1): filtro por faixa de preço
    # Se o usuário informar ?preco_min=X&preco_max=Y, usa bisect
    # para encontrar os produtos na faixa em O(log n) por categoria
    # -----------------------------------------------------------------------
    preco_min = request.GET.get('preco_min')
    preco_max = request.GET.get('preco_max')

    if preco_min or preco_max:
        p_min = Decimal(preco_min) if preco_min else Decimal('0')
        p_max = Decimal(preco_max) if preco_max else Decimal('99999')
        cardapio_filtrado = []
        for item in cardapio:
            # Ordena por preço para pesquisa binária
            produtos_ordenados = sorted(
                item['produtos'],
                key=lambda p: p.preco or Decimal('0')
            )
            # Pesquisa Binária: encontra faixa em O(log n)
            filtrados = produtos_na_faixa_preco(produtos_ordenados, p_min, p_max)
            if filtrados:
                cardapio_filtrado.append({
                    'categoria': item['categoria'],
                    'produtos': filtrados,
                })
        cardapio = cardapio_filtrado

    cardapio_pizzas = [item for item in cardapio if item['categoria'].eh_pizza]
    cardapio_outros = [item for item in cardapio if not item['categoria'].eh_pizza]

    return render(request, 'produtos/cardapio.html', {
        'restaurante': restaurante,
        'cardapio': cardapio,
        'cardapio_pizzas': cardapio_pizzas,
        'cardapio_outros': cardapio_outros,
        'tamanhos_pizza': tamanhos_pizza,
    })


def produto_detalhe(request, produto_id):
    """
    Exibe o detalhe de um produto específico.

    Otimizações:
    - Tabela Hash (Cap. 5): agrupamento de sabores por categoria em O(n)
      usando dicionário ao invés de nested loops O(n²)
    - select_related evita N+1 na categoria
    """
    produto = get_object_or_404(Produto, id=produto_id, disponivel=True)
    if request.user.is_authenticated and not request.user.is_superuser:
        restaurante_usuario = Restaurante.objects.filter(proprietario=request.user).first()
        if restaurante_usuario and produto.restaurante_id != restaurante_usuario.id:
            messages.error(request, 'Você só pode visualizar produtos do seu restaurante.')
            return redirect('cardapio_publico')

    is_pizza = bool(produto.categoria and produto.categoria.eh_pizza)
    tamanhos = (
        produto.restaurante.tamanhos_pizza.filter(ativo=True).order_by('ordem', 'id')
        if is_pizza else []
    )
    tamanho_preselecionado_id = request.GET.get('tamanho')
    try:
        tamanho_preselecionado_id = int(tamanho_preselecionado_id) if tamanho_preselecionado_id else None
    except ValueError:
        tamanho_preselecionado_id = None
    sabores = Produto.objects.none()
    if is_pizza:
        sabores = Produto.objects.filter(
            restaurante=produto.restaurante,
            categoria__eh_pizza=True,
            disponivel=True
        ).select_related('categoria').order_by('categoria__ordem', 'categoria__nome', 'nome')

    # -----------------------------------------------------------------------
    # Tabela Hash (Cap. 5): Agrupamento O(n) usando dicionário
    #
    # Antes: loop com verificação `if categoria_id not in agrupados` — já
    #        usava dict, mas agora usamos a função centralizada que garante
    #        lookup O(1) para cada produto.
    #
    # Para 100 sabores: 100 lookups O(1) = O(100) = O(n)
    # Sem hash table: teria que comparar com todos os grupos = O(n²)
    # -----------------------------------------------------------------------
    agrupados = agrupar_por_categoria_hash(sabores)
    sabores_por_tipo = [
        {'tipo': grupo['categoria'], 'sabores': grupo['produtos']}
        for grupo in agrupados.values()
    ]

    return render(request, 'produtos/produto_detalhe.html', {
        'produto': produto,
        'restaurante': produto.restaurante,
        'is_pizza': is_pizza,
        'tamanhos': tamanhos,
        'tamanho_preselecionado_id': tamanho_preselecionado_id,
        'sabores': sabores,
        'sabores_por_tipo': sabores_por_tipo,
    })


# ---------------------------------------------------------------------------
# Views do painel (CRUD de categorias)
# ---------------------------------------------------------------------------

@login_required
def painel_categorias(request):
    """Lista todas as categorias do restaurante no painel."""
    restaurante = get_object_or_404(Restaurante, proprietario=request.user)
    categorias = Categoria.objects.filter(restaurante=restaurante)
    return render(request, 'painel/categorias.html', {
        'restaurante': restaurante,
        'categorias': categorias,
    })


@login_required
def painel_categoria_criar(request):
    """Cria uma nova categoria para o restaurante."""
    restaurante = get_object_or_404(Restaurante, proprietario=request.user)

    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            categoria = form.save(commit=False)
            categoria.restaurante = restaurante
            categoria.save()
            messages.success(request, f'Categoria "{categoria.nome}" criada!')
            return redirect('painel_categorias')
    else:
        form = CategoriaForm()

    return render(request, 'painel/categoria_form.html', {
        'form': form,
        'restaurante': restaurante,
        'titulo': 'Nova Categoria',
    })


@login_required
def painel_categoria_editar(request, categoria_id):
    """Edita uma categoria existente."""
    restaurante = get_object_or_404(Restaurante, proprietario=request.user)
    categoria = get_object_or_404(Categoria, id=categoria_id, restaurante=restaurante)

    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, f'Categoria "{categoria.nome}" atualizada!')
            return redirect('painel_categorias')
    else:
        form = CategoriaForm(instance=categoria)

    return render(request, 'painel/categoria_form.html', {
        'form': form,
        'restaurante': restaurante,
        'titulo': 'Editar Categoria',
    })


@login_required
def painel_categoria_excluir(request, categoria_id):
    """Exclui uma categoria (com confirmação via POST)."""
    restaurante = get_object_or_404(Restaurante, proprietario=request.user)
    categoria = get_object_or_404(Categoria, id=categoria_id, restaurante=restaurante)

    if request.method == 'POST':
        nome = categoria.nome
        categoria.delete()
        messages.success(request, f'Categoria "{nome}" excluída!')
        return redirect('painel_categorias')

    return render(request, 'painel/confirmar_exclusao.html', {
        'objeto': categoria,
        'tipo': 'categoria',
        'restaurante': restaurante,
    })


# ---------------------------------------------------------------------------
# Views do painel (CRUD de produtos)
# ---------------------------------------------------------------------------

@login_required
def painel_produtos(request):
    """
    Lista todos os produtos do restaurante no painel.

    Pesquisa Binária (Cap. 1): filtro por faixa de preço usando bisect.
    """
    restaurante = get_object_or_404(Restaurante, proprietario=request.user)
    produtos = Produto.objects.filter(restaurante=restaurante).select_related('categoria')

    # Filtro por categoria
    categoria_filtro = request.GET.get('categoria')
    if categoria_filtro:
        produtos = produtos.filter(categoria_id=categoria_filtro)

    # -----------------------------------------------------------------------
    # Pesquisa Binária (Cap. 1): filtro por faixa de preço
    # Em vez de filtrar no banco (WHERE preco BETWEEN), carregamos e
    # usamos bisect para encontrar a faixa em O(log n).
    # Vantagem: funciona mesmo com preços calculados (adicional_sabor).
    # -----------------------------------------------------------------------
    preco_min = request.GET.get('preco_min')
    preco_max = request.GET.get('preco_max')

    if preco_min or preco_max:
        p_min = Decimal(preco_min) if preco_min else Decimal('0')
        p_max = Decimal(preco_max) if preco_max else Decimal('99999')
        produtos_lista = sorted(
            list(produtos),
            key=lambda p: p.preco or Decimal('0')
        )
        produtos = produtos_na_faixa_preco(produtos_lista, p_min, p_max)

    categorias = Categoria.objects.filter(restaurante=restaurante)

    return render(request, 'painel/produtos.html', {
        'restaurante': restaurante,
        'produtos': produtos,
        'categorias': categorias,
        'categoria_filtro': categoria_filtro,
    })


@login_required
def painel_produto_criar(request):
    """Cria um novo produto com upload de imagem."""
    restaurante = get_object_or_404(Restaurante, proprietario=request.user)

    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, restaurante=restaurante)
        if form.is_valid():
            produto = form.save(commit=False)
            produto.restaurante = restaurante
            produto.save()
            messages.success(request, f'Produto "{produto.nome}" criado!')
            return redirect('painel_produtos')
    else:
        form = ProdutoForm(restaurante=restaurante)

    return render(request, 'painel/produto_form.html', {
        'form': form,
        'restaurante': restaurante,
        'titulo': 'Novo Produto',
    })


@login_required
def painel_produto_editar(request, produto_id):
    """Edita um produto existente (incluindo troca de imagem)."""
    restaurante = get_object_or_404(Restaurante, proprietario=request.user)
    produto = get_object_or_404(Produto, id=produto_id, restaurante=restaurante)

    if request.method == 'POST':
        form = ProdutoForm(request.POST, request.FILES, instance=produto, restaurante=restaurante)
        if form.is_valid():
            form.save()
            messages.success(request, f'Produto "{produto.nome}" atualizado!')
            return redirect('painel_produtos')
    else:
        form = ProdutoForm(instance=produto, restaurante=restaurante)

    return render(request, 'painel/produto_form.html', {
        'form': form,
        'restaurante': restaurante,
        'titulo': 'Editar Produto',
        'produto': produto,
    })


@login_required
def painel_produto_excluir(request, produto_id):
    """Exclui um produto (com confirmação via POST)."""
    restaurante = get_object_or_404(Restaurante, proprietario=request.user)
    produto = get_object_or_404(Produto, id=produto_id, restaurante=restaurante)

    if request.method == 'POST':
        nome = produto.nome
        produto.delete()
        messages.success(request, f'Produto "{nome}" excluído!')
        return redirect('painel_produtos')

    return render(request, 'painel/confirmar_exclusao.html', {
        'objeto': produto,
        'tipo': 'produto',
        'restaurante': restaurante,
    })
