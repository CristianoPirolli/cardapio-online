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

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404

from apps.restaurantes.models import Restaurante
from .models import Categoria, Produto
from .forms import CategoriaForm, ProdutoForm


# ---------------------------------------------------------------------------
# Views públicas (cardápio)
# ---------------------------------------------------------------------------

def cardapio_publico(request):
    """
    Exibe o cardápio público de um restaurante.

    O restaurante é identificado pelo middleware multi-tenant (subdomínio)
    ou pelo parâmetro GET ?restaurante=<subdominio> em desenvolvimento.

    Agrupa produtos por categoria para exibição organizada.
    """
    restaurante = request.restaurante

    # Em modo SaaS, usuário autenticado (não superuser) só enxerga o próprio cardápio.
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
        # Fallback: se acessado sem subdomínio, tenta pelo ID na query string
        rest_id = request.GET.get('id')
        if rest_id:
            restaurante = get_object_or_404(Restaurante, id=rest_id, ativo=True)
        else:
            return render(request, 'produtos/selecionar_restaurante.html', {
                'restaurantes': Restaurante.objects.filter(ativo=True)
            })

    categorias = Categoria.objects.filter(
        restaurante=restaurante, ativo=True
    ).prefetch_related('produtos')
    tamanhos_pizza = restaurante.tamanhos_pizza.filter(ativo=True).order_by('ordem', 'id')

    # Filtra apenas produtos disponíveis em cada categoria
    cardapio = []
    for cat in categorias:
        produtos = cat.produtos.filter(disponivel=True)
        if produtos.exists():
            cardapio.append({'categoria': cat, 'produtos': produtos})

    return render(request, 'produtos/cardapio.html', {
        'restaurante': restaurante,
        'cardapio': cardapio,
        'tamanhos_pizza': tamanhos_pizza,
    })


def produto_detalhe(request, produto_id):
    """Exibe o detalhe de um produto específico."""
    produto = get_object_or_404(Produto, id=produto_id, disponivel=True)
    if request.user.is_authenticated and not request.user.is_superuser:
        restaurante_usuario = Restaurante.objects.filter(proprietario=request.user).first()
        if restaurante_usuario and produto.restaurante_id != restaurante_usuario.id:
            messages.error(request, 'Você só pode visualizar produtos do seu restaurante.')
            return redirect('cardapio_publico')

    tamanhos = produto.restaurante.tamanhos_pizza.filter(ativo=True).order_by('ordem', 'id')
    tamanho_preselecionado_id = request.GET.get('tamanho')
    try:
        tamanho_preselecionado_id = int(tamanho_preselecionado_id) if tamanho_preselecionado_id else None
    except ValueError:
        tamanho_preselecionado_id = None
    sabores = Produto.objects.filter(
        restaurante=produto.restaurante,
        disponivel=True
    ).select_related('categoria').order_by('categoria__ordem', 'categoria__nome', 'nome')

    sabores_por_tipo = []
    agrupados = {}
    for sabor in sabores:
        categoria = sabor.categoria
        categoria_id = categoria.id if categoria else 0
        if categoria_id not in agrupados:
            agrupados[categoria_id] = {
                'tipo': categoria,
                'sabores': [],
            }
        agrupados[categoria_id]['sabores'].append(sabor)

    sabores_por_tipo = list(agrupados.values())

    return render(request, 'produtos/produto_detalhe.html', {
        'produto': produto,
        'restaurante': produto.restaurante,
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
    """Lista todos os produtos do restaurante no painel."""
    restaurante = get_object_or_404(Restaurante, proprietario=request.user)
    produtos = Produto.objects.filter(restaurante=restaurante).select_related('categoria')

    # Filtro por categoria
    categoria_filtro = request.GET.get('categoria')
    if categoria_filtro:
        produtos = produtos.filter(categoria_id=categoria_filtro)

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
