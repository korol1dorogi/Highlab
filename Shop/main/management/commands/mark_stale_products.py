# -*- coding: utf-8 -*-
"""Помечает недоступными товары, которых нет в свежем выгрузке парсера.

Нужна для авто-обновления каталога: если товар пропал с laudlink.ru, он не должен
оставаться «в наличии» на сайте.
Запуск:  python manage.py mark_stale_products /path/to/all_products_with_variants.json
"""
import json

from django.core.management.base import BaseCommand, CommandError

from main.models import Product


class Command(BaseCommand):
    help = "Помечает available=False товары, отсутствующие в JSON последнего парсинга."

    def add_arguments(self, parser):
        parser.add_argument('products_json', type=str, help='JSON товаров от парсера')

    def handle(self, *args, **options):
        path = options['products_json']
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            raise CommandError(f"Не удалось прочитать {path}: {e}")

        if isinstance(data, dict):
            data = [data]
        fresh_ids = {str(p.get('id')) for p in data if p.get('id')}
        if not fresh_ids:
            self.stdout.write(self.style.WARNING("В JSON нет товаров — пропускаю, чтобы не обнулить каталог."))
            return

        stale = Product.objects.exclude(external_id__in=fresh_ids).filter(available=True)
        count = stale.count()
        stale.update(available=False)
        # Обнуляем количество вариантов у снятых с продажи товаров.
        from main.models import ProductVariant
        ProductVariant.objects.filter(product__available=False).update(quantity=0)
        self.stdout.write(self.style.SUCCESS(f"Помечено недоступными: {count}"))
