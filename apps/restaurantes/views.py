# =============================================================================
# apps/restaurantes/views.py - Views HTML do app restaurantes
#
# Views para:
# - Página inicial (landing page ou redirecionamento para cardápio)
# - Painel do restaurante (dashboard com métricas)
# - CRUD de restaurante via formulário
# =============================================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q, F, Avg, DurationField, ExpressionWrapper, DecimalField
from django.utils import timezone
from django.db.models.functions import TruncDate, ExtractHour
from datetime import datetime, timedelta
from collections import Counter

from .models import Restaurante
from .forms import RestauranteForm, TamanhoPizzaFormSet, ZonaEntregaFormSet
from apps.pedidos.models import Pedido, ItemPedido
from apps.core.algorithms import GRAFO_STATUS_PEDIDO
from apps.pagamentos.models import ChavePix
from apps.pagamentos.forms import ChavePixForm


def _restaurante_do_usuario(request):
    """Retorna o restaurante do usuário logado ou None."""
    return Restaurante.objects.filter(proprietario=request.user).first()


def _redirecionar_sem_restaurante(request):
    messages.warning(
        request,
        'Sua conta ainda não está vinculada a um restaurante. '
        'Solicite o vínculo ao administrador master.'
    )
    return redirect('home')


def home(request):
    """
    Página inicial simplificada.

    Exibe apenas um card de estabelecimento com botão para abrir o cardápio.
    Prioriza o restaurante do tenant atual; se não houver, usa o primeiro ativo.
    """
    restaurante = request.restaurante
    if not restaurante:
        restaurante = Restaurante.objects.filter(ativo=True).first()

    return render(request, 'home.html', {'restaurante': restaurante})


@login_required
def painel_dashboard(request):
    """
    Dashboard principal do painel do restaurante.

    Exibe métricas:
    - Total de pedidos (geral e do dia)
    - Faturamento (geral e do dia)
    - Ticket médio
    - Pedidos recentes
    - Pedidos por status
    """
    restaurante = _restaurante_do_usuario(request)
    if not restaurante:
        return _redirecionar_sem_restaurante(request)

    hoje = timezone.localdate()
    # Regra de negócio: estabelecimento só opera pedidos com pagamento aprovado.
    pedidos = Pedido.objects.filter(restaurante=restaurante, pago=True)
    pedidos_hoje = pedidos.filter(criado_em__date=hoje)

    # Métricas gerais
    total_pedidos = pedidos.count()
    pedidos_concluidos = pedidos.filter(status='concluido').count()
    pedidos_cancelados = pedidos.filter(status='cancelado').count()
    faturamento_total = pedidos.filter(
        status='concluido'
    ).aggregate(total=Sum('total'))['total'] or 0
    faturamento_hoje = pedidos_hoje.filter(
        status='concluido'
    ).aggregate(total=Sum('total'))['total'] or 0
    ticket_medio = faturamento_total / total_pedidos if total_pedidos > 0 else 0
    taxa_conclusao = (pedidos_concluidos / total_pedidos * 100) if total_pedidos > 0 else 0
    taxa_cancelamento = (pedidos_cancelados / total_pedidos * 100) if total_pedidos > 0 else 0

    # Pedidos por status
    pedidos_por_status_qs = pedidos.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    status_labels = dict(Pedido.STATUS_CHOICES)
    pedidos_por_status = [
        {
            'status': item['status'],
            'label': status_labels.get(item['status'], item['status'].title()),
            'count': item['count'],
            'percentual': (item['count'] / total_pedidos * 100) if total_pedidos > 0 else 0,
        }
        for item in pedidos_por_status_qs
    ]

    # Tendência diária dos últimos 7 dias (pedidos e faturamento concluído)
    inicio_periodo = hoje - timedelta(days=6)
    pedidos_7d = pedidos.filter(criado_em__date__gte=inicio_periodo, criado_em__date__lte=hoje)
    faturamento_7_dias = pedidos_7d.filter(status='concluido').aggregate(total=Sum('total'))['total'] or 0
    pedidos_por_dia_qs = pedidos_7d.annotate(dia=TruncDate('criado_em')).values('dia').annotate(
        total_pedidos=Count('id'),
        faturamento=Sum('total', filter=Q(status='concluido')),
    ).order_by('dia')

    pedidos_por_dia_map = {
        item['dia']: {
            'total_pedidos': item['total_pedidos'],
            'faturamento': item['faturamento'] or 0,
        }
        for item in pedidos_por_dia_qs
    }
    tendencia_7_dias = []
    for i in range(7):
        dia = inicio_periodo + timedelta(days=i)
        dados_dia = pedidos_por_dia_map.get(dia, {'total_pedidos': 0, 'faturamento': 0})
        tendencia_7_dias.append({
            'data': dia,
            'total_pedidos': dados_dia['total_pedidos'],
            'faturamento': dados_dia['faturamento'],
        })

    maior_volume_dia = max((item['total_pedidos'] for item in tendencia_7_dias), default=0)

    # Mix de tipo de entrega
    tipos_entrega_qs = pedidos.values('tipo_entrega').annotate(count=Count('id')).order_by('tipo_entrega')
    labels_tipo_entrega = dict(Pedido.TIPO_ENTREGA_CHOICES)
    tipos_entrega = [
        {
            'tipo': item['tipo_entrega'],
            'label': labels_tipo_entrega.get(item['tipo_entrega'], item['tipo_entrega'].title()),
            'count': item['count'],
            'percentual': (item['count'] / total_pedidos * 100) if total_pedidos > 0 else 0,
        }
        for item in tipos_entrega_qs
    ]

    # Ranking de sabores e combinações de pizza
    itens_pizza = ItemPedido.objects.filter(
        pedido__restaurante=restaurante,
        pedido__pago=True,
    ).exclude(
        pedido__status='cancelado'
    ).exclude(
        sabores_descricao=''
    ).values_list('sabores_descricao', 'quantidade')

    contador_sabores = Counter()
    contador_combinacoes = Counter()

    for sabores_descricao, quantidade in itens_pizza:
        sabores = [s.strip() for s in sabores_descricao.split(',') if s.strip()]
        if not sabores:
            continue

        for sabor in sabores:
            contador_sabores[sabor] += quantidade

        if len(sabores) > 1:
            combinacao = ' + '.join(sorted(sabores))
            contador_combinacoes[combinacao] += quantidade

    sabores_ordenados = sorted(contador_sabores.items(), key=lambda x: x[1], reverse=True)
    sabores_mais_pedidos = [
        {'nome': nome, 'count': count}
        for nome, count in sabores_ordenados[:5]
    ]
    sabores_menos_pedidos = [
        {'nome': nome, 'count': count}
        for nome, count in sorted(contador_sabores.items(), key=lambda x: (x[1], x[0]))[:5]
    ]

    combinacoes_ordenadas = sorted(contador_combinacoes.items(), key=lambda x: x[1], reverse=True)
    combinacoes_mais_pedidas = [
        {'nome': nome, 'count': count}
        for nome, count in combinacoes_ordenadas[:5]
    ]
    combinacoes_menos_pedidas = [
        {'nome': nome, 'count': count}
        for nome, count in sorted(contador_combinacoes.items(), key=lambda x: (x[1], x[0]))[:5]
    ]

    maior_sabor_count = max((item['count'] for item in sabores_mais_pedidos), default=0)
    maior_combinacao_count = max((item['count'] for item in combinacoes_mais_pedidas), default=0)

    # Faixa horária de pedidos (0h-23h)
    pedidos_por_hora_qs = pedidos_7d.annotate(hora=ExtractHour('criado_em')).values('hora').annotate(
        count=Count('id')
    ).order_by('hora')
    pedidos_por_hora_map = {int(item['hora']): item['count'] for item in pedidos_por_hora_qs if item['hora'] is not None}
    faixas_horarias = []
    for hora_inicio in range(0, 24, 3):
        hora_fim = hora_inicio + 2
        total_faixa = sum(pedidos_por_hora_map.get(h, 0) for h in range(hora_inicio, hora_fim + 1))
        faixas_horarias.append({
            'faixa': f'{hora_inicio:02d}h-{hora_fim:02d}h',
            'count': total_faixa,
        })
    maior_faixa_horaria_count = max((item['count'] for item in faixas_horarias), default=0)

    # Tempo médio de ciclo (criado -> atualizado) para pedidos concluídos
    duracao_expr = ExpressionWrapper(
        F('atualizado_em') - F('criado_em'),
        output_field=DurationField(),
    )
    tempo_medio_ciclo = pedidos.filter(status='concluido').annotate(
        duracao=duracao_expr
    ).aggregate(media=Avg('duracao'))['media']
    tempo_medio_ciclo_min = round(tempo_medio_ciclo.total_seconds() / 60, 1) if tempo_medio_ciclo else 0

    tempo_ciclo_por_status_qs = pedidos.filter(status__in=['recebido', 'preparo', 'entrega', 'concluido']).values('status').annotate(
        count=Count('id')
    )
    status_pipeline = {item['status']: item['count'] for item in tempo_ciclo_por_status_qs}

    # Faturamento por categoria (proxy de margem sem custo cadastrado)
    faturamento_item_expr = ExpressionWrapper(
        F('preco_unitario') * F('quantidade'),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    categorias_qs = ItemPedido.objects.filter(
        pedido__restaurante=restaurante,
        pedido__pago=True,
        pedido__status='concluido',
        produto__categoria__isnull=False,
    ).values('produto__categoria__nome').annotate(
        faturamento=Sum(faturamento_item_expr),
        itens=Sum('quantidade')
    ).order_by('-faturamento')[:6]
    categorias_faturamento = [
        {
            'nome': item['produto__categoria__nome'],
            'faturamento': item['faturamento'] or 0,
            'itens': item['itens'] or 0,
        }
        for item in categorias_qs
    ]
    maior_categoria_faturamento = max((item['faturamento'] for item in categorias_faturamento), default=0)

    # Pedidos recentes: separar em pendentes e finalizados
    pedidos_pendentes = pedidos.exclude(status__in=['concluido', 'cancelado']).select_related('restaurante').order_by('-criado_em')[:10]
    pedidos_finalizados = pedidos.filter(status__in=['concluido', 'cancelado']).select_related('restaurante').order_by('-criado_em')[:10]

    context = {
        'restaurante': restaurante,
        'total_pedidos': total_pedidos,
        'pedidos_hoje': pedidos_hoje.count(),
        'faturamento_total': faturamento_total,
        'faturamento_hoje': faturamento_hoje,
        'ticket_medio': ticket_medio,
        'pedidos_concluidos': pedidos_concluidos,
        'pedidos_cancelados': pedidos_cancelados,
        'taxa_conclusao': taxa_conclusao,
        'taxa_cancelamento': taxa_cancelamento,
        'pedidos_por_status': pedidos_por_status,
        'tendencia_7_dias': tendencia_7_dias,
        'faturamento_7_dias': faturamento_7_dias,
        'maior_volume_dia': maior_volume_dia,
        'tipos_entrega': tipos_entrega,
        'sabores_mais_pedidos': sabores_mais_pedidos,
        'sabores_menos_pedidos': sabores_menos_pedidos,
        'combinacoes_mais_pedidas': combinacoes_mais_pedidas,
        'combinacoes_menos_pedidas': combinacoes_menos_pedidas,
        'maior_sabor_count': maior_sabor_count,
        'maior_combinacao_count': maior_combinacao_count,
        'faixas_horarias': faixas_horarias,
        'maior_faixa_horaria_count': maior_faixa_horaria_count,
        'tempo_medio_ciclo_min': tempo_medio_ciclo_min,
        'status_pipeline': status_pipeline,
        'categorias_faturamento': categorias_faturamento,
        'maior_categoria_faturamento': maior_categoria_faturamento,
        'pedidos_pendentes': pedidos_pendentes,
        'pedidos_finalizados': pedidos_finalizados,
    }
    return render(request, 'painel/dashboard.html', context)


@login_required
def painel_configuracoes(request):
    """
    Página de configurações do restaurante.

    Permite editar informações do restaurante, gerenciar zonas de entrega e chaves PIX.
    """
    restaurante = _restaurante_do_usuario(request)
    if not restaurante:
        return _redirecionar_sem_restaurante(request)

    if request.method == 'POST':
        form = RestauranteForm(request.POST, request.FILES, instance=restaurante)
        zonas_formset = ZonaEntregaFormSet(
            request.POST, instance=restaurante, prefix='zonas'
        )
        if form.is_valid() and zonas_formset.is_valid():
            form.save()
            zonas_formset.save()
            messages.success(request, 'Configurações atualizadas com sucesso!')
            return redirect('painel_configuracoes')
    else:
        form = RestauranteForm(instance=restaurante)
        zonas_formset = ZonaEntregaFormSet(instance=restaurante, prefix='zonas')

    # Contexto para chaves PIX (somente leitura + edição inline)
    pix_edit_form = None
    pix_chave_editando = None
    pix_chave_editando_id = request.GET.get('pix_edit')
    if pix_chave_editando_id:
        pix_chave_editando = ChavePix.objects.filter(
            restaurante=restaurante, id=pix_chave_editando_id
        ).first()
        if pix_chave_editando:
            pix_edit_form = ChavePixForm(instance=pix_chave_editando, restaurante=restaurante)

    return render(request, 'painel/configuracoes.html', {
        'form': form,
        'restaurante': restaurante,
        'zonas_formset': zonas_formset,
        'chaves': ChavePix.objects.filter(restaurante=restaurante).order_by('prioridade', 'id'),
        'pix_form': ChavePixForm(restaurante=restaurante),
        'pix_edit_form': pix_edit_form,
        'pix_chave_editando': pix_chave_editando,
    })


@login_required
def painel_pizzas(request):
    """
    Página de gerenciamento de pizzas.

    Permite editar:
    - Tamanhos de pizza (preço base, fatias, max. sabores etc.)
    """
    restaurante = _restaurante_do_usuario(request)
    if not restaurante:
        return _redirecionar_sem_restaurante(request)

    if request.method == 'POST':
        tamanhos_formset = TamanhoPizzaFormSet(
            request.POST, instance=restaurante, prefix='tamanhos'
        )
        if tamanhos_formset.is_valid():
            tamanhos_formset.save()
            messages.success(request, 'Configurações de pizzas atualizadas com sucesso!')
            return redirect('painel_pizzas')
    else:
        tamanhos_formset = TamanhoPizzaFormSet(instance=restaurante, prefix='tamanhos')

    return render(request, 'painel/pizzas.html', {
        'restaurante': restaurante,
        'tamanhos_formset': tamanhos_formset,
    })


@login_required
def painel_pedidos(request):
    """
    Listagem de pedidos do restaurante no painel administrativo.

    Permite filtrar por status e data.
    """
    restaurante = _restaurante_do_usuario(request)
    if not restaurante:
        return _redirecionar_sem_restaurante(request)

    # Pedidos em produção (já pagos)
    pedidos = Pedido.objects.filter(
        restaurante=restaurante,
        pago=True,
    ).select_related('restaurante').order_by('-criado_em')

    # Pedidos aguardando confirmação PIX (pago=False, status especial)
    pendentes_pix = Pedido.objects.filter(
        restaurante=restaurante,
        forma_pagamento='pix',
        status='aguardando_confirmacao',
    ).select_related('restaurante').order_by('-criado_em')

    # Filtro operacional por período para fila de revisão manual.
    periodo_ativo = request.GET.get('periodo', '').strip().lower()
    data_inicio = request.GET.get('data_inicio', '').strip()
    data_fim = request.GET.get('data_fim', '').strip()
    periodo_session_key = 'painel_pedidos_periodo_valido'
    filtros_periodo = {}

    def _parse_data_iso(valor):
        if not valor:
            return None
        try:
            return datetime.strptime(valor, '%Y-%m-%d').date()
        except ValueError:
            return None

    def _salvar_periodo_valido(payload):
        request.session[periodo_session_key] = payload
        request.session.modified = True

    def _filtros_por_periodo(periodo, inicio_custom='', fim_custom=''):
        hoje_local = timezone.localdate()
        if periodo == 'hoje':
            return {'criado_em__date': hoje_local}, {'periodo': 'hoje'}
        if periodo == 'ontem':
            return {'criado_em__date': hoje_local - timedelta(days=1)}, {'periodo': 'ontem'}
        if periodo == '7d':
            return {'criado_em__date__gte': hoje_local - timedelta(days=6)}, {'periodo': '7d'}
        if periodo == '30d':
            return {'criado_em__date__gte': hoje_local - timedelta(days=29)}, {'periodo': '30d'}
        if periodo != 'custom':
            return {}, None

        inicio = _parse_data_iso(inicio_custom)
        fim = _parse_data_iso(fim_custom)
        if not inicio or not fim or fim < inicio:
            return None, None
        return {
            'criado_em__date__gte': inicio,
            'criado_em__date__lte': fim,
        }, {
            'periodo': 'custom',
            'data_inicio': inicio.isoformat(),
            'data_fim': fim.isoformat(),
        }

    filtros_periodo, periodo_payload = _filtros_por_periodo(periodo_ativo, data_inicio, data_fim)
    if filtros_periodo is None:
        messages.error(request, 'Periodo personalizado invalido. Mantivemos o ultimo periodo valido.')
        ultimo_valido = request.session.get(periodo_session_key, {})
        periodo_ativo = ultimo_valido.get('periodo', '')
        data_inicio = ultimo_valido.get('data_inicio', '')
        data_fim = ultimo_valido.get('data_fim', '')
        filtros_periodo, _ = _filtros_por_periodo(periodo_ativo, data_inicio, data_fim)
        filtros_periodo = filtros_periodo or {}
    else:
        if periodo_payload:
            periodo_ativo = periodo_payload.get('periodo', periodo_ativo)
            data_inicio = periodo_payload.get('data_inicio', '')
            data_fim = periodo_payload.get('data_fim', '')
            _salvar_periodo_valido(periodo_payload)
        else:
            periodo_ativo = ''
            data_inicio = ''
            data_fim = ''

    if filtros_periodo:
        pendentes_pix = pendentes_pix.filter(**filtros_periodo)

    # Filtro por status
    status_filtro = request.GET.get('status')

    # Filtro por data
    data_filtro = request.GET.get('data')
    if data_filtro:
        pedidos = pedidos.filter(criado_em__date=data_filtro)

    if status_filtro == 'aguardando_confirmacao':
        pedidos_filtrados = pendentes_pix
    elif status_filtro:
        pedidos_filtrados = pedidos.filter(status=status_filtro)
    else:
        pedidos_filtrados = pedidos

    # Paginação: limita a 50 pedidos por página
    from django.core.paginator import Paginator
    paginator = Paginator(pedidos_filtrados, 50)
    page_number = request.GET.get('page')
    pedidos_page = paginator.get_page(page_number)

    return render(request, 'painel/pedidos.html', {
        'restaurante': restaurante,
        'pedidos': pedidos_page,
        'pendentes_pix': pendentes_pix if not status_filtro or status_filtro == 'aguardando_confirmacao' else [],
        'status_filtro': status_filtro,
        'periodo_ativo': periodo_ativo,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'paginator': paginator,
        'pendentes_pix_count': pendentes_pix.count(),
    })


@login_required
def painel_pedidos_abertos_count(request):
    """
    Retorna em JSON a quantidade de pedidos em aberto do restaurante logado.

    Considera em aberto: pedidos pagos com status diferente de concluído/cancelado.
    """
    restaurante = _restaurante_do_usuario(request)
    if not restaurante:
        return JsonResponse({'pedidos_abertos': 0})

    pedidos_abertos = Pedido.objects.filter(
        restaurante=restaurante,
        pago=True,
    ).exclude(
        status__in=['concluido', 'cancelado']
    ).count()

    return JsonResponse({'pedidos_abertos': pedidos_abertos})


@login_required
def painel_pedido_detalhe(request, pedido_id):
    """
    Detalhe de um pedido específico com opção de atualizar status.

    Otimizações:
    - BFS (Cap. 6): mostra próximo passo sugerido e status alcançáveis
    - Tabela Hash (Cap. 5): lookup O(1) para transições válidas
    """
    restaurante = _restaurante_do_usuario(request)
    if not restaurante:
        return _redirecionar_sem_restaurante(request)

    pedido = get_object_or_404(
        Pedido, id=pedido_id, restaurante=restaurante
    )

    if request.method == 'POST':
        novo_status = request.POST.get('status')
        if novo_status in dict(Pedido.STATUS_CHOICES):
            valido, msg = pedido.validar_transicao_status(novo_status)
            if valido:
                pedido.status = novo_status
                pedido.save()
                messages.success(request, f'Status atualizado para: {pedido.get_status_display()}')
            else:
                messages.error(request, msg)
            return redirect('painel_pedido_detalhe', pedido_id=pedido.id)

    # BFS (Cap. 6): informações de navegação do status
    nomes_status = dict(Pedido.STATUS_CHOICES)
    transicoes_diretas = GRAFO_STATUS_PEDIDO.get(pedido.status, [])
    caminho_conclusao = pedido.caminho_ate_status('concluido')

    # Add comprovante when awaiting PIX, and always expose audit trail only in detail.
    from apps.pagamentos.models import Pagamento, PagamentoRevisaoHistorico
    pagamento_pix = None
    if pedido.status == 'aguardando_confirmacao':
        pagamento_pix = Pagamento.objects.filter(
            pedido=pedido, gateway='pix_manual'
        ).first()
    historico_revisao_pagamento = list(
        PagamentoRevisaoHistorico.objects.filter(pedido=pedido)
        .only('acao', 'criado_em')
        .order_by('-criado_em', '-id')
    )

    return render(request, 'painel/pedido_detalhe.html', {
        'restaurante': restaurante,
        'pedido': pedido,
        # BFS: dados de navegação de status
        'proximo_passo': pedido.proximo_passo,
        'proximo_passo_nome': nomes_status.get(pedido.proximo_passo, ''),
        'passos_para_concluir': pedido.passos_para_concluir,
        'caminho_conclusao': [nomes_status.get(s, s) for s in caminho_conclusao],
        'transicoes_disponiveis': [
            {'status': s, 'nome': nomes_status.get(s, s)}
            for s in transicoes_diretas
        ],
        'pagamento_pix': pagamento_pix,
        'historico_revisao_pagamento': historico_revisao_pagamento,
    })
