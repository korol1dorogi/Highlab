# -*- coding: utf-8 -*-
"""Тематическая группировка моделей в админке.

Штатно Django группирует админку по приложениям (index / main / content / …),
из-за чего настройки, оформление, партнёры, посадочные и заявки оказываются
в одной куче внутри приложения `index`. Здесь мы переопределяем
`AdminSite.get_app_list`, чтобы в боковом меню и на дашборде модели были
разложены по смыслу: Контент / Оформление / Настройки / Магазин / Заявки /
Служебное — независимо от того, в каком приложении объявлена модель.

Иконки для групп заданы в settings.JAZZMIN_SETTINGS['icons'] по ключам
"<синтетический app_label>.<модель>" (jazzmin берёт app_label из группы).

Модуль импортируется из Shop/urls.py — патч применяется один раз при старте.
"""
from django.contrib import admin

# (Название группы, синтетический app_label, [ключи 'app_label.model' по порядку])
GROUP_DEFS = [
    ('Контент', 'grp_content', [
        'content.service', 'content.project', 'content.article',
        'content.faqitem', 'content.mediaitem', 'index.landing',
    ]),
    ('Оформление сайта', 'grp_design', [
        'index.servicecard', 'index.advantage', 'index.companystat',
        'index.teamcontact', 'index.partner',
    ]),
    ('Настройки сайта', 'grp_settings', [
        'index.sitesettings',
    ]),
    ('Магазин', 'grp_shop', [
        'main.category', 'main.product', 'main.productvariant',
        'main.productproperty', 'main.productimage', 'main.review',
    ]),
    ('Заявки и заказы', 'grp_orders', [
        'index.lead', 'main.order', 'main.orderitem',
    ]),
]
SYSTEM_GROUP = ('Служебное', 'grp_system')

_original_get_app_list = admin.AdminSite.get_app_list


def grouped_get_app_list(self, request, app_label=None):
    # Для страницы отдельного приложения (/admin/<app>/) — штатное поведение.
    if app_label:
        return _original_get_app_list(self, request, app_label)

    app_dict = self._build_app_dict(request)
    index = {}
    for label, app in app_dict.items():
        for model in app['models']:
            index[f"{label}.{model['object_name'].lower()}"] = model

    result = []
    used = set()
    for name, slug, keys in GROUP_DEFS:
        models = [index[k] for k in keys if k in index]
        used.update(keys)
        if models:
            result.append({
                'name': name,
                'app_label': slug,
                'app_url': '',
                'has_module_perms': True,
                'models': models,
            })

    leftovers = [m for k, m in index.items() if k not in used]
    if leftovers:
        leftovers.sort(key=lambda m: m['name'])
        result.append({
            'name': SYSTEM_GROUP[0],
            'app_label': SYSTEM_GROUP[1],
            'app_url': '',
            'has_module_perms': True,
            'models': leftovers,
        })
    return result


admin.AdminSite.get_app_list = grouped_get_app_list
