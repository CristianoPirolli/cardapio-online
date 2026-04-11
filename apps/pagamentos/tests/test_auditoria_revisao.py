from django.apps import apps
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

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
        self.assertNotContains(response, self.proprietario.username)
        self.assertNotContains(response, "valido")
        self.assertNotContains(response, "comprovante consistente com valor e dados do pedido")
