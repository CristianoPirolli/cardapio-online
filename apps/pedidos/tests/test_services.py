from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from apps.entregas.models import Entrega
from apps.pedidos.models import Pedido
from apps.pedidos.services import (
    PedidoCheckoutError,
    criar_pedido_do_carrinho,
    validar_dados_checkout,
)
from apps.produtos.models import Categoria, Produto
from apps.restaurantes.models import Restaurante


class PedidoServicesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', password='123')
        self.restaurante = Restaurante.objects.create(
            nome='Pizzaria Teste',
            subdominio='pizzaria-teste',
            proprietario=self.user,
            endereco='Rua A, 10',
            cidade='Cidade',
            estado='SP',
            cep='01000-000',
            telefone='11999999999',
            email='restaurante@test.com',
            taxa_entrega=Decimal('5.00'),
            pedido_minimo=Decimal('10.00'),
            taxa_imposto=Decimal('10.00'),
            ativo=True,
        )
        self.categoria = Categoria.objects.create(
            restaurante=self.restaurante,
            nome='Pizzas',
            ordem=1,
            adicional_sabor='0.00',
            eh_pizza=True,
            ativo=True,
        )
        self.produto = Produto.objects.create(
            restaurante=self.restaurante,
            categoria=self.categoria,
            nome='Calabresa',
            preco=Decimal('20.00'),
            disponivel=True,
        )

    def test_validar_dados_checkout_exige_nome_e_telefone(self):
        with self.assertRaises(PedidoCheckoutError):
            validar_dados_checkout({
                'cliente_nome': '',
                'cliente_telefone': '',
                'tipo_entrega': 'delivery',
            })

    def test_criar_pedido_do_carrinho_cria_pedido_itens_e_entrega(self):
        itens_sessao = {
            str(self.produto.id): {
                'produto_id': self.produto.id,
                'quantidade': 1,
                'observacao': '',
                'tamanho_nome': '',
                'sabores_nomes': [self.produto.nome],
                'preco_unitario': '20.00',
                'preco_base': '20.00',
                'adicional_sabores': '0.00',
            }
        }
        dados = validar_dados_checkout({
            'cliente_nome': 'Cliente Teste',
            'cliente_telefone': '11911111111',
            'cliente_email': 'cliente@test.com',
            'endereco_entrega': 'Rua B, 20',
            'tipo_entrega': 'delivery',
            'observacoes': 'Sem cebola',
        })

        pedido = criar_pedido_do_carrinho(self.restaurante, itens_sessao, dados)

        pedido.refresh_from_db()
        self.assertEqual(Pedido.objects.count(), 1)
        self.assertEqual(pedido.itens.count(), 1)
        self.assertEqual(pedido.subtotal, self.produto.preco)
        self.assertEqual(pedido.taxa_entrega, self.restaurante.taxa_entrega)
        self.assertTrue(Entrega.objects.filter(pedido=pedido).exists())

    def test_criar_pedido_do_carrinho_faz_rollback_quando_minimo_nao_atingido(self):
        self.restaurante.pedido_minimo = Decimal('50.00')
        self.restaurante.save(update_fields=['pedido_minimo'])

        itens_sessao = {
            str(self.produto.id): {
                'produto_id': self.produto.id,
                'quantidade': 1,
                'observacao': '',
                'tamanho_nome': '',
                'sabores_nomes': [self.produto.nome],
                'preco_unitario': '20.00',
                'preco_base': '20.00',
                'adicional_sabores': '0.00',
            }
        }
        dados = validar_dados_checkout({
            'cliente_nome': 'Cliente Teste',
            'cliente_telefone': '11911111111',
            'endereco_entrega': 'Rua B, 20',
            'tipo_entrega': 'delivery',
        })

        with self.assertRaises(PedidoCheckoutError):
            criar_pedido_do_carrinho(self.restaurante, itens_sessao, dados)

        self.assertEqual(Pedido.objects.count(), 0)
        self.assertEqual(Entrega.objects.count(), 0)
