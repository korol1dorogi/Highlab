from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_report_alert(self, report_id):
    """Мгновенное сообщение в Telegram: бэкап упал или снова заработал."""
    from .models import Report
    from .services import format_alert, send_telegram

    try:
        report = Report.objects.select_related('job__host__company').get(pk=report_id)
    except Report.DoesNotExist:
        logger.warning('Отчёт мониторинга #%s не найден', report_id)
        return False

    sent = send_telegram(format_alert(report))
    if not sent:
        try:
            raise self.retry()
        except self.MaxRetriesExceededError:
            logger.error('Не удалось отправить тревогу по отчёту #%s', report_id)
    return sent
