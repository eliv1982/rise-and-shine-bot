#!/usr/bin/env bash
# Post-deploy smoke check. Run this on the server right after `docker compose up -d`
# (Stage 7, not now). Read-only: no paid generation is triggered, no Telegram/OpenAI
# calls are made - this only inspects `docker compose ps`/`docker compose logs`
# against markers the app already logs at startup.
#
# Usage: scripts/smoke_check.sh [service] [log-lines]
#   service    docker compose service name (default: bot)
#   log-lines  how many recent log lines to scan (default: 200)

set -euo pipefail
cd "$(dirname "$0")/.."

SERVICE="${1:-bot}"
LOG_LINES="${2:-200}"
FAILURES=0

check() {
    local description="$1"
    local ok="$2"
    if [ "$ok" = "0" ]; then
        echo "[smoke] OK   - $description"
    else
        echo "[smoke] FAIL - $description"
        FAILURES=$((FAILURES + 1))
    fi
}

echo "[smoke] Checking container state ($SERVICE)..."
STATE_LINE="$(docker compose ps "$SERVICE" 2>&1 || true)"
echo "$STATE_LINE"
echo "$STATE_LINE" | grep -qi "Up" && check "container is running" 0 || check "container is running" 1

LOGS="$(docker compose logs --no-color --tail "$LOG_LINES" "$SERVICE" 2>&1 || true)"

echo "$LOGS" | grep -q "Database initialized" && check "DB initialized" 0 || check "DB initialized" 1
echo "$LOGS" | grep -q "Scheduler started with jobs:.*daily_affirmations" && check "daily delivery job registered" 0 || check "daily delivery job registered" 1
echo "$LOGS" | grep -q "Scheduler started with jobs:.*outputs_cleanup" && check "output cleanup job registered" 0 || check "output cleanup job registered" 1
echo "$LOGS" | grep -q "Start polling" && check "polling started" 0 || check "polling started" 1
echo "$LOGS" | grep -qE "Traceback \(most recent call last\)" && check "no startup exception (found a traceback)" 1 || check "no startup exception" 0

echo ""
if [ "$FAILURES" -eq 0 ]; then
    echo "[smoke] All checks passed."
    exit 0
else
    echo "[smoke] $FAILURES check(s) failed. Inspect: docker compose logs -f $SERVICE"
    exit 1
fi
