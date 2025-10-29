# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # URL магазина
    path('shop/', include('main.urls', namespace='main')),
    
    # Главная страница (будет создана позже)
    path('', include('index.urls', namespace='index')),
]

# Обслуживание медиа-файлов в разработке
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)