# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # URL магазина электроники
    path('shop_electronic/', include('main.urls', namespace='main')),
    
    # URL магазина строй товаров
    path('shop_building/', include('main2.urls', namespace='main2')),
    # Главная страница (будет создана позже)
    path('', include('index.urls', namespace='index')),
]

# Обслуживание медиа-файлов в разработке
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)