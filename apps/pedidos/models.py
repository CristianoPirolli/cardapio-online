# =============================================================================
# apps/pedidos/models.py - Models de Pedido e ItemPedido
#
# Estrutura do pedido:
# - Pedido: cabeçalho com dados do cliente, restaurante, totais e status
# - ItemPedido: cada item do pedido (produto + quantidade + preço unitário)
#
# Fluxo de status: recebido → preparo → entrega → concluido (ou cancelado)
#
# Cálculos automáticos:
# - subtotal: soma dos itens (quantidade × preço unitário)
# - imposto: percentual sobre o subtotal (configurado no restaurante)
# - taxa_entrega: valor fixo do restaurante
# - total: subtotal + imposto + taxa_entrega
# =============================================================================

from django.db import models
from django.core.validators import MinValueValidator
from apps.restaurantes.models import Restaurante
from apps.produtos.models import Produto


class Pedido(models.Model):
    """
    Pedido realizado por um cliente em um restaurante.

    Status possíveis:
    - recebido: Pedido acabou de ser feito
    - preparo: Restaurante está preparando
    - entrega: Saiu para entrega
    - concluido: Entregue com sucesso
    - cancelado: Pedido cancelado

    Campos de valor:
    - subtotal: Soma dos itens (calculado automaticamente)
    - taxa_entrega: Copiada do restaurante no momento do pedido
    - imposto: Calculado com base na taxa_imposto do restaurante
    - total: subtotal + taxa_entrega + imposto
    """

    STATUS_CHOICES = [
        ('recebido', 'Recebido'),
        ('preparo', 'Em Preparo'),
        ('entrega', 'Saiu para Entrega'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]

    # Transicoes de status permitidas
    VALID_TRANSITIONS = {
        'recebido': ['preparo', 'cancelado'],
        'preparo': ['entrega', 'cancelado'],
        'entrega': ['concluido', 'cancelado'],
        'concluido': [],
        'cancelado': [],
    }

    TIPO_ENTREGA_CHOICES = [
        ('delivery', 'Delivery'),
        ('retirada', 'Retirada no Local'),
    ]

    restaurante = models.ForeignKey(
        Restaurante,
        on_delete=models.CASCADE,
        related_name='pedidos',
        verbose_name='Restaurante'
    )
    # Dados do cliente (sem necessidade de login para pedir)
    cliente_nome = models.CharField(max_length=200, verbose_name='Nome do Cliente')
    cliente_telefone = models.CharField(max_length=20, verbose_name='Telefone')
    cliente_email = models.EmailField(blank=True, verbose_name='Email')
    endereco_entrega = models.TextField(blank=True, verbose_name='Endereço de Entrega')
    tipo_entrega = models.CharField(
        max_length=10,
        choices=TIPO_ENTREGA_CHOICES,
        default='delivery',
        verbose_name='Tipo de Entrega'
    )
    observacoes = models.TextField(blank=True, verbose_name='Observações')

    # Valores do pedido
    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Subtotal (R$)'
    )
    taxa_entrega = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        verbose_name='Taxa de Entrega (R$)'
    )
    imposto = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        verbose_name='Imposto (R$)'
    )
    total = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Total (R$)'
    )

    # Status e pagamento
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='recebido',
        verbose_name='Status'
    )
    pago = models.BooleanField(default=False, verbose_name='Pago')
    stripe_payment_intent_id = models.CharField(
        max_length=255, blank=True,
        verbose_name='Stripe Payment Intent ID'
    )

    # Timestamps
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-criado_em']

    def __str__(self):
        return f'Pedido #{self.id} - {self.cliente_nome} ({self.get_status_display()})'

    def validar_transicao_status(self, novo_status):
        """
        Valida se a transicao de status e permitida.
        Retorna (is_valid, error_message).
        """
        if novo_status == self.status:
            return True, ''
        permitidas = self.VALID_TRANSITIONS.get(self.status, [])
        if novo_status not in permitidas:
            nomes = {k: v for k, v in self.STATUS_CHOICES}
            return False, (
                f'Transição inválida: {nomes.get(self.status, self.status)} → '
                f'{nomes.get(novo_status, novo_status)}. '
                f'Transições permitidas: {[nomes.get(s, s) for s in permitidas]}'
            )
        return True, ''

    def save(self, *args, **kwargs):
        if self.pk and not getattr(self, '_skip_status_validation', False):
            old_status = Pedido.objects.filter(pk=self.pk).values_list(
                'status', flat=True
            ).first()
            if old_status and old_status != self.status:
                # Temporariamente restaura o status antigo para validar
                novo = self.status
                self.status = old_status
                valido, msg = self.validar_transicao_status(novo)
                self.status = novo
                if not valido:
                    raise ValueError(msg)
        super().save(*args, **kwargs)

    def calcular_totais(self):
        """
        Calcula subtotal, imposto e total do pedido com base nos itens.

        Deve ser chamado após adicionar/remover/alterar itens.
        A taxa de entrega é copiada do restaurante (ou zero para retirada).
        O imposto é calculado como percentual do subtotal.
        """
        # Subtotal = soma de (quantidade × preco_unitario) de cada item
        self.subtotal = sum(
            item.quantidade * item.preco_unitario
            for item in self.itens.all()
        )

        # Taxa de entrega (zero para retirada no local)
        if self.tipo_entrega == 'delivery':
            self.taxa_entrega = self.restaurante.taxa_entrega
        else:
            self.taxa_entrega = 0

        # Imposto = percentual do subtotal
        taxa_pct = self.restaurante.taxa_imposto / 100
        self.imposto = round(self.subtotal * taxa_pct, 2)

        # Total
        self.total = self.subtotal + self.taxa_entrega + self.imposto
        self.save()


class ItemPedido(models.Model):
    """
    Item individual dentro de um pedido.

    Armazena o preço unitário no momento da compra para manter
    o histórico mesmo se o preço do produto mudar depois.

    Campos:
    - pedido: FK para o Pedido
    - produto: FK para o Produto
    - quantidade: Quantidade solicitada
    - preco_unitario: Preço no momento do pedido (snapshot)
    - observacao: Observação específica do item (ex: "sem cebola")
    """

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Pedido'
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Produto'
    )
    quantidade = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name='Quantidade'
    )
    preco_unitario = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Preço Unitário (R$)'
    )
    observacao = models.CharField(
        max_length=300, blank=True,
        verbose_name='Observação do Item'
    )
    tamanho_nome = models.CharField(
        max_length=80,
        blank=True,
        verbose_name='Tamanho'
    )
    sabores_descricao = models.CharField(
        max_length=300,
        blank=True,
        verbose_name='Sabores'
    )

    class Meta:
        verbose_name = 'Item do Pedido'
        verbose_name_plural = 'Itens do Pedido'

    def __str__(self):
        return f'{self.quantidade}x {self.produto.nome if self.produto else "Removido"}'

    @property
    def subtotal(self):
        """Calcula o subtotal deste item (quantidade × preço unitário)."""
        return self.quantidade * self.preco_unitario
