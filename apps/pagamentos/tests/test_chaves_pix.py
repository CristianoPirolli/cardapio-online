from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.pagamentos.models import ChavePix
from apps.pagamentos.services import (
    criar_pagamento_pix_manual,
    selecionar_chave_pix_checkout,
)
from apps.pedidos.models import Pedido
from apps.restaurantes.models import Restaurante


def _make_restaurante(suffix=""):
    user = User.objects.create_user(
        username=f"pixkeys{suffix}",
        password="pass",
    )
    return Restaurante.objects.create(
        proprietario=user,
        nome=f"Restaurante Pix {suffix}",
        subdominio=f"pixkeys{suffix}",
        endereco="Rua Teste, 100",
        cidade="Sao Paulo",
        estado="SP",
        cep="01001-000",
        telefone="11999999999",
        email=f"pix{suffix}@example.com",
    )


class ChavePixModelTest(TestCase):
    def setUp(self):
        self.restaurante = _make_restaurante("a")

    def test_restaurante_pode_ter_multiplas_chaves_ativas_validas(self):
        ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.CPF,
            valor="52998224725",
            ativo=True,
            prioridade=10,
        )
        ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.EMAIL,
            valor="financeiro@restaurante.com",
            ativo=True,
            prioridade=20,
        )

        self.assertEqual(
            ChavePix.objects.filter(restaurante=self.restaurante, ativo=True).count(),
            2,
        )

    def test_apenas_uma_chave_padrao_ativa_por_restaurante(self):
        ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.EMAIL,
            valor="padrao@restaurante.com",
            ativo=True,
            padrao=True,
            prioridade=10,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ChavePix.objects.create(
                    restaurante=self.restaurante,
                    tipo=ChavePix.Tipo.TELEFONE,
                    valor="+5511999999999",
                    ativo=True,
                    padrao=True,
                    prioridade=20,
                )

    def test_prioridade_ativa_deve_ser_unica_por_restaurante(self):
        ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.EMAIL,
            valor="contato@restaurante.com",
            ativo=True,
            prioridade=1,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ChavePix.objects.create(
                    restaurante=self.restaurante,
                    tipo=ChavePix.Tipo.CNPJ,
                    valor="19131243000197",
                    ativo=True,
                    prioridade=1,
                )

    def test_validacao_obrigatoria_por_tipo(self):
        casos_invalidos = [
            (ChavePix.Tipo.CPF, "12345678901"),
            (ChavePix.Tipo.CNPJ, "12345678000100"),
            (ChavePix.Tipo.EMAIL, "email-invalido"),
            (ChavePix.Tipo.TELEFONE, "11999999999"),
            (ChavePix.Tipo.UUID, "nao-e-uuid"),
        ]
        for tipo, valor in casos_invalidos:
            with self.subTest(tipo=tipo):
                chave = ChavePix(
                    restaurante=self.restaurante,
                    tipo=tipo,
                    valor=valor,
                    ativo=True,
                    prioridade=50,
                )
                with self.assertRaises(ValidationError):
                    chave.full_clean()


def _make_pedido(restaurante, suffix=""):
    return Pedido.objects.create(
        restaurante=restaurante,
        cliente_nome=f"Cliente {suffix}",
        cliente_telefone="11999999999",
        status="aguardando",
        pago=False,
        subtotal="50.00",
        taxa_entrega="5.00",
        imposto="0.00",
        total="55.00",
    )


class ChavePixServiceTest(TestCase):
    def setUp(self):
        self.restaurante = _make_restaurante("svc")

    def test_selecao_prioriza_padrao_ativa_e_fallback_por_prioridade(self):
        ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.EMAIL,
            valor="fallback@restaurante.com",
            ativo=True,
            prioridade=2,
        )
        menor_prioridade = ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.CNPJ,
            valor="19131243000197",
            ativo=True,
            prioridade=1,
        )
        padrao = ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.TELEFONE,
            valor="+5511911111111",
            ativo=True,
            padrao=True,
            prioridade=3,
        )

        selecionada = selecionar_chave_pix_checkout(self.restaurante)
        self.assertEqual(selecionada.id, padrao.id)

        padrao.ativo = False
        padrao.padrao = False
        padrao.save(update_fields=["ativo", "padrao", "atualizado_em"])

        selecionada_sem_padrao = selecionar_chave_pix_checkout(self.restaurante)
        self.assertEqual(selecionada_sem_padrao.id, menor_prioridade.id)

    def test_quando_nao_ha_chave_ativa_gera_falha_controlada(self):
        with self.assertRaisesRegex(ValueError, "Nenhuma chave PIX ativa"):
            selecionar_chave_pix_checkout(self.restaurante)

    def test_pagamento_pendente_preserva_snapshot_apos_manutencao_de_chaves(self):
        chave_inicial = ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.EMAIL,
            valor="inicio@restaurante.com",
            ativo=True,
            padrao=True,
            prioridade=1,
        )
        pedido = _make_pedido(self.restaurante, "snap")

        pagamento = criar_pagamento_pix_manual(pedido)
        self.assertEqual(pagamento.pix_chave_id_snapshot, chave_inicial.id)
        self.assertEqual(pagamento.pix_chave_tipo_snapshot, ChavePix.Tipo.EMAIL)
        self.assertEqual(pagamento.pix_chave_valor_snapshot, "inicio@restaurante.com")

        chave_inicial.ativo = False
        chave_inicial.padrao = False
        chave_inicial.save(update_fields=["ativo", "padrao", "atualizado_em"])
        ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.TELEFONE,
            valor="+5511998888777",
            ativo=True,
            padrao=True,
            prioridade=1,
        )

        reuso = criar_pagamento_pix_manual(pedido)
        self.assertEqual(reuso.id, pagamento.id)
        self.assertEqual(reuso.pix_chave_id_snapshot, chave_inicial.id)
        self.assertEqual(reuso.pix_chave_valor_snapshot, "inicio@restaurante.com")
