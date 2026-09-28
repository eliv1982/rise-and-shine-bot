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

The live bot runs in Docker Compose (this repo's `docker-compose.yml`), one project
(`rise-and-shine-bot`, named after this directory) with two services: `bot` and
`postgres`. **PostgreSQL in production is the `postgres` service in this same
Compose project** — not a separate, self-managed service outside it. Data persists
in the named volume `postgres_data` (the actual Docker volume name under this
project is `rise-and-shine-bot_postgres_data`); the bot's own data (SQLite fallback
file, logs, outputs) persists separately in `bot_data`
(`rise-and-shine-bot_bot_data`). The bot reaches Postgres over the Compose network
at hostname `postgres`, and only talks to it through `DATABASE_URL`.

Concretely, this means:

- Production does **not** use `bot.db` (SQLite). SQLite is the fallback for direct
  local Python development (running `bot.py` outside Docker Compose) only.
- Production PostgreSQL **is** started and managed by `docker compose up` in this
  repo, as the `postgres` service — `bot` waits for it to report healthy
  (`depends_on: postgres: condition: service_healthy`) before starting.
- Inside the bot's container, `localhost`/`127.0.0.1` in `DATABASE_URL` resolves to
  the *container itself*, not the `postgres` service — it will not reach Postgres.
  Point `DATABASE_URL` at the Compose DNS hostname `postgres` (the service name in
  `docker-compose.yml`). `scripts/check_runtime_config.py` warns when
  `DATABASE_URL`'s host is `localhost`/`127.0.0.1`/`::1`.
- No Postgres port is published to the host — nothing outside the Compose project
  needs to reach it directly, and there is no demonstrated operational need for one.

```env
# Production PostgreSQL (the `postgres` service in this repo's docker-compose.yml)
POSTGRES_USER=rise_bot
POSTGRES_PASSWORD=...
POSTGRES_DB=rise_bot
DATABASE_URL=postgresql://rise_bot:...@postgres:5432/rise_bot

# SQLite fallback for direct local Python development (only used when
# DATABASE_URL is absent, e.g. running bot.py outside Docker Compose)
SQLITE_DB_PATH=bot.db
```

- If `DATABASE_URL` is absent, the bot uses SQLite. Docker Compose always starts
  `postgres` regardless (it is not optional/profile-gated) — direct local Python
  development without Compose is the only path that stays SQLite-only.
- If `DATABASE_URL` starts with `postgres://` or `postgresql://`, the bot uses
  PostgreSQL; anything else is a blocking configuration error (see
  `scripts/preflight_check.py`), because a malformed value would otherwise silently
  fall back to SQLite in production.
- `docker-compose.yml` requires `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB`
  (`${VAR:?...}` interpolation) — `docker compose config`/`up` fails fast with a
  clear message instead of starting Postgres with blank credentials if any is
  missing. `scripts/preflight.sh` already runs `docker compose config --quiet`
  before every deploy, so this is caught pre-deploy.

## Backup and restore

- `scripts/backup.sh [dir]` — backend-aware: `pg_dump` when `DATABASE_URL` is
  PostgreSQL, a safe SQLite online backup otherwise. This is the production path today
  (production runs PostgreSQL).
- `scripts/restore.sh <backup-file>` — restores a backup made by `backup.sh`
  (`pg_restore` for `.dump`, file copy for `.db`). Interactive, requires typed
  confirmation, never runs automatically.
- **PostgreSQL via Docker Compose**: when `DATABASE_URL`'s host is `postgres` (the
  Compose service), both scripts run `pg_dump`/`pg_restore` through
  `docker compose exec postgres` rather than directly against `DATABASE_URL` from the
  host shell — that hostname is Compose-internal DNS and does not resolve outside the
  Compose network, so this is required, not just convenient. It also keeps the
  `pg_dump`/`pg_restore` version matched to the `postgres:16` server without a host
  install. A `DATABASE_URL` pointing anywhere else (e.g. a host-reachable Postgres used
  for local/alternative testing) still uses host-installed `pg_dump`/`pg_restore`
  directly.
- `scripts/backup_sqlite.py` — the SQLite-specific backup helper `backup.sh` and
  `DEPLOY.md`'s Docker note call into; relevant to the local/dev SQLite fallback, not
  to production.
- **Not yet verified**: an actual PostgreSQL backup → restore dry run has not been
  performed against a real production-shaped database. Do this once before relying on
  it for Stage 7B.

## Runtime config checks

- `python scripts/preflight_check.py` — deploy preflight: fails if required config
  (`BOT_TOKEN`, `OPENAI_API_KEY`, etc.) is missing, or `DATABASE_URL` is malformed. No
  network calls. Dependency-free by design (stdlib only, parses `.env` itself, never
  imports `config.py`/`python-dotenv`): the deployment host only needs system Python,
  not a project virtualenv or any application package — those stay inside the Docker
  image, delivered to the container by `docker-compose.yml`'s `env_file: .env`.
- `python scripts/check_runtime_config.py` — read-only config report: provider (always
  `openai`), role flags, database backend/warnings, and any pre-Stage-6 Yandex/Proxi/
  provider-selection env vars still present in `.env` (listed as ignored/safe to
  remove, never treated as active config). No network calls. Also dependency-free.

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
