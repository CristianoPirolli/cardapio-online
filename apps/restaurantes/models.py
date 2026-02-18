# =============================================================================
# apps/restaurantes/models.py - Models do app de restaurantes
#
# Contém o model Restaurante, que é o tenant principal do sistema SaaS.
# Cada restaurante possui um subdomínio único e configurações próprias.
# =============================================================================

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from slugify import slugify
from datetime import timedelta


class Restaurante(models.Model):
    """
    Representa um restaurante cadastrado no sistema SaaS.

    Cada restaurante é um tenant isolado, identificado por um subdomínio único.
    Exemplo: pizzaria1.meusistema.com → subdominio='pizzaria1'

    Campos:
    - nome: Nome de exibição do restaurante
    - subdominio: Identificador único usado na URL (slug, sem espaços)
    - proprietario: Usuário Django que gerencia o restaurante
    - endereco, cidade, estado, cep: Dados de localização
    - telefone: Contato do restaurante
    - email: Email para notificações
    - logo: Imagem da logo (upload)
    - taxa_entrega: Valor fixo cobrado por entrega
    - pedido_minimo: Valor mínimo para aceitar pedidos
    - raio_entrega_km: Raio máximo de entrega em quilômetros
    - horario_abertura / horario_fechamento: Horário de funcionamento
    - ativo: Se o restaurante está ativo e visível
    - criado_em / atualizado_em: Timestamps automáticos
    """

    nome = models.CharField(
        max_length=200,
        verbose_name='Nome do Restaurante',
        help_text='Nome de exibição do restaurante'
    )
    subdominio = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name='Subdomínio',
        help_text='Identificador único na URL (ex: pizzaria1)'
    )
    proprietario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='restaurante',
        verbose_name='Proprietário'
    )
    descricao = models.TextField(
        blank=True,
        verbose_name='Descrição',
        help_text='Descrição curta do restaurante para exibição no cardápio'
    )
    endereco = models.CharField(max_length=300, verbose_name='Endereço')
    cidade = models.CharField(max_length=100, verbose_name='Cidade')
    estado = models.CharField(max_length=2, verbose_name='Estado (UF)')
    cep = models.CharField(max_length=9, verbose_name='CEP')
    telefone = models.CharField(max_length=20, verbose_name='Telefone')
    email = models.EmailField(verbose_name='Email')
    logo = models.ImageField(
        upload_to='restaurantes/logos/',
        blank=True,
        null=True,
        verbose_name='Logo'
    )
    taxa_entrega = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=5.00,
        validators=[MinValueValidator(0)],
        verbose_name='Taxa de Entrega (R$)'
    )
    pedido_minimo = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name='Pedido Mínimo (R$)'
    )
    raio_entrega_km = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=10.0,
        validators=[MinValueValidator(0)],
        verbose_name='Raio de Entrega (km)'
    )
    taxa_imposto = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Taxa de Imposto (%)',
        help_text='Percentual de imposto aplicado sobre o subtotal'
    )
    tempo_retirada_min = models.PositiveIntegerField(
        default=25,
        validators=[MinValueValidator(1)],
        verbose_name='Tempo de Retirada (min)'
    )
    tempo_entrega_min = models.PositiveIntegerField(
        default=45,
        validators=[MinValueValidator(1)],
        verbose_name='Tempo de Entrega (min)'
    )
    funciona_segunda = models.BooleanField(default=True, verbose_name='Segunda-feira')
    funciona_terca = models.BooleanField(default=True, verbose_name='Terça-feira')
    funciona_quarta = models.BooleanField(default=True, verbose_name='Quarta-feira')
    funciona_quinta = models.BooleanField(default=True, verbose_name='Quinta-feira')
    funciona_sexta = models.BooleanField(default=True, verbose_name='Sexta-feira')
    funciona_sabado = models.BooleanField(default=True, verbose_name='Sábado')
    funciona_domingo = models.BooleanField(default=True, verbose_name='Domingo')
    horario_abertura = models.TimeField(
        default='08:00',
        verbose_name='Horário de Abertura'
    )
    horario_fechamento = models.TimeField(
        default='23:00',
        verbose_name='Horário de Fechamento'
    )
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Restaurante'
        verbose_name_plural = 'Restaurantes'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        """Gera o subdomínio automaticamente a partir do nome, se não fornecido."""
        if not self.subdominio:
            self.subdominio = slugify(self.nome)
        super().save(*args, **kwargs)

    def funciona_no_dia(self, data):
        """Retorna se aceita pedidos no dia da semana informado."""
        mapa = {
            0: self.funciona_segunda,
            1: self.funciona_terca,
            2: self.funciona_quarta,
            3: self.funciona_quinta,
            4: self.funciona_sexta,
            5: self.funciona_sabado,
            6: self.funciona_domingo,
        }
        return mapa.get(data.weekday(), False)

    @property
    def esta_aberto(self):
        """
        Verifica se o restaurante aceita pedidos no momento atual.

        Regras:
        - respeita dias selecionados;
        - suporta horários que cruzam meia-noite (ex: 18:00 às 00:00).
        """
        from django.utils import timezone
        agora_dt = timezone.localtime()
        agora = agora_dt.time()
        hoje = agora_dt.date()
        ontem = hoje - timedelta(days=1)

        abertura = self.horario_abertura
        fechamento = self.horario_fechamento
        cruza_meia_noite = fechamento <= abertura

        if not cruza_meia_noite:
            return self.funciona_no_dia(hoje) and abertura <= agora <= fechamento

        # Faixa após abertura no mesmo dia (ex: 18:00-23:59)
        if self.funciona_no_dia(hoje) and agora >= abertura:
            return True

        # Faixa após meia-noite herdada do dia anterior (ex: 00:00-02:00)
        if self.funciona_no_dia(ontem) and agora <= fechamento:
            return True

        return False


class TamanhoPizza(models.Model):
    """
    Tamanhos de pizza configurados por restaurante.

    O preço base parte deste tamanho e os sabores podem adicionar valor.
    """

    restaurante = models.ForeignKey(
        Restaurante,
        on_delete=models.CASCADE,
        related_name='tamanhos_pizza',
        verbose_name='Restaurante'
    )
    nome = models.CharField(max_length=80, verbose_name='Nome do Tamanho')
    fatias = models.PositiveIntegerField(
        default=0,
        verbose_name='Fatias',
        help_text='Use 0 se não se aplicar.'
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
        verbose_name='Máx. Sabores'
    )
    preco_base = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Preço Base (R$)'
    )
    ordem = models.PositiveIntegerField(default=0, verbose_name='Ordem')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Tamanho de Pizza'
        verbose_name_plural = 'Tamanhos de Pizza'
        ordering = ['ordem', 'id']
        unique_together = ['restaurante', 'nome']

    def __str__(self):
        return f'{self.restaurante.nome} - {self.nome}'
