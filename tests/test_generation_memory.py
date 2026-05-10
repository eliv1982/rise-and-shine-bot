import asyncio

import aiosqlite

import database as db


def test_init_db_creates_generation_memory_tables(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "memory.db"))
        await db.init_db()

        async with aiosqlite.connect(db.DB_PATH) as conn:
            cur = await conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name IN ('generation_history', 'visual_history')
                ORDER BY name
                """
            )
            tables = [row[0] for row in await cur.fetchall()]
            await cur.close()

        assert tables == ["generation_history", "visual_history"]

    asyncio.run(run())


def test_save_and_get_recent_generation_history(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "generation_history.db"))
        await db.init_db()

        first_id = await db.save_generation_history(
            telegram_user_id=100,
            request_type="interactive",
            focus_title="Morning clarity",
            theme_category="inner_peace",
            affirmations=["I breathe", "I focus"],
            soft_action="Take one quiet minute",
            text_model="yandexgpt-lite/latest",
            scene_model="scene-planner-v1",
            image_model="gpt-image-1",
            image_prompt="bright morning lake",
            telegram_image_file_id="file-1",
        )
        second_id = await db.save_generation_history(
            telegram_user_id=100,
            request_type="subscription",
            focus_title="Steady energy",
            affirmations=["I move gently"],
            status="error",
            error_message="temporary timeout",
        )

        assert isinstance(first_id, int)
        assert isinstance(second_id, int)

        history = await db.get_recent_generation_history(100)
        assert [item["id"] for item in history] == [second_id, first_id]
        assert history[0]["focus_title"] == "Steady energy"
        assert history[0]["affirmations"] == ["I move gently"]
        assert history[0]["status"] == "error"
        assert history[1]["focus_title"] == "Morning clarity"
        assert history[1]["theme_category"] == "inner_peace"
        assert history[1]["affirmations"] == ["I breathe", "I focus"]
        assert history[1]["soft_action"] == "Take one quiet minute"
        assert history[1]["text_model"] == "yandexgpt-lite/latest"
        assert history[1]["scene_model"] == "scene-planner-v1"
        assert history[1]["image_model"] == "gpt-image-1"
        assert history[1]["telegram_image_file_id"] == "file-1"

    asyncio.run(run())


def test_get_recent_generation_history_handles_invalid_json(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "generation_history_bad_json.db"))
        await db.init_db()

        async with aiosqlite.connect(db.DB_PATH) as conn:
            await conn.execute(
                """
                INSERT INTO generation_history (
                    telegram_user_id, created_at, request_type, affirmations_json, status
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (55, "2030-01-01T00:00:00+00:00", "interactive", "{bad-json", "success"),
            )
            await conn.commit()

        history = await db.get_recent_generation_history(55)
        assert len(history) == 1
        assert history[0]["affirmations"] is None

    asyncio.run(run())


def test_save_and_get_recent_visual_history(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "visual_history.db"))
        await db.init_db()

        generation_id = await db.save_generation_history(
            telegram_user_id=200,
            request_type="interactive",
            focus_title="Calm order",
        )
        first_id = await db.save_visual_history(
            telegram_user_id=200,
            generation_id=generation_id,
            scene_type="window_still_life",
            human_presence="none",
            visual_motifs={"objects": ["cup", "plant"]},
        )
        second_id = await db.save_visual_history(
            telegram_user_id=200,
            scene_type="coastal_path",
            human_presence="distant",
            visual_motifs=["shore", "sea", "clouds"],
        )

        assert isinstance(first_id, int)
        assert isinstance(second_id, int)

        history = await db.get_recent_visual_history(200)
        assert [item["id"] for item in history] == [second_id, first_id]
        assert history[0]["scene_type"] == "coastal_path"
        assert history[0]["visual_motifs"] == ["shore", "sea", "clouds"]
        assert history[1]["generation_id"] == generation_id
        assert history[1]["human_presence"] == "none"
        assert history[1]["visual_motifs"] == {"objects": ["cup", "plant"]}

    asyncio.run(run())


def test_get_recent_visual_history_handles_invalid_json(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "visual_history_bad_json.db"))
        await db.init_db()

        async with aiosqlite.connect(db.DB_PATH) as conn:
            await conn.execute(
                """
                INSERT INTO visual_history (
                    telegram_user_id, created_at, scene_type, visual_motifs_json
                )
                VALUES (?, ?, ?, ?)
                """,
                (77, "2030-01-01T00:00:00+00:00", "botanical_corner", "{bad-json"),
            )
            await conn.commit()

        history = await db.get_recent_visual_history(77)
        assert len(history) == 1
        assert history[0]["visual_motifs"] is None

    asyncio.run(run())
