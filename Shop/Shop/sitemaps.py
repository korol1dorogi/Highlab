"""Карты сайта (sitemap.xml). Домен берётся из запроса (RequestSite),
поэтому django.contrib.sites не требуется. Протокол — https (за прокси)."""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from main.models import Product, Category
from content.models import Service, Project, Article


class BaseSitemap(Sitemap):
    """Общая база: отдаём ссылки по https (сайт работает за TLS-прокси)."""
    protocol = 'https'


# Приоритеты страниц по важности (для поисковика — подсказка о структуре).
STATIC_PRIORITY = {
    'index:index': 1.0,
    'content:hub': 0.9,
    'shop:product_list': 0.9,
    'content:project_list': 0.7,
    'content:article_list': 0.6,
    'content:media_list': 0.4,
    'shop:category_list': 0.5,
    'shop:credits': 0.3,
}


class StaticViewSitemap(BaseSitemap):
    changefreq = 'weekly'

    def items(self):
        return list(STATIC_PRIORITY.keys())

    def priority(self, item):
        return STATIC_PRIORITY.get(item, 0.5)

    def location(self, item):
        return reverse(item)


class ProductSitemap(BaseSitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return Product.objects.filter(available=True)

    def lastmod(self, obj):
        return obj.updated


class CategorySitemap(BaseSitemap):
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Category.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated


class ServiceSitemap(BaseSitemap):
    changefreq = 'monthly'
    priority = 0.8

    def items(self):
        return Service.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated


class ProjectSitemap(BaseSitemap):
    changefreq = 'monthly'
    priority = 0.7

    def items(self):
        return Project.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated


class ArticleSitemap(BaseSitemap):
    changefreq = 'monthly'
    priority = 0.6

    def items(self):
        return Article.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated


sitemaps = {
    'static': StaticViewSitemap,
    'services': ServiceSitemap,
    'projects': ProjectSitemap,
    'articles': ArticleSitemap,
    'categories': CategorySitemap,
    'products': ProductSitemap,
}
