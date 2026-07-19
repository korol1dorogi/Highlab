"""Простые SEO-эндпоинты: robots.txt и файлы верификации веб-мастеров."""
from django.http import HttpResponse, Http404


# Файлы подтверждения прав в веб-мастерах (Яндекс, Google и т.п.):
# имя файла в корне сайта -> его содержимое.
SITE_VERIFICATIONS = {
    'yandex_8812ea615580c1d0.html': (
        '<html>\n'
        '    <head>\n'
        '        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">\n'
        '    </head>\n'
        '    <body>Verification: 8812ea615580c1d0</body>\n'
        '</html>\n'
    ),
}


def site_verification(request, filename):
    """Отдаёт файл подтверждения прав (Яндекс.Вебмастер и др.) из корня сайта."""
    content = SITE_VERIFICATIONS.get(filename)
    if content is None:
        raise Http404()
    return HttpResponse(content, content_type='text/html; charset=utf-8')


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
