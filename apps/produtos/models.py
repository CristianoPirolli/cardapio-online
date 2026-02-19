# =============================================================================
# apps/produtos/models.py - Models de Categoria e Produto
#
# Define as categorias de produtos (ex: Pizzas, Bebidas, Sobremesas)
# e os produtos em si, com preço, descrição, imagem e disponibilidade.
# Cada produto pertence a um restaurante (tenant) e uma categoria.
# =============================================================================

from django.db import models
from django.core.validators import MinValueValidator
from apps.restaurantes.models import Restaurante


class Categoria(models.Model):
    """
    Categoria de produtos de um restaurante.

    Exemplos: Pizzas, Hamburgueres, Bebidas, Sobremesas.
    Cada restaurante tem suas próprias categorias.

    Campos:
    - restaurante: FK para o restaurante (tenant)
    - nome: Nome da categoria (ex: "Pizzas Tradicionais")
    - descricao: Descrição opcional
    - ordem: Número para ordenação no cardápio
    - ativo: Se a categoria está visível no cardápio
    """

    restaurante = models.ForeignKey(
        Restaurante,
        on_delete=models.CASCADE,
        related_name='categorias',
        verbose_name='Restaurante'
    )
    nome = models.CharField(max_length=100, verbose_name='Nome da Categoria')
    descricao = models.TextField(blank=True, verbose_name='Descrição')
    ordem = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordem de Exibição',
        help_text='Categorias com menor número aparecem primeiro'
    )
    adicional_sabor = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Adicional por Sabor (R$)',
        help_text='Valor opcional somado ao preço base da pizza para sabores desta categoria.'
    )
    eh_pizza = models.BooleanField(
        default=True,
        verbose_name='Categoria de Pizza',
        help_text='Marque para categorias que usam lógica de pizza (tamanho + sabores).'
    )
    ativo = models.BooleanField(default=True, verbose_name='Ativa')

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['ordem', 'nome']
        unique_together = ['restaurante', 'nome']
        # Big O (Cap. 1): índice composto para filtros frequentes
        indexes = [
            models.Index(fields=['restaurante', 'ativo', 'ordem'], name='idx_cat_rest_ativo_ord'),
        ]

    def __str__(self):
        return f'{self.nome} ({self.restaurante.nome})'


class Produto(models.Model):
    """
    Produto do cardápio de um restaurante.

    Cada produto pertence a uma categoria e a um restaurante.
    Suporta upload de imagem para exibição no cardápio.

    Campos:
    - restaurante: FK para o restaurante (tenant)
    - categoria: FK para a categoria do produto
    - nome: Nome de exibição (ex: "Pizza Margherita")
    - descricao: Descrição detalhada (ingredientes, tamanho, etc.)
    - preco: Preço unitário em reais
    - imagem: Upload de foto do produto
    - disponivel: Se o produto está disponível para pedidos
    - destaque: Se o produto é destaque (aparece em primeiro no cardápio)
    - criado_em / atualizado_em: Timestamps automáticos
    """

    restaurante = models.ForeignKey(
        Restaurante,
        on_delete=models.CASCADE,
        related_name='produtos',
        verbose_name='Restaurante'
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='produtos',
        verbose_name='Categoria'
    )
    nome = models.CharField(max_length=200, verbose_name='Nome do Produto')
    descricao = models.TextField(blank=True, verbose_name='Descrição')
    preco = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
        default=None,
        verbose_name='Preço (R$)',
        help_text='Opcional. Se vazio, usa o adicional do tipo de sabor.'
    )
    imagem = models.ImageField(
        upload_to='produtos/',
        blank=True,
        null=True,
        verbose_name='Imagem do Produto'
    )
    disponivel = models.BooleanField(
        default=True,
        verbose_name='Disponível',
        help_text='Desmarque se o produto está temporariamente indisponível'
    )
    destaque = models.BooleanField(
        default=False,
        verbose_name='Produto Destaque',
        help_text='Produtos destaque aparecem em primeiro no cardápio'
    )
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['-destaque', 'categoria__ordem', 'nome']
        # Big O (Cap. 1): índices para queries frequentes
        # Transforma scan O(n) em lookup O(log n)
        indexes = [
            models.Index(fields=['restaurante', 'disponivel'], name='idx_prod_rest_disponivel'),
            models.Index(fields=['restaurante', 'categoria', 'disponivel'], name='idx_prod_rest_cat_disp'),
            models.Index(fields=['disponivel', '-destaque'], name='idx_prod_disp_destaque'),
        ]

    def __str__(self):
        return f'{self.nome} - R$ {self.preco}'

    @property
    def possui_tamanhos(self):
        """Indica se o restaurante possui tamanhos de pizza configurados."""
        return bool(
            self.categoria and self.categoria.eh_pizza and
            self.restaurante.tamanhos_pizza.filter(ativo=True).exists()
        )


class ProdutoTamanho(models.Model):
    """
    Configuração de tamanho para um produto (ex: pizza 6 fatias, 12 fatias).

    Permite definir preço e quantidade máxima de sabores para cada tamanho.
    """

    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='tamanhos',
        verbose_name='Produto'
    )
    nome = models.CharField(
        max_length=80,
        verbose_name='Nome do Tamanho',
        help_text='Ex: Broto, Média, Grande'
    )
    fatias = models.PositiveIntegerField(
        default=0,
        verbose_name='Fatias',
        help_text='Quantidade de fatias (opcional). Use 0 se não se aplicar.'
    )
    diametro_cm = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.1)],
        verbose_name='Diâmetro (cm)'
    )
    max_sabores = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name='Máximo de Sabores'
    )
    preco = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name='Preço (R$)'
    )
    ordem = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordem'
    )
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Tamanho de Produto'
        verbose_name_plural = 'Tamanhos de Produto'
        ordering = ['ordem', 'id']
        unique_together = ['produto', 'nome']

    def __str__(self):
        return f'{self.produto.nome} - {self.nome}'
