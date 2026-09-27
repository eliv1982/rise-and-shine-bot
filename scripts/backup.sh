#!/usr/bin/env bash
# Back up the bot's database. Backend-aware: PostgreSQL (pg_dump) when
# DATABASE_URL is set to a postgres(ql):// URL, SQLite (safe online backup,
# not a raw file copy) otherwise - the same selection config.py makes at
# runtime. Never prints secret values, never overwrites a prior backup, fails
# loudly, and always names exactly where the backup went.
#
# Usage: scripts/backup.sh [output-dir]   (default: ./backups)
#
# Note (SQLite + Docker): this script reads SQLITE_DB_PATH/BOT_DATA_DIR from
# .env the same way the app does. For a non-Docker SQLite deployment that
# resolves directly to the right file. For a Dockerized SQLite deployment,
# BOT_DATA_DIR only means /app/data *inside* the container, so run this
# script inside the container instead:
#   docker compose exec bot python scripts/backup_sqlite.py \
#       --source /app/data/bot.db --destination /app/data/backups/sqlite_<ts>.db
# Production currently runs PostgreSQL, so this note only applies to a local
# or alternative SQLite deployment.

set -euo pipefail
cd "$(dirname "$0")/.."

BACKUP_DIR="${1:-backups}"
mkdir -p "$BACKUP_DIR"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"

PYTHON_BIN=""
for candidate in python3 python; do
    # command -v alone is not enough: e.g. on Windows, "python3" can resolve to a
    # Microsoft Store alias stub that "exists" but errors out instead of running.
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" --version >/dev/null 2>&1; then
        PYTHON_BIN="$candidate"
        break
    fi
done
[ -n "$PYTHON_BIN" ] || { echo "[backup] FAIL: no working python3/python found on PATH." >&2; exit 1; }

# Load .env the same way config.py does, without ever printing its contents.
DATABASE_URL="$("$PYTHON_BIN" scripts/runtime_value.py database_url)"

if [[ "$DATABASE_URL" == postgres://* || "$DATABASE_URL" == postgresql://* ]]; then
    command -v pg_dump >/dev/null 2>&1 || { echo "[backup] FAIL: pg_dump not found on PATH." >&2; exit 1; }
    DEST="$BACKUP_DIR/postgres_${TIMESTAMP}.dump"
    [ -e "$DEST" ] && { echo "[backup] FAIL: $DEST already exists." >&2; exit 1; }
    echo "[backup] PostgreSQL -> $DEST"
    pg_dump --format=custom --file="$DEST" "$DATABASE_URL"
    echo "[backup] OK: $DEST ($(du -h "$DEST" | cut -f1))"
else
    SQLITE_PATH="$("$PYTHON_BIN" scripts/runtime_value.py sqlite_db_path)"
    [ -f "$SQLITE_PATH" ] || { echo "[backup] FAIL: SQLite database not found: $SQLITE_PATH" >&2; exit 1; }
    DEST="$BACKUP_DIR/sqlite_${TIMESTAMP}.db"
    echo "[backup] SQLite ($SQLITE_PATH) -> $DEST"
    "$PYTHON_BIN" scripts/backup_sqlite.py --source "$SQLITE_PATH" --destination "$DEST"
    echo "[backup] OK: $DEST ($(du -h "$DEST" | cut -f1))"
fi
