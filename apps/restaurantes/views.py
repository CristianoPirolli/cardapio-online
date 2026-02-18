# =============================================================================
# apps/restaurantes/views.py - Views HTML do app restaurantes
#
# Views para:
# - Página inicial (landing page ou redirecionamento para cardápio)
# - Painel do restaurante (dashboard com métricas)
# - CRUD de restaurante via formulário
# =============================================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils import timezone

from .models import Restaurante
from .forms import RestauranteForm, TamanhoPizzaFormSet
from apps.produtos.forms import TipoSaborFormSet
from apps.pedidos.models import Pedido


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
    Página inicial do sistema.

    Se o request possui um restaurante (identificado pelo middleware multi-tenant),
    redireciona para o cardápio desse restaurante.
    Caso contrário, exibe a landing page com lista de restaurantes.
    """
    if request.restaurante:
        return redirect('cardapio_publico')

    restaurantes = Restaurante.objects.filter(ativo=True)[:12]
    return render(request, 'home.html', {'restaurantes': restaurantes})


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
    pedidos = Pedido.objects.filter(restaurante=restaurante)
    pedidos_hoje = pedidos.filter(criado_em__date=hoje)

    # Métricas gerais
    total_pedidos = pedidos.count()
    faturamento_total = pedidos.filter(
        status='concluido'
    ).aggregate(total=Sum('total'))['total'] or 0
    faturamento_hoje = pedidos_hoje.filter(
        status='concluido'
    ).aggregate(total=Sum('total'))['total'] or 0
    ticket_medio = faturamento_total / total_pedidos if total_pedidos > 0 else 0

    # Pedidos por status
    pedidos_por_status = pedidos.values('status').annotate(
        count=Count('id')
    ).order_by('status')

    # Pedidos recentes (últimos 10)
    pedidos_recentes = pedidos.order_by('-criado_em')[:10]

    context = {
        'restaurante': restaurante,
        'total_pedidos': total_pedidos,
        'pedidos_hoje': pedidos_hoje.count(),
        'faturamento_total': faturamento_total,
        'faturamento_hoje': faturamento_hoje,
        'ticket_medio': ticket_medio,
        'pedidos_por_status': pedidos_por_status,
        'pedidos_recentes': pedidos_recentes,
    }
    return render(request, 'painel/dashboard.html', context)


@login_required
def painel_configuracoes(request):
    """
    Página de configurações do restaurante.

    Permite editar informações do restaurante via formulário.
    """
    restaurante = _restaurante_do_usuario(request)
    if not restaurante:
        return _redirecionar_sem_restaurante(request)

    if request.method == 'POST':
        form = RestauranteForm(request.POST, request.FILES, instance=restaurante)
        tamanhos_formset = TamanhoPizzaFormSet(
            request.POST, instance=restaurante, prefix='tamanhos'
        )
        tipos_sabor_formset = TipoSaborFormSet(
            request.POST, instance=restaurante, prefix='tipos_sabor'
        )
        if form.is_valid() and tamanhos_formset.is_valid() and tipos_sabor_formset.is_valid():
            form.save()
            tamanhos_formset.save()
            tipos_sabor_formset.save()
            messages.success(request, 'Configurações atualizadas com sucesso!')
            return redirect('painel_configuracoes')
    else:
        form = RestauranteForm(instance=restaurante)
        tamanhos_formset = TamanhoPizzaFormSet(instance=restaurante, prefix='tamanhos')
        tipos_sabor_formset = TipoSaborFormSet(instance=restaurante, prefix='tipos_sabor')

    return render(request, 'painel/configuracoes.html', {
        'form': form,
        'tamanhos_formset': tamanhos_formset,
        'tipos_sabor_formset': tipos_sabor_formset,
        'restaurante': restaurante,
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

    pedidos = Pedido.objects.filter(restaurante=restaurante).order_by('-criado_em')

    # Filtro por status
    status_filtro = request.GET.get('status')
    if status_filtro:
        pedidos = pedidos.filter(status=status_filtro)

    # Filtro por data
    data_filtro = request.GET.get('data')
    if data_filtro:
        pedidos = pedidos.filter(criado_em__date=data_filtro)

    return render(request, 'painel/pedidos.html', {
        'restaurante': restaurante,
        'pedidos': pedidos,
        'status_filtro': status_filtro,
    })


@login_required
def painel_pedido_detalhe(request, pedido_id):
    """
    Detalhe de um pedido específico com opção de atualizar status.
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

    return render(request, 'painel/pedido_detalhe.html', {
        'restaurante': restaurante,
        'pedido': pedido,
    })
