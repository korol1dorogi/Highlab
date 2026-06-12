import os

from celery import Celery

# Указываем модуль настроек Django для Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Shop.settings')

app = Celery('Shop')

# Берём конфигурацию из настроек Django с префиксом CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим tasks.py в установленных приложениях
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
