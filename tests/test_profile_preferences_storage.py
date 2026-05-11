import asyncio

import aiosqlite

import database as db


def test_init_db_adds_profile_preferences_column_for_sqlite(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "profile_prefs_schema.db"))
        await db.init_db()

        async with aiosqlite.connect(db.DB_PATH) as conn:
            cur = await conn.execute("PRAGMA table_info(users)")
            columns = {row[1] for row in await cur.fetchall()}
            await cur.close()

        assert "profile_preferences_json" in columns

    asyncio.run(run())


def test_default_profile_preferences_are_empty_dict(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "profile_prefs_default.db"))
        await db.init_db()
        await db.create_or_update_user(100, "user100", name="User")

        preferences = await db.get_user_profile_preferences(100)

        assert preferences == {}

    asyncio.run(run())


def test_update_and_read_profile_preferences(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "profile_prefs_update.db"))
        await db.init_db()
        await db.create_or_update_user(101, "user101", name="User")

        changed = await db.update_user_profile_preferences(
            101,
            {
                "tone_preference": "warm grounded",
                "support_style": "gentle",
                "favorite_visual_styles": ["cozy_home_photo", "book_nook_photo"],
            },
        )

        preferences = await db.get_user_profile_preferences(101)

        assert changed is True
        assert preferences == {
            "tone_preference": "warm grounded",
            "support_style": "gentle",
            "favorite_visual_styles": ["cozy_home_photo", "book_nook_photo"],
        }

    asyncio.run(run())


def test_merge_profile_preferences(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "profile_prefs_merge.db"))
        await db.init_db()
        await db.create_or_update_user(102, "user102", name="User")
        await db.update_user_profile_preferences(
            102,
            {
                "tone_preference": "soft",
                "avoid_topics": ["burnout"],
                "life_areas": ["work"],
            },
        )

        changed = await db.merge_user_profile_preferences(
            102,
            {
                "tone_preference": "calm clear",
                "avoid_topics": ["burnout", " guilt ", ""],
                "current_focus": "career reset",
            },
        )

        preferences = await db.get_user_profile_preferences(102)

        assert changed is True
        assert preferences == {
            "tone_preference": "calm clear",
            "avoid_topics": ["burnout", "guilt"],
            "life_areas": ["work"],
            "current_focus": "career reset",
        }

    asyncio.run(run())


def test_unknown_keys_are_ignored(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "profile_prefs_unknown.db"))
        await db.init_db()
        await db.create_or_update_user(103, "user103", name="User")

        await db.update_user_profile_preferences(
            103,
            {
                "tone_preference": "warm",
                "timezone": "Europe/Moscow",
                "daily_time": "09:00",
                "unknown_key": "value",
            },
        )

        preferences = await db.get_user_profile_preferences(103)

        assert preferences == {"tone_preference": "warm"}

    asyncio.run(run())


def test_corrupted_json_returns_empty_dict(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "profile_prefs_bad_json.db"))
        await db.init_db()
        await db.create_or_update_user(104, "user104", name="User")

        async with aiosqlite.connect(db.DB_PATH) as conn:
            await conn.execute(
                "UPDATE users SET profile_preferences_json = ? WHERE user_id = ?",
                ("{bad-json", 104),
            )
            await conn.commit()

        preferences = await db.get_user_profile_preferences(104)

        assert preferences == {}

    asyncio.run(run())


def test_list_normalization_and_empty_scalars(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "profile_prefs_normalize.db"))
        await db.init_db()
        await db.create_or_update_user(105, "user105", name="User")

        await db.update_user_profile_preferences(
            105,
            {
                "tone_preference": "   ",
                "avoid_words": [" страх ", "", "страх", " давление "],
                "favorite_visual_styles": "not-a-list",
                "life_areas": [" home ", None, "home", "career"],
            },
        )

        preferences = await db.get_user_profile_preferences(105)

        assert preferences == {
            "avoid_words": ["страх", "давление"],
            "life_areas": ["home", "career"],
        }

    asyncio.run(run())


def test_merge_can_remove_keys_with_empty_values(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "profile_prefs_remove.db"))
        await db.init_db()
        await db.create_or_update_user(106, "user106", name="User")
        await db.update_user_profile_preferences(
            106,
            {
                "current_focus": "rest",
                "avoid_words": ["pressure"],
            },
        )

        await db.merge_user_profile_preferences(
            106,
            {
                "current_focus": "",
                "avoid_words": [],
            },
        )

        preferences = await db.get_user_profile_preferences(106)

        assert preferences == {}

    asyncio.run(run())
