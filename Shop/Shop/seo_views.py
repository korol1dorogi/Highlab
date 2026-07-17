"""Простые SEO-эндпоинты: robots.txt."""
from django.http import HttpResponse


def robots_txt(request):
    host = request.get_host()
    scheme = request.scheme

    # Общие запреты для всех роботов (без Clean-param — это директива только Яндекса).
    disallow = [
        "Disallow: /admin/",
        "Disallow: /ckeditor5/",
        "Disallow: /accounts/",
        "Disallow: /shop_electronic/cart/",
        "Disallow: /shop_electronic/checkout/",
        "Disallow: /shop_electronic/order/",
        "Disallow: /shop_electronic/search/",
        "Disallow: /*?search=",
    ]

    lines = ["User-agent: *", "Allow: /", *disallow, ""]

    # Отдельная секция Яндекса: те же запреты + схлопывание GET-параметров каталога,
    # чтобы фильтры/сортировка/поиск не плодили дубли страниц.
    lines += [
        "User-agent: Yandex",
        "Allow: /",
        *disallow,
        "Clean-param: page&sort&price_mode&min_price&max_price&search /shop_electronic/",
        "",
    ]

    lines.append(f"Sitemap: {scheme}://{host}/sitemap.xml")
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")
