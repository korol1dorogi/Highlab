from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0008_sitesettings_metrika_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='source',
            field=models.CharField(
                blank=True, max_length=160, verbose_name='Источник',
                help_text='Откуда пришла заявка: обратный звонок, квиз, посадочная страница и т.п.',
            ),
        ),
        migrations.CreateModel(
            name='Landing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=160, verbose_name='Название (внутреннее)')),
                ('slug', models.SlugField(allow_unicode=True, blank=True, help_text='Адрес будет /lp/<slug>/', max_length=180, unique=True, verbose_name='URL (slug)')),
                ('h1', models.CharField(help_text='Главный заголовок, точно под запрос из рекламы', max_length=200, verbose_name='Заголовок H1')),
                ('subtitle', models.CharField(blank=True, max_length=300, verbose_name='Подзаголовок')),
                ('bullets', models.TextField(blank=True, help_text='Каждая строка — отдельный пункт списка «почему мы».', verbose_name='Преимущества (по одному на строку)')),
                ('price_from', models.CharField(blank=True, help_text='Например: «Диагностика — бесплатно» или «от 500 ₽».', max_length=80, verbose_name='Цена от')),
                ('cta_text', models.CharField(default='Оставить заявку', max_length=80, verbose_name='Текст кнопки')),
                ('quiz_type', models.CharField(choices=[('repair', 'Квиз по ремонту (устройство → проблема → срочность)'), ('none', 'Без квиза — короткая форма заявки')], default='repair', max_length=10, verbose_name='Тип формы')),
                ('phone', models.CharField(blank=True, help_text='Если пусто — берётся из контактов сайта.', max_length=40, verbose_name='Телефон на странице')),
                ('trust_note', models.CharField(blank=True, help_text='Например: «Гарантия до 12 мес · Работаем с 2014 года».', max_length=200, verbose_name='Строка доверия')),
                ('seo_title', models.CharField(blank=True, help_text='Если пусто — берётся H1.', max_length=200, verbose_name='SEO title')),
                ('seo_description', models.CharField(blank=True, max_length=300, verbose_name='SEO description')),
                ('is_active', models.BooleanField(default=True, verbose_name='Опубликована')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Создана')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='Обновлена')),
            ],
            options={
                'verbose_name': 'Посадочная страница',
                'verbose_name_plural': 'Посадочные страницы',
                'ordering': ['title'],
            },
        ),
    ]
