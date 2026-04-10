from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Order, Profile

@receiver(pre_save, sender=Order)
def handle_postpay_reservation(sender, instance, **kwargs):
    """Управление резервом и долгом при изменении статуса заказа с постоплатой"""
    if not instance.pk or not instance.user:
        return  # Новый заказ или без пользователя – обрабатывается в checkout
    
    try:
        old_order = Order.objects.get(pk=instance.pk)
    except Order.DoesNotExist:
        return
    
    # Только для заказов с постоплатой
    if old_order.payment_method != 'postpay':
        return
    
    old_status = old_order.status
    new_status = instance.status
    
    # Если статус не изменился – ничего не делаем
    if old_status == new_status:
        return
    
    profile = instance.user.profile
    total = old_order.total_price
    
    # Переход в completed: освобождаем резерв, добавляем в долг
    if old_status != 'completed' and new_status == 'completed':
        profile.reserved_postpay = max(0, profile.reserved_postpay - total)
        profile.debt += total
        # Устанавливаем дату погашения, если ещё не установлена или просрочена
        if not profile.debt_deadline or profile.debt_deadline < timezone.now().date():
            profile.debt_deadline = timezone.now().date() + timezone.timedelta(days=30)
        profile.save(update_fields=['reserved_postpay', 'debt', 'debt_deadline'])
    
    # Переход из completed обратно в другой статус (редко, но для полноты)
    elif old_status == 'completed' and new_status != 'completed':
        # Возвращаем долг в резерв
        profile.debt = max(0, profile.debt - total)
        profile.reserved_postpay += total
        profile.save(update_fields=['reserved_postpay', 'debt'])
    
    # Отмена заказа до завершения: просто освобождаем резерв
    elif old_status != 'completed' and new_status == 'cancelled':
        profile.reserved_postpay = max(0, profile.reserved_postpay - total)
        profile.save(update_fields=['reserved_postpay'])
    
    # Если заказ восстанавливается из отменённого (маловероятно)
    elif old_status == 'cancelled' and new_status not in ['completed', 'cancelled']:
        profile.reserved_postpay += total
        profile.save(update_fields=['reserved_postpay'])