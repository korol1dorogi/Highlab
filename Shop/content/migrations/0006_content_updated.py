from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0005_faq'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='updated',
            field=models.DateTimeField(auto_now=True, verbose_name='Обновлена'),
        ),
        migrations.AddField(
            model_name='project',
            name='updated',
            field=models.DateTimeField(auto_now=True, verbose_name='Обновлён'),
        ),
        migrations.AddField(
            model_name='article',
            name='updated',
            field=models.DateTimeField(auto_now=True, verbose_name='Обновлена'),
        ),
    ]
