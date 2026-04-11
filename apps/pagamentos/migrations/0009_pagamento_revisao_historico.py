from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('pagamentos', '0008_chave_pix_models_and_snapshot'),
    ]

    operations = [
        migrations.CreateModel(
            name='PagamentoRevisaoHistorico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('acao', models.CharField(choices=[('aceito', 'Aceito'), ('rejeitado', 'Rejeitado')], max_length=16, verbose_name='Acao')),
                ('motivo', models.CharField(choices=[('valido', 'Valido'), ('invalido', 'Invalido'), ('outro', 'Outro')], max_length=16, verbose_name='Motivo')),
                ('justificativa', models.TextField(verbose_name='Justificativa')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('operador', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='historico_revisao_pagamento', to=settings.AUTH_USER_MODEL, verbose_name='Operador')),
                ('pagamento', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='historico_revisao', to='pagamentos.pagamento', verbose_name='Pagamento')),
                ('pedido', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historico_revisao_pagamento', to='pedidos.pedido', verbose_name='Pedido')),
            ],
            options={
                'verbose_name': 'Historico de Revisao de Pagamento',
                'verbose_name_plural': 'Historico de Revisoes de Pagamento',
                'ordering': ['-criado_em', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='pagamentorevisaohistorico',
            index=models.Index(fields=['pedido', '-criado_em'], name='idx_rev_hist_pedido_criado'),
        ),
    ]
