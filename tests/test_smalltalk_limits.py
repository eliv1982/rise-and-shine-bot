import asyncio

import database as db


def test_smalltalk_reserve_allows_up_to_limit_then_blocks(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "st.db"))
        await db.init_db()
        await db.create_or_update_user(1, "u", name="Test")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        for _ in range(3):
            assert await db.reserve_smalltalk_usage(1, 3) is True
        assert await db.reserve_smalltalk_usage(1, 3) is False
        assert await db.get_smalltalk_usage_today(1) == 3

    asyncio.run(run())


def test_smalltalk_usage_resets_next_utc_day(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "st2.db"))
        await db.init_db()
        await db.create_or_update_user(2, "u", name="T")

        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-06-01")
        await db.reserve_smalltalk_usage(2, 5)
        await db.reserve_smalltalk_usage(2, 5)
        assert await db.get_smalltalk_usage_today(2) == 2

        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-06-02")
        assert await db.get_smalltalk_usage_today(2) == 0

        assert await db.reserve_smalltalk_usage(2, 5) is True
        assert await db.get_smalltalk_usage_today(2) == 1

    asyncio.run(run())


def test_smalltalk_release_undoes_reservation(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "st3.db"))
        await db.init_db()
        await db.create_or_update_user(3, "u", name="T")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        assert await db.reserve_smalltalk_usage(3, 2) is True
        assert await db.get_smalltalk_usage_today(3) == 1

        await db.release_smalltalk_usage(3)
        assert await db.get_smalltalk_usage_today(3) == 0

        # Released capacity is usable again, and the cap is still enforced afterwards.
        assert await db.reserve_smalltalk_usage(3, 2) is True
        assert await db.reserve_smalltalk_usage(3, 2) is True
        assert await db.reserve_smalltalk_usage(3, 2) is False

    asyncio.run(run())


def test_smalltalk_release_is_a_noop_below_zero(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "st_noop.db"))
        await db.init_db()
        await db.create_or_update_user(9, "u", name="T")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        # No reservation was ever made for today; releasing must not go negative.
        await db.release_smalltalk_usage(9)
        assert await db.get_smalltalk_usage_today(9) == 0

    asyncio.run(run())


def test_smalltalk_unlimited_when_limit_zero(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "st4.db"))
        await db.init_db()
        assert await db.reserve_smalltalk_usage(4, 0) is True
        # An unlimited reservation does not even write a row.
        assert await db.get_smalltalk_usage_today(4) == 0

    asyncio.run(run())


def test_smalltalk_concurrent_reservations_do_not_exceed_limit(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "st5.db"))
        await db.init_db()
        await db.create_or_update_user(5, "u", name="T")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        limit = 5
        results = await asyncio.gather(*[db.reserve_smalltalk_usage(5, limit) for _ in range(20)])
        allowed = sum(1 for r in results if r)
        assert allowed == limit
        assert await db.get_smalltalk_usage_today(5) == limit

    asyncio.run(run())


def test_delete_user_completely_clears_smalltalk_limits(monkeypatch, tmp_path):
    """Regression for the full /reset flow (handlers/start.py's cmd_reset ->
    delete_user_completely). Stage 3 added the durable smalltalk_limits table, and
    delete_user_completely must clear it along with the user's other rows: otherwise a
    deleted-then-re-registered Telegram account would inherit the previous account's
    smalltalk usage for the rest of that UTC day.
    """

    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "st_delete.db"))
        await db.init_db()
        await db.create_or_update_user(7, "u", name="T")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        await db.reserve_smalltalk_usage(7, 3)
        await db.reserve_smalltalk_usage(7, 3)
        assert await db.get_smalltalk_usage_today(7) == 2

        await db.delete_user_completely(7)
        assert await db.get_smalltalk_usage_today(7) == 0

        # Re-registering the same Telegram id must start with a clean quota, not
        # inherit the count left over from before the delete.
        await db.create_or_update_user(7, "u", name="T again")
        assert await db.get_smalltalk_usage_today(7) == 0
        assert await db.reserve_smalltalk_usage(7, 3) is True
        assert await db.get_smalltalk_usage_today(7) == 1

    asyncio.run(run())


def test_smalltalk_limit_does_not_affect_generation_limit(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "st6.db"))
        await db.init_db()
        await db.create_or_update_user(6, "u", name="T")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        await db.reserve_smalltalk_usage(6, 3)
        await db.reserve_smalltalk_usage(6, 3)
        await db.record_interactive_generation(6)

        assert await db.get_smalltalk_usage_today(6) == 2
        assert await db.get_generation_usage_today(6) == 1

    asyncio.run(run())
