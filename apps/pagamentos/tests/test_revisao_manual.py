from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.pagamentos.models import ChavePix, Pagamento
from apps.pedidos.models import Pedido
from apps.restaurantes.models import Restaurante


def _criar_restaurante(sufixo: str) -> Restaurante:
    user = User.objects.create_user(username=f"rev_{sufixo}", password="pass123")
    return Restaurante.objects.create(
        proprietario=user,
        nome=f"Restaurante {sufixo}",
        subdominio=f"rest-{sufixo}",
        endereco="Rua Teste, 100",
        cidade="Sao Paulo",
        estado="SP",
        cep="01001-000",
        telefone="11999999999",
        email=f"{sufixo}@example.com",
    )


def _criar_pedido_aguardando_confirmacao(restaurante: Restaurante, cliente: str = "Cliente") -> Pedido:
    pedido = Pedido.objects.create(
        restaurante=restaurante,
        cliente_nome=cliente,
        cliente_telefone="11999999999",
        status="aguardando_confirmacao",
        pago=False,
        subtotal="50.00",
        taxa_entrega="5.00",
        imposto="0.00",
        total="55.00",
    )
    ChavePix.objects.create(
        restaurante=restaurante,
        tipo=ChavePix.Tipo.EMAIL,
        valor=f"{restaurante.subdominio}@rest.com",
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
class RevisaoManualContratoTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.restaurante = _criar_restaurante("owner")
        self.pedido = _criar_pedido_aguardando_confirmacao(self.restaurante)
        self.proprietario = self.restaurante.proprietario

    def test_aceitar_sem_motivo_nao_altera_pedido(self):
        self.client.force_login(self.proprietario)

        response = self.client.post(
            reverse("aceitar_pix", args=[self.pedido.id]),
            {"justificativa_revisao": "comprovante confere visualmente"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.pedido.refresh_from_db()
        pagamento = Pagamento.objects.get(pedido=self.pedido, gateway="pix_manual")
        self.assertFalse(self.pedido.pago)
        self.assertEqual(self.pedido.status, "aguardando_confirmacao")
        self.assertEqual(pagamento.status, "pendente")

    def test_rejeitar_sem_justificativa_nao_altera_pedido(self):
        self.client.force_login(self.proprietario)

        response = self.client.post(
            reverse("rejeitar_pix", args=[self.pedido.id]),
            {"motivo_revisao": "invalido"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.pedido.refresh_from_db()
        pagamento = Pagamento.objects.get(pedido=self.pedido, gateway="pix_manual")
        self.assertFalse(self.pedido.pago)
        self.assertEqual(self.pedido.status, "aguardando_confirmacao")
        self.assertEqual(pagamento.status, "pendente")

    def test_justificativa_com_menos_dez_caracteres_e_rejeitada(self):
        self.client.force_login(self.proprietario)

        response = self.client.post(
            reverse("aceitar_pix", args=[self.pedido.id]),
            {
                "motivo_revisao": "valido",
                "justificativa_revisao": "curta",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.pedido.refresh_from_db()
        pagamento = Pagamento.objects.get(pedido=self.pedido, gateway="pix_manual")
        self.assertEqual(self.pedido.status, "aguardando_confirmacao")
        self.assertEqual(pagamento.status, "pendente")

    def test_motivo_fora_da_lista_e_rejeitado(self):
        self.client.force_login(self.proprietario)

        response = self.client.post(
            reverse("aceitar_pix", args=[self.pedido.id]),
            {
                "motivo_revisao": "nao-listado",
                "justificativa_revisao": "comprovante sem divergencia aparente",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.pedido.refresh_from_db()
        pagamento = Pagamento.objects.get(pedido=self.pedido, gateway="pix_manual")
        self.assertEqual(self.pedido.status, "aguardando_confirmacao")
        self.assertEqual(pagamento.status, "pendente")

    def test_isolamento_por_restaurante_impede_revisao_cruzada(self):
        outro_restaurante = _criar_restaurante("outro")
        pedido_outro = _criar_pedido_aguardando_confirmacao(outro_restaurante, cliente="Outro Cliente")

        self.client.force_login(self.proprietario)
        response = self.client.post(
            reverse("aceitar_pix", args=[pedido_outro.id]),
            {
                "motivo_revisao": "valido",
                "justificativa_revisao": "tentativa sem autorizacao no tenant",
            },
        )

        self.assertEqual(response.status_code, 404)
        pedido_outro.refresh_from_db()
        self.assertFalse(pedido_outro.pago)
        self.assertEqual(pedido_outro.status, "aguardando_confirmacao")
