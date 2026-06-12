from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0002_seed_landing_content'),
    ]

    operations = [
        # --- SiteSettings: новые поля героя и блока заявки ---
        migrations.AddField(
            model_name='sitesettings',
            name='hero_subtitle',
            field=models.TextField(
                default='Автоматизация АСУ ТП, разработка ПО, ремонт и восстановление техники, '
                        'магазин электроники. Полный цикл — от идеи до поддержки.',
                verbose_name='Подзаголовок главного экрана',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='lead_title',
            field=models.CharField(default='Обсудим ваш проект?', max_length=200, verbose_name='Заголовок блока заявки'),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='lead_subtitle',
            field=models.TextField(
                default='Оставьте заявку — перезвоним и бесплатно проконсультируем.',
                verbose_name='Подзаголовок блока заявки',
            ),
        ),
        migrations.AlterField(
            model_name='sitesettings',
            name='hero_title',
            field=models.CharField(
                default='Инженерные решения для бизнеса и дома в Курске',
                max_length=160, verbose_name='Заголовок главного экрана',
            ),
        ),
        migrations.AlterField(
            model_name='sitesettings',
            name='about_text',
            field=models.TextField(
                default='Мы — команда инженеров и мастеров: автоматизируем производства, '
                        'разрабатываем ПО, ремонтируем и восстанавливаем технику. Наша цель — '
                        'комплексные решения для вашего дома, офиса и производства.',
                verbose_name='Текст блока «О компании»',
            ),
        ),
        # --- ServiceCard: emoji -> ключ иконки ---
        migrations.AddField(
            model_name='servicecard',
            name='icon_key',
            field=models.CharField(
                choices=[
                    ('repair', 'Ремонт / инструмент'),
                    ('shop', 'Магазин / корзина'),
                    ('automation', 'Автоматизация / чип'),
                    ('development', 'Разработка / код'),
                    ('building', 'Стройматериалы / коробка'),
                    ('default', 'По умолчанию'),
                ],
                default='default', max_length=20, verbose_name='Иконка',
            ),
        ),
        migrations.RemoveField(
            model_name='servicecard',
            name='icon',
        ),
        migrations.AlterField(
            model_name='servicecard',
            name='accent_color',
            field=models.CharField(
                default='#2b7de9', max_length=7,
                help_text='Цвет верхней полоски карточки, например #2b7de9',
                verbose_name='Цвет акцента (HEX)',
            ),
        ),
        # --- Новые модели ---
        migrations.CreateModel(
            name='CompanyStat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(help_text='Например: 12, 250+, ОВЕН. Поставьте «…», если данные нужно дополнить позже.', max_length=40, verbose_name='Значение')),
                ('label', models.CharField(max_length=120, verbose_name='Подпись')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('is_active', models.BooleanField(default=True, verbose_name='Показывать на сайте')),
            ],
            options={
                'verbose_name': 'Цифра-доказательство',
                'verbose_name_plural': 'Цифры-доказательства',
                'ordering': ['order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Lead',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, verbose_name='Имя')),
                ('phone', models.CharField(max_length=40, verbose_name='Телефон')),
                ('message', models.TextField(blank=True, verbose_name='Сообщение')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('is_processed', models.BooleanField(default=False, verbose_name='Обработана')),
            ],
            options={
                'verbose_name': 'Заявка',
                'verbose_name_plural': 'Заявки',
                'ordering': ['-created'],
            },
        ),
    ]
