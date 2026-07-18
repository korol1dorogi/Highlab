# shop/cart.py
from .models import Cart, CartItem, ProductVariant


def _merge_carts(primary, others):
    """Переносит позиции из корзин others в primary и удаляет пустые корзины-дубли.
    Количество одинаковых вариантов суммируется с ограничением по остатку на складе."""
    for other in others:
        if other.pk == primary.pk:
            continue
        for item in other.items.all():
            existing = primary.items.filter(product_variant=item.product_variant).first()
            if existing:
                total = existing.quantity + item.quantity
                cap = item.product_variant.quantity or total
                existing.quantity = min(total, cap)
                existing.save()
                item.delete()
            else:
                item.cart = primary
                item.save()
        other.delete()


def merge_session_cart_into_user(request, old_session_key, user):
    """При входе/регистрации переносит анонимную корзину (по старому ключу сессии)
    в корзину пользователя, чтобы набранные товары не терялись."""
    if not old_session_key:
        return
    anon_carts = list(Cart.objects.filter(session_key=old_session_key, user__isnull=True).order_by('id'))
    if not anon_carts:
        return
    user_carts = list(Cart.objects.filter(user=user).order_by('id'))
    if user_carts:
        primary = user_carts[0]
        _merge_carts(primary, user_carts[1:])
    else:
        primary = Cart.objects.create(user=user)
    _merge_carts(primary, anon_carts)


class CartManager:
    def __init__(self, request):
        self.request = request
        self.cart = self._get_or_create_cart()

    def _resolve_cart(self, **lookup):
        """Находит или создаёт корзину, безопасно переживая дубли (гонка get_or_create):
        если корзин несколько — сливает их в самую раннюю, а не падает 500."""
        carts = list(Cart.objects.filter(**lookup).order_by('id'))
        if not carts:
            return Cart.objects.create(**lookup)
        primary = carts[0]
        if len(carts) > 1:
            _merge_carts(primary, carts[1:])
        return primary

    def _get_or_create_cart(self):
        """Создаем или получаем корзину - РАБОТАЕТ ДЛЯ АНОНИМОВ"""
        if self.request.user.is_authenticated:
            # Для авторизованных пользователей
            return self._resolve_cart(user=self.request.user)
        # Для анонимных пользователей (через сессии)
        session_key = self.request.session.session_key
        if not session_key:
            self.request.session.create()
            session_key = self.request.session.session_key
        return self._resolve_cart(session_key=session_key, user=None)
    
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