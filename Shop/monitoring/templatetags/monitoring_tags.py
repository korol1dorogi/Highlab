from django import template

from ..models import STATUS_ICONS, STATUS_LABELS
from ..services import human_size as _human_size

register = template.Library()


@register.filter
def human_size(value):
    return _human_size(value)


@register.filter
def status_icon(value):
    return STATUS_ICONS.get(value, '')


@register.filter
def status_label(value):
    return STATUS_LABELS.get(value, value)


@register.filter
def duration(value):
    """timedelta → «1 ч 05 мин» / «3 мин 12 с»."""
    if value is None:
        return ''
    total = int(value.total_seconds())
    h, rest = divmod(total, 3600)
    m, s = divmod(rest, 60)
    if h:
        return f'{h} ч {m:02d} мин'
    if m:
        return f'{m} мин {s:02d} с'
    return f'{s} с'
