# shop/telegram_service.py
import requests
from django.conf import settings

class TelegramService:
    """Сервис для отправки уведомлений в Telegram"""
    
    def __init__(self):
        self.bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '8057120036:AAFki_EMGugtSa8pCQJ_p8ypFZR4l9lwteE')
        self.chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', '720118745')
    
    def send_order_notification(self, order):
        """Отправка уведомления о новом заказе"""
        if not self.bot_token or not self.chat_id:
            print("⚠️ Telegram bot token или chat_id не настроены!")
            return False
        
        message = self._format_order_message(order)
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                print("✅ Уведомление отправлено в Telegram!")
                return True
            else:
                print(f"❌ Ошибка отправки в Telegram: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Ошибка подключения к Telegram: {e}")
            return False
    
    def _format_order_message(self, order):
        """Форматирование сообщения для Telegram"""
        items_text = ""
        for item in order.items.all():
            items_text += f"• {item.product.name}\n"
            items_text += f"  Количество: {item.quantity} шт.\n"
            items_text += f"  Цена: {item.price} ₽\n"
            items_text += f"  Сумма: {item.total_price} ₽\n\n"
        
        message = f"""
🛍 <b>НОВЫЙ ЗАКАЗ #{order.id}</b>

👤 <b>Клиент:</b>
{order.full_name}
📞 {order.phone}
📧 {order.email}

🏠 <b>Адрес доставки:</b>
{order.address}

📦 <b>Состав заказа:</b>
{items_text}

💰 <b>Итого: {order.total_price} ₽</b>

💬 <b>Комментарий:</b>
{order.comment if order.comment else 'Нет комментария'}

⏰ <b>Заказ создан:</b>
{order.created.strftime('%d.%m.%Y %H:%M')}
        """
        return message.strip()