from datetime import date

from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field


DIRECTION_CHOICES = [
    ('automation', 'АСУ ТП'),
    ('development', 'Разработка ПО'),
    ('repair', 'Ремонт и восстановление'),
    ('other', 'Другое'),
]

ICON_CHOICES = [
    ('repair', 'Ремонт / инструмент'),
    ('shop', 'Магазин / корзина'),
    ('automation', 'Автоматизация / чип'),
    ('development', 'Разработка / код'),
    ('building', 'Стройматериалы / коробка'),
    ('default', 'По умолчанию'),
]


class Service(models.Model):
    """Услуга мастерской (карточка на хабе /service/ + отдельная страница)."""
    title = models.CharField(max_length=160, verbose_name='Название услуги')
    slug = models.SlugField(max_length=180, unique=True, blank=True, verbose_name='URL (slug)')
    icon_key = models.CharField(max_length=20, choices=ICON_CHOICES, default='default', verbose_name='Иконка')
    description = models.TextField(verbose_name='Краткое описание', help_text='Для карточки на хабе')
    body = CKEditor5Field(blank=True, verbose_name='Подробное описание', config_name='default',
                          help_text='Полный текст на странице услуги. Если пусто — показывается краткое описание.')
    cover = models.ImageField(upload_to='content/services/', blank=True, verbose_name='Обложка')
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES, default='other', verbose_name='Направление')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, verbose_name='Показывать')

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('content:service_detail', args=[self.slug])


class Project(models.Model):
    """Кейс / реализованный проект."""
    title = models.CharField(max_length=220, verbose_name='Название')
    slug = models.SlugField(max_length=220, unique=True, verbose_name='URL (slug)')
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES, default='automation', verbose_name='Направление')
    summary = models.CharField(max_length=300, verbose_name='Краткое описание', help_text='Для карточки в списке')
    client = models.CharField(max_length=160, blank=True, verbose_name='Заказчик')
    sphere = models.CharField(max_length=160, blank=True, verbose_name='Отрасль / сфера')
    task = models.TextField(verbose_name='Задача')
    solution = CKEditor5Field(verbose_name='Решение', config_name='default')
    equipment = models.TextField(blank=True, verbose_name='Оборудование / стек')
    result = CKEditor5Field(blank=True, verbose_name='Результат', config_name='default')
    cover = models.ImageField(upload_to='content/projects/', blank=True, verbose_name='Обложка')
    published_at = models.DateField(default=date.today, verbose_name='Дата публикации')
    is_published = models.BooleanField(default=True, verbose_name='Опубликован')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок (закрепление)')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Создан')

    class Meta:
        ordering = ['order', '-published_at', '-id']
        verbose_name = 'Кейс'
        verbose_name_plural = 'Кейсы'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('content:project_detail', args=[self.slug])


class Article(models.Model):
    """Статья / материал базы знаний."""
    title = models.CharField(max_length=220, verbose_name='Заголовок')
    slug = models.SlugField(max_length=220, unique=True, verbose_name='URL (slug)')
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES, default='other', verbose_name='Направление')
    excerpt = models.CharField(max_length=300, verbose_name='Анонс', help_text='Короткий текст для карточки')
    cover = models.ImageField(upload_to='content/articles/', blank=True, verbose_name='Обложка')
    body = CKEditor5Field(verbose_name='Текст статьи', config_name='default')
    published_at = models.DateField(default=date.today, verbose_name='Дата публикации')
    is_published = models.BooleanField(default=True, verbose_name='Опубликована')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Создана')

    class Meta:
        ordering = ['-published_at', '-id']
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('content:article_detail', args=[self.slug])


class FAQItem(models.Model):
    """Вопрос-ответ для блока FAQ (с микроразметкой FAQPage)."""
    question = models.CharField(max_length=255, verbose_name='Вопрос')
    answer = models.TextField(verbose_name='Ответ')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, verbose_name='Показывать')

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Вопрос-ответ (FAQ)'
        verbose_name_plural = 'Вопросы-ответы (FAQ)'

    def __str__(self):
        return self.question


class MediaItem(models.Model):
    """Упоминание: конкурс, награда, интервью, публикация в СМИ."""
    KIND_CHOICES = [
        ('contest', 'Конкурс'),
        ('award', 'Награда'),
        ('interview', 'Интервью'),
        ('press', 'Публикация в СМИ'),
    ]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='press', verbose_name='Тип')
    title = models.CharField(max_length=220, verbose_name='Заголовок')
    date = models.DateField(default=date.today, verbose_name='Дата')
    description = models.TextField(blank=True, verbose_name='Описание')
    external_url = models.URLField(blank=True, verbose_name='Внешняя ссылка')
    image = models.ImageField(upload_to='content/media/', blank=True, verbose_name='Изображение / лого')
    is_published = models.BooleanField(default=True, verbose_name='Показывать')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        ordering = ['order', '-date', '-id']
        verbose_name = 'Медиа / упоминание'
        verbose_name_plural = 'Медиа и упоминания'

    def __str__(self):
        return f'{self.get_kind_display()}: {self.title}'
