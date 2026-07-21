import requests
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_lead_notification(self, lead_id):
    """Асинхронная отправка заявки с лендинга в Telegram."""
    from .models import Lead

    try:
        lead = Lead.objects.get(id=lead_id)
    except Lead.DoesNotExist:
        logger.warning('Заявка #%s не найдена', lead_id)
        return False

    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat_ids = getattr(settings, 'TELEGRAM_CHAT_IDS', None) or []
    if not token or not chat_ids:
        logger.warning('Telegram не настроен — заявка #%s сохранена, но не отправлена', lead_id)
        return False

    text = (
        f'🆕 <b>Новая заявка с сайта</b>\n\n'
        f'👤 {lead.name}\n'
        f'📞 {lead.phone}\n'
    )
    if getattr(lead, 'source', ''):
        text += f'🎯 {lead.source}\n'
    if lead.message:
        text += f'\n💬 {lead.message}\n'
    text += f'\n⏰ {lead.created.strftime("%d.%m.%Y %H:%M")}'

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    sent_any = False
    for chat_id in chat_ids:
        try:
            resp = requests.post(
                url,
                json={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'},
                timeout=10,
            )
            if resp.status_code == 200:
                sent_any = True
            else:
                logger.error('Telegram вернул %s по заявке #%s (chat %s)', resp.status_code, lead_id, chat_id)
        except requests.RequestException as exc:
            logger.error('Ошибка отправки заявки #%s в чат %s: %s', lead_id, chat_id, exc)
    if not sent_any:
        try:
            raise self.retry()
        except self.MaxRetriesExceededError:
            pass
    return sent_any
