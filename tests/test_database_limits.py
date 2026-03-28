import pytest

import database as db


@pytest.mark.asyncio
async def test_generation_limit_five_per_day(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "lim.db"))
    await db.init_db()
    await db.create_or_update_user(42, "u", name="Test")

    monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

    for _ in range(5):
        await db.record_interactive_generation(42)

    allowed, used = await db.can_start_interactive_generation(42, 5)
    assert not allowed and used == 5


@pytest.mark.asyncio
async def test_generation_limit_resets_next_utc_day(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "lim2.db"))
    await db.init_db()
    await db.create_or_update_user(7, "u", name="T")

    monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-06-01")
    await db.record_interactive_generation(7)
    await db.record_interactive_generation(7)
    assert await db.get_generation_usage_today(7) == 2

    monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-06-02")
    assert await db.get_generation_usage_today(7) == 0

    allowed, used = await db.can_start_interactive_generation(7, 5)
    assert allowed and used == 0

    await db.record_interactive_generation(7)
    assert await db.get_generation_usage_today(7) == 1


@pytest.mark.asyncio
async def test_unlimited_when_limit_zero(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "lim3.db"))
    await db.init_db()
    allowed, used = await db.can_start_interactive_generation(99, 0)
    assert allowed and used == 0
