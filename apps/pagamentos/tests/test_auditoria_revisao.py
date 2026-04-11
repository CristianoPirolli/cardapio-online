from datetime import timedelta

from django.apps import apps
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.pagamentos.models import ChavePix, Pagamento
from apps.pedidos.models import Pedido
from apps.restaurantes.models import Restaurante


def _restaurante(sufixo: str) -> Restaurante:
    user = User.objects.create_user(username=f"aud_{sufixo}", password="pass123")
    return Restaurante.objects.create(
        proprietario=user,
        nome=f"Auditoria {sufixo}",
        subdominio=f"aud-{sufixo}",
        endereco="Rua Teste, 123",
        cidade="Sao Paulo",
        estado="SP",
        cep="01001-000",
        telefone="11988887777",
        email=f"aud-{sufixo}@example.com",
    )


def _pedido_pix(restaurante: Restaurante) -> Pedido:
    pedido = Pedido.objects.create(
        restaurante=restaurante,
        cliente_nome="Cliente Auditoria",
        cliente_telefone="11988887777",
        status="aguardando_confirmacao",
        pago=False,
        subtotal="40.00",
        taxa_entrega="5.00",
        imposto="0.00",
        total="45.00",
    )
    ChavePix.objects.create(
        restaurante=restaurante,
        tipo=ChavePix.Tipo.EMAIL,
        valor=f"{restaurante.subdominio}@example.com",
        ativo=True,
        padrao=True,
        prioridade=1,
    )
    Pagamento.objects.create(
        pedido=pedido,
        gateway="pix_manual",
        valor=pedido.total,
        status="pendente",
    )
    return pedido


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class AuditoriaRevisaoContratoTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.restaurante = _restaurante("owner")
        self.pedido = _pedido_pix(self.restaurante)
        self.proprietario = self.restaurante.proprietario

    def test_modelo_de_historico_deve_existir(self):
        model = apps.get_model("pagamentos", "PagamentoRevisaoHistorico")
        self.assertIsNotNone(model)

    def test_decisao_valida_registra_operador_e_timestamp(self):
        self.client.force_login(self.proprietario)
        response = self.client.post(
            reverse("aceitar_pix", args=[self.pedido.id]),
            {
                "motivo_revisao": "valido",
                "justificativa_revisao": "comprovante consistente com valor e destinatario",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        model = apps.get_model("pagamentos", "PagamentoRevisaoHistorico")
        evento = model.objects.filter(pedido=self.pedido).latest("criado_em")
        self.assertEqual(evento.operador_id, self.proprietario.id)
        self.assertIsNotNone(evento.criado_em)

    def test_feed_no_detalhe_mostra_apenas_acao_e_data_hora(self):
        self.client.force_login(self.proprietario)
        model = apps.get_model("pagamentos", "PagamentoRevisaoHistorico")
        model.objects.create(
            pedido=self.pedido,
            pagamento=Pagamento.objects.get(pedido=self.pedido, gateway="pix_manual"),
            acao="aceito",
            motivo="valido",
            justificativa="comprovante consistente com valor e dados do pedido",
            operador=self.proprietario,
        )

        response = self.client.get(reverse("painel_pedido_detalhe", args=[self.pedido.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "aceito")
        self.assertContains(response, "Histórico")
        self.assertNotContains(response, "Operador")
        self.assertNotContains(response, "comprovante consistente com valor e dados do pedido")

    def test_feed_no_detalhe_ordenado_por_mais_recente(self):
        self.client.force_login(self.proprietario)
        model = apps.get_model("pagamentos", "PagamentoRevisaoHistorico")

        antigo = model.objects.create(
            pedido=self.pedido,
            pagamento=Pagamento.objects.get(pedido=self.pedido, gateway="pix_manual"),
            acao="rejeitado",
            motivo="invalido",
            justificativa="primeiro evento para teste de ordenacao no detalhe",
            operador=self.proprietario,
        )
        recente = model.objects.create(
            pedido=self.pedido,
            pagamento=Pagamento.objects.get(pedido=self.pedido, gateway="pix_manual"),
            acao="aceito",
            motivo="valido",
            justificativa="segundo evento para teste de ordenacao no detalhe",
            operador=self.proprietario,
        )
        model.objects.filter(pk=antigo.pk).update(criado_em=timezone.now() - timedelta(days=2))
        model.objects.filter(pk=recente.pk).update(criado_em=timezone.now() - timedelta(days=1))

        response = self.client.get(reverse("painel_pedido_detalhe", args=[self.pedido.id]))

        self.assertEqual(response.status_code, 200)
        eventos = response.context["historico_revisao_pagamento"]
        self.assertEqual([evento.acao for evento in eventos[:2]], ["aceito", "rejeitado"])

    def test_historico_so_aparece_no_detalhe_e_nao_na_lista(self):
        self.client.force_login(self.proprietario)
        model = apps.get_model("pagamentos", "PagamentoRevisaoHistorico")
        model.objects.create(
            pedido=self.pedido,
            pagamento=Pagamento.objects.get(pedido=self.pedido, gateway="pix_manual"),
            acao="aceito",
            motivo="valido",
            justificativa="evento valido para confirmar escopo de exibicao",
            operador=self.proprietario,
        )

        response_lista = self.client.get(reverse("painel_pedidos"))
        response_detalhe = self.client.get(reverse("painel_pedido_detalhe", args=[self.pedido.id]))

        self.assertEqual(response_lista.status_code, 200)
        self.assertNotContains(response_lista, "Histórico")
        self.assertEqual(response_detalhe.status_code, 200)
        self.assertContains(response_detalhe, "Histórico")

    def test_historico_permanece_no_detalhe_apos_saida_da_fila(self):
        self.client.force_login(self.proprietario)
        model = apps.get_model("pagamentos", "PagamentoRevisaoHistorico")
        model.objects.create(
            pedido=self.pedido,
            pagamento=Pagamento.objects.get(pedido=self.pedido, gateway="pix_manual"),
            acao="aceito",
            motivo="valido",
            justificativa="historico deve ficar no detalhe apos pagamento confirmado",
            operador=self.proprietario,
        )
        Pedido.objects.filter(pk=self.pedido.pk).update(status="recebido", pago=True)

        response = self.client.get(reverse("painel_pedido_detalhe", args=[self.pedido.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Histórico")
        self.assertContains(response, "aceito")
