"""Шаблонные теги магазина: генерация лёгких WebP-превью на лету (Pillow).
Превью кэшируется в media/cache/thumbs/ и переиспользуется."""
import os
import hashlib

from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def thumb(image_field, size=400):
    """Возвращает URL WebP-превью изображения, вписанного в квадрат size×size.
    При ошибке/отсутствии файла возвращает оригинал."""
    if not image_field:
        return ''
    try:
        src_path = image_field.path
        rel_name = image_field.name
    except Exception:
        try:
            return image_field.url
        except Exception:
            return ''

    if not src_path or not os.path.exists(src_path):
        try:
            return image_field.url
        except Exception:
            return ''

    try:
        size = int(size)
    except (TypeError, ValueError):
        size = 400

    key = hashlib.md5(f'{rel_name}|{size}'.encode('utf-8')).hexdigest()
    cache_rel = f'cache/thumbs/{key}.webp'
    cache_abs = os.path.join(settings.MEDIA_ROOT, cache_rel)

    if not os.path.exists(cache_abs):
        try:
            from PIL import Image
            os.makedirs(os.path.dirname(cache_abs), exist_ok=True)
            img = Image.open(src_path)
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            img.thumbnail((size, size), Image.LANCZOS)
            img.save(cache_abs, 'WEBP', quality=82, method=4)
        except Exception:
            return image_field.url

    return settings.MEDIA_URL.rstrip('/') + '/' + cache_rel
