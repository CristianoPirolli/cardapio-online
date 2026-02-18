from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pedidos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='itempedido',
            name='sabores_descricao',
            field=models.CharField(blank=True, max_length=300, verbose_name='Sabores'),
        ),
        migrations.AddField(
            model_name='itempedido',
            name='tamanho_nome',
            field=models.CharField(blank=True, max_length=80, verbose_name='Tamanho'),
        ),
    ]
