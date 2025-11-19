from django.contrib import admin
from django.utils.html import format_html
from mptt.admin import MPTTModelAdmin
from .models import Category, Product, ProductImage, ProductProperty, ProductVariant, Review, Order, OrderItem

@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):
    """
    Админ-класс для категорий с древовидной структурой
    """
    list_display = ['name', 'slug', 'is_active', 'product_count', 'created']
    list_filter = ['is_active', 'created', 'updated']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created', 'updated']
    mptt_level_indent = 20
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'parent', 'description')
        }),
        ('Изображение', {
            'fields': ('image',),
            'classes': ('collapse',)
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
        ('Даты', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )

    def product_count(self, obj):
        """Количество товаров в категории"""
        return obj.products.count()
    product_count.short_description = 'Количество товаров'

class ProductImageInline(admin.TabularInline):
    """
    Inline для управления изображениями товара
    """
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'order', 'image_preview']
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        """Превью изображения в админке"""
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "Нет изображения"
    image_preview.short_description = 'Превью'

class ProductPropertyInline(admin.TabularInline):
    """
    Inline для управления характеристиками товара
    """
    model = ProductProperty
    extra = 1
    fields = ['name', 'value', 'order']

class ProductVariantInline(admin.TabularInline):
    """
    Inline для управления вариантами товара
    """
    model = ProductVariant
    extra = 1
    fields = ['name', 'price', 'quantity', 'is_active']
    readonly_fields = ['external_id']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Админ-класс для товаров
    """
    list_display = [
        'name', 
        'sku', 
        'category', 
        'base_price', 
        'old_price', 
        'available', 
        'in_stock',
        'has_discount',
        'created',
    ]
    list_filter = [
        'available', 
        'category', 
        'created', 
        'updated'
    ]
    search_fields = ['name', 'sku', 'description', 'external_id']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created', 'updated', 'main_image_preview', 'total_quantity', 'external_id']
    list_editable = ['base_price', 'old_price', 'available']
    actions = ['make_available', 'make_unavailable']
    
    # Inline для изображений, характеристик и вариантов
    inlines = [ProductImageInline, ProductPropertyInline, ProductVariantInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('category', 'name', 'slug', 'sku', 'external_id', 'description')
        }),
        ('Цены и наличие', {
            'fields': ('base_price', 'old_price', 'total_quantity', 'available')
        }),
        ('Главное изображение', {
            'fields': ('main_image', 'main_image_preview'),
        }),
        ('Дополнительная информация', {
            'fields': ('external_url', 'search_synonyms'),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )

    def main_image_preview(self, obj):
        """Превью главного изображения"""
        if obj.main_image:
            return format_html('<img src="{}" width="100" height="100" />', obj.main_image.url)
        return "Нет изображения"
    main_image_preview.short_description = 'Превью главного изображения'

    def in_stock(self, obj):
        """Отображение статуса наличия"""
        return obj.in_stock
    in_stock.boolean = True
    in_stock.short_description = 'В наличии'

    def has_discount(self, obj):
        """Отображение наличия скидки"""
        return obj.has_discount
    has_discount.boolean = True
    has_discount.short_description = 'Скидка'

    # Кастомные действия
    def make_available(self, request, queryset):
        """Сделать выбранные товары доступными"""
        updated = queryset.update(available=True)
        self.message_user(request, f'{updated} товаров теперь доступны')
    make_available.short_description = "Сделать доступными выбранные товары"

    def make_unavailable(self, request, queryset):
        """Сделать выбранные товары недоступными"""
        updated = queryset.update(available=False)
        self.message_user(request, f'{updated} товаров теперь недоступны')
    make_unavailable.short_description = "Сделать недоступными выбранные товары"

@admin.register(ProductProperty)
class ProductPropertyAdmin(admin.ModelAdmin):
    """
    Админ-класс для характеристик товара
    """
    list_display = ['product', 'name', 'value', 'order']
    list_filter = ['product']
    search_fields = ['product__name', 'name', 'value']
    list_editable = ['value', 'order']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('product', 'name', 'value', 'order')
        }),
    )

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """
    Админ-класс для вариантов товара
    """
    list_display = ['product', 'name', 'price', 'quantity', 'is_active', 'external_id']
    list_filter = ['is_active', 'product']
    search_fields = ['product__name', 'name', 'external_id']
    list_editable = ['price', 'quantity', 'is_active']
    readonly_fields = ['external_id', 'created', 'updated']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('product', 'external_id', 'name', 'sku')
        }),
        ('Цена и наличие', {
            'fields': ('price', 'quantity', 'is_active')
        }),
        ('Даты', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """
    Админ-класс для отзывов
    """
    list_display = [
        'product', 
        'user', 
        'rating_stars', 
        'is_approved', 
        'created', 
        'comment_preview'
    ]
    list_filter = [
        'rating', 
        'is_approved', 
        'created'
    ]
    search_fields = [
        'product__name', 
        'user__username', 
        'comment'
    ]
    list_editable = ['is_approved']
    readonly_fields = ['created', 'updated']
    actions = ['approve_reviews', 'disapprove_reviews']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('product', 'user', 'rating')
        }),
        ('Содержание', {
            'fields': ('comment',)
        }),
        ('Модерация', {
            'fields': ('is_approved',)
        }),
        ('Даты', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )

    def rating_stars(self, obj):
        """Отображение рейтинга в виде звезд"""
        return obj.get_rating_stars
    rating_stars.short_description = 'Рейтинг'

    def comment_preview(self, obj):
        """Превью комментария"""
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_preview.short_description = 'Комментарий'

    # Кастомные действия
    def approve_reviews(self, request, queryset):
        """Одобрить выбранные отзывы"""
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} отзывов одобрено')
    approve_reviews.short_description = "Одобрить выбранные отзывы"

    def disapprove_reviews(self, request, queryset):
        """Отклонить выбранные отзывы"""
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} отзывов отклонено')
    disapprove_reviews.short_description = "Отклонить выбранные отзывы"

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """
    Админ-класс для изображений товаров
    """
    list_display = [
        'product', 
        'image_preview', 
        'alt_text', 
        'order', 
        'created'
    ]
    list_filter = [
        'product', 
        'created'
    ]
    search_fields = [
        'product__name', 
        'alt_text'
    ]
    list_editable = ['order']
    readonly_fields = ['created', 'image_preview_large']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('product', 'image', 'alt_text', 'order')
        }),
        ('Превью', {
            'fields': ('image_preview_large',),
        }),
        ('Даты', {
            'fields': ('created',),
            'classes': ('collapse',)
        }),
    )

    def image_preview(self, obj):
        """Маленькое превью в списке"""
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "Нет изображения"
    image_preview.short_description = 'Превью'

    def image_preview_large(self, obj):
        """Большое превью в форме редактирования"""
        if obj.image:
            return format_html('<img src="{}" width="200" height="200" />', obj.image.url)
        return "Нет изображения"
    image_preview_large.short_description = 'Большое превью'

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ['product_variant', 'quantity', 'price']
    extra = 0

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product_variant', 'quantity', 'price']
    list_filter = ['order']
    search_fields = ['order__id', 'product_variant__name']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'email', 'phone', 'total_price', 'status', 'created']
    list_filter = ['status', 'created']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['created', 'updated']
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Контактные данные', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Адрес доставки', {
            'fields': ('address',)
        }),
        ('Информация о заказе', {
            'fields': ('total_price', 'status', 'comment')
        }),
        ('Пользователь', {
            'fields': ('user', 'session_key'),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )