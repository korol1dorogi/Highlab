from django.db import models
from django.utils.text import slugify


class SingletonModel(models.Model):
    """Базовая модель-синглтон: всегда существует ровно одна запись (pk=1)."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Синглтон удалять нельзя
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SiteSettings(SingletonModel):
    """Глобальные настройки сайта и контент главной страницы."""
    company_name = models.CharField(
        max_length=120, default='Лаборатория ВТ',
        verbose_name='Название компании'
    )
    # --- Герой ---
    hero_title = models.CharField(
        max_length=160,
        default='Инженерные решения для бизнеса и дома в Курске',
        verbose_name='Заголовок главного экрана'
    )
    hero_subtitle = models.TextField(
        default='Автоматизация АСУ ТП, разработка ПО, ремонт и восстановление техники, '
                'магазин электроники. Полный цикл — от идеи до поддержки.',
        verbose_name='Подзаголовок главного экрана'
    )
    # --- О компании ---
    about_title = models.CharField(
        max_length=200, default='О Лаборатории ВТ',
        verbose_name='Заголовок блока «О компании»'
    )
    about_text = models.TextField(
        verbose_name='Текст блока «О компании»',
        default='Мы — команда инженеров и мастеров: автоматизируем производства, '
                'разрабатываем ПО, ремонтируем и восстанавливаем технику. Наша цель — '
                'комплексные решения для вашего дома, офиса и производства.'
    )
    advantages_title = models.CharField(
        max_length=200, default='Почему выбирают нас',
        verbose_name='Заголовок блока «Преимущества»'
    )
    # --- Блок заявки ---
    lead_title = models.CharField(
        max_length=200, default='Обсудим ваш проект?',
        verbose_name='Заголовок блока заявки'
    )
    lead_subtitle = models.TextField(
        default='Оставьте заявку — перезвоним и бесплатно проконсультируем.',
        verbose_name='Подзаголовок блока заявки'
    )
    # --- Контакты ---
    address = models.CharField(
        max_length=255, default='Курск, ул. Суворовская, 103 Б',
        verbose_name='Адрес'
    )
    email = models.CharField(
        max_length=120, default='info@лаборатория-вт.рф',
        verbose_name='Email'
    )
    vk_url = models.URLField(
        blank=True, default='https://vk.com/remont_kompyuterov_kursk',
        verbose_name='Ссылка ВКонтакте'
    )
    social_text = models.CharField(
        max_length=200, default='Подписывайтесь на наши новости и акции',
        verbose_name='Текст блока соцсетей'
    )
    copyright_text = models.CharField(
        max_length=200, default='© 2025 Лаборатория ВТ. Все права защищены.',
        verbose_name='Копирайт'
    )
    # --- Аналитика ---
    metrika_id = models.CharField(
        max_length=20, blank=True, verbose_name='Номер счётчика Яндекс.Метрики',
        help_text='Только число (например 12345678). Пусто — счётчик не подключается.'
    )

    class Meta:
        verbose_name = 'Настройки сайта'
        verbose_name_plural = 'Настройки сайта'

    def __str__(self):
        return 'Настройки сайта'


class ServiceCard(models.Model):
    """Карточка направления на главном экране."""
    ICON_CHOICES = [
        ('repair', 'Ремонт / инструмент'),
        ('shop', 'Магазин / корзина'),
        ('automation', 'Автоматизация / чип'),
        ('development', 'Разработка / код'),
        ('building', 'Стройматериалы / коробка'),
        ('default', 'По умолчанию'),
    ]

    title = models.CharField(max_length=120, verbose_name='Заголовок')
    icon_key = models.CharField(
        max_length=20, choices=ICON_CHOICES, default='default',
        verbose_name='Иконка'
    )
    description = models.TextField(verbose_name='Описание')
    url = models.CharField(
        max_length=255, blank=True,
        verbose_name='Ссылка',
        help_text='Например: /service/ или /shop_electronic/. Оставьте пустым, если раздел в разработке.'
    )
    accent_color = models.CharField(
        max_length=7, default='#2b7de9',
        verbose_name='Цвет акцента (HEX)',
        help_text='Цвет верхней полоски карточки, например #2b7de9'
    )
    button_text = models.CharField(
        max_length=60, default='Подробнее', verbose_name='Текст кнопки'
    )
    is_enabled = models.BooleanField(
        default=True, verbose_name='Раздел доступен',
        help_text='Если выключено — карточка показывается как «в разработке».'
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, verbose_name='Показывать на сайте')

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Карточка направления'
        verbose_name_plural = 'Карточки направлений'

    def __str__(self):
        return self.title


class CompanyStat(models.Model):
    """Цифра-доказательство в полосе под героем (лет на рынке, проектов и т.п.)."""
    value = models.CharField(
        max_length=40, verbose_name='Значение',
        help_text='Например: 12, 250+, ОВЕН. Поставьте «…», если данные нужно дополнить позже.'
    )
    label = models.CharField(max_length=120, verbose_name='Подпись')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, verbose_name='Показывать на сайте')

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Цифра-доказательство'
        verbose_name_plural = 'Цифры-доказательства'

    def __str__(self):
        return f'{self.value} — {self.label}'


class Partner(models.Model):
    """Партнёр / производитель, с которым работаем (тихая строка под героем).
    Все партнёры равноправны; порядок задаётся полем «Порядок»."""
    name = models.CharField(max_length=120, verbose_name='Название')
    logo = models.ImageField(
        upload_to='partners/', blank=True, verbose_name='Логотип',
        help_text='Необязательно. Если загружен — показывается вместо текста.'
    )
    description = models.CharField(
        max_length=200, blank=True, verbose_name='Краткое описание',
        help_text='Короткий текст под логотипом в карточке.'
    )
    url = models.URLField(blank=True, verbose_name='Ссылка на сайт партнёра')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, verbose_name='Показывать на сайте')

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Партнёр'
        verbose_name_plural = 'Партнёры'

    def __str__(self):
        return self.name


class TeamContact(models.Model):
    """Контакт специалиста в подвале сайта."""
    role_title = models.CharField(
        max_length=120, verbose_name='Направление',
        help_text='Например: Восстановление, Автоматизация, Разработка ПО'
    )
    person_name = models.CharField(max_length=120, verbose_name='Имя')
    phone = models.CharField(max_length=40, verbose_name='Телефон')
    telegram_url = models.URLField(blank=True, verbose_name='Ссылка на Telegram')
    description = models.TextField(verbose_name='Описание зоны ответственности')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, verbose_name='Показывать на сайте')

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Контакт специалиста'
        verbose_name_plural = 'Контакты специалистов'

    def __str__(self):
        return f'{self.role_title} — {self.person_name}'


class Advantage(models.Model):
    """Пункт блока «Почему выбирают нас»."""
    text = models.CharField(max_length=255, verbose_name='Текст преимущества')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, verbose_name='Показывать на сайте')

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Преимущество'
        verbose_name_plural = 'Преимущества'

    def __str__(self):
        return self.text


class Lead(models.Model):
    """Заявка с лендинга (форма «Обсудим проект»). Уведомление уходит в Telegram."""
    name = models.CharField(max_length=120, verbose_name='Имя')
    phone = models.CharField(max_length=40, verbose_name='Телефон')
    message = models.TextField(blank=True, verbose_name='Сообщение')
    source = models.CharField(
        max_length=160, blank=True, verbose_name='Источник',
        help_text='Откуда пришла заявка: обратный звонок, квиз, посадочная страница и т.п.'
    )
    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    is_processed = models.BooleanField(default=False, verbose_name='Обработана')

    class Meta:
        ordering = ['-created']
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'

    def __str__(self):
        return f'Заявка от {self.name} ({self.phone})'


class Landing(models.Model):
    """Посадочная страница под контекстную рекламу (Яндекс.Директ).
    Отдельный конверсионный URL /lp/<slug>/ с квизом/формой заявки."""
    QUIZ_CHOICES = [
        ('repair', 'Квиз по ремонту (устройство → проблема → срочность)'),
        ('none', 'Без квиза — короткая форма заявки'),
    ]

    title = models.CharField(max_length=160, verbose_name='Название (внутреннее)')
    slug = models.SlugField(max_length=180, unique=True, blank=True, allow_unicode=True,
                            verbose_name='URL (slug)', help_text='Адрес будет /lp/<slug>/')
    h1 = models.CharField(max_length=200, verbose_name='Заголовок H1',
                          help_text='Главный заголовок, точно под запрос из рекламы')
    subtitle = models.CharField(max_length=300, blank=True, verbose_name='Подзаголовок')
    bullets = models.TextField(
        blank=True, verbose_name='Преимущества (по одному на строку)',
        help_text='Каждая строка — отдельный пункт списка «почему мы».'
    )
    price_from = models.CharField(max_length=80, blank=True, verbose_name='Цена от',
                                  help_text='Например: «Диагностика — бесплатно» или «от 500 ₽».')
    cta_text = models.CharField(max_length=80, default='Оставить заявку', verbose_name='Текст кнопки')
    quiz_type = models.CharField(max_length=10, choices=QUIZ_CHOICES, default='repair',
                                 verbose_name='Тип формы')
    phone = models.CharField(max_length=40, blank=True, verbose_name='Телефон на странице',
                             help_text='Если пусто — берётся из контактов сайта.')
    trust_note = models.CharField(max_length=200, blank=True, verbose_name='Строка доверия',
                                  help_text='Например: «Гарантия до 12 мес · Работаем с 2014 года».')
    seo_title = models.CharField(max_length=200, blank=True, verbose_name='SEO title',
                                 help_text='Если пусто — берётся H1.')
    seo_description = models.CharField(max_length=300, blank=True, verbose_name='SEO description')
    is_active = models.BooleanField(default=True, verbose_name='Опубликована')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Создана')
    updated = models.DateTimeField(auto_now=True, verbose_name='Обновлена')

    class Meta:
        verbose_name = 'Посадочная страница'
        verbose_name_plural = 'Посадочные страницы'
        ordering = ['title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('index:landing', kwargs={'slug': self.slug})

    @property
    def bullet_list(self):
        return [b.strip() for b in self.bullets.splitlines() if b.strip()]
