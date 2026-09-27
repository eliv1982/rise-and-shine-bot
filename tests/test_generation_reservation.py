"""Regression tests for the atomic interactive-generation quota reservation.

Corrective pass: the interactive/manual generation path used to check usage
(`can_start_interactive_generation`), perform paid text/image provider work, send the
result, then increment usage afterward (`record_interactive_generation`). Concurrent
callback presses/messages could all observe available quota and launch paid OpenAI
work before any one request was accounted for. `reserve_generation_usage` /
`release_generation_usage` mirror the already-accepted `smalltalk_limits` atomic
UPSERT pattern (see test_smalltalk_limits.py) so one unit is claimed before any paid
work begins, and released if the reserved use does not end in a delivered result.

Stage 7A cross-midnight follow-up: `reserve_generation_usage` now returns the exact
UTC day it used for the upsert, and `release_generation_usage` requires that day back
(rather than recomputing "today" itself) so a release can never be misapplied to a
different UTC day's row - see the cross-midnight tests below for the exact regression
this closes.
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
            reserved, _day = await db.reserve_generation_usage(1, 3)
            assert reserved is True
        reserved, _day = await db.reserve_generation_usage(1, 3)
        assert reserved is False
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

        reserved, day = await db.reserve_generation_usage(2, 5)
        assert reserved is True
        assert day == "2030-06-02"
        assert await db.get_generation_usage_today(2) == 1

    asyncio.run(run())


def test_generation_release_undoes_reservation(monkeypatch, tmp_path):
    """Requirement 1: a same-day failed request releases its own reservation."""

    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "gen3.db"))
        await db.init_db()
        await db.create_or_update_user(3, "u", name="T")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        reserved, reservation_day = await db.reserve_generation_usage(3, 2)
        assert reserved is True
        assert reservation_day == "2030-01-01"
        assert await db.get_generation_usage_today(3) == 1

        await db.release_generation_usage(3, reservation_day)
        assert await db.get_generation_usage_today(3) == 0

        # Released capacity is usable again, and the cap is still enforced afterwards.
        reserved_1, _ = await db.reserve_generation_usage(3, 2)
        reserved_2, _ = await db.reserve_generation_usage(3, 2)
        reserved_3, _ = await db.reserve_generation_usage(3, 2)
        assert reserved_1 is True
        assert reserved_2 is True
        assert reserved_3 is False

    asyncio.run(run())


def test_generation_release_is_a_noop_below_zero(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "gen_noop.db"))
        await db.init_db()
        await db.create_or_update_user(9, "u", name="T")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        # No reservation was ever made for today; releasing must not go negative.
        await db.release_generation_usage(9, "2030-01-01")
        assert await db.get_generation_usage_today(9) == 0

    asyncio.run(run())


def test_generation_release_is_noop_after_cross_midnight_rollover(monkeypatch, tmp_path):
    """Requirement 2: a cross-midnight stale release must be a no-op once the stored row
    has actually rolled over to a newer UTC day.

    This exercises the release call with an explicit ``day_utc`` argument that no longer
    matches the (already-rolled-over) stored row, proving the guard is keyed on the exact
    reservation day rather than on any freshly recomputed "today".
    """

    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "gen_rollover.db"))
        await db.init_db()
        await db.create_or_update_user(10, "u", name="T")

        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")
        reserved, reservation_day = await db.reserve_generation_usage(10, 2)
        assert reserved is True
        assert reservation_day == "2030-01-01"
        assert await db.get_generation_usage_today(10) == 1

        # Simulate the row having rolled over to a newer day by the time release runs
        # (e.g. another reservation on the new day already reset it). A release keyed on
        # the stale captured day must not touch the new day's row.
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-02")
        reserved_new_day, new_day = await db.reserve_generation_usage(10, 2)
        assert reserved_new_day is True
        assert new_day == "2030-01-02"
        assert await db.get_generation_usage_today(10) == 1

        # The stale (day-1) release must be a no-op: it must not decrement day 2's count.
        await db.release_generation_usage(10, reservation_day)
        assert await db.get_generation_usage_today(10) == 1

    asyncio.run(run())


def test_generation_cross_midnight_stale_release_does_not_erase_next_day_reservation(monkeypatch, tmp_path):
    """Requirement 3: exact regression scenario.

      1. Request A reserves generation quota on UTC day 1.
      2. UTC rolls over.
      3. Request B reserves on UTC day 2, resetting the row to day 2 / count 1.
      4. Request A fails and releases using its own captured day-1 reservation identity.
      5. Day-2 usage remains 1: A's stale release must not erase B's valid reservation.
    """

    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "gen_midnight_race.db"))
        await db.init_db()
        await db.create_or_update_user(11, "u", name="T")

        # 1. Request A reserves on day 1.
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-03-01")
        reserved_a, day_a = await db.reserve_generation_usage(11, 3)
        assert reserved_a is True
        assert day_a == "2030-03-01"

        # 2. UTC rolls over.
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-03-02")

        # 3. Request B reserves on day 2, resetting the row to day 2 / count 1.
        reserved_b, day_b = await db.reserve_generation_usage(11, 3)
        assert reserved_b is True
        assert day_b == "2030-03-02"
        assert await db.get_generation_usage_today(11) == 1

        # 4. Request A fails and releases using its own day-1 reservation identity, not a
        #    recomputed "today" (which would be day 2 here and would wrongly match B's row).
        await db.release_generation_usage(11, day_a)

        # 5. Day-2 usage remains 1: A's stale release did not erase B's valid reservation.
        assert await db.get_generation_usage_today(11) == 1

    asyncio.run(run())


def test_generation_unlimited_when_limit_zero(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "gen4.db"))
        await db.init_db()
        reserved, day = await db.reserve_generation_usage(4, 0)
        assert reserved is True
        assert day  # day is still reported even though unlimited reservations write no row
        # An unlimited reservation does not even write a row.
        assert await db.get_generation_usage_today(4) == 0

    asyncio.run(run())


def test_generation_concurrent_reservations_do_not_exceed_limit(monkeypatch, tmp_path):
    """Requirement 4: deterministic concurrency regression. Many concurrent same-day
    reservation attempts race against a real temporary SQLite database with a cap smaller
    than the attempt count. Correctness is asserted on the exact number of successful
    reservations, never on wall-clock timing.
    """

    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "gen5.db"))
        await db.init_db()
        await db.create_or_update_user(5, "u", name="T")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        limit = 5
        results = await asyncio.gather(*[db.reserve_generation_usage(5, limit) for _ in range(20)])
        allowed = sum(1 for reserved, _day in results if reserved)
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
        reserved, _day = await db.reserve_generation_usage(7, 3)
        assert reserved is True
        assert await db.get_generation_usage_today(7) == 1

    asyncio.run(run())
