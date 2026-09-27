# Production Environment Notes

## Provider

OpenAI is the only supported provider for text, image, TTS and STT (Stage 6). There is
no `TEXT_PROVIDER`/`IMAGE_PROVIDER`/`TTS_PROVIDER`/`STT_PROVIDER` selection any more —
these capabilities always use OpenAI, and setting those env vars has no effect. A
second provider may be introduced later strictly as a resilience fallback (e.g. if
OpenAI has an outage), not as per-request stylistic/model routing — no such fallback
exists yet, and none is planned for the current stage.

Required provider env vars:

```env
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_TEXT_MODEL=gpt-4o-mini
OPENAI_IMAGE_MODEL=gpt-image-1
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_STT_MODEL=gpt-4o-mini-transcribe
```

Only official OpenAI endpoints are used (`api.openai.com`). `OPENAI_BASE_URL` should not
be pointed at a third-party proxy; `scripts/check_runtime_config.py` warns if it isn't
the official URL.

## Database: architecture and truthfulness

The live bot runs in Docker (this repo's `docker-compose.yml`). **PostgreSQL in
production is a separate, self-managed service on the same server** — it is not a
service inside `docker-compose.yml`, and this repo does not provision or manage it.
The bot only talks to it through `DATABASE_URL`.

Concretely, this means:

- Production does **not** use `bot.db` (SQLite). SQLite is a local/dev fallback only,
  used automatically when `DATABASE_URL` is unset.
- Production PostgreSQL is **not** started or managed by `docker compose up` in this
  repo — it must already be running on the server before the bot starts.
- Inside the bot's container, `localhost`/`127.0.0.1` in `DATABASE_URL` resolves to the
  *container itself*, not the host — it will not reach a Postgres running directly on
  the host. Point `DATABASE_URL` at a container-reachable host/IP (the Docker bridge
  gateway IP, an `extra_hosts` entry, or a hostname resolvable from inside the
  container). `scripts/check_runtime_config.py` warns when `DATABASE_URL`'s host is
  `localhost`/`127.0.0.1`/`::1`.

```env
# Production PostgreSQL (self-managed on the same server, outside docker-compose.yml)
DATABASE_URL=postgresql://user:password@db-host:5432/dbname

# Local/dev SQLite fallback (only used when DATABASE_URL is unset)
SQLITE_DB_PATH=bot.db
```

- If `DATABASE_URL` is absent, the bot uses SQLite.
- If `DATABASE_URL` starts with `postgres://` or `postgresql://`, the bot uses
  PostgreSQL; anything else is a blocking configuration error (see
  `scripts/preflight_check.py`), because a malformed value would otherwise silently
  fall back to SQLite in production.

## Backup and restore

- `scripts/backup.sh [dir]` — backend-aware: `pg_dump` when `DATABASE_URL` is
  PostgreSQL, a safe SQLite online backup otherwise. This is the production path today
  (production runs PostgreSQL).
- `scripts/restore.sh <backup-file>` — restores a backup made by `backup.sh`
  (`pg_restore` for `.dump`, file copy for `.db`). Interactive, requires typed
  confirmation, never runs automatically.
- `scripts/backup_sqlite.py` — the SQLite-specific backup helper `backup.sh` and
  `DEPLOY.md`'s Docker note call into; relevant to the local/dev SQLite fallback, not
  to production.
- **Not yet verified**: an actual PostgreSQL backup → restore dry run has not been
  performed against a real production-shaped database. Do this once before relying on
  it for Stage 7.

## Runtime config checks

- `python scripts/preflight_check.py` — deploy preflight: fails if required config
  (`BOT_TOKEN`, `OPENAI_API_KEY`, etc.) is missing, or `DATABASE_URL` is malformed. No
  network calls.
- `python scripts/check_runtime_config.py` — read-only config report: provider (always
  `openai`), role flags, database backend/warnings, and any pre-Stage-6 Yandex/Proxi/
  provider-selection env vars still present in `.env` (listed as ignored/safe to
  remove, never treated as active config). No network calls.

Recommended planner flags:

```env
SCENE_PLANNER_SHADOW_ENABLED=true
SCENE_PLANNER_IMAGE_PROMPT_ENABLED=true
TEXT_PLANNER_SHADOW_ENABLED=true
```

Warnings:

- Image generation is paid.
- Avoid running local and server bots at the same time with the same Telegram token.

Deployment reminders:

- After changing `.env`, restart the container.
- After code changes, rebuild the container.
- See [DEPLOY.md](../DEPLOY.md) for the full preflight/backup/deploy/smoke-check
  checklist, including the one-time non-root volume-ownership fix for volumes created
  before Stage 5.

Role metadata inspection:

- Inspect latest role metadata locally or on the server with:
  `python scripts/inspect_generation_roles.py --db bot.db --limit 5`
