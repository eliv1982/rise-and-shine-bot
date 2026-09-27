import asyncio
import os

import dotenv
import pytest

# config.py calls load_dotenv() at import time, which would copy a developer's local
# .env into os.environ for the whole test session. Neutralize it before any project
# module is imported so tests only see values set explicitly here or inside a test.
dotenv.load_dotenv = lambda *args, **kwargs: False

# Минимальные переменные до импорта модулей, вызывающих get_settings()
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("BOT_TOKEN", "test-bot-token")
os.environ.setdefault("OPENAI_BASE_URL", "https://api.openai.com/v1")
os.environ.setdefault("OPENAI_TEXT_MODEL", "gpt-4o-mini")
os.environ.setdefault("OPENAI_IMAGE_MODEL", "gpt-image-1")
os.environ.setdefault("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
os.environ.setdefault("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")


@pytest.fixture(autouse=True)
def isolate_provider_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
    monkeypatch.setenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    monkeypatch.setenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
    monkeypatch.setenv("BOT_TOKEN", "test-bot-token")


@pytest.fixture(autouse=True)
def isolate_generation_limit_env(monkeypatch):
    """Generation-limit behaviour must not depend on a developer's .env or shell."""
    monkeypatch.setenv("DISABLE_DAILY_GENERATION_LIMIT", "false")
    monkeypatch.setenv("DAILY_GENERATION_LIMIT", "5")
    monkeypatch.delenv("GENERATION_DAILY_LIMIT", raising=False)
    monkeypatch.setenv("SMALLTALK_DAILY_LIMIT", "20")


@pytest.fixture(autouse=True)
def sqlite_db_path(monkeypatch, tmp_path_factory) -> str:
    """Give every test its own empty, uninitialised SQLite path and outputs dir.

    Nothing can reach the developer's bot.db or outputs/. A test that needs the
    production schema requests `initialized_db`; a test that touches the DB without
    it fails deterministically ("no such table") instead of depending on local state.
    """
    import database

    data_dir = tmp_path_factory.mktemp("data")
    db_path = str(data_dir / "bot.db")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SQLITE_DB_PATH", raising=False)
    monkeypatch.setenv("BOT_DATA_DIR", str(data_dir))
    monkeypatch.setattr(database, "DB_PATH", db_path)
    return db_path


@pytest.fixture
def initialized_db(sqlite_db_path) -> str:
    """Per-test SQLite DB with the real production schema applied via init_db()."""
    import database

    asyncio.run(database.init_db())
    return sqlite_db_path
