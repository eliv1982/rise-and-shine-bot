#!/usr/bin/env bash
# Деплой на сервер: подтянуть код, пересобрать образ и перезапустить контейнер.
# Запуск: из корня репозитория на сервере: ./scripts/deploy.sh
# Или по cron для автообновления при push (например каждые 5 мин): */5 * * * * cd /opt/rise-and-shine && ./scripts/deploy.sh >> /var/log/rise-and-shine-deploy.log 2>&1
#
# Fails safely: any failed step (preflight, pull, build, or start) aborts the
# deploy with a non-zero exit code instead of leaving a stale container running
# while reporting success.

set -euo pipefail
cd "$(dirname "$0")/.."

echo "[$(date -Iseconds)] Preflight checks..."
bash "$(dirname "$0")/preflight.sh"

echo "[$(date -Iseconds)] Pulling..."
git pull --ff-only

echo "[$(date -Iseconds)] Building and starting..."
docker compose build --no-cache
docker compose up -d

echo "[$(date -Iseconds)] Done."
