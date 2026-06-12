from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_order_notification(self, order_id):
    """Асинхронная отправка уведомления о заказе в Telegram."""
    from .models import Order
    from .telegram_service import TelegramService

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        logger.warning("Заказ #%s не найден, уведомление не отправлено", order_id)
        return False

    service = TelegramService()
    sent = service.send_order_notification(order)

    if not sent:
        # Повторяем попытку при сетевой ошибке / недоступности Telegram
        try:
            raise self.retry()
        except self.MaxRetriesExceededError:
            logger.error("Не удалось отправить уведомление по заказу #%s", order_id)
    return sent


@shared_task
def send_order_confirmation(order_id):
    """Письмо-подтверждение заказа покупателю (если указан email)."""
    from django.core.mail import EmailMessage
    from django.template.loader import render_to_string
    from django.conf import settings
    from .models import Order

    try:
        order = Order.objects.prefetch_related('items__product_variant__product').get(id=order_id)
    except Order.DoesNotExist:
        logger.warning("Заказ #%s не найден — письмо не отправлено", order_id)
        return False

    if not order.email:
        return False

    subject = f"Заказ №{order.id} принят — Лаборатория ВТ"
    body = render_to_string('emails/order_confirmation.txt', {'order': order})
    try:
        EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [order.email]).send()
        return True
    except Exception as e:
        logger.error("Не удалось отправить письмо по заказу #%s: %s", order_id, e)
        return False
