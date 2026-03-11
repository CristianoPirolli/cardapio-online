# =============================================================================
# apps/restaurantes/management/commands/seed.py
#
# Comando para popular o banco com dados de teste.
# Uso: python manage.py seed
#
# Cria:
# - 1 superusuário (admin)
# - 2 restaurantes com categorias e produtos
# =============================================================================

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.restaurantes.models import Restaurante
from apps.produtos.models import Categoria, Produto


class Command(BaseCommand):
    help = 'Popula o banco de dados com dados de teste'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando seed...')

        # --- Superusuário ---
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@meusistema.com',
                password='admin123',
                first_name='Admin',
                last_name='Sistema'
            )
            self.stdout.write(self.style.SUCCESS('Superusuário "admin" criado (senha: admin123)'))
        else:
            admin = User.objects.get(username='admin')
            self.stdout.write('Superusuário "admin" já existe.')

        # --- Restaurante 1: Pizzaria ---
        user1, created = User.objects.get_or_create(
            username='pizzaria',
            defaults={
                'email': 'pizzaria@meusistema.com',
                'first_name': 'João',
                'last_name': 'Silva',
            }
        )
        if created:
            user1.set_password('pizza123')
            user1.save()

        rest1, _ = Restaurante.objects.get_or_create(
            subdominio='pizzaria1',
            defaults={
                'nome': 'Pizzaria do João',
                'proprietario': user1,
                'descricao': 'As melhores pizzas artesanais da cidade!',
                'endereco': 'Rua das Flores, 123',
                'cidade': 'São Paulo',
                'estado': 'SP',
                'cep': '01234-567',
                'telefone': '(11) 99999-1111',
                'email': 'contato@pizzariadojoao.com',
                'taxa_entrega': 8.00,
                'pedido_minimo': 25.00,
                'taxa_imposto': 5.00,
            }
        )
        self.stdout.write(self.style.SUCCESS(f'Restaurante: {rest1.nome}'))

        # Categorias e Produtos - Pizzaria
        cat_pizzas, _ = Categoria.objects.get_or_create(
            restaurante=rest1, nome='Pizzas Tradicionais', defaults={'ordem': 1}
        )
        cat_bebidas, _ = Categoria.objects.get_or_create(
            restaurante=rest1, nome='Bebidas', defaults={'ordem': 2}
        )
        cat_sobremesas, _ = Categoria.objects.get_or_create(
            restaurante=rest1, nome='Sobremesas', defaults={'ordem': 3}
        )

        pizzas = [
            ('Pizza Margherita', 'Molho de tomate, mussarela e manjericão fresco', 39.90, True),
            ('Pizza Calabresa', 'Calabresa, cebola e azeitonas pretas', 35.90, False),
            ('Pizza Quatro Queijos', 'Mussarela, provolone, gorgonzola e parmesão', 45.90, True),
            ('Pizza Portuguesa', 'Presunto, ovos, cebola, azeitonas e ervilha', 42.90, False),
            ('Pizza Frango com Catupiry', 'Frango desfiado com catupiry', 40.90, False),
        ]
        for nome, desc, preco, destaque in pizzas:
            Produto.objects.get_or_create(
                restaurante=rest1, nome=nome,
                defaults={
                    'categoria': cat_pizzas, 'descricao': desc,
                    'preco': preco, 'destaque': destaque,
                }
            )

        bebidas = [
            ('Coca-Cola 350ml', 'Lata', 6.00),
            ('Guaraná Antarctica 350ml', 'Lata', 5.50),
            ('Suco Natural de Laranja', '500ml', 9.90),
            ('Água Mineral 500ml', 'Com ou sem gás', 3.50),
        ]
        for nome, desc, preco in bebidas:
            Produto.objects.get_or_create(
                restaurante=rest1, nome=nome,
                defaults={
                    'categoria': cat_bebidas, 'descricao': desc,
                    'preco': preco,
                }
            )

        sobremesas = [
            ('Petit Gâteau', 'Bolo de chocolate com sorvete de creme', 22.90),
            ('Tiramisù', 'Sobremesa italiana com café e mascarpone', 18.90),
        ]
        for nome, desc, preco in sobremesas:
            Produto.objects.get_or_create(
                restaurante=rest1, nome=nome,
                defaults={
                    'categoria': cat_sobremesas, 'descricao': desc,
                    'preco': preco,
                }
            )

        # --- Restaurante 2: Hamburgueria ---
        user2, created = User.objects.get_or_create(
            username='hamburgueria',
            defaults={
                'email': 'hamburgueria@meusistema.com',
                'first_name': 'Maria',
                'last_name': 'Santos',
            }
        )
        if created:
            user2.set_password('burger123')
            user2.save()

        rest2, _ = Restaurante.objects.get_or_create(
            subdominio='hamburgueria2',
            defaults={
                'nome': 'Burger da Maria',
                'proprietario': user2,
                'descricao': 'Hambúrgueres artesanais com ingredientes premium!',
                'endereco': 'Av. Paulista, 456',
                'cidade': 'São Paulo',
                'estado': 'SP',
                'cep': '01310-100',
                'telefone': '(11) 99999-2222',
                'email': 'contato@burgerdamaria.com',
                'taxa_entrega': 6.00,
                'pedido_minimo': 30.00,
                'taxa_imposto': 5.00,
            }
        )
        self.stdout.write(self.style.SUCCESS(f'Restaurante: {rest2.nome}'))

        cat_burgers, _ = Categoria.objects.get_or_create(
            restaurante=rest2, nome='Hambúrgueres', defaults={'ordem': 1}
        )
        cat_acomp, _ = Categoria.objects.get_or_create(
            restaurante=rest2, nome='Acompanhamentos', defaults={'ordem': 2}
        )
        cat_beb2, _ = Categoria.objects.get_or_create(
            restaurante=rest2, nome='Bebidas', defaults={'ordem': 3}
        )

        burgers = [
            ('Classic Burger', 'Blend 180g, queijo cheddar, alface, tomate e molho especial', 32.90, True),
            ('Bacon Burger', 'Blend 180g, bacon crocante, queijo e cebola caramelizada', 36.90, True),
            ('Veggie Burger', 'Hambúrguer de grão-de-bico, queijo e salada', 29.90, False),
            ('Double Smash', 'Dois blends 90g, queijo americano e pickles', 38.90, False),
        ]
        for nome, desc, preco, destaque in burgers:
            Produto.objects.get_or_create(
                restaurante=rest2, nome=nome,
                defaults={
                    'categoria': cat_burgers, 'descricao': desc,
                    'preco': preco, 'destaque': destaque,
                }
            )

        acomp = [
            ('Batata Frita', 'Porção crocante com sal e orégano', 15.90),
            ('Onion Rings', 'Anéis de cebola empanados', 18.90),
        ]
        for nome, desc, preco in acomp:
            Produto.objects.get_or_create(
                restaurante=rest2, nome=nome,
                defaults={
                    'categoria': cat_acomp, 'descricao': desc, 'preco': preco,
                }
            )

        self.stdout.write(self.style.SUCCESS('Seed concluído com sucesso!'))
        self.stdout.write('')
        self.stdout.write('Contas criadas:')
        self.stdout.write('  admin     / admin123   (superusuário)')
        self.stdout.write('  pizzaria  / pizza123   (Pizzaria do João)')
        self.stdout.write('  hamburgueria / burger123 (Burger da Maria)')
