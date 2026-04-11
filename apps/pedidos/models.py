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

from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from apps.restaurantes.models import Restaurante
from apps.produtos.models import Produto
from apps.core.algorithms import (
    GRAFO_STATUS_PEDIDO,
    bfs_caminho_mais_curto,
    bfs_status_alcancaveis,
    proximo_status_para_concluir,
    calcular_subtotal_otimizado,
)


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

    Algoritmos utilizados:
    - BFS (Cap. 6): Validação de transições e caminho até status final
    - Tabela Hash (Cap. 5): VALID_TRANSITIONS como dicionário O(1)
    - Memoização (Cap. 8): Cache de cálculo de totais
    """

    STATUS_CHOICES = [
        ('aguardando', 'Aguardando Pagamento'),
        ('aguardando_confirmacao', 'Aguardando Confirmação'),
        ('recebido', 'Recebido'),
        ('preparo', 'Em Preparo'),
        ('entrega', 'Saiu para Entrega'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]

    # Tabela Hash (Cap. 5): transições como dicionário para lookup O(1)
    # Antes: se fosse uma lista de tuplas, buscar seria O(n)
    # Agora: dict.get() é O(1) amortizado
    VALID_TRANSITIONS = GRAFO_STATUS_PEDIDO

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
        max_length=25, choices=STATUS_CHOICES, default='aguardando',
        verbose_name='Status'
    )
    pago = models.BooleanField(default=False, verbose_name='Pago')
    external_payment_id = models.CharField(
        max_length=255, blank=True,
        verbose_name='ID do Pagamento (Gateway)'
    )

    # Timestamps
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-criado_em']
        # Big O (Cap. 1): índices transformam busca de O(n) para O(log n)
        # Sem índice: o banco varre toda a tabela (full scan) = O(n)
        # Com índice: usa B-tree para encontrar em O(log n)
        indexes = [
            models.Index(fields=['restaurante', 'status'], name='idx_pedido_rest_status'),
            models.Index(fields=['restaurante', 'criado_em'], name='idx_pedido_rest_criado'),
            models.Index(fields=['status', 'criado_em'], name='idx_pedido_status_criado'),
            models.Index(fields=['external_payment_id'], name='idx_pedido_ext_payment'),
        ]

    def __str__(self):
        return f'Pedido #{self.id} - {self.cliente_nome} ({self.get_status_display()})'

    # -------------------------------------------------------------------
    # Pesquisa em Largura / BFS (Cap. 6)
    # -------------------------------------------------------------------

    def validar_transicao_status(self, novo_status):
        """
        Valida se a transição de status é permitida.

        Usa Tabela Hash (Cap. 5) para lookup O(1) das transições diretas.
        """
        if novo_status == self.status:
            return True, ''
        permitidas = self.VALID_TRANSITIONS.get(self.status, [])
        if novo_status not in permitidas:
            nomes = dict(self.STATUS_CHOICES)
            return False, (
                f'Transição inválida: {nomes.get(self.status, self.status)} → '
                f'{nomes.get(novo_status, novo_status)}. '
                f'Transições permitidas: {[nomes.get(s, s) for s in permitidas]}'
            )
        return True, ''

    def caminho_ate_status(self, status_destino):
        """
        BFS (Cap. 6): Encontra o caminho mais curto do status atual até o destino.

        Livro: "A pesquisa em largura encontra o caminho mais curto"

        Exemplo: pedido.status = 'recebido'
        pedido.caminho_ate_status('concluido')
        → ['recebido', 'preparo', 'entrega', 'concluido']

        Útil para mostrar ao usuário quantos passos faltam.
        """
        return bfs_caminho_mais_curto(GRAFO_STATUS_PEDIDO, self.status, status_destino)

    def status_alcancaveis(self):
        """
        BFS (Cap. 6): Retorna todos os status alcançáveis e a distância.

        Exemplo: pedido.status = 'preparo'
        → {'preparo': 0, 'entrega': 1, 'cancelado': 1, 'concluido': 2}
        """
        return bfs_status_alcancaveis(GRAFO_STATUS_PEDIDO, self.status)

    @property
    def proximo_passo(self):
        """
        BFS (Cap. 6): Sugere o próximo status no caminho até 'concluido'.

        Útil para o painel do restaurante mostrar a ação recomendada.
        """
        return proximo_status_para_concluir(self.status)

    @property
    def passos_para_concluir(self):
        """Número de passos até 'concluido' via BFS."""
        caminho = self.caminho_ate_status('concluido')
        return max(len(caminho) - 1, 0) if caminho else -1

    def save(self, *args, **kwargs):
        if self.pk and not getattr(self, '_skip_status_validation', False):
            old_status = Pedido.objects.filter(pk=self.pk).values_list(
                'status', flat=True
            ).first()
            if old_status and old_status != self.status:
                novo = self.status
                self.status = old_status
                valido, msg = self.validar_transicao_status(novo)
                self.status = novo
                if not valido:
                    raise ValueError(msg)
        super().save(*args, **kwargs)

    # -------------------------------------------------------------------
    # Recursão + Memoização (Cap. 3 e 8) / Big O (Cap. 1)
    # -------------------------------------------------------------------

    def calcular_totais(self, itens_prefetched=None, taxa_entrega_override=None):
        """
        Calcula subtotal, imposto e total do pedido com base nos itens.

        Otimizações aplicadas:

        1. Big O (Cap. 1) - Eliminação de query N+1:
           ANTES: self.itens.all() disparava uma query SQL a cada chamada
           AGORA: aceita itens_prefetched para evitar query extra.
           Reduz de O(n) queries para O(1) query.

        2. Memoização (Cap. 8):
           O cálculo usa calcular_subtotal_otimizado() que acumula em
           uma passada O(n) sem queries adicionais.

        3. Tabela Hash (Cap. 5):
           Ao salvar, invalida o cache se implementado.

        Args:
            itens_prefetched: Lista de itens já carregados (evita query extra).
            taxa_entrega_override: Se fornecida, usa este valor em vez de calcular
                                   pela zona ou taxa padrão do restaurante.
                                   Usado quando as zonas já foram calculadas.
        """
        # Se recebeu itens pré-carregados, usa direto (0 queries extras)
        # Se não, carrega uma vez só com .all() (1 query)
        itens = itens_prefetched if itens_prefetched is not None else self.itens.all()

        # Memoização: calcula subtotal em O(n) com uma passada
        self.subtotal = calcular_subtotal_otimizado(itens)

        # Taxa de entrega: respeita override (zonas por raio) ou usa padrão
        if self.tipo_entrega == 'delivery':
            if taxa_entrega_override is not None:
                self.taxa_entrega = taxa_entrega_override
            elif not self.taxa_entrega:
                self.taxa_entrega = self.restaurante.taxa_entrega
        else:
            self.taxa_entrega = Decimal('0')

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
        indexes = [
            models.Index(fields=['pedido'], name='idx_itempedido_pedido'),
            models.Index(fields=['produto'], name='idx_itempedido_produto'),
        ]

    def __str__(self):
        return f'{self.quantidade}x {self.produto.nome if self.produto else "Removido"}'

    @property
    def subtotal(self):
        """Calcula o subtotal deste item (quantidade × preço unitário)."""
        return self.quantidade * self.preco_unitario
