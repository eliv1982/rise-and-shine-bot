import asyncio
import datetime as dt

import database as db


def test_generation_limit_five_per_day(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "lim.db"))
        await db.init_db()
        await db.create_or_update_user(42, "u", name="Test")

        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        for _ in range(5):
            await db.record_interactive_generation(42)

        allowed, used = await db.can_start_interactive_generation(42, 5)
        assert not allowed and used == 5

    asyncio.run(run())


def test_generation_limit_resets_next_utc_day(monkeypatch, tmp_path):
    async def run():
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

    asyncio.run(run())


def test_unlimited_when_limit_zero(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "lim3.db"))
        await db.init_db()
        allowed, used = await db.can_start_interactive_generation(99, 0)
        assert allowed and used == 0

    asyncio.run(run())


def test_subscription_v2_columns_are_added(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "sub.db"))
        await db.init_db()
        await db.create_or_update_user(10, "u", name="Sub")
        await db.upsert_subscription(
            user_id=10,
            sphere="random",
            subsphere=None,
            image_style="auto",
            language="ru",
            hour=8,
            minute=0,
            subscription_mode="weekly_balance",
            subscription_sphere=None,
            subscription_style_mode="auto",
            visual_mode="mixed",
        )
        sub = await db.get_subscription(10)
        assert sub["subscription_mode"] == "weekly_balance"
        assert sub["subscription_style_mode"] == "auto"
        assert sub["visual_mode"] == "mixed"

    asyncio.run(run())


def test_user_can_create_three_active_subscriptions(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "multi.db"))
        await db.init_db()
        await db.create_or_update_user(20, "u", name="Multi")
        for hour in (7, 12, 21):
            await db.create_subscription(
                user_id=20,
                sphere="random",
                subsphere=None,
                image_style="auto",
                language="ru",
                hour=hour,
                minute=0,
                subscription_mode="weekly_balance",
                subscription_style_mode="auto",
                visual_mode="mixed",
            )
        subscriptions = await db.get_active_subscriptions(20)
        assert len(subscriptions) == 3
        assert await db.count_active_subscriptions(20) == 3

    asyncio.run(run())


def test_second_subscription_does_not_deactivate_first(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "multi2.db"))
        await db.init_db()
        await db.create_or_update_user(21, "u", name="Multi")
        first_id = await db.create_subscription(21, "random", None, "auto", "ru", 8, 0)
        second_id = await db.create_subscription(21, "money", None, "bright_nature_card", "ru", 18, 0)
        subscriptions = await db.get_active_subscriptions(21)
        assert {sub["id"] for sub in subscriptions} == {first_id, second_id}

    asyncio.run(run())


def test_fourth_subscription_is_blocked(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "multi3.db"))
        await db.init_db()
        await db.create_or_update_user(22, "u", name="Multi")
        for hour in (7, 12, 21):
            await db.create_subscription(22, "random", None, "auto", "ru", hour, 0)
        try:
            await db.create_subscription(22, "money", None, "auto", "ru", 22, 0)
        except ValueError as exc:
            assert str(exc) == "active_subscription_limit_reached"
        else:
            raise AssertionError("Expected active subscription limit to be enforced")

    asyncio.run(run())


def test_deactivate_subscription_deactivates_only_selected(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "multi4.db"))
        await db.init_db()
        await db.create_or_update_user(23, "u", name="Multi")
        first_id = await db.create_subscription(23, "random", None, "auto", "ru", 8, 0)
        second_id = await db.create_subscription(23, "money", None, "auto", "ru", 18, 0)
        await db.deactivate_subscription(23, first_id)
        subscriptions = await db.get_active_subscriptions(23)
        assert [sub["id"] for sub in subscriptions] == [second_id]

    asyncio.run(run())


def test_update_subscription_changes_only_selected_subscription(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "multi_update.db"))
        await db.init_db()
        await db.create_or_update_user(25, "u", name="Multi")
        first_id = await db.create_subscription(25, "random", None, "auto", "ru", 8, 0)
        second_id = await db.create_subscription(25, "money", None, "auto", "ru", 18, 0)
        updated = await db.update_subscription(
            subscription_id=second_id,
            user_id=25,
            sphere="money",
            subsphere=None,
            image_style="bright_photo_card",
            language="en",
            hour=19,
            minute=30,
            subscription_mode="sphere_focus",
            subscription_sphere="money",
            subscription_style_mode="bright_photo_card",
            visual_mode="photo",
        )
        assert updated is True
        first = await db.get_subscription_by_id(first_id, 25)
        second = await db.get_subscription_by_id(second_id, 25)
        assert first["hour"] == 8
        assert first["image_style"] == "auto"
        assert second["hour"] == 19
        assert second["minute"] == 30
        assert second["language"] == "en"
        assert second["visual_mode"] == "photo"

    asyncio.run(run())


def test_due_subscriptions_returns_multiple_for_same_user(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "due.db"))
        await db.init_db()
        await db.create_or_update_user(24, "u", name="Due")
        await db.create_subscription(24, "random", None, "auto", "ru", 9, 0)
        await db.create_subscription(24, "money", None, "auto", "ru", 9, 0)
        due = await db.get_due_subscriptions(dt.datetime(2030, 1, 1, 9, 0))
        assert len(due) == 2
        assert {sub["user_id"] for sub in due} == {24}

    asyncio.run(run())
