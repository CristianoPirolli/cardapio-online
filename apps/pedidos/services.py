from decimal import Decimal

from django.db import transaction

from apps.produtos.models import Produto
from apps.core.algorithms import calcular_distancia_km, zona_entrega_para_distancia

from .models import ItemPedido, Pedido


class PedidoCheckoutError(Exception):
    """Erro de regra de negocio no fluxo de checkout."""


def validar_dados_checkout(dados):
    """Valida e normaliza os dados do cliente para checkout."""
    tipo_entrega = dados.get('tipo_entrega', 'delivery')
    if tipo_entrega not in ('delivery', 'retirada'):
        tipo_entrega = 'delivery'

    forma_pagamento = dados.get('forma_pagamento', 'pix')
    if forma_pagamento not in ('pix', 'dinheiro', 'cartao'):
        forma_pagamento = 'pix'

    cliente_nome = (dados.get('cliente_nome') or '').strip()
    cliente_telefone = (dados.get('cliente_telefone') or '').strip()
    cliente_email = (dados.get('cliente_email') or '').strip()
    endereco_entrega = (dados.get('endereco_entrega') or '').strip()
    observacoes = (dados.get('observacoes') or '').strip()

    if not cliente_nome or not cliente_telefone:
        raise PedidoCheckoutError('Nome e telefone sao obrigatorios.')

    if tipo_entrega == 'delivery' and not endereco_entrega:
        raise PedidoCheckoutError('Informe o endereco de entrega.')

    # Coordenadas opcionais (geocoding via frontend)
    lat_cliente = dados.get('lat_cliente')
    lng_cliente = dados.get('lng_cliente')
    try:
        lat_cliente = float(lat_cliente) if lat_cliente else None
        lng_cliente = float(lng_cliente) if lng_cliente else None
    except (TypeError, ValueError):
        lat_cliente = None
        lng_cliente = None

    return {
        'cliente_nome': cliente_nome,
        'cliente_telefone': cliente_telefone,
        'cliente_email': cliente_email,
        'endereco_entrega': endereco_entrega,
        'tipo_entrega': tipo_entrega,
        'forma_pagamento': forma_pagamento,
        'observacoes': observacoes,
        'lat_cliente': lat_cliente,
        'lng_cliente': lng_cliente,
    }


def montar_resumo_carrinho(restaurante, itens_sessao, tipo_entrega='delivery',
                           lat_cliente=None, lng_cliente=None):
    """
    Monta o resumo de itens/totais a partir da sessao e detecta itens invalidos.

    Se tipo_entrega='delivery' e o restaurante tiver coordenadas + zonas de entrega
    configuradas, a taxa de entrega é calculada pela zona correspondente à distância
    do cliente. Caso contrário, usa a taxa padrão do restaurante.
    """
    itens_sessao = itens_sessao or {}
    tipo_entrega = tipo_entrega if tipo_entrega in ('delivery', 'retirada') else 'delivery'

    produto_ids = list({
        _produto_id_do_item(item_key, item_data)
        for item_key, item_data in itens_sessao.items()
    })

    produtos_por_id = {
        str(prod.id): prod
        for prod in Produto.objects.filter(
            id__in=produto_ids,
            restaurante=restaurante,
            disponivel=True,
        ).select_related('categoria')
    }

    itens = []
    subtotal = Decimal('0.00')
    keys_invalidas = []
    ids_invalidos = []

    for item_key, item_data in itens_sessao.items():
        produto_id = _produto_id_do_item(item_key, item_data)
        produto = produtos_por_id.get(produto_id)
        if not produto:
            keys_invalidas.append(item_key)
            ids_invalidos.append(produto_id)
            continue

        quantidade = item_data.get('quantidade', 1)
        preco_unitario = Decimal(str(item_data.get('preco_unitario', _preco_padrao_sabor(produto))))
        item_subtotal = preco_unitario * quantidade
        subtotal += item_subtotal

        sabores_nomes = item_data.get('sabores_nomes', [])
        if not sabores_nomes:
            sabores_ids = item_data.get('sabores', [])
            sabores_nomes = [
                produtos_por_id[str(sid)].nome for sid in sabores_ids
                if str(sid) in produtos_por_id
            ]

        itens.append({
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

    nomes_invalidos = {
        str(prod.id): prod.nome
        for prod in Produto.objects.filter(id__in=ids_invalidos).only('id', 'nome')
    }
    itens_removidos = [nomes_invalidos.get(pid, f'Produto #{pid}') for pid in ids_invalidos]

    taxa_entrega_restaurante = Decimal(str(restaurante.taxa_entrega or 0))
    taxa_imposto_restaurante = Decimal(str(restaurante.taxa_imposto or 0))

    if tipo_entrega != 'delivery':
        taxa_entrega = Decimal('0.00')
        zona_nome = None
        fora_da_area = False
    else:
        zona_nome, taxa_entrega, fora_da_area = _calcular_taxa_por_zona(
            restaurante, lat_cliente, lng_cliente, taxa_entrega_restaurante
        )

    imposto = round(subtotal * taxa_imposto_restaurante / Decimal('100'), 2)
    total = subtotal + taxa_entrega + imposto

    return {
        'itens': itens,
        'subtotal': subtotal,
        'taxa_entrega': taxa_entrega,
        'imposto': imposto,
        'total': total,
        'keys_invalidas': keys_invalidas,
        'itens_removidos': itens_removidos,
        'zona_nome': zona_nome,
        'fora_da_area': fora_da_area,
    }


def criar_pedido_do_carrinho(restaurante, itens_sessao, dados_cliente):
    """
    Cria pedido + itens em transacao atomica.
    """
    resumo = montar_resumo_carrinho(
        restaurante=restaurante,
        itens_sessao=itens_sessao,
        tipo_entrega=dados_cliente['tipo_entrega'],
        lat_cliente=dados_cliente.get('lat_cliente'),
        lng_cliente=dados_cliente.get('lng_cliente'),
    )

    if not resumo['itens']:
        raise PedidoCheckoutError('Os itens do carrinho ficaram indisponiveis. Revise seu carrinho.')

    if dados_cliente['tipo_entrega'] == 'delivery' and resumo.get('fora_da_area'):
        raise PedidoCheckoutError(
            'Seu endereço está fora da área de entrega do restaurante.'
        )

    with transaction.atomic():
        pedido = Pedido.objects.create(
            restaurante=restaurante,
            cliente_nome=dados_cliente['cliente_nome'],
            cliente_telefone=dados_cliente['cliente_telefone'],
            cliente_email=dados_cliente['cliente_email'],
            endereco_entrega=dados_cliente['endereco_entrega'],
            tipo_entrega=dados_cliente['tipo_entrega'],
            forma_pagamento=dados_cliente.get('forma_pagamento', 'dinheiro'),
            observacoes=dados_cliente['observacoes'],
        )

        itens_pedido = [
            ItemPedido(
                pedido=pedido,
                produto=item['produto'],
                quantidade=item['quantidade'],
                preco_unitario=item['preco_unitario'],
                observacao=item['observacao'],
                tamanho_nome=item['tamanho_nome'],
                sabores_descricao=', '.join(item['sabores_nomes']),
            )
            for item in resumo['itens']
        ]
        ItemPedido.objects.bulk_create(itens_pedido)

        # Override taxa_entrega com o valor calculado pelas zonas
        pedido.calcular_totais(
            itens_prefetched=itens_pedido,
            taxa_entrega_override=resumo['taxa_entrega'] if dados_cliente['tipo_entrega'] == 'delivery' else None,
        )

        pedido_minimo = Decimal(str(restaurante.pedido_minimo or 0))
        if pedido.subtotal < pedido_minimo:
            raise PedidoCheckoutError(f'Pedido minimo e R$ {pedido_minimo:.2f}.')

    return pedido


def _calcular_taxa_por_zona(restaurante, lat_cliente, lng_cliente, taxa_padrao):
    """
    Calcula a taxa de entrega usando zonas por raio, se disponíveis.

    Retorna (zona_nome, taxa_entrega, fora_da_area).
    """
    zonas = restaurante.zonas_entrega.filter(ativo=True).order_by('raio_max_km')

    if not zonas.exists():
        # Sem zonas configuradas — usa taxa padrão
        return None, taxa_padrao, False

    if not restaurante.latitude or not restaurante.longitude:
        # Sem coordenadas do restaurante — usa taxa padrão
        return None, taxa_padrao, False

    if lat_cliente is None or lng_cliente is None:
        # Sem coordenadas do cliente — usa taxa padrão (será confirmado no checkout)
        return None, taxa_padrao, False

    distancia = calcular_distancia_km(
        restaurante.latitude, restaurante.longitude,
        lat_cliente, lng_cliente,
    )
    zona = zona_entrega_para_distancia(zonas, distancia)

    if zona is None:
        return None, Decimal('0.00'), True  # fora da área

    return zona.nome, zona.taxa_entrega, False


def _produto_id_do_item(item_key, item_data):
    if item_data.get('produto_id'):
        return str(item_data['produto_id'])
    return str(item_key).split(':')[0]


def _preco_padrao_sabor(produto):
    if produto.preco is not None:
        return produto.preco
    if produto.categoria and produto.categoria.adicional_sabor is not None:
        return produto.categoria.adicional_sabor
    return Decimal('0.00')
