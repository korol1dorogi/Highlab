# Highlab shop

Сайт «Лаборатория ВТ» (Курск): лендинг, страница услуг мастерской и интернет-магазин
электроники `/shop_electronic/` на Django, с асинхронными уведомлениями о заказах в Telegram через Celery.

Версия 0.1

## Стек

- Django 5.2 + Gunicorn
- PostgreSQL
- Redis (брокер Celery)
- Celery (фоновые задачи — отправка уведомлений в Telegram)
- WhiteNoise (статика)
- Всё упаковано в Docker / docker-compose

## Запуск через Docker

```bash
# 1. Подготовьте окружение (по желанию поправьте значения)
cp .env.example .env

# 2. Соберите и поднимите стек
docker compose up -d --build

# 3. Приложение доступно на http://localhost:8000
```

Сервисы:
- `web` — Django + Gunicorn (порт 8000). При старте автоматически применяет миграции и собирает статику.
- `celery` — воркер Celery.
- `db` — PostgreSQL.
- `redis` — брокер и backend результатов Celery.

### Создать суперпользователя

```bash
docker compose exec web python manage.py createsuperuser
```

### Редактирование контента (без правки кода)

Контент лендинга вынесен в БД и редактируется через админку `/admin/`:
- **Настройки сайта** — заголовок главного экрана, блок «О компании», адрес, email, соцсети, копирайт.
- **Карточки направлений** — три карточки на главной (текст, иконка, ссылка, цвет, флаг «в разработке»).
- **Контакты специалистов** — блоки контактов в подвале (имя, телефон, Telegram, описание).
- **Преимущества** — пункты блока «Почему выбирают нас».

### Логи / остановка

```bash
docker compose logs -f web celery
docker compose down            # остановить
docker compose down -v         # остановить и удалить тома (БД, медиа, статика)
```

## Переменные окружения

См. [.env.example](.env.example). Ключевые:
`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `POSTGRES_*`, `CELERY_BROKER_URL`,
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_ID`.

Если `POSTGRES_DB` не задан, Django использует локальный SQLite (удобно для запуска без Docker).

## Локальный запуск без Docker

```bash
cd Shop
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
# Celery (в отдельном терминале, нужен запущенный Redis):
celery -A Shop worker -l info
```
