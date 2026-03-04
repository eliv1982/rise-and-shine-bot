import os
import datetime as dt
import logging
from typing import Any, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)

# В Docker задают BOT_DATA_DIR (например /app/data) — тогда БД там
_data_dir = os.getenv("BOT_DATA_DIR", "").strip()
DB_PATH = os.path.join(_data_dir, "bot.db") if _data_dir else "bot.db"


async def init_db() -> None:
    """
    Инициализация схемы БД (если таблиц ещё нет).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                name        TEXT,
                gender      TEXT,
                language    TEXT DEFAULT 'ru',
                created_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                sphere      TEXT NOT NULL,
                subsphere   TEXT,
                image_style TEXT NOT NULL,
                language    TEXT NOT NULL,
                hour        INTEGER NOT NULL,
                minute      INTEGER NOT NULL,
                is_active   INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            );
            """
        )
        await db.commit()
    logger.info("Database initialized")


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        await cur.close()
    return dict(row) if row else None


async def create_or_update_user(
    user_id: int,
    username: Optional[str],
    name: Optional[str] = None,
    gender: Optional[str] = None,
    language: str = "ru",
) -> None:
    """
    Обновляет или создаёт пользователя.
    """
    now = dt.datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, name, gender, language, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                name=COALESCE(excluded.name, users.name),
                gender=COALESCE(excluded.gender, users.gender),
                language=COALESCE(excluded.language, users.language)
            """,
            (user_id, username, name, gender, language, now),
        )
        await db.commit()


async def update_user_profile(user_id: int, name: Optional[str] = None, gender: Optional[str] = None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        if name is not None:
            await db.execute("UPDATE users SET name = ? WHERE user_id = ?", (name, user_id))
        if gender is not None:
            await db.execute("UPDATE users SET gender = ? WHERE user_id = ?", (gender, user_id))
        await db.commit()


async def update_user_language(user_id: int, language: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))
        await db.commit()


async def get_subscription(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM subscriptions WHERE user_id = ? AND is_active = 1 ORDER BY id DESC LIMIT 1", (user_id,)
        )
        row = await cur.fetchone()
        await cur.close()
    return dict(row) if row else None


async def upsert_subscription(
    user_id: int,
    sphere: str,
    subsphere: Optional[str],
    image_style: str,
    language: str,
    hour: int,
    minute: int,
) -> None:
    """
    Создаёт новую активную подписку и деактивирует старые.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE subscriptions SET is_active = 0 WHERE user_id = ?", (user_id,))
        await db.execute(
            """
            INSERT INTO subscriptions (user_id, sphere, subsphere, image_style, language, hour, minute, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (user_id, sphere, subsphere, image_style, language, hour, minute),
        )
        await db.commit()


async def deactivate_subscription(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE subscriptions SET is_active = 0 WHERE user_id = ?", (user_id,))
        await db.commit()


async def get_due_subscriptions(now: dt.datetime) -> List[Dict[str, Any]]:
    """
    Возвращает подписки, которым пора отправить рассылку.
    """
    hour = now.hour
    minute = now.minute
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT s.*, u.language AS user_language, u.gender AS user_gender, u.name AS user_name
            FROM subscriptions s
            JOIN users u ON u.user_id = s.user_id
            WHERE s.is_active = 1 AND s.hour = ? AND s.minute = ?
            """,
            (hour, minute),
        )
        rows = await cur.fetchall()
        await cur.close()
    return [dict(r) for r in rows]


async def delete_user_completely(user_id: int) -> None:
    """
    Полностью удаляет пользователя и все его подписки.
    Удобно для повторной регистрации.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()

