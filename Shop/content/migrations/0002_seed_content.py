from django.db import migrations


def seed(apps, schema_editor):
    Service = apps.get_model('content', 'Service')
    Project = apps.get_model('content', 'Project')
    Article = apps.get_model('content', 'Article')
    MediaItem = apps.get_model('content', 'MediaItem')

    if not Service.objects.exists():
        Service.objects.bulk_create([
            Service(title='Ремонт компьютеров и ноутбуков', icon_key='repair', direction='repair', order=1,
                    description='Диагностика и ремонт ПК, ноутбуков и электроники: чистка, замена комплектующих, устранение неисправностей.'),
            Service(title='Восстановление данных', icon_key='repair', direction='repair', order=2,
                    description='Восстановление утерянных данных с жёстких дисков, SSD и других носителей.'),
            Service(title='Промышленная автоматизация АСУ ТП', icon_key='automation', direction='automation', order=3,
                    description='Проектирование и внедрение АСУ ТП, программирование контроллеров, диспетчеризация и пусконаладка.'),
            Service(title='Разработка ПО и сайтов', icon_key='development', direction='development', order=4,
                    description='Создание сайтов и программного обеспечения: полный цикл от идеи до поддержки, 3D-прототипирование.'),
            Service(title='Умный дом и инженерные системы', icon_key='automation', direction='other', order=5,
                    description='Настройка умных домов и котельных, прокладка электрики и слаботочных систем.'),
        ])

    if not Project.objects.exists():
        Project.objects.bulk_create([
            Project(
                title='Автоматизация котельной (пример)', slug='avtomatizaciya-kotelnoy',
                direction='automation',
                summary='Пример кейса по АСУ ТП — замените реальным проектом в админке.',
                client='дополнить потом…', sphere='Теплоснабжение',
                task='дополнить потом… — опишите исходную задачу заказчика.',
                solution='<p>дополнить потом… — опишите внедрённое решение.</p>',
                equipment='ОВЕН ПЛК, датчики температуры и давления, SCADA',
                result='<p>дополнить потом… — итог и измеримый эффект.</p>',
                order=1,
            ),
            Project(
                title='Корпоративный сайт и CRM (пример)', slug='korporativny-sajt-crm',
                direction='development',
                summary='Пример кейса по разработке — замените реальным проектом в админке.',
                task='дополнить потом… — задача проекта.',
                solution='<p>дополнить потом… — что реализовано.</p>',
                result='<p>дополнить потом… — результат для бизнеса.</p>',
                order=2,
            ),
        ])

    if not Article.objects.exists():
        Article.objects.bulk_create([
            Article(
                title='Как выбрать ПЛК для АСУ ТП (пример)', slug='kak-vybrat-plk',
                direction='automation',
                excerpt='Пример статьи — замените своим материалом базы знаний.',
                body='<p>дополнить потом… — текст статьи с разметкой, изображениями и списками.</p>',
            ),
            Article(
                title='Восстановление данных: что важно знать (пример)', slug='vosstanovlenie-dannyh',
                direction='repair',
                excerpt='Пример статьи — замените своим материалом.',
                body='<p>дополнить потом…</p>',
            ),
        ])

    if not MediaItem.objects.exists():
        MediaItem.objects.bulk_create([
            MediaItem(kind='contest', title='Участие в конкурсе (пример)', order=1,
                      description='дополнить потом… — название конкурса, результат, ссылка.'),
            MediaItem(kind='interview', title='Интервью (пример)', order=2,
                      description='дополнить потом… — где вышло интервью, краткая суть.'),
        ])


def unseed(apps, schema_editor):
    for model_name in ('Service', 'Project', 'Article', 'MediaItem'):
        apps.get_model('content', model_name).objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
