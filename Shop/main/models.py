# shop/models.py
from django.db import models
from django.urls import reverse
from mptt.models import MPTTModel, TreeForeignKey

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
        return reverse('shop:product_list_by_category', args=[self.slug])
    
# shop/models.py
class Product(models.Model):
    """
    Модель товаров магазина
    Особенности: связи с категориями, индексы для поиска, slug для ЧПУ
    """
    category = models.ForeignKey(
        Category,
        related_name='products',
        on_delete=models.CASCADE,
        verbose_name='Категория'
    )
    name = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name='Название товара'
    )
    slug = models.SlugField(
        max_length=200,
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
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена'
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
    quantity = models.PositiveIntegerField(
        default=0,
        verbose_name='Количество на складе'
    )
    main_image = models.ImageField(
        upload_to='products/main/%Y/%m/%d/',
        verbose_name='Главное изображение'
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
            models.Index(fields=['-created']),
        ]
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_detail', args=[self.slug])

    @property
    def in_stock(self):
        """Проверка наличия товара"""
        return self.quantity > 0

    @property
    def has_discount(self):
        """Проверка наличия скидки"""
        return self.old_price and self.old_price > self.price
    

# shop/models.py
class ProductImage(models.Model):
    """
    Модель для дополнительных изображений товара
    Особенности: связь с товаром, порядок отображения
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
    
# shop/models.py
from django.contrib.auth.models import User

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
        verbose_name='Пользователь'
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
        verbose_name='Пользователь'
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
    Модель элемента корзины
    Особенности: связь с корзиной и товаром, хранение количества
    """
    cart = models.ForeignKey(
        Cart,
        related_name='items',
        on_delete=models.CASCADE,
        verbose_name='Корзина'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='Товар'
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
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.product.name} - {self.quantity} шт."

    @property
    def total_price(self):
        """Общая стоимость позиции"""
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

    # Контактные данные
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    email = models.EmailField(verbose_name='Email')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    address = models.TextField(verbose_name='Адрес доставки')
    comment = models.TextField(blank=True, verbose_name='Комментарий к заказу')
    
    # Данные заказа
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Общая стоимость')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name='Статус')
    
    # Связи
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Пользователь')
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
    """Товар в заказе"""
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name='Заказ')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена на момент заказа')

    class Meta:
        verbose_name = 'Элемент заказа'
        verbose_name_plural = 'Элементы заказа'

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def total_price(self):
        return self.quantity * self.price