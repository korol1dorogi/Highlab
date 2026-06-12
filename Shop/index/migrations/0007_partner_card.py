import os

from django.conf import settings
from django.db import migrations, models


SAMPLE_LOGO_REL = 'partners/oven-sample.png'
PLACEHOLDER_DESC = ('Контроллеры, датчики и приборы автоматизации. Проверенное оборудование, '
                    'на котором мы строим решения АСУ ТП.')


def make_sample_logo():
    """Генерирует тестовый логотип в media/partners/. Возвращает rel-путь или ''."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return ''
    try:
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'partners'), exist_ok=True)
        abs_path = os.path.join(settings.MEDIA_ROOT, SAMPLE_LOGO_REL)

        def F(sz):
            try:
                return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', sz)
            except Exception:
                try:
                    return ImageFont.load_default(sz)
                except Exception:
                    return ImageFont.load_default()

        W, H = 320, 96
        img = Image.new('RGBA', (W, H), (255, 255, 255, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([8, 26, 52, 70], radius=8, fill=(226, 35, 26, 255))
        d.text((64, 28), 'ОВЕН', font=F(46), fill=(20, 28, 38, 255))
        img.save(abs_path)
        return SAMPLE_LOGO_REL
    except Exception:
        return ''


def seed_oven_card(apps, schema_editor):
    Partner = apps.get_model('index', 'Partner')
    p = Partner.objects.filter(name='ОВЕН').first()
    if p is None:
        p = Partner(name='ОВЕН', order=1, is_active=True)
    if not p.description:
        p.description = PLACEHOLDER_DESC
    if not p.url:
        p.url = 'https://owen.ru/'
    rel = make_sample_logo()
    if rel and not p.logo:
        p.logo = rel
    p.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0006_partners'),
    ]

    operations = [
        migrations.AddField(
            model_name='partner',
            name='description',
            field=models.CharField(blank=True, help_text='Короткий текст под логотипом в карточке.', max_length=200, verbose_name='Краткое описание'),
        ),
        migrations.RunPython(seed_oven_card, noop),
    ]
