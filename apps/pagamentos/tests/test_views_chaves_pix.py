from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings

from apps.pagamentos.models import ChavePix, ChavePixHistorico
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

    def test_mutacoes_de_painel_geram_historico_com_ator_quando_acao_e_diff(self):
        create_response = self.client.post(
            '/pagamentos/painel/chaves-pix/criar/',
            data={
                'tipo': ChavePix.Tipo.EMAIL,
                'valor': 'auditoria@restaurante.com',
                'ativo': 'on',
                'padrao': 'on',
                'prioridade': 1,
            },
        )
        self.assertEqual(create_response.status_code, 302)
        chave = ChavePix.objects.get(restaurante=self.restaurante)

        edit_response = self.client.post(
            f'/pagamentos/painel/chaves-pix/{chave.id}/editar/',
            data={
                'tipo': ChavePix.Tipo.EMAIL,
                'valor': 'auditoria-nova@restaurante.com',
                'ativo': 'on',
                'padrao': 'on',
                'prioridade': 2,
            },
        )
        self.assertEqual(edit_response.status_code, 302)

        eventos = list(
            ChavePixHistorico.objects.filter(chave_pix=chave).order_by('-criado_em', '-id')
        )
        self.assertEqual(len(eventos), 2)
        self.assertEqual(eventos[0].acao, ChavePixHistorico.Acao.EDICAO)
        self.assertEqual(eventos[0].ator_id, self.proprietario.id)
        self.assertIsNotNone(eventos[0].criado_em)
        self.assertEqual(eventos[0].antes.get('prioridade'), 1)
        self.assertEqual(eventos[0].depois.get('prioridade'), 2)
        self.assertEqual(eventos[1].acao, ChavePixHistorico.Acao.CRIACAO)
        self.assertEqual(eventos[1].antes, {})
        self.assertEqual(eventos[1].depois.get('tipo'), ChavePix.Tipo.EMAIL)

    def test_eventos_de_checkout_nao_entram_no_historico_de_painel(self):
        ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.EMAIL,
            valor='checkout@restaurante.com',
            ativo=True,
            padrao=True,
            prioridade=1,
        )
        pedido = Pedido.objects.create(
            restaurante=self.restaurante,
            cliente_nome='Cliente Checkout',
            cliente_telefone='11999999999',
            status='aguardando',
            pago=False,
            subtotal='50.00',
            taxa_entrega='5.00',
            imposto='0.00',
            total='55.00',
        )

        before = ChavePixHistorico.objects.count()
        response = self.client.get(f'/pagamentos/{pedido.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChavePixHistorico.objects.count(), before)

    def test_historico_aparece_na_tela_ordenado_do_mais_recente_para_antigo(self):
        self.client.post(
            '/pagamentos/painel/chaves-pix/criar/',
            data={
                'tipo': ChavePix.Tipo.EMAIL,
                'valor': 'ordem@restaurante.com',
                'ativo': 'on',
                'padrao': 'on',
                'prioridade': 1,
            },
        )
        chave = ChavePix.objects.get(restaurante=self.restaurante)

        self.client.post(
            f'/pagamentos/painel/chaves-pix/{chave.id}/editar/',
            data={
                'tipo': ChavePix.Tipo.EMAIL,
                'valor': 'ordem2@restaurante.com',
                'ativo': 'on',
                'padrao': 'on',
                'prioridade': 2,
            },
        )
        self.client.post(f'/pagamentos/painel/chaves-pix/{chave.id}/desativar/')

        response = self.client.get('/painel/chaves-pix/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Desativacao')
        self.assertContains(response, 'Edicao')
        self.assertContains(response, 'Criacao')

        content = response.content.decode('utf-8')
        self.assertLess(content.find('Desativacao'), content.find('Edicao'))
        self.assertLess(content.find('Edicao'), content.find('Criacao'))

    def test_painel_pix_keys_exige_login(self):
        self.client.logout()
        response = self.client.get('/painel/chaves-pix/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/', response['Location'])

    def test_usuario_de_outro_restaurante_nao_pode_editar_chave(self):
        chave = ChavePix.objects.create(
            restaurante=self.restaurante,
            tipo=ChavePix.Tipo.EMAIL,
            valor='seguro@restaurante.com',
            ativo=True,
            padrao=True,
            prioridade=1,
        )
        outro_user = User.objects.create_user(username='outro-owner', password='pass')
        outro_restaurante = Restaurante.objects.create(
            proprietario=outro_user,
            nome='Outro Restaurante',
            subdominio='outro-rest',
            endereco='Rua B, 1',
            cidade='Sao Paulo',
            estado='SP',
            cep='01002-000',
            telefone='11998887777',
            email='outro@example.com',
        )
        self.assertIsNotNone(outro_restaurante.id)
        self.client.force_login(outro_user)

        response = self.client.post(
            f'/pagamentos/painel/chaves-pix/{chave.id}/editar/',
            data={
                'tipo': ChavePix.Tipo.EMAIL,
                'valor': 'hacker@restaurante.com',
                'ativo': 'on',
                'padrao': 'on',
                'prioridade': 3,
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_painel_pedidos_regressao_basica_permanece_funcional(self):
        response = self.client.get('/painel/pedidos/')
        self.assertEqual(response.status_code, 200)
