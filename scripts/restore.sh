#!/usr/bin/env bash
# Restore the bot's database from a backup created by scripts/backup.sh.
#
# This is an explicit, interactive operator action - it is never run
# automatically (not from deploy.sh, not from the app's startup) and it
# refuses to run without typed confirmation. Stop the bot (or otherwise make
# sure nothing is writing to the target database) before running this.
#
# Usage: scripts/restore.sh <backup-file>
#   *.dump  -> pg_restore --clean into the configured DATABASE_URL
#   *.db    -> replaces the configured SQLite database file
#
# Note (PostgreSQL via Docker Compose): when DATABASE_URL's host is `postgres`
# (the Compose service in docker-compose.yml), pg_restore runs via
# `docker compose exec postgres` instead of directly against DATABASE_URL, for
# the same reason as backup.sh (that hostname isn't resolvable from this host
# shell). A DATABASE_URL pointing anywhere else still uses a host-installed
# pg_restore directly, as before.
#
# Note (SQLite + Docker): as with backup.sh, this resolves SQLITE_DB_PATH/
# BOT_DATA_DIR the way the app does on the host it runs on. For a Dockerized
# SQLite deployment, run the equivalent copy inside the container instead so
# the path (and resulting file ownership - the container runs as a non-root
# user, see Dockerfile) is correct.

set -euo pipefail
cd "$(dirname "$0")/.."

usage() {
    echo "Usage: $0 <backup-file>" >&2
    exit 1
}

[ $# -eq 1 ] || usage
BACKUP_FILE="$1"
[ -f "$BACKUP_FILE" ] || { echo "[restore] FAIL: backup file not found: $BACKUP_FILE" >&2; exit 1; }

PYTHON_BIN=""
for candidate in python3 python; do
    # command -v alone is not enough: e.g. on Windows, "python3" can resolve to a
    # Microsoft Store alias stub that "exists" but errors out instead of running.
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" --version >/dev/null 2>&1; then
        PYTHON_BIN="$candidate"
        break
    fi
done
[ -n "$PYTHON_BIN" ] || { echo "[restore] FAIL: no working python3/python found on PATH." >&2; exit 1; }

echo "!!! This will REPLACE the target database with the contents of:"
echo "    $BACKUP_FILE"
echo "!!! Make sure the bot is stopped (or its database writes are quiesced) first."
read -r -p "Type 'restore' to continue: " CONFIRM
[ "$CONFIRM" = "restore" ] || { echo "[restore] Aborted (confirmation not given)." >&2; exit 1; }

case "$BACKUP_FILE" in
    *.dump)
        DATABASE_URL="$("$PYTHON_BIN" scripts/runtime_value.py database_url)"
        if [[ "$DATABASE_URL" != postgres://* && "$DATABASE_URL" != postgresql://* ]]; then
            echo "[restore] FAIL: DATABASE_URL is not set to a PostgreSQL URL; refusing to restore a Postgres dump into it." >&2
            exit 1
        fi
        DB_HOST="$("$PYTHON_BIN" scripts/runtime_value.py database_url_host)"
        if [ "$DB_HOST" = "postgres" ]; then
            command -v docker >/dev/null 2>&1 || { echo "[restore] FAIL: docker not found on PATH." >&2; exit 1; }
            echo "[restore] pg_restore --clean --if-exists (docker compose exec postgres) into the configured database..."
            docker compose exec -T postgres sh -c \
                'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
                < "$BACKUP_FILE"
        else
            command -v pg_restore >/dev/null 2>&1 || { echo "[restore] FAIL: pg_restore not found on PATH." >&2; exit 1; }
            echo "[restore] pg_restore --clean --if-exists into the configured DATABASE_URL..."
            pg_restore --clean --if-exists --no-owner --dbname="$DATABASE_URL" "$BACKUP_FILE"
        fi
        echo "[restore] OK."
        ;;
    *.db)
        SQLITE_PATH="$("$PYTHON_BIN" scripts/runtime_value.py sqlite_db_path)"
        echo "[restore] SQLite target: $SQLITE_PATH"
        if [ -f "$SQLITE_PATH" ]; then
            PRE_RESTORE="${SQLITE_PATH}.pre-restore-$(date -u +%Y%m%dT%H%M%SZ)"
            cp "$SQLITE_PATH" "$PRE_RESTORE"
            echo "[restore] existing database saved to $PRE_RESTORE first"
        fi
        mkdir -p "$(dirname "$SQLITE_PATH")"
        cp "$BACKUP_FILE" "$SQLITE_PATH"
        echo "[restore] OK."
        ;;
    *)
        echo "[restore] FAIL: unrecognized backup file extension (expected .dump or .db): $BACKUP_FILE" >&2
        exit 1
        ;;
esac
