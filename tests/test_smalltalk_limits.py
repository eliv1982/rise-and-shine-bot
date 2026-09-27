"""Regression tests for the atomic smalltalk quota reservation.

Stage 7A follow-up: `reserve_smalltalk_usage` now returns the exact UTC day it used for
the upsert, and `release_smalltalk_usage` requires that day back (rather than recomputing
"today" itself) so a release can never be misapplied to a different UTC day's row - this
mirrors the identical fix applied to `reserve_generation_usage` / `release_generation_usage`
(see test_generation_reservation.py). The cross-midnight tests below prove the same
regression this closes, on the smalltalk quota path.
"""
import asyncio

import database as db


def test_smalltalk_reserve_allows_up_to_limit_then_blocks(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "st.db"))
        await db.init_db()
        await db.create_or_update_user(1, "u", name="Test")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        for _ in range(3):
            reserved, _day = await db.reserve_smalltalk_usage(1, 3)
            assert reserved is True
        reserved, _day = await db.reserve_smalltalk_usage(1, 3)
        assert reserved is False
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

        reserved, day = await db.reserve_smalltalk_usage(2, 5)
        assert reserved is True
        assert day == "2030-06-02"
        assert await db.get_smalltalk_usage_today(2) == 1

    asyncio.run(run())


def test_smalltalk_release_undoes_reservation(monkeypatch, tmp_path):
    """Requirement 1: a same-day smalltalk failure releases its own reservation."""

    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "st3.db"))
        await db.init_db()
        await db.create_or_update_user(3, "u", name="T")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        reserved, reservation_day = await db.reserve_smalltalk_usage(3, 2)
        assert reserved is True
        assert reservation_day == "2030-01-01"
        assert await db.get_smalltalk_usage_today(3) == 1

        await db.release_smalltalk_usage(3, reservation_day)
        assert await db.get_smalltalk_usage_today(3) == 0

        # Released capacity is usable again, and the cap is still enforced afterwards.
        reserved_1, _ = await db.reserve_smalltalk_usage(3, 2)
        reserved_2, _ = await db.reserve_smalltalk_usage(3, 2)
        reserved_3, _ = await db.reserve_smalltalk_usage(3, 2)
        assert reserved_1 is True
        assert reserved_2 is True
        assert reserved_3 is False

    asyncio.run(run())


def test_smalltalk_release_is_a_noop_below_zero(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "st_noop.db"))
        await db.init_db()
        await db.create_or_update_user(9, "u", name="T")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        # No reservation was ever made for today; releasing must not go negative.
        await db.release_smalltalk_usage(9, "2030-01-01")
        assert await db.get_smalltalk_usage_today(9) == 0

    asyncio.run(run())


def test_smalltalk_release_is_noop_after_cross_midnight_rollover(monkeypatch, tmp_path):
    """Requirement 2 (partial): a cross-midnight stale release must be a no-op once the
    stored row has actually rolled over to a newer UTC day - i.e. once another reservation
    on the new day has reset it. Releasing with the stale, captured old-day identity must
    not touch that new-day row."""

    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "st_rollover.db"))
        await db.init_db()
        await db.create_or_update_user(10, "u", name="T")

        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")
        reserved, reservation_day = await db.reserve_smalltalk_usage(10, 2)
        assert reserved is True
        assert reservation_day == "2030-01-01"
        assert await db.get_smalltalk_usage_today(10) == 1

        # The row rolls over to a new day once another reservation happens there.
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-02")
        reserved_new_day, new_day = await db.reserve_smalltalk_usage(10, 2)
        assert reserved_new_day is True
        assert new_day == "2030-01-02"
        assert await db.get_smalltalk_usage_today(10) == 1

        # The stale (day-1) release must be a no-op: it must not decrement day 2's count.
        await db.release_smalltalk_usage(10, reservation_day)
        assert await db.get_smalltalk_usage_today(10) == 1

    asyncio.run(run())


def test_smalltalk_cross_midnight_stale_release_does_not_erase_next_day_reservation(monkeypatch, tmp_path):
    """Requirement 2: exact cross-midnight regression scenario.

      1. Smalltalk request A reserves on UTC day 1.
      2. UTC rolls over.
      3. Smalltalk request B reserves on UTC day 2, resetting the row to day 2 / count 1.
      4. Request A fails and releases using its own captured day-1 reservation identity.
      5. Day-2 usage remains 1: A's stale release must not erase B's valid reservation.
    """

    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "st_midnight_race.db"))
        await db.init_db()
        await db.create_or_update_user(11, "u", name="T")

        # 1. Request A reserves on day 1.
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-03-01")
        reserved_a, day_a = await db.reserve_smalltalk_usage(11, 3)
        assert reserved_a is True
        assert day_a == "2030-03-01"

        # 2. UTC rolls over.
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-03-02")

        # 3. Request B reserves on day 2, resetting the row to day 2 / count 1.
        reserved_b, day_b = await db.reserve_smalltalk_usage(11, 3)
        assert reserved_b is True
        assert day_b == "2030-03-02"
        assert await db.get_smalltalk_usage_today(11) == 1

        # 4. Request A fails and releases using its own day-1 reservation identity, not a
        #    recomputed "today" (which would be day 2 here and would wrongly match B's row).
        await db.release_smalltalk_usage(11, day_a)

        # 5. Day-2 usage remains 1: A's stale release did not erase B's valid reservation.
        assert await db.get_smalltalk_usage_today(11) == 1

    asyncio.run(run())


def test_smalltalk_unlimited_when_limit_zero(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "st4.db"))
        await db.init_db()
        reserved, day = await db.reserve_smalltalk_usage(4, 0)
        assert reserved is True
        assert day  # day is still reported even though unlimited reservations write no row
        # An unlimited reservation does not even write a row.
        assert await db.get_smalltalk_usage_today(4) == 0

    asyncio.run(run())


def test_smalltalk_concurrent_reservations_do_not_exceed_limit(monkeypatch, tmp_path):
    """Requirement 4: same-day concurrent reservations still cannot exceed the cap."""

    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "st5.db"))
        await db.init_db()
        await db.create_or_update_user(5, "u", name="T")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        limit = 5
        results = await asyncio.gather(*[db.reserve_smalltalk_usage(5, limit) for _ in range(20)])
        allowed = sum(1 for reserved, _day in results if reserved)
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
        reserved, _day = await db.reserve_smalltalk_usage(7, 3)
        assert reserved is True
        assert await db.get_smalltalk_usage_today(7) == 1

    asyncio.run(run())


def test_smalltalk_limit_does_not_affect_generation_limit(monkeypatch, tmp_path):
    """Requirement 9: generation quota behavior remains unchanged by this smalltalk fix."""

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
