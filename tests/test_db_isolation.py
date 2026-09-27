import asyncio
import os
import sqlite3
from pathlib import Path

import pytest

import database as db
from config import get_bot_data_dir, get_outputs_dir, get_settings

REPO_DEFAULT_DB = Path(__file__).resolve().parents[1] / "bot.db"


def test_default_db_path_is_per_test_temp_and_not_the_repo_bot_db(sqlite_db_path, tmp_path_factory):
    resolved = Path(sqlite_db_path).resolve()

    assert db.DB_PATH == sqlite_db_path
    assert db._resolve_sqlite_db_path() == sqlite_db_path
    assert db.get_database_backend_name() == "sqlite"
    assert resolved != REPO_DEFAULT_DB
    assert resolved.is_relative_to(tmp_path_factory.getbasetemp().resolve())
    assert not resolved.exists()


def test_outputs_dir_is_redirected_next_to_the_temp_db(sqlite_db_path):
    assert Path(get_bot_data_dir()) == Path(sqlite_db_path).parent
    assert Path(get_outputs_dir()) == Path(sqlite_db_path).parent / "outputs"


def test_generation_limit_settings_are_pinned_regardless_of_local_env():
    settings = get_settings()

    assert settings.disable_daily_generation_limit is False
    assert settings.generation_daily_limit == 5


def test_initialized_db_has_the_production_schema(initialized_db):
    with sqlite3.connect(initialized_db) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}

    assert {"users", "subscriptions", "generation_limits", "generation_history", "visual_history"} <= tables
    assert asyncio.run(db.can_start_interactive_generation(1, 5)) == (True, 0)


@pytest.mark.parametrize("run", ["first", "second"])
def test_initialized_db_is_fresh_for_every_test(initialized_db, run):
    async def scenario():
        assert await db.get_user(4242) is None
        await db.create_or_update_user(4242, "u", name="Isolation")
        assert await db.get_user(4242) is not None

    # Both runs must see an empty DB; the second would fail if state leaked between tests.
    asyncio.run(scenario())
    assert os.path.exists(initialized_db)
