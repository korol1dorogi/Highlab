from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_product_slug_unique'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='delivery_method',
            field=models.CharField(
                choices=[
                    ('pickup', 'Самовывоз (бесплатно)'),
                    ('courier', 'Курьер по Курску'),
                    ('shipping', 'Транспортная компания по России'),
                ],
                default='pickup',
                max_length=20,
                verbose_name='Способ получения',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.CharField(
                choices=[
                    ('cash', 'Наличными при получении'),
                    ('card', 'Картой при получении'),
                    ('transfer', 'Перевод по реквизитам'),
                ],
                default='cash',
                max_length=20,
                verbose_name='Способ оплаты',
            ),
        ),
        migrations.AlterField(
            model_name='order',
            name='address',
            field=models.TextField(blank=True, verbose_name='Адрес доставки'),
        ),
    ]
