from django.db import migrations, models


def adjust(apps, schema_editor):
    SiteSettings = apps.get_model('index', 'SiteSettings')
    CompanyStat = apps.get_model('index', 'CompanyStat')

    SiteSettings.objects.filter(pk=1).update(
        partners_text='Работаем с оборудованием ОВЕН и других производителей промышленной автоматики',
    )
    # «ОВЕН» переезжает в строку доверия — как счётчик он больше не нужен
    CompanyStat.objects.filter(value='ОВЕН').delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0004_seed_landing_revamp'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='partners_text',
            field=models.CharField(
                blank=True,
                default='Работаем с оборудованием ОВЕН и других производителей промышленной автоматики',
                help_text='Тихая строка под героем. Очистите, чтобы скрыть.',
                max_length=255,
                verbose_name='Строка доверия / партнёры',
            ),
        ),
        migrations.RunPython(adjust, noop),
    ]
