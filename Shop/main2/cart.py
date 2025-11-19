# shop/cart.py
from .models import Cart, CartItem, Product

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
    
    def add(self, product_id, quantity=1):
        try:
            product = Product.objects.get(id=product_id, available=True)
        
        # Проверяем наличие товара
            if quantity > product.quantity:
                return False, "Недостаточно товара на складе"
        
        # Получаем или создаем элемент корзины
            cart_item, created = CartItem.objects.get_or_create(
                cart=self.cart,
                product=product,
                defaults={
                    'quantity': quantity,
                    'price': product.price
                }
            )
        
            if not created:
                # Если товар уже в корзине, увеличиваем количество
                cart_item.quantity += quantity
                if cart_item.quantity > product.quantity:
                    cart_item.quantity = product.quantity
                cart_item.save()
        
            return True, "Товар добавлен в корзину"
        
        except Product.DoesNotExist:
            return False, "Товар не найден"
    
    def get_items(self):
        """Получить элементы корзины"""
        return self.cart.items.select_related('product').all()
    
    def get_total_quantity(self):
        """Общее количество товаров в корзине"""
        return sum(item.quantity for item in self.cart.items.all())
    
    def get_total_price(self):
        """Общая стоимость корзины"""
        return sum(item.total_price for item in self.cart.items.all())
    def clear(self):
        """Очистка корзины"""
        self.cart.items.all().delete()
    
    def update(self, product_id, quantity):
        """Обновить количество товара в корзине - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        try:
            product = Product.objects.get(id=product_id, available=True)
        
            if quantity <= 0:
                return self.remove(product_id)
        
            if quantity > product.quantity:
                return False, "Недостаточно товара на складе"
        
            try:
                cart_item = CartItem.objects.get(
                    cart=self.cart,
                    product_id=product_id
                )
                cart_item.quantity = quantity
                cart_item.save()
                return True, "Количество обновлено"
            except CartItem.DoesNotExist:
                return False, "Товар не найден в корзине"
            
        except Product.DoesNotExist:
            return False, "Товар не найден"

    def remove(self, product_id):
        """Удалить товар из корзины - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        deleted_count, _ = CartItem.objects.filter(
            cart=self.cart,
            product_id=product_id
        ).delete()
    
        if deleted_count > 0:
            return True, "Товар удален из корзины"
        else:
            return False, "Товар не найден в корзине"