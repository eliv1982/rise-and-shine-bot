import importlib
from types import SimpleNamespace

import pytest


def _reload_database_module(monkeypatch):
    import database

    return importlib.reload(database)


def test_backend_defaults_to_sqlite_when_database_url_absent(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    db = _reload_database_module(monkeypatch)

    assert db.get_database_backend_name() == "sqlite"


def test_backend_uses_postgres_for_postgres_scheme(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/rise")

    db = _reload_database_module(monkeypatch)

    assert db.get_database_backend_name() == "postgresql"


def test_backend_uses_postgres_for_postgresql_scheme(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/rise")

    db = _reload_database_module(monkeypatch)

    assert db.get_database_backend_name() == "postgresql"


def test_postgres_placeholder_conversion(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db = _reload_database_module(monkeypatch)

    converted = db._convert_sql_placeholders_for_postgres(
        "SELECT * FROM users WHERE user_id = ? AND language = ?"
    )

    assert converted == "SELECT * FROM users WHERE user_id = $1 AND language = $2"


def test_postgres_placeholder_conversion_ignores_single_quoted_literals(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db = _reload_database_module(monkeypatch)

    converted = db._convert_sql_placeholders_for_postgres(
        "SELECT '?' AS literal_value, * FROM users WHERE note = 'why?' AND user_id = ?"
    )

    assert converted == "SELECT '?' AS literal_value, * FROM users WHERE note = 'why?' AND user_id = $1"


def test_postgres_placeholder_conversion_ignores_escaped_single_quotes(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db = _reload_database_module(monkeypatch)

    converted = db._convert_sql_placeholders_for_postgres(
        "SELECT * FROM notes WHERE body = 'it''s still ? here' AND user_id = ?"
    )

    assert converted == "SELECT * FROM notes WHERE body = 'it''s still ? here' AND user_id = $1"


def test_postgres_placeholder_conversion_ignores_double_quoted_identifiers(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db = _reload_database_module(monkeypatch)

    converted = db._convert_sql_placeholders_for_postgres(
        'SELECT "weird?column" FROM "table?" WHERE user_id = ? AND language = ?'
    )

    assert converted == 'SELECT "weird?column" FROM "table?" WHERE user_id = $1 AND language = $2'


def test_sqlite_path_falls_back_to_default_db_path(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SQLITE_DB_PATH", raising=False)
    db = _reload_database_module(monkeypatch)

    monkeypatch.setattr(db, "DB_PATH", "tmp/fallback.db")

    assert db._resolve_sqlite_db_path() == "tmp/fallback.db"


def test_sqlite_path_uses_env_override(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SQLITE_DB_PATH", "tmp/override.db")
    db = _reload_database_module(monkeypatch)

    monkeypatch.setattr(db, "DB_PATH", "tmp/fallback.db")

    assert db._resolve_sqlite_db_path() == "tmp/override.db"


@pytest.mark.asyncio
async def test_update_subscription_postgres_returns_true_when_row_updated(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/rise")
    db = _reload_database_module(monkeypatch)

    captured = {}

    class _FakeConn:
        async def fetchrow(self, query, *params):
            captured["query"] = query
            captured["params"] = params
            return (1,)

        async def close(self):
            return None

    async def _fake_connect():
        return _FakeConn()

    monkeypatch.setattr(db, "_connect_postgres", _fake_connect)

    changed = await db.update_subscription(
        subscription_id=7,
        user_id=42,
        sphere="inner_peace",
        subsphere=None,
        image_style="auto",
        language="ru",
        hour=8,
        minute=30,
    )

    assert changed is True
    assert "RETURNING 1" in captured["query"]


@pytest.mark.asyncio
async def test_update_subscription_postgres_returns_false_when_no_row_updated(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/rise")
    db = _reload_database_module(monkeypatch)

    class _FakeConn:
        async def fetchrow(self, query, *params):
            return None

        async def close(self):
            return None

    async def _fake_connect():
        return _FakeConn()

    monkeypatch.setattr(db, "_connect_postgres", _fake_connect)

    changed = await db.update_subscription(
        subscription_id=7,
        user_id=42,
        sphere="inner_peace",
        subsphere=None,
        image_style="auto",
        language="ru",
        hour=8,
        minute=30,
    )

    assert changed is False
