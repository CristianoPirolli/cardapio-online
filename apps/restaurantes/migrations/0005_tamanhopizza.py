from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('restaurantes', '0004_restaurante_dias_funcionamento'),
    ]

    operations = [
        migrations.CreateModel(
            name='TamanhoPizza',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=80, verbose_name='Nome do Tamanho')),
                ('fatias', models.PositiveIntegerField(default=0, help_text='Use 0 se não se aplicar.', verbose_name='Fatias')),
                ('diametro_cm', models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(0.1)], verbose_name='Diâmetro (cm)')),
                ('max_sabores', models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)], verbose_name='Máx. Sabores')),
                ('preco_base', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Preço Base (R$)')),
                ('ordem', models.PositiveIntegerField(default=0, verbose_name='Ordem')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('restaurante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tamanhos_pizza', to='restaurantes.restaurante', verbose_name='Restaurante')),
            ],
            options={
                'verbose_name': 'Tamanho de Pizza',
                'verbose_name_plural': 'Tamanhos de Pizza',
                'ordering': ['ordem', 'id'],
                'unique_together': {('restaurante', 'nome')},
            },
        ),
    ]
