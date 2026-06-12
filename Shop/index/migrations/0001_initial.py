from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='SiteSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(default='Лаборатория ВТ', max_length=120, verbose_name='Название компании')),
                ('hero_title', models.TextField(default='Комплексные решения: от ремонта оргтехники, восстановления утерянных данных, промышленной автоматизации и разработки ПО до дистрибьюции стройматериалов в Курске', verbose_name='Заголовок главного экрана')),
                ('about_title', models.CharField(default='О Лаборатории ВТ', max_length=200, verbose_name='Заголовок блока «О компании»')),
                ('about_text', models.TextField(default='Мы - команда профессионалов, объединяющая компетенции в ремонте электроники, продаже качественной техники и поставках строительных материалов. Наша цель - предоставлять комплексные решения для вашего дома, офиса и ремонта.', verbose_name='Текст блока «О компании»')),
                ('advantages_title', models.CharField(default='Почему выбирают нас', max_length=200, verbose_name='Заголовок блока «Преимущества»')),
                ('address', models.CharField(default='Курск, ул. Суворовская, 103 Б', max_length=255, verbose_name='Адрес')),
                ('email', models.CharField(default='info@лаборатория-вт.рф', max_length=120, verbose_name='Email')),
                ('vk_url', models.URLField(blank=True, default='https://vk.com/remont_kompyuterov_kursk', verbose_name='Ссылка ВКонтакте')),
                ('social_text', models.CharField(default='Подписывайтесь на наши новости и акции', max_length=200, verbose_name='Текст блока соцсетей')),
                ('copyright_text', models.CharField(default='© 2025 Лаборатория ВТ. Все права защищены.', max_length=200, verbose_name='Копирайт')),
            ],
            options={
                'verbose_name': 'Настройки сайта',
                'verbose_name_plural': 'Настройки сайта',
            },
        ),
        migrations.CreateModel(
            name='ServiceCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=120, verbose_name='Заголовок')),
                ('icon', models.CharField(blank=True, max_length=8, verbose_name='Иконка (эмодзи)')),
                ('description', models.TextField(verbose_name='Описание')),
                ('url', models.CharField(blank=True, help_text='Например: /service/ или /shop_electronic/. Оставьте пустым, если раздел в разработке.', max_length=255, verbose_name='Ссылка')),
                ('accent_color', models.CharField(default='#3498db', help_text='Цвет верхней полоски карточки, например #3498db', max_length=7, verbose_name='Цвет акцента (HEX)')),
                ('button_text', models.CharField(default='Подробнее', max_length=60, verbose_name='Текст кнопки')),
                ('is_enabled', models.BooleanField(default=True, help_text='Если выключено — карточка показывается как «в разработке».', verbose_name='Раздел доступен')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('is_active', models.BooleanField(default=True, verbose_name='Показывать на сайте')),
            ],
            options={
                'verbose_name': 'Карточка направления',
                'verbose_name_plural': 'Карточки направлений',
                'ordering': ['order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='TeamContact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role_title', models.CharField(help_text='Например: Восстановление, Автоматизация, Разработка ПО', max_length=120, verbose_name='Направление')),
                ('person_name', models.CharField(max_length=120, verbose_name='Имя')),
                ('phone', models.CharField(max_length=40, verbose_name='Телефон')),
                ('telegram_url', models.URLField(blank=True, verbose_name='Ссылка на Telegram')),
                ('description', models.TextField(verbose_name='Описание зоны ответственности')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('is_active', models.BooleanField(default=True, verbose_name='Показывать на сайте')),
            ],
            options={
                'verbose_name': 'Контакт специалиста',
                'verbose_name_plural': 'Контакты специалистов',
                'ordering': ['order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Advantage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=255, verbose_name='Текст преимущества')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('is_active', models.BooleanField(default=True, verbose_name='Показывать на сайте')),
            ],
            options={
                'verbose_name': 'Преимущество',
                'verbose_name_plural': 'Преимущества',
                'ordering': ['order', 'id'],
            },
        ),
    ]
