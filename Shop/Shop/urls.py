# config/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.contrib.sitemaps.views import sitemap

from .sitemaps import sitemaps as all_sitemaps
from .seo_views import robots_txt

urlpatterns = [
    path('admin/', admin.site.urls),

    # SEO
    path('sitemap.xml', sitemap, {'sitemaps': all_sitemaps}, name='sitemap'),
    path('robots.txt', robots_txt, name='robots'),

    # Rich-text редактор (загрузка изображений в статьи/кейсы)
    path('ckeditor5/', include('django_ckeditor_5.urls')),

    # Магазин электроники
    path('shop_electronic/', include('main.urls', namespace='main')),

    # Услуги и экспертиза (кейсы, статьи, медиа)
    path('service/', include('content.urls', namespace='content')),

    # Личный кабинет (регистрация, вход, профиль)
    path('accounts/', include('accounts.urls', namespace='accounts')),

    # Главная страница
    path('', include('index.urls', namespace='index')),
]

# Раздача медиафайлов. Для небольшого проекта отдаём через Django даже в проде;
# на реальном продакшене лучше вынести на nginx / объектное хранилище.
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
