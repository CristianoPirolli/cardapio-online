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

from django.conf import settings
from django.contrib import messages
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from apps.pedidos.models import Pedido

from .models import Pagamento
from .services import criar_pagamento_pix_manual

logger = logging.getLogger(__name__)

# Maximum comprovante file size: 10 MB
MAX_COMPROVANTE_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_COMPROVANTE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'pdf']


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
    criar_pagamento_pix_manual(pedido)

    pix_key = getattr(settings, 'PIX_KEY', '')

    return render(request, 'pagamentos/pagamento.html', {
        'pedido': pedido,
        'restaurante': pedido.restaurante,
        'pix_key': pix_key,
    })


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
        pagamento = criar_pagamento_pix_manual(pedido)

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
