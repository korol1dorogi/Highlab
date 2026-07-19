# Деплой на прод (VPS, Ubuntu + Docker, nginx + Let's Encrypt)

Домен: **лаборатория-вт.рф** (punycode `xn----7sbadh8ar0abscwf3p.xn--p1ai`).

## 0. Предпосылки
- Установлены Docker и Docker Compose, открыты порты 80/443.
- **A-запись домена** (и `www`) указывает на IP сервера. Проверить:
  `dig +short A xn----7sbadh8ar0abscwf3p.xn--p1ai`

## 1. Код и .env
```bash
git clone https://github.com/korol1dorogi/Highlab.git
cd Highlab
cp .env.prod.example .env
# сгенерировать SECRET_KEY:
docker compose -f docker-compose.prod.yml run --rm web \
  python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
nano .env   # вписать SECRET_KEY, пароль БД, Telegram; SECURE_SSL_REDIRECT=False
```

## 2. Первый запуск (HTTP) + выпуск сертификата
```bash
# bootstrap-конфиг nginx (HTTP-only), чтобы стартовать без сертификата
cp deploy/nginx/bootstrap.conf deploy/nginx/highlab.conf
docker compose -f docker-compose.prod.yml up -d --build

# когда DNS указывает на сервер — выпустить сертификат
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d xn----7sbadh8ar0abscwf3p.xn--p1ai -d www.xn----7sbadh8ar0abscwf3p.xn--p1ai \
  --email ВАШ_EMAIL --agree-tos --no-eff-email
```

## 3. Включить HTTPS
```bash
git checkout deploy/nginx/highlab.conf          # вернуть боевой HTTPS-конфиг
sed -i 's/^SECURE_SSL_REDIRECT=.*/SECURE_SSL_REDIRECT=True/' .env
docker compose -f docker-compose.prod.yml up -d --force-recreate web nginx
```

## 4. Наполнение и проверка
```bash
docker compose -f docker-compose.prod.yml exec web python manage.py seed_owen_content
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```
- В админке `/admin/` → Настройки сайта → вписать номер Метрики (110848535).
- Оформить тестовый заказ и заявку — проверить Telegram и цели Метрики.

## 5. Бэкапы БД (cron на хосте)
```bash
# ежедневно в 3:30
30 3 * * * cd /root/Highlab && docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U highlab highlab | gzip > /root/backups/highlab-$(date +\%F).sql.gz
```

## Обновление кода
```bash
git pull && docker compose -f docker-compose.prod.yml up -d --build
```
