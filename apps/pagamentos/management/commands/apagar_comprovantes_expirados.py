from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import os


class Command(BaseCommand):
    help = 'Remove arquivos de comprovante PIX com mais de 30 dias para economizar espaço.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=30,
            help='Quantidade de dias para expiração (padrão: 30)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas lista o que seria apagado, sem deletar nada.',
        )

    def handle(self, *args, **options):
        from apps.pagamentos.models import Pagamento

        dias = options['dias']
        dry_run = options['dry_run']
        limite = timezone.now() - timedelta(days=dias)

        expirados = Pagamento.objects.filter(
            criado_em__lt=limite,
        ).exclude(comprovante='').exclude(comprovante=None)

        total = expirados.count()

        if total == 0:
            self.stdout.write('Nenhum comprovante expirado encontrado.')
            return

        if dry_run:
            self.stdout.write(f'[dry-run] {total} comprovante(s) seriam removidos:')
            for p in expirados:
                self.stdout.write(f'  Pagamento #{p.id} | Pedido #{p.pedido_id} | {p.comprovante.name}')
            return

        removidos = 0
        erros = 0

        for pagamento in expirados:
            caminho = pagamento.comprovante.path if pagamento.comprovante else None
            try:
                if caminho and os.path.isfile(caminho):
                    os.remove(caminho)
                pagamento.comprovante = None
                pagamento.save(update_fields=['comprovante'])
                removidos += 1
            except Exception as e:
                self.stderr.write(f'Erro ao remover Pagamento #{pagamento.id}: {e}')
                erros += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Concluído: {removidos} comprovante(s) removido(s), {erros} erro(s).'
            )
        )
