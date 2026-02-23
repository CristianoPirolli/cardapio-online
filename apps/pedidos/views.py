# =============================================================================
# apps/pedidos/views.py - Views HTML para carrinho e pedidos
#
# Views:
# - Carrinho de compras (sessão do navegador)
# - Adicionar/remover itens do carrinho
# - Finalizar pedido (checkout)
# - Acompanhamento de pedido
# =============================================================================

import json
from decimal import Decimal
from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.restaurantes.models import Restaurante, TamanhoPizza
from apps.produtos.models import Produto
from .models import Pedido, ItemPedido
from apps.entregas.models import Entrega


def _get_carrinho(request):
    """
    Obtém o carrinho da sessão do usuário.

    Estrutura do carrinho na sessão:
    {
        "restaurante_id": 1,
        "itens": {
            "5": {"quantidade": 2, "observacao": ""},
            "8": {"quantidade": 1, "observacao": "Sem cebola"}
        }
    }
    """
    return request.session.get('carrinho', {'restaurante_id': None, 'itens': {}})


def _salvar_carrinho(request, carrinho):
    """Salva o carrinho na sessão."""
    request.session['carrinho'] = carrinho
    request.session.modified = True


def _produto_id_do_item(item_key, item_data):
    """Retorna o ID de produto associado ao item do carrinho."""
    if item_data.get('produto_id'):
        return str(item_data['produto_id'])
    return str(item_key).split(':')[0]


def _item_key(produto_id, tamanho_id=None, sabor_ids=None):
    """
    Gera uma chave estável para o item no carrinho.
    Permite separar o mesmo produto por configuração (tamanho/sabores).
    """
    if not tamanho_id:
        return str(produto_id)
    sabores = '-'.join(str(sid) for sid in sorted(sabor_ids or []))
    return f'{produto_id}:{tamanho_id}:{sabores}'


def _redirect_com_status_carrinho(request, fallback='/cardapio/', **params):
    """
    Redireciona para a página de origem preservando query params e
    adicionando sinalizadores para feedback de UX no frontend.
    """
    destino = request.META.get('HTTP_REFERER', fallback) or fallback
    partes = urlsplit(destino)
    query = parse_qs(partes.query, keep_blank_values=True)
    for chave, valor in params.items():
        query[chave] = [str(valor)]
    nova_query = urlencode(query, doseq=True)
    return redirect(urlunsplit((partes.scheme, partes.netloc, partes.path, nova_query, partes.fragment)))


def _preco_padrao_sabor(produto):
    """
    Retorna o preço padrão de um sabor.
    Prioriza o preço próprio; se vazio, usa o adicional do tipo/categoria.
    """
    if produto.preco is not None:
        return produto.preco
    if produto.categoria and produto.categoria.adicional_sabor is not None:
        return produto.categoria.adicional_sabor
    return Decimal('0.00')


@require_POST
def adicionar_ao_carrinho(request):
    """
    Adiciona um produto ao carrinho.

    POST params:
    - produto_id: ID do produto
    - quantidade: Quantidade (default 1)
    - observacao: Observação opcional
    """
    produto_id = request.POST.get('produto_id')
    quantidade = int(request.POST.get('quantidade', 1))
    observacao = request.POST.get('observacao', '').strip()
    tamanho_id = request.POST.get('tamanho_id')
    sabores_ids = [sid for sid in request.POST.getlist('sabor_ids') if sid]

    produto = get_object_or_404(
        Produto.objects.select_related('categoria', 'restaurante'),
        id=produto_id, disponivel=True
    )
    is_pizza = bool(produto.categoria and produto.categoria.eh_pizza)

    # Verifica se o restaurante esta aberto
    if not produto.restaurante.esta_aberto:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(
                {'success': False, 'error': 'Restaurante fechado no momento.'},
                status=400
            )
        messages.error(request, f'O restaurante {produto.restaurante.nome} está fechado no momento.')
        return redirect(request.META.get('HTTP_REFERER', '/cardapio/'))

    tamanhos_disponiveis = produto.restaurante.tamanhos_pizza.filter(ativo=True).order_by('ordem', 'id')
    tamanho = None
    sabores_escolhidos = [produto]
    sabor_ids_limpos = [produto.id]
    preco_padrao = _preco_padrao_sabor(produto)
    preco_unitario = preco_padrao
    preco_base = preco_padrao
    adicional_sabores = Decimal('0.00')
    tamanho_nome = ''
    max_sabores = 1

    if is_pizza and tamanhos_disponiveis.exists():
        if not tamanho_id:
            msg = 'Selecione um tamanho antes de escolher os sabores.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': msg}, status=400)
            messages.error(request, msg)
            return redirect(request.META.get('HTTP_REFERER', '/cardapio/'))

        tamanho = get_object_or_404(
            TamanhoPizza,
            id=tamanho_id,
            restaurante=produto.restaurante,
            ativo=True
        )
        max_sabores = tamanho.max_sabores
        tamanho_nome = tamanho.nome
        preco_base = tamanho.preco_base

        sabores_query = Produto.objects.filter(
            restaurante=produto.restaurante,
            disponivel=True
        ).select_related('categoria')

        sabores_validos = {str(s.id): s for s in sabores_query}
        sabores_filtrados = []
        for sid in sabores_ids:
            if sid in sabores_validos and sid not in sabores_filtrados:
                sabores_filtrados.append(sid)

        # O sabor base (produto aberto) sempre conta como 1 sabor selecionado.
        principal_id = str(produto.id)
        if principal_id in sabores_filtrados:
            sabores_filtrados = [sid for sid in sabores_filtrados if sid != principal_id]
        sabores_filtrados.insert(0, principal_id)

        if len(sabores_filtrados) > max_sabores:
            extras_permitidos = max(max_sabores - 1, 0)
            msg = (
                f'Para o tamanho "{tamanho.nome}" você pode escolher até {max_sabores} sabor(es) no total '
                f'({extras_permitidos} adicional(is) além do sabor base).'
            )
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': msg}, status=400)
            messages.error(request, msg)
            return redirect(request.META.get('HTTP_REFERER', '/cardapio/'))

        sabores_escolhidos = [sabores_validos[sid] for sid in sabores_filtrados if sid in sabores_validos]
        if not sabores_escolhidos:
            sabores_escolhidos = [produto]
        sabor_ids_limpos = sorted(s.id for s in sabores_escolhidos)
        adicional_sabores = sum(
            (s.categoria.adicional_sabor if s.categoria else Decimal('0.00'))
            for s in sabores_escolhidos
        )
        preco_unitario = preco_base + adicional_sabores
    else:
        preco_base = preco_padrao
        preco_unitario = preco_padrao

    carrinho = _get_carrinho(request)

    # Verifica se o carrinho é do mesmo restaurante
    if carrinho['restaurante_id'] and carrinho['restaurante_id'] != produto.restaurante_id:
        # Limpa o carrinho se mudar de restaurante
        carrinho = {'restaurante_id': produto.restaurante_id, 'itens': {}}

    carrinho['restaurante_id'] = produto.restaurante_id
    str_id = _item_key(produto.id, tamanho.id if tamanho else None, sabor_ids_limpos)

    if str_id in carrinho['itens']:
        carrinho['itens'][str_id]['quantidade'] += quantidade
    else:
        carrinho['itens'][str_id] = {
            'produto_id': produto.id,
            'quantidade': quantidade,
            'observacao': observacao,
            'tamanho_id': tamanho.id if tamanho else None,
            'tamanho_nome': tamanho_nome,
            'max_sabores': max_sabores,
            'sabores': sabor_ids_limpos,
            'sabores_nomes': [s.nome for s in sabores_escolhidos],
            'preco_base': str(preco_base),
            'adicional_sabores': str(adicional_sabores),
            'preco_unitario': str(preco_unitario),
        }

    _salvar_carrinho(request, carrinho)

    # Retorna JSON para requisições AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        total_itens = sum(item['quantidade'] for item in carrinho['itens'].values())
        return JsonResponse({'success': True, 'total_itens': total_itens})

    if is_pizza and request.POST.get('abrir_bebidas') == '1':
        return redirect('upsell_bebidas')

    if tamanho_nome:
        messages.success(request, f'"{produto.nome}" ({tamanho_nome}) adicionado ao carrinho!')
    else:
        messages.success(request, f'"{produto.nome}" adicionado ao carrinho!')
    return _redirect_com_status_carrinho(
        request,
        '/cardapio/',
        item_adicionado=1,
    )


def upsell_bebidas(request):
    """
    Tela intermediária para incluir bebidas após adicionar pizza.
    """
    carrinho = _get_carrinho(request)
    if not carrinho['itens'] or not carrinho['restaurante_id']:
        messages.warning(request, 'Seu carrinho está vazio.')
        return redirect('cardapio_publico')

    restaurante = get_object_or_404(Restaurante, id=carrinho['restaurante_id'], ativo=True)
    bebidas = Produto.objects.filter(
        restaurante=restaurante,
        categoria__eh_pizza=False,
        disponivel=True
    ).select_related('categoria').order_by('categoria__ordem', 'categoria__nome', 'nome')

    if request.method == 'POST':
        bebida_ids = request.POST.getlist('bebida_ids')
        quantidades = {}
        for bebida_id in bebida_ids:
            try:
                qtd = int(request.POST.get(f'quantidade_{bebida_id}', '0'))
            except ValueError:
                qtd = 0
            if qtd > 0:
                quantidades[bebida_id] = qtd

        if quantidades:
            produtos_bebida = {
                str(p.id): p
                for p in Produto.objects.filter(
                    id__in=quantidades.keys(),
                    restaurante=restaurante,
                    categoria__eh_pizza=False,
                    disponivel=True
                )
            }

            for bebida_id, qtd in quantidades.items():
                produto = produtos_bebida.get(str(bebida_id))
                if not produto:
                    continue
                item_key = _item_key(produto.id)
                if item_key in carrinho['itens']:
                    carrinho['itens'][item_key]['quantidade'] += qtd
                else:
                    carrinho['itens'][item_key] = {
                        'produto_id': produto.id,
                        'quantidade': qtd,
                        'observacao': '',
                        'tamanho_id': None,
                        'tamanho_nome': '',
                        'max_sabores': 1,
                        'sabores': [produto.id],
                        'sabores_nomes': [produto.nome],
                        'preco_base': str(produto.preco or Decimal('0.00')),
                        'adicional_sabores': '0.00',
                        'preco_unitario': str(produto.preco or Decimal('0.00')),
                    }

            _salvar_carrinho(request, carrinho)

        acao = request.POST.get('acao')
        if acao == 'continuar':
            return redirect('cardapio_publico')
        if acao == 'finalizar':
            return redirect('checkout')
        return redirect('upsell_bebidas')

    return render(request, 'pedidos/upsell_bebidas.html', {
        'restaurante': restaurante,
        'bebidas': bebidas,
    })


@require_POST
def remover_do_carrinho(request):
    """
    Remove um produto do carrinho.

    POST params:
    - produto_id: ID do produto a remover
    """
    item_key = request.POST.get('item_key')
    produto_id = str(request.POST.get('produto_id', ''))
    carrinho = _get_carrinho(request)

    if item_key and item_key in carrinho['itens']:
        del carrinho['itens'][item_key]
    elif produto_id in carrinho['itens']:
        del carrinho['itens'][produto_id]

    if not carrinho['itens']:
        carrinho['restaurante_id'] = None

    _salvar_carrinho(request, carrinho)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    messages.info(request, 'Item removido do carrinho.')
    return redirect('ver_carrinho')


@require_POST
def atualizar_carrinho(request):
    """
    Atualiza a quantidade de um item no carrinho.

    POST params:
    - produto_id: ID do produto
    - quantidade: Nova quantidade (0 para remover)
    """
    item_key = request.POST.get('item_key')
    produto_id = str(request.POST.get('produto_id', ''))
    quantidade = int(request.POST.get('quantidade', 1))
    carrinho = _get_carrinho(request)
    alvo = item_key if item_key in carrinho['itens'] else produto_id

    if quantidade <= 0:
        if alvo in carrinho['itens']:
            del carrinho['itens'][alvo]
    elif alvo in carrinho['itens']:
        carrinho['itens'][alvo]['quantidade'] = quantidade

    if not carrinho['itens']:
        carrinho['restaurante_id'] = None

    _salvar_carrinho(request, carrinho)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})

    return redirect('ver_carrinho')


def ver_carrinho(request):
    """
    Exibe o carrinho de compras com cálculo de totais.
    """
    carrinho = _get_carrinho(request)
    itens_carrinho = []
    subtotal = Decimal('0.00')
    restaurante = None

    if carrinho['restaurante_id']:
        restaurante = Restaurante.objects.filter(
            id=carrinho['restaurante_id'], ativo=True
        ).first()

    itens_removidos = []

    if restaurante and carrinho['itens']:
        itens_sessao = carrinho['itens']
        itens_por_produto_id = {}
        for item_key, item_data in itens_sessao.items():
            pid = _produto_id_do_item(item_key, item_data)
            if pid not in itens_por_produto_id:
                itens_por_produto_id[pid] = []
            itens_por_produto_id[pid].append((item_key, item_data))

        produto_ids = list(itens_por_produto_id.keys())
        produtos = Produto.objects.filter(
            id__in=produto_ids,
            disponivel=True
        ).select_related('categoria')
        produtos_por_id = {str(prod.id): prod for prod in produtos}

        # Detecta itens indisponiveis em lote
        ids_disponiveis = set(produtos_por_id.keys())
        ids_indisponiveis = [pid for pid in produto_ids if pid not in ids_disponiveis]
        keys_para_remover = []
        if ids_indisponiveis:
            nomes_indisponiveis = {
                str(prod.id): prod.nome
                for prod in Produto.objects.filter(id__in=ids_indisponiveis).only('id', 'nome')
            }
            for pid in ids_indisponiveis:
                itens_removidos.append(nomes_indisponiveis.get(pid, f'Produto #{pid}'))
                for item_key, _ in itens_por_produto_id.get(pid, []):
                    keys_para_remover.append(item_key)

        # Remove itens indisponiveis da sessao
        if keys_para_remover:
            for item_key in keys_para_remover:
                if item_key in carrinho['itens']:
                    del carrinho['itens'][item_key]
            if not carrinho['itens']:
                carrinho['restaurante_id'] = None
            _salvar_carrinho(request, carrinho)
            itens_sessao = carrinho['itens']

        for item_key, item_data in itens_sessao.items():
            pid = _produto_id_do_item(item_key, item_data)
            produto = produtos_por_id.get(pid)
            if not produto:
                continue

            quantidade = item_data['quantidade']
            preco_padrao = _preco_padrao_sabor(produto)
            preco_unitario = Decimal(str(item_data.get('preco_unitario', preco_padrao)))
            item_subtotal = preco_unitario * quantidade
            subtotal += item_subtotal
            sabores_nomes = item_data.get('sabores_nomes', [])
            if not sabores_nomes:
                sabores_ids = item_data.get('sabores', [])
                sabores_nomes = [
                    produtos_por_id[str(sid)].nome for sid in sabores_ids
                    if str(sid) in produtos_por_id
                ]

            itens_carrinho.append({
                'item_key': item_key,
                'produto': produto,
                'quantidade': quantidade,
                'observacao': item_data.get('observacao', ''),
                'preco_base': Decimal(str(item_data.get('preco_base', preco_unitario))),
                'adicional_sabores': Decimal(str(item_data.get('adicional_sabores', '0'))),
                'preco_unitario': preco_unitario,
                'tamanho_nome': item_data.get('tamanho_nome', ''),
                'sabores_nomes': sabores_nomes,
                'subtotal': item_subtotal,
            })

    # Cálculos
    taxa_entrega = restaurante.taxa_entrega if restaurante else Decimal('0.00')
    imposto = Decimal('0.00')
    if restaurante:
        imposto = round(subtotal * restaurante.taxa_imposto / 100, 2)
    total = subtotal + taxa_entrega + imposto

    return render(request, 'pedidos/carrinho.html', {
        'itens': itens_carrinho,
        'restaurante': restaurante,
        'subtotal': subtotal,
        'taxa_entrega': taxa_entrega,
        'imposto': imposto,
        'total': total,
        'itens_removidos': itens_removidos,
    })


def checkout(request):
    """
    Página de checkout (finalização do pedido).

    GET: Exibe formulário com dados do cliente e resumo do pedido.
    POST: Cria o pedido e redireciona para pagamento.
    """
    carrinho = _get_carrinho(request)

    if not carrinho['itens']:
        messages.warning(request, 'Seu carrinho está vazio.')
        return redirect('cardapio_publico')

    restaurante = get_object_or_404(
        Restaurante, id=carrinho['restaurante_id'], ativo=True
    )

    # Verifica se o restaurante esta aberto
    if not restaurante.esta_aberto:
        messages.error(request, 'O restaurante está fechado no momento. Não é possível finalizar o pedido.')
        return redirect('ver_carrinho')

    if request.method == 'POST':
        # Dados do cliente
        cliente_nome = request.POST.get('cliente_nome', '').strip()
        cliente_telefone = request.POST.get('cliente_telefone', '').strip()
        cliente_email = request.POST.get('cliente_email', '').strip()
        endereco_entrega = request.POST.get('endereco_entrega', '').strip()
        tipo_entrega = request.POST.get('tipo_entrega', 'delivery')
        observacoes = request.POST.get('observacoes', '').strip()

        # Validação básica
        if not cliente_nome or not cliente_telefone:
            messages.error(request, 'Nome e telefone são obrigatórios.')
            return redirect('checkout')

        if tipo_entrega == 'delivery' and not endereco_entrega:
            messages.error(request, 'Informe o endereço de entrega.')
            return redirect('checkout')

        # Cria o pedido
        pedido = Pedido.objects.create(
            restaurante=restaurante,
            cliente_nome=cliente_nome,
            cliente_telefone=cliente_telefone,
            cliente_email=cliente_email,
            endereco_entrega=endereco_entrega,
            tipo_entrega=tipo_entrega,
            observacoes=observacoes,
        )

        # Cria os itens (busca produtos em lote e insere em bulk)
        itens_sessao = carrinho['itens']
        produto_ids = list({
            _produto_id_do_item(item_key, item_data)
            for item_key, item_data in itens_sessao.items()
        })
        produtos_por_id = {
            str(prod.id): prod
            for prod in Produto.objects.filter(
                id__in=produto_ids,
                restaurante=restaurante,
                disponivel=True
            ).select_related('categoria')
        }

        itens_pedido = []
        for item_key, item_data in itens_sessao.items():
            produto = produtos_por_id.get(_produto_id_do_item(item_key, item_data))
            if not produto:
                continue
            sabores_nomes = item_data.get('sabores_nomes', [])
            itens_pedido.append(ItemPedido(
                pedido=pedido,
                produto=produto,
                quantidade=item_data['quantidade'],
                preco_unitario=Decimal(str(item_data.get('preco_unitario', _preco_padrao_sabor(produto)))),
                observacao=item_data.get('observacao', ''),
                tamanho_nome=item_data.get('tamanho_nome', ''),
                sabores_descricao=', '.join(sabores_nomes),
            ))

        if not itens_pedido:
            pedido.delete()
            messages.error(request, 'Os itens do carrinho ficaram indisponíveis. Revise seu carrinho.')
            return redirect('ver_carrinho')

        ItemPedido.objects.bulk_create(itens_pedido)

        # Memoização (Cap. 8) + Big O (Cap. 1):
        # Passa itens já em memória para calcular_totais evitando query N+1
        pedido.calcular_totais(itens_prefetched=itens_pedido)

        # Verifica pedido mínimo
        if pedido.subtotal < restaurante.pedido_minimo:
            pedido.delete()
            messages.error(
                request,
                f'Pedido mínimo é R$ {restaurante.pedido_minimo:.2f}.'
            )
            return redirect('ver_carrinho')

        # Cria registro de entrega para pedidos delivery
        if pedido.tipo_entrega == 'delivery':
            from apps.entregas.models import Entrega
            Entrega.objects.create(pedido=pedido, status='aguardando')

        # Limpa o carrinho
        request.session['carrinho'] = {'restaurante_id': None, 'itens': {}}
        request.session.modified = True

        # Redireciona para pagamento
        return redirect('pagamento_escolher', pedido_id=pedido.id)

    # GET: exibe formulário de checkout
    # Calcula totais para exibição
    itens_carrinho = []
    subtotal = Decimal('0.00')

    produto_ids = [
        _produto_id_do_item(item_key, item_data)
        for item_key, item_data in carrinho['itens'].items()
    ]
    produtos = Produto.objects.filter(id__in=produto_ids, disponivel=True)
    produtos_por_id = {str(prod.id): prod for prod in produtos}

    for item_key, item_data in carrinho['itens'].items():
        pid = _produto_id_do_item(item_key, item_data)
        produto = produtos_por_id.get(pid)
        if produto:
            quantidade = item_data['quantidade']
            preco_unitario = Decimal(str(item_data.get('preco_unitario', _preco_padrao_sabor(produto))))
            item_subtotal = preco_unitario * quantidade
            subtotal += item_subtotal
            sabores_nomes = item_data.get('sabores_nomes', [])
            itens_carrinho.append({
                'item_key': item_key,
                'produto': produto,
                'quantidade': quantidade,
                'preco_base': Decimal(str(item_data.get('preco_base', preco_unitario))),
                'adicional_sabores': Decimal(str(item_data.get('adicional_sabores', '0'))),
                'preco_unitario': preco_unitario,
                'tamanho_nome': item_data.get('tamanho_nome', ''),
                'sabores_nomes': sabores_nomes,
                'observacao': item_data.get('observacao', ''),
                'subtotal': item_subtotal,
            })

    tipo_entrega_inicial = request.GET.get('tipo_entrega', 'delivery')
    if tipo_entrega_inicial not in ('delivery', 'retirada'):
        tipo_entrega_inicial = 'delivery'

    taxa_entrega = restaurante.taxa_entrega if tipo_entrega_inicial == 'delivery' else Decimal('0.00')
    imposto = round(subtotal * restaurante.taxa_imposto / 100, 2)
    total = subtotal + taxa_entrega + imposto

    return render(request, 'pedidos/checkout.html', {
        'itens': itens_carrinho,
        'restaurante': restaurante,
        'subtotal': subtotal,
        'taxa_entrega': taxa_entrega,
        'imposto': imposto,
        'total': total,
        'tipo_entrega_inicial': tipo_entrega_inicial,
    })


def acompanhar_pedido(request, pedido_id):
    """
    Página pública de acompanhamento de pedido.

    Otimizações:
    - Big O (Cap. 1): select_related evita queries extras para restaurante
    - BFS (Cap. 6): mostra caminho até conclusão e próximo passo
    """
    pedido = get_object_or_404(
        Pedido.objects.select_related('restaurante'),
        id=pedido_id
    )

    # BFS (Cap. 6): informações de progresso
    nomes_status = dict(Pedido.STATUS_CHOICES)
    caminho = pedido.caminho_ate_status('concluido')

    return render(request, 'pedidos/acompanhar.html', {
        'pedido': pedido,
        'restaurante': pedido.restaurante,
        'passos_para_concluir': pedido.passos_para_concluir,
        'caminho_conclusao': [nomes_status.get(s, s) for s in caminho],
    })


def acompanhar_pedido_status(request, pedido_id):
    """
    Endpoint AJAX que retorna o status atual do pedido como JSON.
    Usado para polling na pagina de acompanhamento.

    Big O (Cap. 1): .only() carrega apenas campos necessários
    ao invés de todos os campos do model. Reduz transferência de dados.
    """
    pedido = get_object_or_404(
        Pedido.objects.only('id', 'status'),
        id=pedido_id
    )
    return JsonResponse({
        'status': pedido.status,
        'status_display': pedido.get_status_display(),
        'proximo_passo': pedido.proximo_passo,
        'passos_para_concluir': pedido.passos_para_concluir,
    })


@require_POST
def concluir_pedido_cliente(request, pedido_id):
    """
    Permite ao cliente marcar o pedido como concluído na tela de acompanhamento.

    Regras:
    - Só conclui se estiver em entrega.
    - Se existir registro de Entrega, sincroniza para status "entregue".
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if pedido.status != 'entrega':
        messages.warning(request, 'Este pedido ainda não está pronto para conclusão.')
        return redirect('acompanhar_pedido', pedido_id=pedido.id)

    entrega = Entrega.objects.filter(pedido=pedido).first()
    if entrega and entrega.status != 'entregue':
        entrega.status = 'entregue'
        entrega.save()
    else:
        pedido._skip_status_validation = True
        pedido.status = 'concluido'
        pedido.save()

    messages.success(request, 'Pedido marcado como concluído. Obrigado!')
    return redirect('acompanhar_pedido', pedido_id=pedido.id)
