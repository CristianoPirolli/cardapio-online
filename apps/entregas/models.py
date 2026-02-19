# =============================================================================
# apps/entregas/models.py - Models de Entregador e Entrega
#
# Gerencia entregadores e o rastreio de entregas associadas a pedidos.
# Cada entrega é vinculada a um pedido e (opcionalmente) a um entregador.
# =============================================================================

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from apps.restaurantes.models import Restaurante
from apps.pedidos.models import Pedido


class Entregador(models.Model):
    """
    Entregador cadastrado no sistema.

    Pode ser vinculado a um restaurante específico ou atender vários.

    Campos:
    - usuario: FK para User (login do entregador)
    - restaurante: FK para o restaurante associado
    - nome: Nome completo do entregador
    - telefone: Contato
    - veiculo: Tipo de veículo (moto, bicicleta, carro, a pé)
    - disponivel: Se está disponível para entregas
    - ativo: Se o cadastro está ativo
    """

    VEICULO_CHOICES = [
        ('moto', 'Moto'),
        ('bicicleta', 'Bicicleta'),
        ('carro', 'Carro'),
        ('a_pe', 'A Pé'),
    ]

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='entregador',
        verbose_name='Usuário'
    )
    restaurante = models.ForeignKey(
        Restaurante,
        on_delete=models.CASCADE,
        related_name='entregadores',
        verbose_name='Restaurante'
    )
    nome = models.CharField(max_length=200, verbose_name='Nome Completo')
    telefone = models.CharField(max_length=20, verbose_name='Telefone')
    veiculo = models.CharField(
        max_length=10, choices=VEICULO_CHOICES, default='moto',
        verbose_name='Veículo'
    )
    disponivel = models.BooleanField(default=True, verbose_name='Disponível')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Entregador'
        verbose_name_plural = 'Entregadores'
        ordering = ['nome']
        # Big O (Cap. 1): índice para busca rápida de entregadores disponíveis
        indexes = [
            models.Index(fields=['restaurante', 'disponivel', 'ativo'], name='idx_entregador_disp'),
        ]

    def __str__(self):
        return f'{self.nome} ({self.get_veiculo_display()})'


class Entrega(models.Model):
    """
    Registro de entrega de um pedido.

    Rastreia o status da entrega desde a saída do restaurante
    até a conclusão ou cancelamento.

    Status:
    - aguardando: Aguardando atribuição de entregador
    - coletado: Entregador coletou o pedido no restaurante
    - em_transito: A caminho do cliente
    - entregue: Entregue com sucesso
    - cancelado: Entrega cancelada

    Campos:
    - pedido: FK para o pedido (OneToOne, cada pedido tem uma entrega)
    - entregador: FK para o entregador (pode ser null inicialmente)
    - status: Status atual da entrega
    - observacoes: Notas sobre a entrega
    - saiu_em: Timestamp de quando saiu do restaurante
    - entregue_em: Timestamp de quando foi entregue
    """

    STATUS_CHOICES = [
        ('aguardando', 'Aguardando Entregador'),
        ('coletado', 'Coletado'),
        ('em_transito', 'Em Trânsito'),
        ('entregue', 'Entregue'),
        ('cancelado', 'Cancelado'),
    ]

    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.CASCADE,
        related_name='entrega',
        verbose_name='Pedido'
    )
    entregador = models.ForeignKey(
        Entregador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entregas',
        verbose_name='Entregador'
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='aguardando',
        verbose_name='Status'
    )
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    saiu_em = models.DateTimeField(null=True, blank=True, verbose_name='Saiu em')
    entregue_em = models.DateTimeField(null=True, blank=True, verbose_name='Entregue em')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Entrega'
        verbose_name_plural = 'Entregas'
        ordering = ['-criado_em']
        # Big O (Cap. 1): índices para queries frequentes no painel
        indexes = [
            models.Index(fields=['status', 'criado_em'], name='idx_entrega_status_criado'),
            models.Index(fields=['entregador', 'status'], name='idx_entrega_entregador'),
        ]

    def __str__(self):
        return f'Entrega #{self.id} - Pedido #{self.pedido_id} ({self.get_status_display()})'

    def save(self, *args, **kwargs):
        # Detecta mudanca de status
        old_status = None
        if self.pk:
            old_status = Entrega.objects.filter(pk=self.pk).values_list(
                'status', flat=True
            ).first()

        # Auto-preenche timestamps
        if self.status == 'coletado' and not self.saiu_em:
            self.saiu_em = timezone.now()
        elif self.status == 'entregue' and not self.entregue_em:
            self.entregue_em = timezone.now()

        super().save(*args, **kwargs)

        # Sincroniza status com o pedido (apenas se mudou)
        if old_status != self.status:
            pedido = self.pedido
            if self.status == 'em_transito' and pedido.status != 'entrega':
                pedido._skip_status_validation = True
                pedido.status = 'entrega'
                pedido.save()
            elif self.status == 'entregue' and pedido.status != 'concluido':
                pedido._skip_status_validation = True
                pedido.status = 'concluido'
                pedido.save()
