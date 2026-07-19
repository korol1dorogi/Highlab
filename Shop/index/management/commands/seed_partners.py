# -*- coding: utf-8 -*-
"""Заводит партнёров/бренды в блок «Партнёры и бренды, с которыми работаем»
и подтягивает их логотипы с официальных источников.

Идемпотентна: повторный запуск обновляет карточки по названию, не плодя дубли.
Логотип скачивается один раз и хранится под стабильным именем (partners/<key>.<ext>),
поэтому ежедневный прогон не засоряет media. Флаг --refresh-logos форсит перекачку.

Запуск:  python manage.py seed_partners
         python manage.py seed_partners --refresh-logos
"""
import urllib.request

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from index.models import Partner


# Для каждого бренда — несколько кандидатов логотипа (пробуем по порядку).
# SVG предпочтительнее: чёткий, с прозрачностью, идеально тянется под карточку.
BRANDS = [
    {
        "key": "oven",
        "name": "ОВЕН",
        "url": "https://owen.ru/",
        "order": 1,
        "description": (
            "Российские контроллеры, датчики и приборы КИПиА. Базовое оборудование "
            "наших решений АСУ ТП: от щитов автоматики до диспетчеризации."
        ),
        "logos": [
            ("https://owen.ru/images/i/logo-35.svg", "svg"),
        ],
    },
    {
        "key": "wirenboard",
        "name": "Wiren Board",
        "url": "https://wirenboard.com/ru/",
        "order": 2,
        "description": (
            "Российские контроллеры для автоматизации зданий и диспетчеризации "
            "(Modbus, MQTT). Собираем на них умные щиты и системы мониторинга."
        ),
        "logos": [
            ("https://raw.githubusercontent.com/wirenboard/brand/main/logos/logo-horizontal.svg", "svg"),
            ("https://raw.githubusercontent.com/wirenboard/brand/main/logos/logo-horizontal.png", "png"),
        ],
    },
    {
        "key": "ekf",
        "name": "EKF",
        "url": "https://ekfgroup.com/ru",
        "order": 3,
        "description": (
            "Электротехника и низковольтное оборудование: автоматика, щиты, УЗО и "
            "модульные приборы. Комплектуем и монтируем электрику объектов."
        ),
        "logos": [
            ("https://ekfgroup.com/images/logo-ekf.svg", "svg"),
            ("https://ekfgroup.com/images/logo-ekf-dark.svg", "svg"),
        ],
    },
    {
        "key": "delta",
        "name": "Delta Electronics",
        "url": "https://www.delta-electronics.com.ru",
        "order": 4,
        "description": (
            "Частотные преобразователи, ПЛК и приводная техника. Применяем в "
            "автоматизации насосов, вентиляции и промышленных установок."
        ),
        "logos": [
            # Public domain (Wikimedia Commons), простые геометрические формы.
            ("https://upload.wikimedia.org/wikipedia/commons/e/e3/DeltaPSU-Logo.svg", "svg"),
        ],
    },
]


def _download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read()


def _looks_like(content, ext):
    """Грубая проверка, что скачали именно картинку, а не HTML-страницу 404/редиректа."""
    if not content:
        return False
    head = content[:1024]
    if ext == "svg":
        low = head.lower()
        return b"<svg" in low or low.lstrip().startswith(b"<?xml")
    if ext == "png":
        return content[:8] == b"\x89PNG\r\n\x1a\n"
    if ext in ("jpg", "jpeg"):
        return content[:2] == b"\xff\xd8"
    return True


class Command(BaseCommand):
    help = "Заводит бренды-партнёры и скачивает их логотипы с официальных источников."

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh-logos", action="store_true",
            help="Перекачать логотипы даже у брендов, у которых логотип уже стоит.",
        )

    def handle(self, *args, **options):
        refresh = options["refresh_logos"]
        for spec in BRANDS:
            partner = Partner.objects.filter(name=spec["name"]).first()
            created = partner is None
            if partner is None:
                partner = Partner(name=spec["name"])

            partner.url = spec["url"]
            partner.description = spec["description"]
            partner.order = spec["order"]
            partner.is_active = True

            logo_status = self._set_logo(partner, spec["key"], spec["logos"], refresh)
            partner.save()

            flag = "создан" if created else "обновлён"
            self.stdout.write(self.style.SUCCESS(
                f"{spec['name']}: {flag}, логотип — {logo_status}"
            ))

        total = Partner.objects.filter(is_active=True).count()
        self.stdout.write(self.style.SUCCESS(f"Активных партнёров в блоке: {total}"))

    def _set_logo(self, partner, key, candidates, refresh):
        """Ставит логотип. Возвращает человекочитаемый статус."""
        current = partner.logo.name if partner.logo else ""
        is_sample = "oven-sample" in current  # плейсхолдер из старой миграции
        has_real_logo = bool(current) and not is_sample
        if has_real_logo and not refresh:
            return "оставлен как есть"

        for url, ext in candidates:
            try:
                content = _download(url)
            except Exception:
                continue
            if not _looks_like(content, ext):
                continue

            target_name = f"{key}.{ext}"           # upload_to='partners/' → partners/<key>.<ext>
            target_path = f"partners/{target_name}"
            # Убираем старый файл, чтобы имя оставалось стабильным (без случайных суффиксов).
            if current and current != target_path:
                partner.logo.delete(save=False)
            if default_storage.exists(target_path):
                default_storage.delete(target_path)
            partner.logo.save(target_name, ContentFile(content), save=False)
            return f"скачан ({url.rsplit('/', 1)[-1]})"

        return "не удалось скачать — показываем текстом"
