"""Regression tests for the Stage 4 /reset data-deletion contract (delete_user_completely).

Original audit gap: delete_user_completely cleared subscriptions/subscription_deliveries and
(Stage 3) smalltalk_limits, but left generation_limits, generation_history and visual_history
behind - so a user who deleted their registration and re-registered under the same Telegram id
could inherit their previous generation quota for the rest of the UTC day, and their old
generation/visual history would still be attributed to the "new" account.
"""
import asyncio
import datetime as dt

import database as db

USER_ID = 701
OTHER_USER_ID = 702


async def _seed_full_user(user_id: int) -> int:
    """Create a user with one row in every user-owned table delete_user_completely must clear."""
    await db.create_or_update_user(user_id, "u", name="T", gender="female")
    await db.record_interactive_generation(user_id)
    await db.reserve_smalltalk_usage(user_id, 5)

    subscription_id = await db.create_subscription(user_id, "random", None, "auto", "ru", 8, 0)
    now = dt.datetime.now(dt.timezone.utc)
    await db.claim_subscription_delivery(
        subscription_id=subscription_id,
        user_id=user_id,
        delivery_date="2030-01-01",
        visual_mode="illustration",
        now=now,
        max_attempts=3,
        retry_backoff=dt.timedelta(minutes=15),
        lease=dt.timedelta(minutes=15),
    )

    generation_id = await db.save_generation_history(user_id, "manual", focus_title="focus")
    await db.save_visual_history(user_id, generation_id=generation_id, scene_type="forest_path")
    return subscription_id


def test_delete_user_completely_clears_generation_limits(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "reset1.db"))
        await db.init_db()
        await _seed_full_user(USER_ID)
        assert await db.get_generation_usage_today(USER_ID) == 1

        await db.delete_user_completely(USER_ID)
        assert await db.get_generation_usage_today(USER_ID) == 0

    asyncio.run(run())


def test_delete_user_completely_clears_smalltalk_limits(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "reset2.db"))
        await db.init_db()
        await _seed_full_user(USER_ID)
        assert await db.get_smalltalk_usage_today(USER_ID) == 1

        await db.delete_user_completely(USER_ID)
        assert await db.get_smalltalk_usage_today(USER_ID) == 0

    asyncio.run(run())


def test_delete_user_completely_clears_subscriptions_and_deliveries(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "reset3.db"))
        await db.init_db()
        await _seed_full_user(USER_ID)
        assert await db.count_active_subscriptions(USER_ID) == 1
        assert await db.get_subscription_deliveries(["2030-01-01"])

        await db.delete_user_completely(USER_ID)
        assert await db.count_active_subscriptions(USER_ID) == 0
        assert await db.get_active_subscriptions(USER_ID) == []
        assert await db.get_subscription_deliveries(["2030-01-01"]) == []

    asyncio.run(run())


def test_delete_user_completely_clears_generation_and_visual_history(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "reset4.db"))
        await db.init_db()
        await _seed_full_user(USER_ID)
        assert await db.get_recent_generation_history(USER_ID) != []
        assert await db.get_recent_visual_history(USER_ID) != []

        await db.delete_user_completely(USER_ID)
        assert await db.get_recent_generation_history(USER_ID) == []
        assert await db.get_recent_visual_history(USER_ID) == []

    asyncio.run(run())


def test_delete_user_completely_clears_the_users_row(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "reset5.db"))
        await db.init_db()
        await _seed_full_user(USER_ID)
        assert await db.get_user(USER_ID) is not None

        await db.delete_user_completely(USER_ID)
        assert await db.get_user(USER_ID) is None

    asyncio.run(run())


def test_delete_user_completely_does_not_touch_another_user(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "reset6.db"))
        await db.init_db()
        await _seed_full_user(USER_ID)
        await _seed_full_user(OTHER_USER_ID)

        await db.delete_user_completely(USER_ID)

        assert await db.get_user(USER_ID) is None
        other = await db.get_user(OTHER_USER_ID)
        assert other is not None and other["name"] == "T"
        assert await db.get_generation_usage_today(OTHER_USER_ID) == 1
        assert await db.get_smalltalk_usage_today(OTHER_USER_ID) == 1
        assert await db.count_active_subscriptions(OTHER_USER_ID) == 1
        assert await db.get_recent_generation_history(OTHER_USER_ID) != []
        assert await db.get_recent_visual_history(OTHER_USER_ID) != []
        assert await db.get_subscription_deliveries(["2030-01-01"]) != []

    asyncio.run(run())


def test_reregistering_same_telegram_id_starts_clean(monkeypatch, tmp_path):
    """The end-to-end promise behind /reset: a deleted-then-re-registered account must not
    inherit the previous account's quota, profile, history or subscriptions."""

    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "reset7.db"))
        await db.init_db()
        await _seed_full_user(USER_ID)

        await db.delete_user_completely(USER_ID)

        await db.create_or_update_user(USER_ID, "u", name="Fresh", gender="male")
        user = await db.get_user(USER_ID)
        assert user["name"] == "Fresh"
        assert user["gender"] == "male"
        assert await db.get_generation_usage_today(USER_ID) == 0
        assert await db.get_smalltalk_usage_today(USER_ID) == 0
        assert await db.count_active_subscriptions(USER_ID) == 0
        assert await db.get_recent_generation_history(USER_ID) == []
        assert await db.get_recent_visual_history(USER_ID) == []

        # Quotas function normally again for the re-registered account.
        await db.record_interactive_generation(USER_ID)
        assert await db.get_generation_usage_today(USER_ID) == 1

    asyncio.run(run())
