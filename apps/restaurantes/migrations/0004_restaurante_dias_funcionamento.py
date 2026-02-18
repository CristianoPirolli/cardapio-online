from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('restaurantes', '0003_restaurante_tempos'),
    ]

    operations = [
        migrations.AddField(
            model_name='restaurante',
            name='funciona_domingo',
            field=models.BooleanField(default=True, verbose_name='Domingo'),
        ),
        migrations.AddField(
            model_name='restaurante',
            name='funciona_quarta',
            field=models.BooleanField(default=True, verbose_name='Quarta-feira'),
        ),
        migrations.AddField(
            model_name='restaurante',
            name='funciona_quinta',
            field=models.BooleanField(default=True, verbose_name='Quinta-feira'),
        ),
        migrations.AddField(
            model_name='restaurante',
            name='funciona_sabado',
            field=models.BooleanField(default=True, verbose_name='Sábado'),
        ),
        migrations.AddField(
            model_name='restaurante',
            name='funciona_segunda',
            field=models.BooleanField(default=True, verbose_name='Segunda-feira'),
        ),
        migrations.AddField(
            model_name='restaurante',
            name='funciona_sexta',
            field=models.BooleanField(default=True, verbose_name='Sexta-feira'),
        ),
        migrations.AddField(
            model_name='restaurante',
            name='funciona_terca',
            field=models.BooleanField(default=True, verbose_name='Terça-feira'),
        ),
    ]
