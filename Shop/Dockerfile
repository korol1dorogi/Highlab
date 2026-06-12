FROM python:3.12-slim

# Параметры окружения Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Системные зависимости:
#  - сборка пакетов (build-essential, pkg-config)
#  - графический стек для WeasyPrint / pycairo (cairo, pango, gdk-pixbuf)
#  - шрифты с кириллицей для PDF (DejaVu, Liberation)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        libcairo2 \
        libcairo2-dev \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        shared-mime-info \
        fonts-dejavu \
        fonts-liberation \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Сначала зависимости — для кэширования слоёв
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Затем исходники проекта
COPY . /app/

# Точка входа: ожидание БД
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

CMD ["gunicorn", "Shop.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
