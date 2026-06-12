import re

from django.contrib.auth.models import User
from django.db import models


def normalize_phone(raw):
    """Приводит телефон к виду 7XXXXXXXXXX (только цифры)."""
    digits = re.sub(r'\D', '', raw or '')
    if len(digits) == 11 and digits[0] == '8':
        digits = '7' + digits[1:]
    if len(digits) == 10:
        digits = '7' + digits
    return digits


class Profile(models.Model):
    """Профиль покупателя: телефон и отчество в дополнение к встроенному User."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile', verbose_name='Пользователь'
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    middle_name = models.CharField(max_length=150, blank=True, verbose_name='Отчество')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Создан')

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'Профиль {self.user.username}'

    @property
    def display_phone(self):
        p = self.phone or ''
        if len(p) == 11 and p.startswith('7'):
            return f'+7 ({p[1:4]}) {p[4:7]}-{p[7:9]}-{p[9:11]}'
        return p

    @property
    def full_name(self):
        parts = [self.user.last_name, self.user.first_name, self.middle_name]
        return ' '.join(p for p in parts if p).strip()
