from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0007_partner_card'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='metrika_id',
            field=models.CharField(blank=True, help_text='Только число (например 12345678). Пусто — счётчик не подключается.', max_length=20, verbose_name='Номер счётчика Яндекс.Метрики'),
        ),
    ]
