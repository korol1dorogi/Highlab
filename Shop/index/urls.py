from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views
app_name = 'index'

urlpatterns = [
    path('', views.index, name='index'),
    path('service/', views.service, name='service')
    # другие маршруты...
]