from django.db import migrations, models


def seed_partners(apps, schema_editor):
    Partner = apps.get_model('index', 'Partner')
    if Partner.objects.exists():
        return
    # Переносим единственного известного партнёра; остальные 3 добавите в админке.
    Partner.objects.create(name='ОВЕН', order=1, is_active=True)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0005_partners_trustline'),
    ]

    operations = [
        migrations.CreateModel(
            name='Partner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, verbose_name='Название')),
                ('logo', models.ImageField(blank=True, help_text='Необязательно. Если загружен — показывается вместо текста.', upload_to='partners/', verbose_name='Логотип')),
                ('url', models.URLField(blank=True, verbose_name='Ссылка на сайт партнёра')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('is_active', models.BooleanField(default=True, verbose_name='Показывать на сайте')),
            ],
            options={
                'verbose_name': 'Партнёр',
                'verbose_name_plural': 'Партнёры',
                'ordering': ['order', 'id'],
            },
        ),
        migrations.RunPython(seed_partners, noop),
        migrations.RemoveField(
            model_name='sitesettings',
            name='partners_text',
        ),
    ]
