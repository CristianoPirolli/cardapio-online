# =============================================================================
# apps/pagamentos/models.py - Model de Pagamento
#
# Registra cada tentativa/confirmação de pagamento associada a um pedido.
# Suporta Mercado Pago (cartão + PIX) e mock (simulação local).
# =============================================================================

import re
import uuid

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, validate_email
from django.db import models
from django.db.models import Q

from apps.pedidos.models import Pedido
from apps.restaurantes.models import Restaurante


class Pagamento(models.Model):
    """
    Registro de pagamento para um pedido.

    Tipos de gateway:
    - mercadopago: Checkout Pro (cartão) ou PIX via API do Mercado Pago
    - mock: Simulação local para desenvolvimento/testes

    Status:
    - pendente: Pagamento criado, aguardando confirmação
    - aprovado: Pagamento confirmado com sucesso
    - recusado: Pagamento recusado pelo gateway
    - reembolsado: Pagamento estornado
    """

    GATEWAY_CHOICES = [
        ('mercadopago', 'Mercado Pago (descontinuado)'),
        ('mock', 'Mock (Simulação)'),
        ('pix_manual', 'PIX Manual'),
    ]

    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('recusado', 'Recusado'),
        ('reembolsado', 'Reembolsado'),
    ]

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='pagamentos',
        verbose_name='Pedido'
    )
    gateway = models.CharField(
        max_length=15, choices=GATEWAY_CHOICES, default='mock',
        verbose_name='Gateway'
    )
    external_payment_id = models.CharField(
        max_length=255, blank=True,
        verbose_name='ID do Pagamento (Gateway)'
    )
    valor = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Valor (R$)'
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='pendente',
        verbose_name='Status'
    )
    dados_resposta = models.JSONField(
        blank=True, null=True,
        verbose_name='Dados da Resposta do Gateway'
    )
    pix_chave_id_snapshot = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        verbose_name='ID da Chave PIX (Snapshot)',
    )
    pix_chave_tipo_snapshot = models.CharField(
        max_length=16,
        blank=True,
        default='',
        verbose_name='Tipo da Chave PIX (Snapshot)',
    )
    pix_chave_valor_snapshot = models.CharField(
        max_length=120,
        blank=True,
        default='',
        verbose_name='Valor da Chave PIX (Snapshot)',
    )
    comprovante = models.FileField(
        upload_to='comprovantes/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Comprovante de Pagamento',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'webp', 'pdf']
            )
        ],
    )
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['pedido'], name='idx_pagamento_pedido'),
            models.Index(fields=['status', 'criado_em'], name='idx_pagamento_status_criado'),
        ]

    def __str__(self):
        return f'Pagamento #{self.id} - Pedido #{self.pedido_id} ({self.get_status_display()})'


class ChavePix(models.Model):
    class Tipo(models.TextChoices):
        CPF = 'cpf', 'CPF'
        CNPJ = 'cnpj', 'CNPJ'
        EMAIL = 'email', 'E-mail'
        TELEFONE = 'telefone', 'Telefone'
        UUID = 'uuid', 'Chave Aleatoria'

    restaurante = models.ForeignKey(
        Restaurante,
        on_delete=models.CASCADE,
        related_name='chaves_pix',
        verbose_name='Restaurante',
    )
    tipo = models.CharField(max_length=16, choices=Tipo.choices, verbose_name='Tipo')
    valor = models.CharField(max_length=120, verbose_name='Valor')
    valor_normalizado = models.CharField(
        max_length=120,
        blank=True,
        verbose_name='Valor Normalizado',
    )
    ativo = models.BooleanField(default=True, verbose_name='Ativa')
    padrao = models.BooleanField(default=False, verbose_name='Padrao')
    prioridade = models.PositiveIntegerField(default=100, verbose_name='Prioridade')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Chave PIX'
        verbose_name_plural = 'Chaves PIX'
        ordering = ['prioridade', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['restaurante'],
                condition=Q(ativo=True, padrao=True),
                name='uq_chave_pix_padrao_ativa_por_restaurante',
            ),
            models.UniqueConstraint(
                fields=['restaurante', 'prioridade'],
                condition=Q(ativo=True),
                name='uq_chave_pix_prioridade_ativa_por_restaurante',
            ),
        ]
        indexes = [
            models.Index(fields=['restaurante', 'ativo'], name='idx_chave_pix_rest_ativo'),
            models.Index(fields=['restaurante', 'padrao', 'ativo'], name='idx_chave_pix_rest_padrao'),
        ]

    def __str__(self):
        return f'{self.restaurante.nome} - {self.get_tipo_display()} ({self.valor})'

    def clean(self):
        normalizado = self._normalizar_valor_por_tipo(self.tipo, self.valor)
        self.valor_normalizado = normalizado

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @classmethod
    def _normalizar_valor_por_tipo(cls, tipo, valor):
        valor_limpo = (valor or '').strip()
        if not valor_limpo:
            raise ValidationError({'valor': 'Informe uma chave PIX valida.'})

        if tipo == cls.Tipo.CPF:
            apenas_digitos = re.sub(r'\D', '', valor_limpo)
            if len(apenas_digitos) != 11 or not _cpf_valido(apenas_digitos):
                raise ValidationError({'valor': 'CPF invalido para chave PIX.'})
            return apenas_digitos

        if tipo == cls.Tipo.CNPJ:
            apenas_digitos = re.sub(r'\D', '', valor_limpo)
            if len(apenas_digitos) != 14 or not _cnpj_valido(apenas_digitos):
                raise ValidationError({'valor': 'CNPJ invalido para chave PIX.'})
            return apenas_digitos

        if tipo == cls.Tipo.EMAIL:
            try:
                validate_email(valor_limpo)
            except ValidationError as exc:
                raise ValidationError({'valor': 'E-mail invalido para chave PIX.'}) from exc
            return valor_limpo.lower()

        if tipo == cls.Tipo.TELEFONE:
            if not re.fullmatch(r'\+[1-9]\d{1,14}', valor_limpo):
                raise ValidationError({'valor': 'Telefone invalido. Use formato E.164.'})
            return valor_limpo

        if tipo == cls.Tipo.UUID:
            try:
                parsed = uuid.UUID(valor_limpo)
            except ValueError as exc:
                raise ValidationError({'valor': 'Chave aleatoria invalida.'}) from exc
            return str(parsed)

        raise ValidationError({'tipo': 'Tipo de chave PIX invalido.'})


class ChavePixHistorico(models.Model):
    class Acao(models.TextChoices):
        CRIACAO = 'criacao', 'Criacao'
        EDICAO = 'edicao', 'Edicao'
        ATIVACAO = 'ativacao', 'Ativacao'
        DESATIVACAO = 'desativacao', 'Desativacao'
        PADRAO = 'padrao', 'Mudanca de padrao'
        PRIORIDADE = 'prioridade', 'Mudanca de prioridade'

    chave_pix = models.ForeignKey(
        ChavePix,
        on_delete=models.CASCADE,
        related_name='historico',
        verbose_name='Chave PIX',
    )
    acao = models.CharField(max_length=20, choices=Acao.choices, verbose_name='Acao')
    ator = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico_chaves_pix',
        verbose_name='Ator',
    )
    antes = models.JSONField(blank=True, null=True, verbose_name='Antes')
    depois = models.JSONField(blank=True, null=True, verbose_name='Depois')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Historico de Chave PIX'
        verbose_name_plural = 'Historico de Chaves PIX'
        ordering = ['-criado_em', '-id']

    def __str__(self):
        return f'Historico #{self.id} ({self.get_acao_display()})'

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError('Historico de chave PIX e append-only.')
        return super().save(*args, **kwargs)


class PagamentoRevisaoHistorico(models.Model):
    class Acao(models.TextChoices):
        ACEITO = 'aceito', 'Aceito'
        REJEITADO = 'rejeitado', 'Rejeitado'

    class Motivo(models.TextChoices):
        VALIDO = 'valido', 'Valido'
        INVALIDO = 'invalido', 'Invalido'
        OUTRO = 'outro', 'Outro'

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='historico_revisao_pagamento',
        verbose_name='Pedido',
    )
    pagamento = models.ForeignKey(
        Pagamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico_revisao',
        verbose_name='Pagamento',
    )
    acao = models.CharField(max_length=16, choices=Acao.choices, verbose_name='Acao')
    motivo = models.CharField(max_length=16, choices=Motivo.choices, verbose_name='Motivo')
    justificativa = models.TextField(verbose_name='Justificativa')
    operador = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico_revisao_pagamento',
        verbose_name='Operador',
    )
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Historico de Revisao de Pagamento'
        verbose_name_plural = 'Historico de Revisoes de Pagamento'
        ordering = ['-criado_em', '-id']
        indexes = [
            models.Index(fields=['pedido', '-criado_em'], name='idx_rev_hist_pedido_criado'),
        ]

    def __str__(self):
        return f'Revisao #{self.id} - Pedido #{self.pedido_id} ({self.acao})'

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError('Historico de revisao e append-only.')
        return super().save(*args, **kwargs)


def _cpf_valido(cpf):
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    dig1 = (soma * 10) % 11
    dig1 = 0 if dig1 == 10 else dig1
    if dig1 != int(cpf[9]):
        return False
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    dig2 = (soma * 10) % 11
    dig2 = 0 if dig2 == 10 else dig2
    return dig2 == int(cpf[10])


def _cnpj_valido(cnpj):
    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        return False

    def _calc_dv(base, pesos):
        total = sum(int(base[i]) * pesos[i] for i in range(len(pesos)))
        resto = total % 11
        return '0' if resto < 2 else str(11 - resto)

    dig1 = _calc_dv(cnpj[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    dig2 = _calc_dv(cnpj[:12] + dig1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return cnpj[-2:] == f'{dig1}{dig2}'
