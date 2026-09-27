#!/usr/bin/env bash
# Deploy preflight: checked by scripts/deploy.sh before it touches the running
# container. Fails loudly (non-zero exit) and does not print secret values.
# No external network calls (no Telegram/OpenAI/Postgres reachability checks).

set -euo pipefail
cd "$(dirname "$0")/.."

fail() {
    echo "[preflight] FAIL: $1" >&2
    exit 1
}

echo "[preflight] Checking working tree is clean..."
if [ -n "$(git status --porcelain)" ]; then
    fail "working tree has uncommitted changes; a deploy checkout must be clean before 'git pull --ff-only' (commit, stash, or discard first)."
fi

echo "[preflight] Checking .env..."
[ -f .env ] || fail ".env not found. Copy .env.example to .env and fill in real values first."

echo "[preflight] Checking Docker..."
command -v docker >/dev/null 2>&1 || fail "docker is not installed or not on PATH."
docker info >/dev/null 2>&1 || fail "docker daemon is not reachable (is it running?)."
docker compose version >/dev/null 2>&1 || fail "'docker compose' (v2) is not available."

echo "[preflight] Validating docker-compose.yml..."
docker compose config --quiet || fail "docker compose config failed to parse docker-compose.yml/.env."

echo "[preflight] Checking runtime configuration..."
PYTHON_BIN=""
for candidate in python3 python; do
    # command -v alone is not enough: e.g. on Windows, "python3" can resolve to a
    # Microsoft Store alias stub that "exists" but errors out instead of running.
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" --version >/dev/null 2>&1; then
        PYTHON_BIN="$candidate"
        break
    fi
done
[ -n "$PYTHON_BIN" ] || fail "no working python3/python found on PATH to run scripts/preflight_check.py."
"$PYTHON_BIN" scripts/preflight_check.py || fail "runtime configuration check failed (see report above)."

echo "[preflight] OK."
