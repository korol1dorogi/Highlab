from django.urls import path, register_converter

from . import views

app_name = 'index'


class UnicodeSlugConverter:
    """Слаг, допускающий кириллицу (в Python 3 \\w в re — Unicode-aware)."""
    regex = r'[-\w]+'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(UnicodeSlugConverter, 'uslug')


urlpatterns = [
    path('', views.index, name='index'),
    path('lead/', views.lead_create, name='lead_create'),
    path('quick-lead/', views.quick_lead, name='quick_lead'),
    path('lp/<uslug:slug>/', views.landing, name='landing'),
    path('privacy/', views.privacy, name='privacy'),
]
