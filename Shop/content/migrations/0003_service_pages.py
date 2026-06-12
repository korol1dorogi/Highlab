from django.db import migrations, models
import django_ckeditor_5.fields
from django.utils.text import slugify


def populate_service_slugs(apps, schema_editor):
    Service = apps.get_model('content', 'Service')
    used = set()
    for service in Service.objects.all():
        base = slugify(service.title, allow_unicode=True) or f'service-{service.pk}'
        slug = base
        i = 2
        while slug in used or Service.objects.filter(slug=slug).exclude(pk=service.pk).exists():
            slug = f'{base}-{i}'
            i += 1
        service.slug = slug
        used.add(slug)
        service.save(update_fields=['slug'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0002_seed_content'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='slug',
            field=models.SlugField(blank=True, db_index=False, default='', max_length=180, verbose_name='URL (slug)'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='service',
            name='body',
            field=django_ckeditor_5.fields.CKEditor5Field(
                blank=True,
                help_text='Полный текст на странице услуги. Если пусто — показывается краткое описание.',
                verbose_name='Подробное описание',
            ),
        ),
        migrations.AddField(
            model_name='service',
            name='cover',
            field=models.ImageField(blank=True, upload_to='content/services/', verbose_name='Обложка'),
        ),
        migrations.AlterField(
            model_name='service',
            name='description',
            field=models.TextField(help_text='Для карточки на хабе', verbose_name='Краткое описание'),
        ),
        migrations.RunPython(populate_service_slugs, noop),
        migrations.AlterField(
            model_name='service',
            name='slug',
            field=models.SlugField(blank=True, max_length=180, unique=True, verbose_name='URL (slug)'),
        ),
    ]
