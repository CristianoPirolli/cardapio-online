from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.pedidos.models import Pedido
from apps.restaurantes.models import Restaurante


def _restaurante(sufixo: str) -> Restaurante:
    user = User.objects.create_user(username=f"rev_{sufixo}", password="pass123")
    return Restaurante.objects.create(
        proprietario=user,
        nome=f"Revisao {sufixo}",
        subdominio=f"rev-{sufixo}",
        endereco="Rua Teste, 123",
        cidade="Sao Paulo",
        estado="SP",
        cep="01001-000",
        telefone="11988887777",
        email=f"rev-{sufixo}@example.com",
    )


def _pedido(
    restaurante: Restaurante,
    *,
    status: str = "aguardando_confirmacao",
    pago: bool = False,
    dias_atras: int = 0,
) -> Pedido:
    pedido = Pedido.objects.create(
        restaurante=restaurante,
        cliente_nome=f"Cliente {dias_atras}",
        cliente_telefone="11988887777",
        status=status,
        pago=pago,
        subtotal="40.00",
        taxa_entrega="5.00",
        imposto="0.00",
        total="45.00",
    )
    Pedido.objects.filter(pk=pedido.pk).update(
        criado_em=timezone.now() - timedelta(days=dias_atras)
    )
    pedido.refresh_from_db()
    return pedido


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class PainelRevisaoPeriodoContratoTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.restaurante = _restaurante("owner")
        self.outro_restaurante = _restaurante("outro")
        self.proprietario = self.restaurante.proprietario
        self.url = reverse("painel_pedidos")
        self.client.force_login(self.proprietario)

    def _query(self, params=None):
        return self.client.get(self.url, params or {})

    def test_default_deve_exibir_visao_todos_os_pedidos_e_secao_aguardando_pix(self):
        _pedido(self.restaurante, status="recebido", pago=True, dias_atras=1)
        _pedido(self.restaurante, status="aguardando_confirmacao", pago=False, dias_atras=0)

        response = self._query()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Todos os pedidos")
        self.assertContains(response, "Aguardando PIX")
        self.assertGreaterEqual(len(response.context["pendentes_pix"]), 1)

    def test_preset_hoje_filtra_pendentes_do_dia(self):
        pedido_hoje = _pedido(self.restaurante, dias_atras=0)
        _pedido(self.restaurante, dias_atras=1)
        _pedido(self.outro_restaurante, dias_atras=0)

        response = self._query({"periodo": "hoje"})
        ids = [pedido.id for pedido in response.context["pendentes_pix"]]

        self.assertEqual(response.status_code, 200)
        self.assertIn(pedido_hoje.id, ids)
        self.assertEqual(len(ids), 1)

    def test_preset_ontem_filtra_pendentes_do_dia_anterior(self):
        pedido_ontem = _pedido(self.restaurante, dias_atras=1)
        _pedido(self.restaurante, dias_atras=0)
        _pedido(self.restaurante, dias_atras=2)

        response = self._query({"periodo": "ontem"})
        ids = [pedido.id for pedido in response.context["pendentes_pix"]]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ids, [pedido_ontem.id])

    def test_preset_7d_filtra_janela_de_7_dias(self):
        pedido_2_dias = _pedido(self.restaurante, dias_atras=2)
        pedido_6_dias = _pedido(self.restaurante, dias_atras=6)
        _pedido(self.restaurante, dias_atras=8)

        response = self._query({"periodo": "7d"})
        ids = [pedido.id for pedido in response.context["pendentes_pix"]]

        self.assertEqual(response.status_code, 200)
        self.assertIn(pedido_2_dias.id, ids)
        self.assertIn(pedido_6_dias.id, ids)
        self.assertEqual(len(ids), 2)

    def test_preset_30d_filtra_janela_de_30_dias(self):
        pedido_10_dias = _pedido(self.restaurante, dias_atras=10)
        pedido_29_dias = _pedido(self.restaurante, dias_atras=29)
        _pedido(self.restaurante, dias_atras=31)

        response = self._query({"periodo": "30d"})
        ids = [pedido.id for pedido in response.context["pendentes_pix"]]

        self.assertEqual(response.status_code, 200)
        self.assertIn(pedido_10_dias.id, ids)
        self.assertIn(pedido_29_dias.id, ids)
        self.assertEqual(len(ids), 2)

    def test_periodo_custom_valido_filtra_intervalo_inclusivo(self):
        pedido_4_dias = _pedido(self.restaurante, dias_atras=4)
        pedido_2_dias = _pedido(self.restaurante, dias_atras=2)
        _pedido(self.restaurante, dias_atras=6)

        inicio = (timezone.localdate() - timedelta(days=4)).isoformat()
        fim = (timezone.localdate() - timedelta(days=2)).isoformat()
        response = self._query(
            {"periodo": "custom", "data_inicio": inicio, "data_fim": fim}
        )
        ids = [pedido.id for pedido in response.context["pendentes_pix"]]

        self.assertEqual(response.status_code, 200)
        self.assertIn(pedido_4_dias.id, ids)
        self.assertIn(pedido_2_dias.id, ids)
        self.assertEqual(len(ids), 2)

    def test_periodo_custom_invalido_mantem_ultima_selecao_valida(self):
        pedido_hoje = _pedido(self.restaurante, dias_atras=0)
        _pedido(self.restaurante, dias_atras=10)

        primeira = self._query({"periodo": "hoje"})
        primeira_ids = [pedido.id for pedido in primeira.context["pendentes_pix"]]
        self.assertEqual(primeira_ids, [pedido_hoje.id])

        invalida = self._query(
            {"periodo": "custom", "data_inicio": "2026-02-10", "data_fim": "2026-01-10"}
        )
        invalida_ids = [pedido.id for pedido in invalida.context["pendentes_pix"]]

        self.assertEqual(invalida.status_code, 200)
        self.assertEqual(invalida_ids, primeira_ids)
        self.assertContains(invalida, "Periodo personalizado invalido")

    def test_fila_aguardando_confirmacao_permanece_ordenada_por_recencia(self):
        mais_antigo = _pedido(self.restaurante, dias_atras=3)
        meio = _pedido(self.restaurante, dias_atras=2)
        mais_novo = _pedido(self.restaurante, dias_atras=1)

        response = self._query({"periodo": "7d"})
        ids = [pedido.id for pedido in response.context["pendentes_pix"]]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ids, [mais_novo.id, meio.id, mais_antigo.id])
