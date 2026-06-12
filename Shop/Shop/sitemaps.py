"""Карты сайта (sitemap.xml). Домен берётся из запроса (RequestSite),
поэтому django.contrib.sites не требуется."""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from main.models import Product, Category
from content.models import Service, Project, Article


class StaticViewSitemap(Sitemap):
    priority = 0.7
    changefreq = 'weekly'

    def items(self):
        return [
            'index:index',
            'content:hub',
            'content:project_list',
            'content:article_list',
            'content:media_list',
            'shop:product_list',
            'shop:category_list',
            'shop:credits',
        ]

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Product.objects.filter(available=True)

    def lastmod(self, obj):
        return obj.updated


class CategorySitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.5

    def items(self):
        return Category.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated


class ServiceSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.8

    def items(self):
        return Service.objects.filter(is_active=True)


class ProjectSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.7

    def items(self):
        return Project.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.created


class ArticleSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.6

    def items(self):
        return Article.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.created


sitemaps = {
    'static': StaticViewSitemap,
    'services': ServiceSitemap,
    'projects': ProjectSitemap,
    'articles': ArticleSitemap,
    'categories': CategorySitemap,
    'products': ProductSitemap,
}
