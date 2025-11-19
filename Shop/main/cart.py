# shop/cart.py
from .models import Cart, CartItem, ProductVariant

class CartManager:
    def __init__(self, request):
        self.request = request
        self.cart = self._get_or_create_cart()
    
    def _get_or_create_cart(self):
        """Создаем или получаем корзину - РАБОТАЕТ ДЛЯ АНОНИМОВ"""
        if self.request.user.is_authenticated:
            # Для авторизованных пользователей
            cart, created = Cart.objects.get_or_create(user=self.request.user)
        else:
            # Для анонимных пользователей (через сессии)
            session_key = self.request.session.session_key
            if not session_key:
                self.request.session.create()
                session_key = self.request.session.session_key
            
            cart, created = Cart.objects.get_or_create(
                session_key=session_key,
                user=None
            )
        return cart
    
    def add(self, variant_id, quantity=1):
        """Добавление варианта товара в корзину"""
        try:
            variant = ProductVariant.objects.get(id=variant_id, is_active=True)
            product = variant.product
            
            # Проверяем наличие варианта
            if quantity > variant.quantity:
                return False, "Недостаточно товара на складе"
            
            # Получаем или создаем элемент корзины
            cart_item, created = CartItem.objects.get_or_create(
                cart=self.cart,
                product_variant=variant,
                defaults={
                    'quantity': quantity,
                    'price': variant.price
                }
            )
            
            if not created:
                # Если товар уже в корзине, увеличиваем количество
                cart_item.quantity += quantity
                if cart_item.quantity > variant.quantity:
                    cart_item.quantity = variant.quantity
                cart_item.save()
            
            return True, "Товар добавлен в корзину"
        
        except ProductVariant.DoesNotExist:
            return False, "Вариант товара не найден"
    
    def get_items(self):
        """Получить элементы корзины"""
        return self.cart.items.select_related('product_variant', 'product_variant__product').all()
    
    def get_total_quantity(self):
        """Общее количество товаров в корзине"""
        return sum(item.quantity for item in self.cart.items.all())
    
    def get_total_price(self):
        """Общая стоимость корзины"""
        return sum(item.total_price for item in self.cart.items.all())
    
    def clear(self):
        """Очистка корзины"""
        self.cart.items.all().delete()
    
    def update(self, variant_id, quantity):
        """Обновить количество варианта товара в корзине"""
        try:
            variant = ProductVariant.objects.get(id=variant_id, is_active=True)
            
            if quantity <= 0:
                return self.remove(variant_id)
            
            if quantity > variant.quantity:
                return False, "Недостаточно товара на складе"
            
            try:
                cart_item = CartItem.objects.get(
                    cart=self.cart,
                    product_variant_id=variant_id
                )
                cart_item.quantity = quantity
                cart_item.save()
                
                return True, "Количество обновлено"
            except CartItem.DoesNotExist:
                return False, "Товар не найден в корзине"
            
        except ProductVariant.DoesNotExist:
            return False, "Вариант товара не найден"

    def remove(self, variant_id):
        """Удалить вариант товара из корзины"""
        deleted_count, _ = CartItem.objects.filter(
            cart=self.cart,
            product_variant_id=variant_id
        ).delete()
        
        if deleted_count > 0:
            return True, "Товар удален из корзины"
        else:
            return False, "Товар не найден в корзине"