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


@pytest.mark.asyncio
async def test_init_db_rejects_malformed_database_url(monkeypatch):
    """Stage 5 item N: a typo'd DATABASE_URL must fail startup loudly, not
    silently fall back to an empty local SQLite database."""
    monkeypatch.setenv("DATABASE_URL", "postgres-server.example.com:5432/rise_bot")
    db = _reload_database_module(monkeypatch)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        await db.init_db()


@pytest.mark.asyncio
async def test_init_db_accepts_valid_postgres_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/rise")
    db = _reload_database_module(monkeypatch)

    class _FakeConn:
        async def execute(self, query, *params):
            return None

        async def close(self):
            return None

    async def _fake_connect():
        return _FakeConn()

    async def _fake_add_column_if_missing(*_a, **_k):
        return None

    monkeypatch.setattr(db, "_connect_postgres", _fake_connect)
    monkeypatch.setattr(db, "add_column_if_missing", _fake_add_column_if_missing)

    await db.init_db()  # must not raise


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

    reserved, day_utc = await db.reserve_smalltalk_usage(42, 5)

    assert reserved is True
    assert day_utc == captured["params"][1]
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

    reserved, day_utc = await db.reserve_smalltalk_usage(42, 5)

    assert reserved is False
    # Even on a rejected reservation, the caller still learns which UTC day was computed
    # (there is nothing to release in this case, but the contract is uniform).
    assert day_utc


@pytest.mark.asyncio
async def test_reserve_smalltalk_usage_postgres_skips_db_when_unlimited(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/rise")
    db = _reload_database_module(monkeypatch)

    async def _fake_connect():
        raise AssertionError("must not touch the DB when the daily limit is disabled")

    monkeypatch.setattr(db, "_connect_postgres", _fake_connect)

    reserved, day_utc = await db.reserve_smalltalk_usage(42, 0)

    assert reserved is True
    assert day_utc


@pytest.mark.asyncio
async def test_release_smalltalk_usage_postgres_executes_guarded_update(monkeypatch):
    """Requirement 8: the PostgreSQL release query shape includes the reservation-day
    guard, and release must never recompute "today" itself - the day_utc value used in the
    query must be exactly the caller-supplied value, not something release derives on its
    own (there is no call to any "today" helper inside this function at all)."""
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

    caller_supplied_day = "2030-01-01"
    await db.release_smalltalk_usage(42, caller_supplied_day)

    assert "count = count - 1" in captured["query"]
    assert "count > 0" in captured["query"]
    assert "day_utc = " in captured["query"]
    # The exact caller-supplied reservation day must reach the query params unchanged.
    assert caller_supplied_day in captured["params"]


@pytest.mark.asyncio
async def test_reserve_generation_usage_postgres_returns_true_when_reserved(monkeypatch):
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
    monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

    reserved, day_utc = await db.reserve_generation_usage(42, 5)

    assert reserved is True
    assert day_utc == "2030-01-01"
    assert day_utc == captured["params"][1]
    assert "RETURNING 1" in captured["query"]
    assert "ON CONFLICT(user_id) DO UPDATE" in captured["query"]
    assert "generation_limits" in captured["query"]
    assert captured["params"][-1] == 5


@pytest.mark.asyncio
async def test_reserve_generation_usage_postgres_returns_false_when_limit_reached(monkeypatch):
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
    monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

    reserved, day_utc = await db.reserve_generation_usage(42, 5)

    assert reserved is False
    assert day_utc == "2030-01-01"


@pytest.mark.asyncio
async def test_reserve_generation_usage_postgres_skips_db_when_unlimited(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/rise")
    db = _reload_database_module(monkeypatch)

    async def _fake_connect():
        raise AssertionError("must not touch the DB when the daily limit is disabled")

    monkeypatch.setattr(db, "_connect_postgres", _fake_connect)
    monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

    reserved, day_utc = await db.reserve_generation_usage(42, 0)

    assert reserved is True
    assert day_utc == "2030-01-01"


@pytest.mark.asyncio
async def test_release_generation_usage_postgres_executes_guarded_update(monkeypatch):
    """Requirement 8: the PostgreSQL release query shape includes the reservation-day
    guard, and release must never recompute "today" itself - the day_utc value used in the
    query must be exactly the caller-supplied value, not something release derives on its
    own (there is no call to any "today" helper inside this function at all)."""
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

    def _unexpected_utc_today():
        raise AssertionError("release must not recompute the UTC day")

    monkeypatch.setattr(db, "_connect_postgres", _fake_connect)
    monkeypatch.setattr(db, "_utc_today_iso", _unexpected_utc_today)

    caller_supplied_day = "2030-01-01"
    await db.release_generation_usage(42, caller_supplied_day)

    assert "count = count - 1" in captured["query"]
    assert "generation_limits" in captured["query"]
    assert "WHERE user_id = $1 AND day_utc = $2 AND count > 0" in captured["query"]
    assert captured["params"] == (42, caller_supplied_day)


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
