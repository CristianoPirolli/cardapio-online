# =============================================================================
# apps/pagamentos/models.py - Model de Pagamento
#
# Registra cada tentativa/confirmação de pagamento associada a um pedido.
# Suporta Mercado Pago (cartão + PIX) e mock (simulação local).
# =============================================================================

from django.db import models
from django.core.validators import FileExtensionValidator
from apps.pedidos.models import Pedido


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
