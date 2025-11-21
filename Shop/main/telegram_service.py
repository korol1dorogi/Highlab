# shop/telegram_service.py
import requests
from django.conf import settings
import re

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
        """Форматирование сообщения для Telegram с правильным отображением вариантов"""
        items_text = ""
        for item in order.items.all():
            # Получаем полное название товара с вариантом
            product_name = self._get_full_product_name(item)
            
            items_text += f"• {product_name}\n"
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
    
    def _get_full_product_name(self, order_item):
        """
        Умное формирование полного названия товара с учетом вариантов
        """
        try:
            product = order_item.product_variant.product
            variant = order_item.product_variant
            
            product_name = product.name
            variant_name = variant.name
            
            # Список базовых/дефолтных названий вариантов, которые не нужно показывать
            base_variant_names = [
                'основной вариант', 'базовый вариант', 'default', 'base',
                'стандартный', 'standard', 'обычный', 'regular'
            ]
            
            # Если вариант базовый - не показываем его
            if (variant_name and 
                variant_name.lower().strip() in base_variant_names):
                return product_name
            
            # Если название варианта слишком короткое (только характеристики)
            # и не содержит слов, указывающих на полное описание
            if self._is_short_variant_name(variant_name):
                return f"{product_name} - {variant_name}"
            
            # Если вариант содержит только характеристики (цифры, объем, цвет и т.д.)
            if self._is_specification_only(variant_name):
                return f"{product_name} - {variant_name}"
            
            # Если название варианта похоже на основное название товара
            if self._is_similar_to_product_name(product_name, variant_name):
                return product_name
            
            # Во всех остальных случаях показываем оба названия
            return f"{product_name} - {variant_name}"
                
        except Exception as e:
            # Fallback на случай ошибок
            print(f"Ошибка формирования названия товара: {e}")
            try:
                return order_item.product_variant.product.name
            except:
                return "Товар"
    
    def _is_short_variant_name(self, variant_name):
        """Проверяет, является ли название варианта коротким (только характеристики)"""
        if not variant_name:
            return False
        
        # Короткие названия (меньше 3 слов и меньше 15 символов)
        words = variant_name.split()
        if len(words) <= 2 and len(variant_name) < 15:
            return True
        
        # Паттерны, указывающие на характеристики
        spec_patterns = [
            r'\d+\s*[ГгTТ][Бб]', r'\d+\s*[GgTt][Bb]', r'\d+\s*[Мм]?[Бб]',
            r'\d+\s*GB', r'\d+\s*TB', r'\d+\s*MB',
            r'\d+\s*[xх×]\s*\d', r'\d+\s*шт', r'\d+\s*гр',
            r'[Кк]расный', r'[Сс]иний', r'[Чч]ерный', r'[Бб]елый',
            r'[Ss]ilver', r'[Bb]lack', r'[Ww]hite', r'[Gg]old'
        ]
        
        for pattern in spec_patterns:
            if re.search(pattern, variant_name, re.IGNORECASE):
                return True
        
        return False
    
    def _is_specification_only(self, variant_name):
        """Проверяет, содержит ли вариант только спецификации"""
        if not variant_name:
            return False
        
        # Слова, указывающие на полное описание (не только характеристики)
        descriptive_words = ['версия', 'модель', 'комплект', 'набор', 'пакет', 'edition', 'model', 'kit']
        
        has_descriptive = any(word in variant_name.lower() for word in descriptive_words)
        
        # Если есть цифры и нет описательных слов - это скорее всего характеристики
        has_numbers = any(char.isdigit() for char in variant_name)
        
        return has_numbers and not has_descriptive
    
    def _is_similar_to_product_name(self, product_name, variant_name):
        """Проверяет, похоже ли название варианта на основное название товара"""
        if not variant_name or not product_name:
            return False
        
        # Если вариант начинается с названия товара
        if variant_name.lower().startswith(product_name.lower()):
            return True
        
        # Если вариант содержит название товара и мало дополнительной информации
        if (product_name.lower() in variant_name.lower() and
            len(variant_name) - len(product_name) < 10):
            return True
        
        return False