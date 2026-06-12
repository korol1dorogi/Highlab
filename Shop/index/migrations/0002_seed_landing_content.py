from django.db import migrations


def seed(apps, schema_editor):
    SiteSettings = apps.get_model('index', 'SiteSettings')
    ServiceCard = apps.get_model('index', 'ServiceCard')
    TeamContact = apps.get_model('index', 'TeamContact')
    Advantage = apps.get_model('index', 'Advantage')

    # Настройки сайта (синглтон) — значения берутся из default'ов полей
    SiteSettings.objects.get_or_create(pk=1)

    if not ServiceCard.objects.exists():
        ServiceCard.objects.bulk_create([
            ServiceCard(
                title='Услуги мастерской', icon='🔧',
                description='Ремонт компьютеров и электроники, настройка умных домов и '
                            'котельных, прокладка электрики. Профессионально и с гарантией.',
                url='/service/', accent_color='#3498db', button_text='Все услуги',
                is_enabled=True, order=1,
            ),
            ServiceCard(
                title='Магазин электроники', icon='📱',
                description='Новая и б/у электроника: смартфоны, ноутбуки, планшеты, '
                            'гаджеты, аксессуары. Доставка по всей России. Гарантия качества.',
                url='/shop_electronic/', accent_color='#e74c3c', button_text='В магазин',
                is_enabled=True, order=2,
            ),
            ServiceCard(
                title='Стройматериалы', icon='🏗️',
                description='Раздел в разработке 🚧 Скоро здесь появятся лакокрасочные '
                            'материалы и товары для строительства от ведущих производителей.',
                url='', accent_color='#95a5a6', button_text='В разработке... 🚧',
                is_enabled=False, order=3,
            ),
        ])

    if not TeamContact.objects.exists():
        TeamContact.objects.bulk_create([
            TeamContact(
                role_title='Восстановление', person_name='Артур Валерьевич',
                phone='+7 (951) 326-60-10', telegram_url='https://t.me/LaboratoryVT',
                description='Ремонт электроники, ПО, консультации по общим вопросам. '
                            'Восстановление утерянных данных с электронных носителей',
                order=1,
            ),
            TeamContact(
                role_title='Автоматизация', person_name='Кирилл Валерьевич',
                phone='+7 (920) 264-54-16', telegram_url='https://t.me/baykkstu',
                description='Промышленная автоматизация [АСУТП], программирование '
                            'контроллеров, консультирование, помощь в проектировании '
                            'и приобретении оборудования',
                order=2,
            ),
            TeamContact(
                role_title='Разработка ПО', person_name='Дмитрий Артурович',
                phone='+7 (951) 314-66-29', telegram_url='https://t.me/difficileArbitrium',
                description='Разработка программного обеспечения, создание сайтов, полный '
                            'цикл от идеи до реализации и поддержки, 3D-прототипирование '
                            'компонентов.',
                order=3,
            ),
        ])

    if not Advantage.objects.exists():
        Advantage.objects.bulk_create([
            Advantage(text='✅ Опытные специалисты в каждой области', order=1),
            Advantage(text='✅ Гарантия качества на все товары и услуги', order=2),
            Advantage(text='✅ Комплексный подход к решению задач', order=3),
            Advantage(text='✅ Доступные цены и выгодные предложения', order=4),
        ])


def unseed(apps, schema_editor):
    for model_name in ('ServiceCard', 'TeamContact', 'Advantage', 'SiteSettings'):
        apps.get_model('index', model_name).objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
