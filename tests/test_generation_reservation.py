"""Regression tests for the atomic interactive-generation quota reservation.

Corrective pass: the interactive/manual generation path used to check usage
(`can_start_interactive_generation`), perform paid text/image provider work, send the
result, then increment usage afterward (`record_interactive_generation`). Concurrent
callback presses/messages could all observe available quota and launch paid OpenAI
work before any one request was accounted for. `reserve_generation_usage` /
`release_generation_usage` mirror the already-accepted `smalltalk_limits` atomic
UPSERT pattern (see test_smalltalk_limits.py) so one unit is claimed before any paid
work begins, and released if the reserved use does not end in a delivered result.
"""
import asyncio

import database as db


def test_generation_reserve_allows_up_to_limit_then_blocks(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "gen.db"))
        await db.init_db()
        await db.create_or_update_user(1, "u", name="Test")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        for _ in range(3):
            assert await db.reserve_generation_usage(1, 3) is True
        assert await db.reserve_generation_usage(1, 3) is False
        assert await db.get_generation_usage_today(1) == 3

    asyncio.run(run())


def test_generation_usage_resets_next_utc_day(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "gen2.db"))
        await db.init_db()
        await db.create_or_update_user(2, "u", name="T")

        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-06-01")
        await db.reserve_generation_usage(2, 5)
        await db.reserve_generation_usage(2, 5)
        assert await db.get_generation_usage_today(2) == 2

        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-06-02")
        assert await db.get_generation_usage_today(2) == 0

        assert await db.reserve_generation_usage(2, 5) is True
        assert await db.get_generation_usage_today(2) == 1

    asyncio.run(run())


def test_generation_release_undoes_reservation(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "gen3.db"))
        await db.init_db()
        await db.create_or_update_user(3, "u", name="T")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        assert await db.reserve_generation_usage(3, 2) is True
        assert await db.get_generation_usage_today(3) == 1

        await db.release_generation_usage(3)
        assert await db.get_generation_usage_today(3) == 0

        # Released capacity is usable again, and the cap is still enforced afterwards.
        assert await db.reserve_generation_usage(3, 2) is True
        assert await db.reserve_generation_usage(3, 2) is True
        assert await db.reserve_generation_usage(3, 2) is False

    asyncio.run(run())


def test_generation_release_is_a_noop_below_zero(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "gen_noop.db"))
        await db.init_db()
        await db.create_or_update_user(9, "u", name="T")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        # No reservation was ever made for today; releasing must not go negative.
        await db.release_generation_usage(9)
        assert await db.get_generation_usage_today(9) == 0

    asyncio.run(run())


def test_generation_unlimited_when_limit_zero(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "gen4.db"))
        await db.init_db()
        assert await db.reserve_generation_usage(4, 0) is True
        # An unlimited reservation does not even write a row.
        assert await db.get_generation_usage_today(4) == 0

    asyncio.run(run())


def test_generation_concurrent_reservations_do_not_exceed_limit(monkeypatch, tmp_path):
    """Deterministic concurrency regression: many concurrent reservation attempts race
    against a real temporary SQLite database with a cap smaller than the attempt count.
    Correctness is asserted on the exact number of successful reservations, never on
    wall-clock timing.
    """

    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "gen5.db"))
        await db.init_db()
        await db.create_or_update_user(5, "u", name="T")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        limit = 5
        results = await asyncio.gather(*[db.reserve_generation_usage(5, limit) for _ in range(20)])
        allowed = sum(1 for r in results if r)
        assert allowed == limit
        assert await db.get_generation_usage_today(5) == limit

    asyncio.run(run())


def test_generation_limit_does_not_affect_smalltalk_limit(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "gen6.db"))
        await db.init_db()
        await db.create_or_update_user(6, "u", name="T")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        await db.reserve_generation_usage(6, 3)
        await db.reserve_generation_usage(6, 3)
        await db.reserve_smalltalk_usage(6, 3)

        assert await db.get_generation_usage_today(6) == 2
        assert await db.get_smalltalk_usage_today(6) == 1

    asyncio.run(run())


def test_delete_user_completely_clears_generation_reservations(monkeypatch, tmp_path):
    """Same /reset contract as test_database_reset.py, exercised through the new
    reservation helper rather than the legacy post-send increment."""

    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "gen_delete.db"))
        await db.init_db()
        await db.create_or_update_user(7, "u", name="T")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        await db.reserve_generation_usage(7, 3)
        await db.reserve_generation_usage(7, 3)
        assert await db.get_generation_usage_today(7) == 2

        await db.delete_user_completely(7)
        assert await db.get_generation_usage_today(7) == 0

        await db.create_or_update_user(7, "u", name="T again")
        assert await db.get_generation_usage_today(7) == 0
        assert await db.reserve_generation_usage(7, 3) is True
        assert await db.get_generation_usage_today(7) == 1

    asyncio.run(run())
