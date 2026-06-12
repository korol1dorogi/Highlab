from django.db import migrations, models


FAQS = [
    ("Сколько стоит диагностика?",
     "Диагностика компьютеров и ноутбуков — бесплатная. Вы платите только за согласованный ремонт, "
     "стоимость озвучиваем до начала работ."),
    ("Вы работаете с организациями?",
     "Да. Работаем с юридическими лицами по договору и безналичному расчёту, предоставляем все необходимые "
     "документы."),
    ("Даёте ли вы гарантию?",
     "Да. На выполненные работы и установленные комплектующие предоставляется гарантия. Срок зависит от типа "
     "работ и озвучивается при оформлении."),
    ("Выезжаете ли вы на объект?",
     "По автоматизации и инженерным системам выезжаем на объект для обследования и монтажа. По ремонту техники "
     "возможен курьер в пределах города Курска."),
    ("Где вы находитесь?",
     "Курск, ул. Суворовская, 103Б. Принимаем технику и выдаём заказы по этому адресу; время визита согласуем "
     "заранее."),
]


def seed_faq(apps, schema_editor):
    FAQItem = apps.get_model('content', 'FAQItem')
    if FAQItem.objects.exists():
        return
    FAQItem.objects.bulk_create([
        FAQItem(question=q, answer=a, order=i, is_active=True)
        for i, (q, a) in enumerate(FAQS, start=1)
    ])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0004_service_bodies'),
    ]

    operations = [
        migrations.CreateModel(
            name='FAQItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=255, verbose_name='Вопрос')),
                ('answer', models.TextField(verbose_name='Ответ')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('is_active', models.BooleanField(default=True, verbose_name='Показывать')),
            ],
            options={
                'verbose_name': 'Вопрос-ответ (FAQ)',
                'verbose_name_plural': 'Вопросы-ответы (FAQ)',
                'ordering': ['order', 'id'],
            },
        ),
        migrations.RunPython(seed_faq, noop),
    ]
