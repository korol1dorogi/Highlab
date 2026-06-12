import datetime

import django.db.models.deletion
import django_ckeditor_5.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=160, verbose_name='Название услуги')),
                ('icon_key', models.CharField(choices=[('repair', 'Ремонт / инструмент'), ('shop', 'Магазин / корзина'), ('automation', 'Автоматизация / чип'), ('development', 'Разработка / код'), ('building', 'Стройматериалы / коробка'), ('default', 'По умолчанию')], default='default', max_length=20, verbose_name='Иконка')),
                ('description', models.TextField(verbose_name='Описание')),
                ('direction', models.CharField(choices=[('automation', 'АСУ ТП'), ('development', 'Разработка ПО'), ('repair', 'Ремонт и восстановление'), ('other', 'Другое')], default='other', max_length=20, verbose_name='Направление')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('is_active', models.BooleanField(default=True, verbose_name='Показывать')),
            ],
            options={
                'verbose_name': 'Услуга',
                'verbose_name_plural': 'Услуги',
                'ordering': ['order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=220, verbose_name='Название')),
                ('slug', models.SlugField(max_length=220, unique=True, verbose_name='URL (slug)')),
                ('direction', models.CharField(choices=[('automation', 'АСУ ТП'), ('development', 'Разработка ПО'), ('repair', 'Ремонт и восстановление'), ('other', 'Другое')], default='automation', max_length=20, verbose_name='Направление')),
                ('summary', models.CharField(help_text='Для карточки в списке', max_length=300, verbose_name='Краткое описание')),
                ('client', models.CharField(blank=True, max_length=160, verbose_name='Заказчик')),
                ('sphere', models.CharField(blank=True, max_length=160, verbose_name='Отрасль / сфера')),
                ('task', models.TextField(verbose_name='Задача')),
                ('solution', django_ckeditor_5.fields.CKEditor5Field(verbose_name='Решение')),
                ('equipment', models.TextField(blank=True, verbose_name='Оборудование / стек')),
                ('result', django_ckeditor_5.fields.CKEditor5Field(blank=True, verbose_name='Результат')),
                ('cover', models.ImageField(blank=True, upload_to='content/projects/', verbose_name='Обложка')),
                ('published_at', models.DateField(default=datetime.date.today, verbose_name='Дата публикации')),
                ('is_published', models.BooleanField(default=True, verbose_name='Опубликован')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок (закрепление)')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
            ],
            options={
                'verbose_name': 'Кейс',
                'verbose_name_plural': 'Кейсы',
                'ordering': ['order', '-published_at', '-id'],
            },
        ),
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=220, verbose_name='Заголовок')),
                ('slug', models.SlugField(max_length=220, unique=True, verbose_name='URL (slug)')),
                ('direction', models.CharField(choices=[('automation', 'АСУ ТП'), ('development', 'Разработка ПО'), ('repair', 'Ремонт и восстановление'), ('other', 'Другое')], default='other', max_length=20, verbose_name='Направление')),
                ('excerpt', models.CharField(help_text='Короткий текст для карточки', max_length=300, verbose_name='Анонс')),
                ('cover', models.ImageField(blank=True, upload_to='content/articles/', verbose_name='Обложка')),
                ('body', django_ckeditor_5.fields.CKEditor5Field(verbose_name='Текст статьи')),
                ('published_at', models.DateField(default=datetime.date.today, verbose_name='Дата публикации')),
                ('is_published', models.BooleanField(default=True, verbose_name='Опубликована')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Создана')),
            ],
            options={
                'verbose_name': 'Статья',
                'verbose_name_plural': 'Статьи',
                'ordering': ['-published_at', '-id'],
            },
        ),
        migrations.CreateModel(
            name='MediaItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('contest', 'Конкурс'), ('award', 'Награда'), ('interview', 'Интервью'), ('press', 'Публикация в СМИ')], default='press', max_length=20, verbose_name='Тип')),
                ('title', models.CharField(max_length=220, verbose_name='Заголовок')),
                ('date', models.DateField(default=datetime.date.today, verbose_name='Дата')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('external_url', models.URLField(blank=True, verbose_name='Внешняя ссылка')),
                ('image', models.ImageField(blank=True, upload_to='content/media/', verbose_name='Изображение / лого')),
                ('is_published', models.BooleanField(default=True, verbose_name='Показывать')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
            ],
            options={
                'verbose_name': 'Медиа / упоминание',
                'verbose_name_plural': 'Медиа и упоминания',
                'ordering': ['order', '-date', '-id'],
            },
        ),
    ]
