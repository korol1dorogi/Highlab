"""Простые SEO-эндпоинты: robots.txt."""
from django.http import HttpResponse


def robots_txt(request):
    host = request.get_host()
    scheme = request.scheme
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /ckeditor5/",
        "Disallow: /shop_electronic/cart/",
        "Disallow: /shop_electronic/checkout/",
        "Disallow: /shop_electronic/order/",
        "Disallow: /shop_electronic/search/",
        "Clean-param: page&sort&price_mode&min_price&max_price /shop_electronic/",
        "",
        f"Sitemap: {scheme}://{host}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")
