from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from monitoring.models import Report
from monitoring.services import build_digest, send_telegram


class Command(BaseCommand):
    help = ('Ежедневная сводка по бэкапам клиентов в Telegram + чистка старых отчётов. '
            'Запускается cron-ом на хосте раз в сутки.')

    def add_arguments(self, parser):
        parser.add_argument('--hours', type=int, default=24, help='За сколько часов сводка (по умолчанию 24)')
        parser.add_argument('--dry-run', action='store_true', help='Только напечатать, не отправлять')

    def handle(self, *args, hours, dry_run, **options):
        text, counters = build_digest(hours=hours)
        if dry_run:
            self.stdout.write(text)
            return

        if send_telegram(text):
            self.stdout.write(self.style.SUCCESS(f'Сводка отправлена: {dict(counters)}'))
        else:
            self.stderr.write('Сводку отправить не удалось (см. лог)')

        keep_days = getattr(settings, 'MONITORING_RETENTION_DAYS', 180)
        deleted, _ = Report.objects.filter(received_at__lt=timezone.now() - timedelta(days=keep_days)).delete()
        if deleted:
            self.stdout.write(f'Удалено старых отчётов: {deleted}')
