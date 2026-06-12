#!/bin/sh
set -e

# Ожидаем доступности PostgreSQL, если он сконфигурирован
if [ -n "$POSTGRES_HOST" ]; then
  echo "Ожидание PostgreSQL на $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
  until nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}"; do
    sleep 1
  done
  echo "PostgreSQL доступен."
fi

exec "$@"
