#!/usr/bin/env bash
# Деплой на сервер: подтянуть код, пересобрать образ и перезапустить контейнер.
# Запуск: из корня репозитория на сервере: ./scripts/deploy.sh
# Или по cron для автообновления при push (например каждые 5 мин): */5 * * * * cd /opt/rise-and-shine && ./scripts/deploy.sh >> /var/log/rise-and-shine-deploy.log 2>&1

set -e
cd "$(dirname "$0")/.."

echo "[$(date -Iseconds)] Pulling..."
git pull --ff-only || true

echo "[$(date -Iseconds)] Building and starting..."
docker compose build --no-cache
docker compose up -d

echo "[$(date -Iseconds)] Done."
