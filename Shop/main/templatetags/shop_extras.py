"""Шаблонные теги магазина: генерация лёгких WebP-превью на лету (Pillow).
Превью кэшируется в media/cache/thumbs/ и переиспользуется."""
import os
import re
import hashlib

from django import template
from django.conf import settings
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

# «Ключ: значение» — короткий ключ без точки, разумной длины значение.
_KV_RE = re.compile(r'^([^:.]{2,40}):\s+(.{1,160})$')


def _is_heading(line):
    """Похожа ли строка на подзаголовок: короткая, без завершающей пунктуации."""
    if len(line) > 80 or line.endswith(('.', '!', '?', ';', ',', ':')):
        return False
    if re.match(r'^\d+\.\s+\S', line):   # нумерованные разделы: «1. Аппаратная платформа»
        return True
    return bool(re.match(r'^[А-ЯЁA-Z]', line))


@register.filter
def format_description(text):
    """Структурирует плоское описание товара от поставщика.

    Строки «Ключ: значение» группируются в блок характеристик, короткие строки
    без точки становятся подзаголовками, остальное — абзацы. Всё экранируется.
    """
    if not text:
        return ''
    out = []
    specs = []

    def flush_specs():
        if specs:
            rows = ''.join(
                f'<div class="dspec__row"><span class="dspec__k">{k}</span>'
                f'<span class="dspec__v">{v}</span></div>'
                for k, v in specs
            )
            out.append(f'<div class="dspec">{rows}</div>')
            specs.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _KV_RE.match(line)
        if m:
            specs.append((escape(m.group(1).strip()), escape(m.group(2).strip())))
            continue
        flush_specs()
        if _is_heading(line):
            out.append(f'<h6 class="desc-sub">{escape(line)}</h6>')
        else:
            out.append(f'<p>{escape(line)}</p>')
    flush_specs()
    return mark_safe('\n'.join(out))


@register.filter
def ru_plural(value, forms):
    """Русское склонение существительного при числе.
    Использование: {{ n|ru_plural:"вариант,варианта,вариантов" }}"""
    try:
        one, few, many = [f.strip() for f in forms.split(',')]
        n = abs(int(value)) % 100
    except (TypeError, ValueError):
        return ''
    if 11 <= n <= 14:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


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
