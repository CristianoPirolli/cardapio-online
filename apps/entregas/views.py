# =============================================================================
# apps/entregas/views.py - Views HTML para gestão de entregas no painel
#
# Views para:
# - Lista de entregas do restaurante
# - Atribuição de entregador
# - CRUD de entregadores
# - Atualização de status de entrega
# =============================================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q

from apps.restaurantes.models import Restaurante
from apps.core.algorithms import (
    ranking_entregadores,
    dijkstra_melhor_entregador,
    dijkstra_estimar_tempo_entrega,
)
from .models import Entregador, Entrega
from .forms import EntregadorForm


def _restaurante_do_proprietario(user):
    return Restaurante.objects.filter(proprietario=user).first()


def _entregador_do_usuario(user):
    return Entregador.objects.filter(usuario=user, ativo=True).first()


@login_required
def painel_entregas(request):
    """Lista entregas do restaurante com filtros de status."""
    restaurante = _restaurante_do_proprietario(request.user)
    if not restaurante:
        messages.warning(request, 'Acesso disponível apenas para gestores de restaurante.')
        return redirect('home')
    entregas = Entrega.objects.filter(
        pedido__restaurante=restaurante
    ).select_related('pedido', 'entregador').order_by('-criado_em')

    # Filtro por status
    status_filtro = request.GET.get('status')
    if status_filtro:
        entregas = entregas.filter(status=status_filtro)

    return render(request, 'entregas/entregas.html', {
        'restaurante': restaurante,
        'entregas': entregas,
        'status_filtro': status_filtro,
    })


@login_required
def painel_entregadores(request):
    """Lista entregadores do restaurante."""
    restaurante = _restaurante_do_proprietario(request.user)
    if not restaurante:
        messages.warning(request, 'Acesso disponível apenas para gestores de restaurante.')
        return redirect('home')
    entregadores = Entregador.objects.filter(restaurante=restaurante)

    return render(request, 'entregas/entregadores.html', {
        'restaurante': restaurante,
        'entregadores': entregadores,
    })


@login_required
def atribuir_entregador(request, entrega_id):
    """
    Atribui um entregador a uma entrega.

    Otimização com Dijkstra (Cap. 7):
    - Rankeia entregadores por "custo" ponderado usando min-heap
    - Fatores: tipo de veículo + entregas ativas pendentes
    - Sugere o melhor entregador automaticamente
    - Complexidade: O(n log n) vs O(n²) sem heap
    """
    restaurante = _restaurante_do_proprietario(request.user)
    if not restaurante:
        messages.warning(request, 'Acesso disponível apenas para gestores de restaurante.')
        return redirect('home')
    entrega = get_object_or_404(
        Entrega, id=entrega_id, pedido__restaurante=restaurante
    )

    if request.method == 'POST':
        entregador_id = request.POST.get('entregador_id')
        entregador = get_object_or_404(
            Entregador, id=entregador_id, restaurante=restaurante
        )
        entrega.entregador = entregador
        entrega.status = 'coletado'
        entrega.save()

        # Dijkstra: estima tempo de entrega baseado no veículo
        tempo_estimado = dijkstra_estimar_tempo_entrega(
            entregador.veiculo,
            distancia_km=restaurante.raio_entrega_km / 2,  # média do raio
        )
        messages.success(
            request,
            f'Entregador {entregador.nome} atribuído! '
            f'Tempo estimado: ~{tempo_estimado} min'
        )
        return redirect('painel_entregas')

    entregadores = Entregador.objects.filter(
        restaurante=restaurante, disponivel=True, ativo=True
    )

    # -----------------------------------------------------------------------
    # Dijkstra (Cap. 7): Ranking inteligente de entregadores
    #
    # Calcula o "custo" de cada entregador usando uma min-heap:
    # custo = peso_veiculo + (entregas_ativas * 1.5)
    #
    # Sem Dijkstra: lista simples sem ordenação inteligente
    # Com Dijkstra: ranking por custo ponderado em O(n log n)
    # -----------------------------------------------------------------------

    # Tabela Hash (Cap. 5): conta entregas ativas por entregador em 1 query
    # Antes: faria N queries (uma por entregador) = O(n)
    # Agora: 1 query com annotate + dict comprehension = O(1) no banco
    entregas_ativas_qs = Entrega.objects.filter(
        entregador__in=entregadores,
        status__in=['coletado', 'em_transito'],
    ).values('entregador_id').annotate(total=Count('id'))

    entregas_ativas_por_entregador = {
        item['entregador_id']: item['total']
        for item in entregas_ativas_qs
    }

    # Dijkstra: gera ranking com custo e tempo estimado
    ranking = ranking_entregadores(
        list(entregadores),
        entregas_ativas_por_entregador,
    )

    # Melhor sugestão automática
    melhor = dijkstra_melhor_entregador(
        list(entregadores),
        entregas_ativas_por_entregador,
    )

    return render(request, 'entregas/atribuir.html', {
        'restaurante': restaurante,
        'entrega': entrega,
        'entregadores': entregadores,
        'ranking': ranking,
        'melhor_entregador': melhor,
    })


@login_required
def painel_entregador_criar(request):
    """Cria um novo entregador para o restaurante."""
    restaurante = _restaurante_do_proprietario(request.user)
    if not restaurante:
        messages.warning(request, 'Acesso disponível apenas para gestores de restaurante.')
        return redirect('home')

    if request.method == 'POST':
        form = EntregadorForm(request.POST, restaurante=restaurante)
        if form.is_valid():
            entregador = form.save(commit=False)
            entregador.restaurante = restaurante
            entregador.save()
            messages.success(request, f'Entregador "{entregador.nome}" cadastrado!')
            return redirect('painel_entregadores')
    else:
        form = EntregadorForm(restaurante=restaurante)

    return render(request, 'entregas/entregador_form.html', {
        'form': form,
        'restaurante': restaurante,
        'titulo': 'Novo Entregador',
    })


@login_required
def painel_entregador_editar(request, entregador_id):
    """Edita um entregador existente."""
    restaurante = _restaurante_do_proprietario(request.user)
    if not restaurante:
        messages.warning(request, 'Acesso disponível apenas para gestores de restaurante.')
        return redirect('home')
    entregador = get_object_or_404(
        Entregador, id=entregador_id, restaurante=restaurante
    )

    if request.method == 'POST':
        form = EntregadorForm(request.POST, instance=entregador, restaurante=restaurante)
        if form.is_valid():
            form.save()
            messages.success(request, f'Entregador "{entregador.nome}" atualizado!')
            return redirect('painel_entregadores')
    else:
        form = EntregadorForm(instance=entregador, restaurante=restaurante)

    return render(request, 'entregas/entregador_form.html', {
        'form': form,
        'restaurante': restaurante,
        'titulo': 'Editar Entregador',
        'entregador': entregador,
    })


@login_required
def painel_entregador_excluir(request, entregador_id):
    """Exclui um entregador (com confirmacao via POST)."""
    restaurante = _restaurante_do_proprietario(request.user)
    if not restaurante:
        messages.warning(request, 'Acesso disponível apenas para gestores de restaurante.')
        return redirect('home')
    entregador = get_object_or_404(
        Entregador, id=entregador_id, restaurante=restaurante
    )

    if request.method == 'POST':
        nome = entregador.nome
        entregador.delete()
        messages.success(request, f'Entregador "{nome}" removido!')
        return redirect('painel_entregadores')

    return render(request, 'painel/confirmar_exclusao.html', {
        'objeto': entregador,
        'tipo': 'entregador',
        'restaurante': restaurante,
    })


@login_required
def atualizar_status_entrega(request, entrega_id):
    """Atualiza o status de uma entrega via POST."""
    restaurante = _restaurante_do_proprietario(request.user)
    entregador = _entregador_do_usuario(request.user)

    if restaurante:
        entrega = get_object_or_404(Entrega, id=entrega_id, pedido__restaurante=restaurante)
    elif entregador:
        entrega = get_object_or_404(Entrega, id=entrega_id, entregador=entregador)
    else:
        messages.error(request, 'Você não tem permissão para atualizar esta entrega.')
        return redirect('home')

    if request.method == 'POST':
        novo_status = request.POST.get('status')
        if novo_status in dict(Entrega.STATUS_CHOICES):
            if entregador and novo_status not in ('em_transito', 'entregue'):
                messages.error(request, 'Entregador só pode marcar Em Trânsito ou Entregue.')
                return redirect('entregador_entregas')
            entrega.status = novo_status
            entrega.save()
            messages.success(
                request,
                f'Status da entrega atualizado para: {entrega.get_status_display()}'
            )
        else:
            messages.error(request, 'Status inválido.')

    if entregador and not restaurante:
        return redirect('entregador_entregas')
    return redirect('painel_entregas')


@login_required
def entregador_entregas(request):
    """
    Painel do entregador logado.
    Exibe apenas entregas atribuídas a ele.
    """
    entregador = _entregador_do_usuario(request.user)
    if not entregador:
        messages.warning(request, 'Esta conta não está vinculada a um entregador.')
        return redirect('home')

    entregas = Entrega.objects.filter(
        entregador=entregador
    ).select_related('pedido', 'pedido__restaurante').order_by('-criado_em')

    status_filtro = request.GET.get('status')
    if status_filtro:
        entregas = entregas.filter(status=status_filtro)

    return render(request, 'entregas/minhas_entregas.html', {
        'entregador': entregador,
        'entregas': entregas,
        'status_filtro': status_filtro,
    })
