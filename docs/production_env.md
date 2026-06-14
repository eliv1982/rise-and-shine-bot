# Production Environment Notes

Recommended provider profile for production:

```env
TEXT_PROVIDER=openai
IMAGE_PROVIDER=openai
TTS_PROVIDER=openai
STT_PROVIDER=openai
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_TEXT_MODEL=gpt-4o-mini
OPENAI_IMAGE_MODEL=gpt-image-1
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_STT_MODEL=gpt-4o-mini-transcribe
```

Database backend:

```env
# Beta / production PostgreSQL
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Local development override for SQLite (optional)
SQLITE_DB_PATH=bot.db
```

- If `DATABASE_URL` is absent, the bot keeps using SQLite by default.
- If `DATABASE_URL` starts with `postgres://` or `postgresql://`, the bot uses PostgreSQL.

Recommended planner flags:

```env
SCENE_PLANNER_SHADOW_ENABLED=true
SCENE_PLANNER_IMAGE_PROMPT_ENABLED=true
TEXT_PLANNER_SHADOW_ENABLED=true
```

Optional / legacy:

- ProxiAPI and Yandex providers are still supported only when explicitly configured.
- Do not set ProxiAPI env vars if direct OpenAI billing is intended.

Warnings:

- Image generation is paid.
- Avoid running local and server bots at the same time with the same Telegram token.

Deployment reminders:

- After changing `.env`, restart the container.
- After code changes, rebuild the container.

Role metadata inspection:

- Inspect latest role metadata locally or on the server with:
  `python scripts/inspect_generation_roles.py --db bot.db --limit 5`
- Check the active runtime config profile with:
  `python scripts/check_runtime_config.py`
