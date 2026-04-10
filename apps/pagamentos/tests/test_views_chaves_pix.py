from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings

from apps.pagamentos.models import ChavePix
from apps.pagamentos.services import criar_pagamento_pix_manual
from apps.pedidos.models import Pedido
from apps.restaurantes.models import Restaurante


@override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
)
class PagamentoPixChaveViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        user = User.objects.create_user(username='viewpix', password='pass')
        self.restaurante = Restaurante.objects.create(
            proprietario=user,
            nome='Restaurante Chave View',
            subdominio='view-pix-key',
            endereco='Rua Teste, 100',
            cidade='Sao Paulo',
            estado='SP',
            cep='01001-000',
            telefone='11999999999',
            email='viewpix@example.com',
        )
        self.pedido = Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='Cliente',
            cliente_telefone='11999999999',
            status='aguardando',
            pago=False,
            subtotal='50.00',
            taxa_entrega='5.00',
            imposto='0.00',
            total='55.00',
        )

    def test_checkout_exibe_chave_selecionada_do_restaurante(self):
        ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.EMAIL,
            valor='pix-restaurante@example.com',
            ativo=True,
            padrao=True,
            prioridade=1,
        )

        response = self.client.get(f'/pagamentos/{self.pedido.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pix-restaurante@example.com')

    @override_settings(PIX_KEY='CHAVE_GLOBAL_LEGACY')
    def test_checkout_nao_usa_pix_key_global_quando_ha_chave_por_restaurante(self):
        ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.TELEFONE,
            valor='+5511988887777',
            ativo=True,
            padrao=True,
            prioridade=1,
        )

        response = self.client.get(f'/pagamentos/{self.pedido.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '+5511988887777')
        self.assertNotContains(response, 'CHAVE_GLOBAL_LEGACY')

    def test_checkout_reapresenta_snapshot_existente_em_pedido_andamento(self):
        chave_inicial = ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.EMAIL,
            valor='snapshot@restaurante.com',
            ativo=True,
            padrao=True,
            prioridade=1,
        )
        criar_pagamento_pix_manual(self.pedido)

        chave_inicial.ativo = False
        chave_inicial.padrao = False
        chave_inicial.save(update_fields=['ativo', 'padrao', 'atualizado_em'])
        ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.CNPJ,
            valor='19131243000197',
            ativo=True,
            padrao=True,
            prioridade=1,
        )

        response = self.client.get(f'/pagamentos/{self.pedido.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'snapshot@restaurante.com')
