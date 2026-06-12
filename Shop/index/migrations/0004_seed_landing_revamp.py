from django.db import migrations


def seed(apps, schema_editor):
    SiteSettings = apps.get_model('index', 'SiteSettings')
    ServiceCard = apps.get_model('index', 'ServiceCard')
    CompanyStat = apps.get_model('index', 'CompanyStat')

    # 1. Чиним устаревшие тексты (упоминания стройматериалов после удаления main2)
    SiteSettings.objects.filter(pk=1).update(
        hero_title='Инженерные решения для бизнеса и дома в Курске',
        hero_subtitle='Автоматизация АСУ ТП, разработка ПО, ремонт и восстановление техники, '
                      'магазин электроники. Полный цикл — от идеи до поддержки.',
        about_text='Мы — команда инженеров и мастеров: автоматизируем производства, '
                   'разрабатываем ПО, ремонтируем и восстанавливаем технику. Наша цель — '
                   'комплексные решения для вашего дома, офиса и производства.',
        lead_title='Обсудим ваш проект?',
        lead_subtitle='Оставьте заявку — перезвоним и бесплатно проконсультируем.',
    )

    # 2. Иконки и акценты карточек направлений
    icon_map = {
        'Услуги мастерской': ('repair', '#2b7de9'),
        'Магазин электроники': ('shop', '#e74c3c'),
        'Стройматериалы': ('building', '#95a5a6'),
    }
    for card in ServiceCard.objects.all():
        if card.title in icon_map:
            card.icon_key, card.accent_color = icon_map[card.title]
            card.save(update_fields=['icon_key', 'accent_color'])

    # 3. Цифры-доказательства («…» — заполнить реальными данными в админке)
    if not CompanyStat.objects.exists():
        CompanyStat.objects.bulk_create([
            CompanyStat(value='…', label='лет на рынке', order=1),
            CompanyStat(value='…', label='реализованных проектов', order=2),
            CompanyStat(value='ОВЕН', label='ключевой партнёр по АСУ ТП', order=3),
        ])


def unseed(apps, schema_editor):
    apps.get_model('index', 'CompanyStat').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0003_landing_revamp'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
