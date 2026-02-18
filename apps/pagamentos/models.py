# =============================================================================
# apps/pagamentos/models.py - Model de Pagamento
#
# Registra cada tentativa/confirmação de pagamento associada a um pedido.
# Suporta Stripe (payment intent) e mock (simulação local).
# =============================================================================

from django.db import models
from apps.pedidos.models import Pedido


class Pagamento(models.Model):
    """
    Registro de pagamento para um pedido.

    Tipos de gateway:
    - stripe: Pagamento real via Stripe
    - mock: Simulação local para desenvolvimento/testes

    Status:
    - pendente: Pagamento criado, aguardando confirmação
    - aprovado: Pagamento confirmado com sucesso
    - recusado: Pagamento recusado pelo gateway
    - reembolsado: Pagamento estornado

    Campos:
    - pedido: FK para o pedido associado
    - gateway: Tipo do gateway ('stripe' ou 'mock')
    - stripe_payment_intent_id: ID do Payment Intent no Stripe
    - valor: Valor cobrado em reais
    - status: Status atual do pagamento
    - dados_resposta: JSON com a resposta completa do gateway
    """

    GATEWAY_CHOICES = [
        ('stripe', 'Stripe'),
        ('mock', 'Mock (Simulação)'),
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
        max_length=10, choices=GATEWAY_CHOICES, default='mock',
        verbose_name='Gateway'
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255, blank=True,
        verbose_name='Stripe Payment Intent ID'
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
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
        ordering = ['-criado_em']

    def __str__(self):
        return f'Pagamento #{self.id} - Pedido #{self.pedido_id} ({self.get_status_display()})'
