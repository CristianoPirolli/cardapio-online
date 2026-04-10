# =============================================================================
# apps/pagamentos/views.py - Views HTML para pagamento PIX Manual
#
# Fluxo do cliente:
#   GET  /pagamentos/<id>/        → Exibe chave PIX + botão copiar
#   GET  /pagamentos/<id>/upload/ → Formulário de upload de comprovante
#   POST /pagamentos/<id>/upload/ → Processa upload, avança status para aguardando_confirmacao
#   GET  /pagamentos/sucesso/<id>/ → Página de sucesso
#   GET  /pagamentos/erro/<id>/   → Página de erro
# =============================================================================

import logging
import re

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.pedidos.models import Pedido
from apps.restaurantes.models import Restaurante

from .forms import ChavePixForm
from .models import ChavePix, ChavePixHistorico, Pagamento
from .services import criar_pagamento_pix_manual, confirmar_pix_manual, rejeitar_pix_manual

logger = logging.getLogger(__name__)

# Maximum comprovante file size: 10 MB
MAX_COMPROVANTE_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_COMPROVANTE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'pdf']


def _restaurante_do_usuario(request):
    return Restaurante.objects.filter(proprietario=request.user).first()


def _snapshot_chave(chave):
    return {
        'id': chave.id,
        'tipo': chave.tipo,
        'valor': chave.valor,
        'valor_normalizado': chave.valor_normalizado,
        'ativo': chave.ativo,
        'padrao': chave.padrao,
        'prioridade': chave.prioridade,
    }


def _registrar_historico(chave, acao, ator, antes=None, depois=None):
    ChavePixHistorico.objects.create(
        chave_pix=chave,
        acao=acao,
        ator=ator,
        antes=antes,
        depois=depois,
    )


def _contexto_painel_pix_keys(restaurante, form=None, edit_form=None, chave_editando=None):
    return {
        'restaurante': restaurante,
        'form': form or ChavePixForm(restaurante=restaurante),
        'edit_form': edit_form,
        'chave_editando': chave_editando,
        'chaves': ChavePix.objects.filter(restaurante=restaurante).order_by('prioridade', 'id'),
        'historico': ChavePixHistorico.objects.filter(
            chave_pix__restaurante=restaurante,
        ).select_related('ator', 'chave_pix').order_by('-criado_em', '-id'),
    }


def pagamento_pix_manual(request, pedido_id):
    """
    Página principal do pagamento PIX.
    Exibe a chave PIX fixa do estabelecimento com botão de cópia.
    O cliente copia, vai ao app do banco, e retorna para fazer o upload.

    A sessão não é necessária para retornar — o pedido_id na URL é o único estado.
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if pedido.pago:
        messages.info(request, 'Este pedido já foi confirmado.')
        return redirect('acompanhar_pedido', pedido_id=pedido.id)

    # Cria (ou reutiliza) o registro de pagamento pendente.
    # Idempotente: o cliente pode recarregar a página sem criar duplicatas.
    try:
        pagamento = criar_pagamento_pix_manual(pedido)
    except ValueError as exc:
        logger.warning(
            "pagamento_pix_manual: restaurante %s sem chave ativa (%s)",
            pedido.restaurante_id,
            exc,
        )
        messages.warning(
            request,
            'Este restaurante está sem chave PIX ativa no momento. Tente novamente em instantes.',
        )
        pagamento = None

    pix_key = pagamento.pix_chave_valor_snapshot if pagamento else ''
    pix_key_tipo = pagamento.pix_chave_tipo_snapshot if pagamento else ''
    pix_key_masked = _mascarar_chave_pix(pix_key_tipo, pix_key) if pix_key else ''
    feature_whatsapp_link = getattr(settings, 'FEATURE_WHATSAPP_LINK', False)

    pedido_url = request.build_absolute_uri()

    return render(request, 'pagamentos/pagamento.html', {
        'pedido': pedido,
        'restaurante': pedido.restaurante,
        'pix_key': pix_key,
        'pix_key_tipo': pix_key_tipo,
        'pix_key_masked': pix_key_masked,
        'feature_whatsapp_link': feature_whatsapp_link,
        'pedido_url': pedido_url,
    })


@login_required
def painel_pix_keys(request):
    restaurante = _restaurante_do_usuario(request)
    if not restaurante:
        messages.error(request, 'Acesso nao autorizado.')
        return redirect('home')

    edit_form = None
    chave_editando = None
    chave_editando_id = request.GET.get('edit')
    if chave_editando_id:
        chave_editando = ChavePix.objects.filter(
            restaurante=restaurante,
            id=chave_editando_id,
        ).first()
        if chave_editando:
            edit_form = ChavePixForm(instance=chave_editando, restaurante=restaurante)

    return render(
        request,
        'painel/pix_keys.html',
        _contexto_painel_pix_keys(
            restaurante=restaurante,
            edit_form=edit_form,
            chave_editando=chave_editando,
        ),
    )


@login_required
def painel_pix_keys_create(request):
    if request.method != 'POST':
        return redirect('painel_pix_keys')

    restaurante = _restaurante_do_usuario(request)
    if not restaurante:
        messages.error(request, 'Acesso nao autorizado.')
        return redirect('home')

    form = ChavePixForm(request.POST, restaurante=restaurante)
    if not form.is_valid():
        return render(request, 'painel/pix_keys.html', _contexto_painel_pix_keys(restaurante, form=form))

    try:
        with transaction.atomic():
            chave = form.save()
            if chave.ativo and chave.padrao:
                ChavePix.objects.filter(
                    restaurante=restaurante,
                    ativo=True,
                    padrao=True,
                ).exclude(id=chave.id).update(padrao=False)
            _registrar_historico(
                chave=chave,
                acao=ChavePixHistorico.Acao.CRIACAO,
                ator=request.user,
                antes={},
                depois=_snapshot_chave(chave),
            )
    except IntegrityError:
        form.add_error('prioridade', 'Ja existe uma chave ativa com essa prioridade.')
        return render(request, 'painel/pix_keys.html', _contexto_painel_pix_keys(restaurante, form=form))

    messages.success(request, 'Chave PIX cadastrada com sucesso.')
    return redirect('painel_pix_keys')


@login_required
def painel_pix_keys_edit(request, chave_id):
    if request.method != 'POST':
        return redirect('painel_pix_keys')

    restaurante = _restaurante_do_usuario(request)
    if not restaurante:
        messages.error(request, 'Acesso nao autorizado.')
        return redirect('home')

    chave = get_object_or_404(ChavePix, id=chave_id, restaurante=restaurante)
    antes = _snapshot_chave(chave)
    form = ChavePixForm(request.POST, instance=chave, restaurante=restaurante)

    if not form.is_valid():
        return render(
            request,
            'painel/pix_keys.html',
            _contexto_painel_pix_keys(
                restaurante,
                edit_form=form,
                chave_editando=chave,
            ),
        )

    try:
        with transaction.atomic():
            chave_atualizada = form.save()
            if chave_atualizada.ativo and chave_atualizada.padrao:
                ChavePix.objects.filter(
                    restaurante=restaurante,
                    ativo=True,
                    padrao=True,
                ).exclude(id=chave_atualizada.id).update(padrao=False)
            _registrar_historico(
                chave=chave_atualizada,
                acao=ChavePixHistorico.Acao.EDICAO,
                ator=request.user,
                antes=antes,
                depois=_snapshot_chave(chave_atualizada),
            )
    except IntegrityError:
        form.add_error('prioridade', 'Ja existe uma chave ativa com essa prioridade.')
        return render(
            request,
            'painel/pix_keys.html',
            _contexto_painel_pix_keys(
                restaurante,
                edit_form=form,
                chave_editando=chave,
            ),
        )

    messages.success(request, 'Chave PIX atualizada com sucesso.')
    return redirect('painel_pix_keys')


@login_required
def painel_pix_keys_activate(request, chave_id):
    if request.method != 'POST':
        return redirect('painel_pix_keys')

    restaurante = _restaurante_do_usuario(request)
    if not restaurante:
        messages.error(request, 'Acesso nao autorizado.')
        return redirect('home')

    chave = get_object_or_404(ChavePix, id=chave_id, restaurante=restaurante)
    antes = _snapshot_chave(chave)

    try:
        with transaction.atomic():
            chave.ativo = True
            if chave.padrao:
                ChavePix.objects.filter(
                    restaurante=restaurante,
                    ativo=True,
                    padrao=True,
                ).exclude(id=chave.id).update(padrao=False)
            chave.save(update_fields=['ativo', 'atualizado_em'])
            _registrar_historico(
                chave=chave,
                acao=ChavePixHistorico.Acao.ATIVACAO,
                ator=request.user,
                antes=antes,
                depois=_snapshot_chave(chave),
            )
    except IntegrityError:
        messages.error(request, 'Nao foi possivel ativar a chave devido a conflito de prioridade ativa.')
        return redirect('painel_pix_keys')

    messages.success(request, 'Chave PIX ativada.')
    return redirect('painel_pix_keys')


@login_required
def painel_pix_keys_deactivate(request, chave_id):
    if request.method != 'POST':
        return redirect('painel_pix_keys')

    restaurante = _restaurante_do_usuario(request)
    if not restaurante:
        messages.error(request, 'Acesso nao autorizado.')
        return redirect('home')

    chave = get_object_or_404(ChavePix, id=chave_id, restaurante=restaurante)
    antes = _snapshot_chave(chave)
    with transaction.atomic():
        chave.ativo = False
        chave.padrao = False
        chave.save(update_fields=['ativo', 'padrao', 'atualizado_em'])
        _registrar_historico(
            chave=chave,
            acao=ChavePixHistorico.Acao.DESATIVACAO,
            ator=request.user,
            antes=antes,
            depois=_snapshot_chave(chave),
        )

    messages.success(request, 'Chave PIX desativada.')
    return redirect('painel_pix_keys')


@login_required
def painel_pix_keys_set_default(request, chave_id):
    if request.method != 'POST':
        return redirect('painel_pix_keys')

    restaurante = _restaurante_do_usuario(request)
    if not restaurante:
        messages.error(request, 'Acesso nao autorizado.')
        return redirect('home')

    chave = get_object_or_404(ChavePix, id=chave_id, restaurante=restaurante)
    if not chave.ativo:
        messages.error(request, 'Ative a chave antes de defini-la como padrao.')
        return redirect('painel_pix_keys')

    antes = _snapshot_chave(chave)
    with transaction.atomic():
        ChavePix.objects.filter(
            restaurante=restaurante,
            ativo=True,
            padrao=True,
        ).exclude(id=chave.id).update(padrao=False)
        chave.padrao = True
        chave.save(update_fields=['padrao', 'atualizado_em'])
        _registrar_historico(
            chave=chave,
            acao=ChavePixHistorico.Acao.PADRAO,
            ator=request.user,
            antes=antes,
            depois=_snapshot_chave(chave),
        )

    messages.success(request, 'Chave PIX definida como padrao.')
    return redirect('painel_pix_keys')


@login_required
def painel_pix_keys_set_priority(request, chave_id):
    if request.method != 'POST':
        return redirect('painel_pix_keys')

    restaurante = _restaurante_do_usuario(request)
    if not restaurante:
        messages.error(request, 'Acesso nao autorizado.')
        return redirect('home')

    chave = get_object_or_404(ChavePix, id=chave_id, restaurante=restaurante)
    prioridade_raw = request.POST.get('prioridade', '').strip()
    try:
        nova_prioridade = int(prioridade_raw)
    except (TypeError, ValueError):
        messages.error(request, 'Prioridade invalida.')
        return redirect('painel_pix_keys')

    if nova_prioridade < 1:
        messages.error(request, 'Prioridade deve ser maior ou igual a 1.')
        return redirect('painel_pix_keys')

    antes = _snapshot_chave(chave)
    chave.prioridade = nova_prioridade
    try:
        chave.full_clean()
        chave.save(update_fields=['prioridade', 'valor_normalizado', 'atualizado_em'])
    except (ValidationError, IntegrityError):
        messages.error(request, 'Ja existe uma chave ativa com essa prioridade.')
        return redirect('painel_pix_keys')

    _registrar_historico(
        chave=chave,
        acao=ChavePixHistorico.Acao.PRIORIDADE,
        ator=request.user,
        antes=antes,
        depois=_snapshot_chave(chave),
    )
    messages.success(request, 'Prioridade da chave PIX atualizada.')
    return redirect('painel_pix_keys')


def upload_comprovante(request, pedido_id):
    """
    Formulário de upload do comprovante de pagamento.

    GET:  Exibe o formulário de upload.
    POST: Valida o arquivo (tipo e tamanho), salva em Pagamento.comprovante,
          avança pedido.status para 'aguardando_confirmacao'.
          Não define pedido.pago=True — isso é responsabilidade do restaurante.
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if pedido.pago:
        return redirect('acompanhar_pedido', pedido_id=pedido.id)

    if pedido.status not in ('aguardando', 'aguardando_confirmacao'):
        messages.warning(request, 'Seu pedido está em um estado que não permite upload de comprovante.')
        return redirect('acompanhar_pedido', pedido_id=pedido.id)

    pagamento = Pagamento.objects.filter(
        pedido=pedido,
        gateway='pix_manual',
        status='pendente',
    ).first()

    if not pagamento:
        # Segurança: se o cliente chegou aqui sem passar pela página de PIX,
        # cria o registro de pagamento agora.
        try:
            pagamento = criar_pagamento_pix_manual(pedido)
        except ValueError:
            messages.error(
                request,
                'Não foi possível iniciar o pagamento PIX porque o restaurante está sem chave ativa.',
            )
            return redirect('acompanhar_pedido', pedido_id=pedido.id)

    if request.method == 'POST':
        arquivo = request.FILES.get('comprovante')

        if not arquivo:
            messages.error(request, 'Selecione um arquivo de comprovante.')
            return render(request, 'pagamentos/pix_upload.html', {
                'pedido': pedido,
                'restaurante': pedido.restaurante,
            })

        # Validação de tamanho (max 10 MB)
        if arquivo.size > MAX_COMPROVANTE_SIZE_BYTES:
            messages.error(
                request,
                f'O arquivo é muito grande. Tamanho máximo: 10 MB. '
                f'Seu arquivo: {arquivo.size // 1024 // 1024} MB.'
            )
            return render(request, 'pagamentos/pix_upload.html', {
                'pedido': pedido,
                'restaurante': pedido.restaurante,
            })

        # Validação de extensão
        validator = FileExtensionValidator(
            allowed_extensions=ALLOWED_COMPROVANTE_EXTENSIONS
        )
        try:
            validator(arquivo)
        except ValidationError:
            messages.error(
                request,
                'Tipo de arquivo não permitido. '
                'Envie uma imagem (JPG, PNG, WEBP) ou PDF.'
            )
            return render(request, 'pagamentos/pix_upload.html', {
                'pedido': pedido,
                'restaurante': pedido.restaurante,
            })

        # Salva o comprovante e avança o status
        pagamento.comprovante = arquivo
        pagamento.save(update_fields=['comprovante', 'atualizado_em'])

        pedido.status = 'aguardando_confirmacao'
        pedido.save()  # BFS: aguardando → aguardando_confirmacao (valid)

        logger.info(
            "upload_comprovante: pedido %s comprovante recebido, aguardando_confirmacao",
            pedido.id
        )
        messages.success(
            request,
            'Comprovante enviado com sucesso! '
            'O restaurante irá verificar seu pagamento em breve.'
        )
        return redirect('pagamento_sucesso', pedido_id=pedido.id)

    return render(request, 'pagamentos/pix_upload.html', {
        'pedido': pedido,
        'restaurante': pedido.restaurante,
        'pagamento': pagamento,
    })


def pagamento_sucesso(request, pedido_id):
    """Página exibida após o cliente submeter o comprovante."""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, 'pagamentos/sucesso.html', {
        'pedido': pedido,
        'restaurante': pedido.restaurante,
    })


def pagamento_erro(request, pedido_id):
    """Página de erro genérica."""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, 'pagamentos/erro.html', {
        'pedido': pedido,
        'restaurante': pedido.restaurante,
    })


@login_required
def aceitar_pix(request, pedido_id):
    """
    Restaurante aceita o comprovante PIX.
    POST only. Calls confirmar_pix_manual(), then redirects to painel_pedido_detalhe.
    Only accessible to logged-in restaurant owner.
    """
    from apps.restaurantes.models import Restaurante

    restaurante = Restaurante.objects.filter(proprietario=request.user).first()
    if not restaurante:
        messages.error(request, 'Acesso não autorizado.')
        return redirect('home')

    pedido = get_object_or_404(
        Pedido, id=pedido_id, restaurante=restaurante,
        status='aguardando_confirmacao'
    )

    pagamento = Pagamento.objects.filter(
        pedido=pedido, gateway='pix_manual', status='pendente'
    ).first()

    if not pagamento:
        messages.error(request, 'Pagamento PIX não encontrado para este pedido.')
        return redirect('painel_pedido_detalhe', pedido_id=pedido.id)

    try:
        confirmar_pix_manual(pagamento)
        messages.success(request, f'Pedido #{pedido.id} confirmado! Entrando na fila de produção.')
    except Exception as exc:
        logger.error("aceitar_pix: %s", exc)
        messages.error(request, f'Erro ao confirmar pagamento: {exc}')

    return redirect('painel_pedido_detalhe', pedido_id=pedido.id)


@login_required
def rejeitar_pix(request, pedido_id):
    """
    Restaurante rejeita o comprovante PIX.
    POST only. Calls rejeitar_pix_manual(), then redirects to painel_pedidos.
    """
    from apps.restaurantes.models import Restaurante

    restaurante = Restaurante.objects.filter(proprietario=request.user).first()
    if not restaurante:
        messages.error(request, 'Acesso não autorizado.')
        return redirect('home')

    pedido = get_object_or_404(
        Pedido, id=pedido_id, restaurante=restaurante,
        status='aguardando_confirmacao'
    )

    pagamento = Pagamento.objects.filter(
        pedido=pedido, gateway='pix_manual', status='pendente'
    ).first()

    if pagamento:
        try:
            rejeitar_pix_manual(pagamento)
            messages.success(request, f'Pedido #{pedido.id} rejeitado e cancelado.')
        except Exception as exc:
            logger.error("rejeitar_pix: %s", exc)
            messages.error(request, f'Erro ao rejeitar pagamento: {exc}')
    else:
        messages.warning(request, 'Pagamento não encontrado; o pedido não foi alterado.')

    return redirect('painel_pedidos')


def _mascarar_chave_pix(tipo, valor):
    valor = (valor or '').strip()
    if not valor:
        return ''

    if tipo == 'email':
        usuario, separador, dominio = valor.partition('@')
        if not separador:
            return valor
        if len(usuario) <= 2:
            usuario_mask = '*' * len(usuario)
        else:
            usuario_mask = f"{usuario[:2]}{'*' * (len(usuario) - 2)}"
        return f'{usuario_mask}@{dominio}'

    if tipo == 'telefone':
        if len(valor) <= 6:
            return valor
        return f'{valor[:4]}***{valor[-3:]}'

    if tipo in {'cpf', 'cnpj'}:
        digitos = re.sub(r'\D', '', valor)
        if len(digitos) <= 4:
            return digitos
        return f"{'*' * (len(digitos) - 4)}{digitos[-4:]}"

    return valor
