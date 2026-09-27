import importlib
import re
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
async def test_reserve_smalltalk_usage_postgres_returns_true_when_reserved(monkeypatch):
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

    reserved = await db.reserve_smalltalk_usage(42, 5)

    assert reserved is True
    assert "RETURNING 1" in captured["query"]
    assert "ON CONFLICT(user_id) DO UPDATE" in captured["query"]
    assert captured["params"][-1] == 5


@pytest.mark.asyncio
async def test_reserve_smalltalk_usage_postgres_returns_false_when_limit_reached(monkeypatch):
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

    reserved = await db.reserve_smalltalk_usage(42, 5)

    assert reserved is False


@pytest.mark.asyncio
async def test_reserve_smalltalk_usage_postgres_skips_db_when_unlimited(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/rise")
    db = _reload_database_module(monkeypatch)

    async def _fake_connect():
        raise AssertionError("must not touch the DB when the daily limit is disabled")

    monkeypatch.setattr(db, "_connect_postgres", _fake_connect)

    reserved = await db.reserve_smalltalk_usage(42, 0)

    assert reserved is True


@pytest.mark.asyncio
async def test_release_smalltalk_usage_postgres_executes_guarded_update(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/rise")
    db = _reload_database_module(monkeypatch)

    captured = {}

    class _FakeConn:
        async def execute(self, query, *params):
            captured["query"] = query
            captured["params"] = params
            return "UPDATE 1"

        async def close(self):
            return None

    async def _fake_connect():
        return _FakeConn()

    monkeypatch.setattr(db, "_connect_postgres", _fake_connect)

    await db.release_smalltalk_usage(42)

    assert "count = count - 1" in captured["query"]
    assert "count > 0" in captured["query"]


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


@pytest.mark.asyncio
async def test_delete_user_completely_postgres_deletes_in_fk_safe_order(monkeypatch):
    """Stage 4: delete_user_completely now also clears generation_limits, generation_history
    and visual_history. On PostgreSQL, visual_history.generation_id references
    generation_history(id) and generation_limits.user_id references users(user_id) (see the
    schema in database.py), so those foreign keys are enforced there - a child table's rows
    must be deleted before the table it references, or the delete raises a foreign-key
    violation. This pins that ordering without needing a live PostgreSQL instance."""

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/rise")
    db = _reload_database_module(monkeypatch)

    executed: list[str] = []

    class _FakeTransaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _FakeConn:
        def transaction(self):
            return _FakeTransaction()

        async def execute(self, query, *params):
            executed.append(query)

        async def close(self):
            return None

    async def _fake_connect():
        return _FakeConn()

    monkeypatch.setattr(db, "_connect_postgres", _fake_connect)

    await db.delete_user_completely(42)

    tables_in_order = [re.search(r"FROM (\w+)", query).group(1) for query in executed]
    assert tables_in_order == [
        "visual_history",
        "generation_history",
        "subscription_deliveries",
        "subscriptions",
        "generation_limits",
        "smalltalk_limits",
        "users",
    ]
