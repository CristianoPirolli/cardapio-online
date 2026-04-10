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


@override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
)
class PainelPixKeysViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.proprietario = User.objects.create_user(username='painel-owner', password='pass')
        self.restaurante = Restaurante.objects.create(
            proprietario=self.proprietario,
            nome='Restaurante Painel PIX',
            subdominio='painel-pix',
            endereco='Rua Teste, 100',
            cidade='Sao Paulo',
            estado='SP',
            cep='01001-000',
            telefone='11999999999',
            email='painelpix@example.com',
        )
        self.client.force_login(self.proprietario)

    def test_restaurante_cria_multiplas_chaves_e_edita_sem_sair_da_tela(self):
        response_1 = self.client.post(
            '/pagamentos/painel/chaves-pix/criar/',
            data={
                'tipo': ChavePix.Tipo.EMAIL,
                'valor': 'financeiro@restaurante.com',
                'ativo': 'on',
                'padrao': 'on',
                'prioridade': 1,
            },
        )
        self.assertEqual(response_1.status_code, 302)

        response_2 = self.client.post(
            '/pagamentos/painel/chaves-pix/criar/',
            data={
                'tipo': ChavePix.Tipo.TELEFONE,
                'valor': '+5511988887777',
                'ativo': 'on',
                'prioridade': 2,
            },
        )
        self.assertEqual(response_2.status_code, 302)
        self.assertEqual(ChavePix.objects.filter(restaurante=self.restaurante).count(), 2)

        chave = ChavePix.objects.get(restaurante=self.restaurante, tipo=ChavePix.Tipo.TELEFONE)
        response_edit = self.client.post(
            f'/pagamentos/painel/chaves-pix/{chave.id}/editar/',
            data={
                'tipo': ChavePix.Tipo.EMAIL,
                'valor': 'novo-financeiro@restaurante.com',
                'ativo': 'on',
                'prioridade': 3,
            },
        )
        self.assertEqual(response_edit.status_code, 302)

        chave.refresh_from_db()
        self.assertEqual(chave.tipo, ChavePix.Tipo.EMAIL)
        self.assertEqual(chave.valor_normalizado, 'novo-financeiro@restaurante.com')
        self.assertEqual(chave.prioridade, 3)

    def test_ativar_desativar_e_definir_padrao_respeitam_integridade(self):
        chave_padrao = ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.EMAIL,
            valor='padrao@restaurante.com',
            ativo=True,
            padrao=True,
            prioridade=1,
        )
        chave_b = ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.CNPJ,
            valor='19131243000197',
            ativo=True,
            padrao=False,
            prioridade=2,
        )

        response_desativar = self.client.post(f'/pagamentos/painel/chaves-pix/{chave_padrao.id}/desativar/')
        self.assertEqual(response_desativar.status_code, 302)

        response_padrao = self.client.post(f'/pagamentos/painel/chaves-pix/{chave_b.id}/padrao/')
        self.assertEqual(response_padrao.status_code, 302)

        chave_padrao.refresh_from_db()
        chave_b.refresh_from_db()
        self.assertFalse(chave_padrao.ativo)
        self.assertFalse(chave_padrao.padrao)
        self.assertTrue(chave_b.padrao)
        self.assertEqual(
            ChavePix.objects.filter(restaurante=self.restaurante, ativo=True, padrao=True).count(),
            1,
        )

    def test_prioridade_ativa_duplicada_por_restaurante_e_rejeitada(self):
        ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.EMAIL,
            valor='um@restaurante.com',
            ativo=True,
            prioridade=7,
        )
        response = self.client.post(
            '/pagamentos/painel/chaves-pix/criar/',
            data={
                'tipo': ChavePix.Tipo.TELEFONE,
                'valor': '+5511977776666',
                'ativo': 'on',
                'prioridade': 7,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ja existe uma chave ativa com essa prioridade.')
        self.assertEqual(ChavePix.objects.filter(restaurante=self.restaurante, ativo=True, prioridade=7).count(), 1)

    def test_validacao_por_tipo_rejeita_cpf_cnpj_email_telefone_e_uuid_invalidos(self):
        casos = [
            (ChavePix.Tipo.CPF, '11111111111'),
            (ChavePix.Tipo.CNPJ, '11111111000111'),
            (ChavePix.Tipo.EMAIL, 'invalido-sem-arroba'),
            (ChavePix.Tipo.TELEFONE, '11999999999'),
            (ChavePix.Tipo.UUID, 'nao-uuid'),
        ]
        for tipo, valor in casos:
            with self.subTest(tipo=tipo):
                response = self.client.post(
                    '/pagamentos/painel/chaves-pix/criar/',
                    data={
                        'tipo': tipo,
                        'valor': valor,
                        'ativo': 'on',
                        'prioridade': 99,
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'inval')

        self.assertEqual(ChavePix.objects.filter(restaurante=self.restaurante).count(), 0)
