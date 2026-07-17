# shop/models.py
from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from mptt.models import MPTTModel, TreeForeignKey
from django.http import Http404

class Category(MPTTModel):
    """
    Модель категорий товаров с поддержкой иерархии
    Особенности: MPTT для древовидной структуры, slug для ЧПУ
    """
    name = models.CharField(
        max_length=200, 
        db_index=True,
        verbose_name='Название категории'
    )
    slug = models.SlugField(
        max_length=200, 
        unique=True,
        verbose_name='URL категории'
    )
    description = models.TextField(
        blank=True, 
        verbose_name='Описание категории'
    )
    image = models.ImageField(
        upload_to='categories/%Y/%m/%d/',
        blank=True,
        verbose_name='Изображение категории'
    )
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Родительская категория'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активная категория'
    )
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class MPTTMeta:
        order_insertion_by = ['name']
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """Генерирует URL с учетом иерархии категорий"""
        if self.parent:
            # Строим путь из slug всех предков
            path = '/'.join([cat.slug for cat in self.get_ancestors(include_self=True)])
            return reverse('shop:product_list_by_category', args=[path])
        else:
            return reverse('shop:product_list_by_category', args=[self.slug])

    def get_all_children(self):
        """Получить всех потомков категории"""
        return self.get_descendants(include_self=False)
    
    def get_all_products(self):
        """Получить все товары в категории и её подкатегориях"""
        from django.db.models import Q
        categories = self.get_descendants(include_self=True)
        return Product.objects.filter(category__in=categories, available=True)
    
    def get_breadcrumbs(self):
        """Получить хлебные крошки для категории"""
        ancestors = self.get_ancestors(include_self=True)
        return [{'name': cat.name, 'url': cat.get_absolute_url()} for cat in ancestors]
    
    def get_products_count(self):
        """Получить общее количество товаров в категории и всех её подкатегориях"""
        from django.db.models import Q
        categories = self.get_descendants(include_self=True)
        return Product.objects.filter(
            category__in=categories, 
            available=True
        ).count()
    
    @classmethod
    def get_root_categories(cls):
        """Получить корневые категории (без родителей)"""
        return cls.objects.filter(parent=None, is_active=True)

class Product(models.Model):
    """
    Модель товаров магазина (обновленная)
    """
    category = models.ForeignKey(
        Category,
        related_name='products',
        on_delete=models.CASCADE,
        verbose_name='Категория'
    )
    external_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Внешний ID товара',
        db_index=True
    )
    name = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name='Название товара'
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        db_index=True,
        verbose_name='URL товара'
    )
    sku = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Артикул'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание товара'
    )
    # Основная цена (минимальная из вариантов или базовая)
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Базовая цена'
    )
    old_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Старая цена'
    )
    available = models.BooleanField(
        default=True,
        verbose_name='Доступен для заказа'
    )
    
    # Общее количество (сумма всех вариантов)
    total_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name='Общее количество на складе'
    )
    main_image = models.ImageField(
        upload_to='products/main/%Y/%m/%d/',
        verbose_name='Главное изображение'
    )
    external_url = models.URLField(
        blank=True,
        verbose_name='Внешняя ссылка на товар'
    )
    search_synonyms = models.TextField(
        verbose_name='Поисковые синонимы',
        blank=True,
        help_text='Синонимы для поиска через запятую'
    )
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['id', 'slug']),
            models.Index(fields=['name']),
            models.Index(fields=['external_id']),
            models.Index(fields=['-created']),
        ]
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_detail', args=[self.slug])

    def save(self, *args, **kwargs):
        # Автоматическое обновление total_quantity при сохранении
        if self.pk and hasattr(self, 'variants'):
            self.total_quantity = sum(variant.quantity for variant in self.variants.all())
        super().save(*args, **kwargs)

    @property
    def in_stock(self):
        """Проверка наличия товара (хотя бы один вариант в наличии)"""
        if hasattr(self, 'variants') and self.variants.exists():
            return any(variant.quantity > 0 for variant in self.variants.all())
        return self.total_quantity > 0

    @property
    def min_price(self):
        """Минимальная цена среди всех вариантов"""
        if hasattr(self, 'variants') and self.variants.exists():
            return min(variant.price for variant in self.variants.all())
        return self.base_price

    @property
    def max_price(self):
        """Максимальная цена среди всех вариантов"""
        if hasattr(self, 'variants') and self.variants.exists():
            return max(variant.price for variant in self.variants.all())
        return self.base_price

    @property
    def price_range(self):
        """Диапазон цен для отображения"""
        if hasattr(self, 'variants') and self.variants.count() > 1:
            return f"{self.min_price} - {self.max_price}"
        return self.min_price

    def get_search_synonyms_list(self):
        """Возвращает список синонимов"""
        if self.search_synonyms:
            return [s.strip().lower() for s in self.search_synonyms.split(',')]
        return []

    @property
    def has_discount(self):
        """Есть ли скидка на товар"""
        return self.old_price and self.old_price > self.base_price

    @property
    def discount_percent(self):
        """Процент скидки"""
        if self.has_discount:
            return ((self.old_price - self.base_price) / self.old_price) * 100
        return 0

class ProductProperty(models.Model):
    """
    Модель для характеристик товара
    """
    product = models.ForeignKey(
        'Product',
        related_name='properties',
        on_delete=models.CASCADE,
        verbose_name='Товар'
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Название характеристики'
    )
    value = models.TextField(
        verbose_name='Значение характеристики'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок отображения'
    )

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Характеристика товара'
        verbose_name_plural = 'Характеристики товаров'
        unique_together = ['product', 'name']

    def __str__(self):
        return f"{self.name}: {self.value}"

class ProductVariant(models.Model):
    """
    Модель для вариантов товара
    """
    product = models.ForeignKey(
        'Product',
        related_name='variants',
        on_delete=models.CASCADE,
        verbose_name='Товар'
    )
    external_id = models.CharField(
        max_length=100,
        verbose_name='Внешний ID варианта',
        db_index=True
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Название варианта'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена варианта'
    )
    quantity = models.PositiveIntegerField(
        default=0,
        verbose_name='Количество варианта'
    )
    sku = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Артикул варианта'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активный вариант'
    )
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        ordering = ['price', 'name']
        verbose_name = 'Вариант товара'
        verbose_name_plural = 'Варианты товаров'
        unique_together = ['product', 'external_id']

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    @property
    def in_stock(self):
        return self.quantity > 0

class ProductImage(models.Model):
    """
    Модель для дополнительных изображений товара
    """
    product = models.ForeignKey(
        Product,
        related_name='images',
        on_delete=models.CASCADE,
        verbose_name='Товар'
    )
    image = models.ImageField(
        upload_to='products/additional/%Y/%m/%d/',
        verbose_name='Изображение'
    )
    external_url = models.URLField(
        blank=True,
        verbose_name='Внешняя ссылка на изображение'
    )
    alt_text = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Альтернативный текст'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок отображения'
    )
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        ordering = ['order', 'created']
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'

    def __str__(self):
        return f"Изображение для {self.product.name}"

class Review(models.Model):
    """
    Модель отзывов о товарах
    Особенности: связь с пользователем и товаром, рейтинг
    """
    RATING_CHOICES = [
        (1, '1 - Ужасно'),
        (2, '2 - Плохо'),
        (3, '3 - Нормально'),
        (4, '4 - Хорошо'),
        (5, '5 - Отлично'),
    ]

    product = models.ForeignKey(
        Product,
        related_name='reviews',
        on_delete=models.CASCADE,
        verbose_name='Товар'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='main_reviews'
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        verbose_name='Рейтинг'
    )
    comment = models.TextField(
        verbose_name='Комментарий'
    )
    is_approved = models.BooleanField(
        default=False,
        verbose_name='Одобрен'
    )
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        ordering = ['-created']
        unique_together = ['product', 'user']  # один отзыв на товар от пользователя
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'

    def __str__(self):
        return f"Отзыв от {self.user} на {self.product}"

    @property
    def get_rating_stars(self):
        """Возвращает рейтинг в виде звезд"""
        return '★' * self.rating + '☆' * (5 - self.rating)

class Cart(models.Model):
    """
    Модель корзины покупок
    Особенности: связь с пользователем, хранение временных данных
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Пользователь',
        related_name='main_carts'
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        verbose_name='Ключ сессии'
    )
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

    def __str__(self):
        if self.user:
            return f"Корзина пользователя {self.user.username}"
        return f"Корзина (сессия: {self.session_key})"

    @property
    def total_price(self):
        """Общая стоимость корзины"""
        return sum(item.total_price for item in self.items.all())

    @property
    def total_quantity(self):
        """Общее количество товаров в корзине"""
        return sum(item.quantity for item in self.items.all())

class CartItem(models.Model):
    """
    Модель элемента корзины (обновленная)
    """
    cart = models.ForeignKey(
        Cart,
        related_name='items',
        on_delete=models.CASCADE,
        verbose_name='Корзина'
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        verbose_name='Вариант товара'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name='Количество'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена на момент добавления'
    )
    added = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления'
    )

    class Meta:
        verbose_name = 'Элемент корзины'
        verbose_name_plural = 'Элементы корзины'
        unique_together = ['cart', 'product_variant']

    def __str__(self):
        return f"{self.product_variant.product.name} - {self.product_variant.name} - {self.quantity} шт."

    @property
    def total_price(self):
        return self.quantity * self.price

class Order(models.Model):
    """Модель заказа"""
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('confirmed', 'Подтвержден'),
        ('processing', 'В обработке'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]

    DELIVERY_CHOICES = [
        ('pickup', 'Самовывоз (бесплатно)'),
        ('courier', 'Курьер по Курску'),
        ('shipping', 'Транспортная компания по России'),
    ]

    PAYMENT_CHOICES = [
        ('cash', 'Наличными при получении'),
        ('card', 'Картой при получении'),
        ('transfer', 'Перевод по реквизитам'),
    ]

    # Контактные данные
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    email = models.EmailField(verbose_name='Email')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    delivery_method = models.CharField(
        max_length=20, choices=DELIVERY_CHOICES, default='pickup',
        verbose_name='Способ получения'
    )
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_CHOICES, default='cash',
        verbose_name='Способ оплаты'
    )
    address = models.TextField(blank=True, verbose_name='Адрес доставки')
    comment = models.TextField(blank=True, verbose_name='Комментарий к заказу')
    
    # Данные заказа
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Общая стоимость')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name='Статус')
    
    # Связи
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Пользователь',related_name='main_orders')
    session_key = models.CharField(max_length=100, blank=True, verbose_name='Ключ сессии')
    
    # Даты
    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created']

    def __str__(self):
        return f"Заказ #{self.id} - {self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class OrderItem(models.Model):
    """Товар в заказе (обновленная)"""
    order = models.ForeignKey(
        Order, 
        related_name='items', 
        on_delete=models.CASCADE, 
        verbose_name='Заказ'
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        verbose_name='Вариант товара'
    )
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name='Цена на момент заказа'
    )

    class Meta:
        verbose_name = 'Элемент заказа'
        verbose_name_plural = 'Элементы заказа'

    def __str__(self):
        return f"{self.product_variant.product.name} - {self.product_variant.name} x {self.quantity}"

    @property
    def total_price(self):
        return self.quantity * self.price