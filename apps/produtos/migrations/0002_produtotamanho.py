from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProdutoTamanho',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(help_text='Ex: Broto, Média, Grande', max_length=80, verbose_name='Nome do Tamanho')),
                ('fatias', models.PositiveIntegerField(default=0, help_text='Quantidade de fatias (opcional). Use 0 se não se aplicar.', verbose_name='Fatias')),
                ('diametro_cm', models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(0.1)], verbose_name='Diâmetro (cm)')),
                ('max_sabores', models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)], verbose_name='Máximo de Sabores')),
                ('preco', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)], verbose_name='Preço (R$)')),
                ('ordem', models.PositiveIntegerField(default=0, verbose_name='Ordem')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tamanhos', to='produtos.produto', verbose_name='Produto')),
            ],
            options={
                'verbose_name': 'Tamanho de Produto',
                'verbose_name_plural': 'Tamanhos de Produto',
                'ordering': ['ordem', 'id'],
                'unique_together': {('produto', 'nome')},
            },
        ),
    ]
