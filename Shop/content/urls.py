from django.urls import path, register_converter

from . import views

app_name = 'content'


class UnicodeSlugConverter:
    """Слаг, допускающий кириллицу (в Python 3 \\w в re — Unicode-aware)."""
    regex = r'[-\w]+'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(UnicodeSlugConverter, 'uslug')


urlpatterns = [
    path('', views.hub, name='hub'),
    path('services/<uslug:slug>/', views.service_detail, name='service_detail'),
    path('projects/', views.project_list, name='project_list'),
    path('projects/<uslug:slug>/', views.project_detail, name='project_detail'),
    path('articles/', views.article_list, name='article_list'),
    path('articles/<uslug:slug>/', views.article_detail, name='article_detail'),
    path('media/', views.media_list, name='media_list'),
]
