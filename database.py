import json
import logging
import os
import datetime as dt
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

from config import get_database_url, get_sqlite_db_path

try:
    import asyncpg
except ModuleNotFoundError:  # pragma: no cover - exercised only when dependency is absent
    asyncpg = None

logger = logging.getLogger(__name__)
MAX_ACTIVE_SUBSCRIPTIONS = 3

DB_PATH = get_sqlite_db_path()
_POSTGRES_PREFIXES = ("postgres://", "postgresql://")

_SQLITE_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id     INTEGER PRIMARY KEY,
        username    TEXT,
        name        TEXT,
        gender      TEXT,
        language    TEXT DEFAULT 'ru',
        created_at  TEXT
    )
    """,
    """
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
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS generation_limits (
        user_id   INTEGER PRIMARY KEY,
        day_utc   TEXT NOT NULL,
        count     INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS generation_history (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_user_id        INTEGER NOT NULL,
        created_at              TEXT NOT NULL,
        request_type            TEXT NOT NULL,
        focus_title             TEXT,
        theme_category          TEXT,
        affirmations_json       TEXT,
        soft_action             TEXT,
        text_model              TEXT,
        scene_model             TEXT,
        image_model             TEXT,
        image_prompt            TEXT,
        telegram_image_file_id  TEXT,
        status                  TEXT NOT NULL DEFAULT 'success',
        error_message           TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS visual_history (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        generation_id       INTEGER,
        telegram_user_id    INTEGER NOT NULL,
        created_at          TEXT NOT NULL,
        scene_type          TEXT,
        human_presence      TEXT,
        visual_motifs_json  TEXT,
        FOREIGN KEY (generation_id) REFERENCES generation_history(id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_generation_history_user_created_at
    ON generation_history(telegram_user_id, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_visual_history_user_created_at
    ON visual_history(telegram_user_id, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_visual_history_scene_type
    ON visual_history(scene_type)
    """,
]

_POSTGRES_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id     BIGINT PRIMARY KEY,
        username    TEXT,
        name        TEXT,
        gender      TEXT,
        language    TEXT DEFAULT 'ru',
        created_at  TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS subscriptions (
        id          BIGSERIAL PRIMARY KEY,
        user_id     BIGINT NOT NULL,
        sphere      TEXT NOT NULL,
        subsphere   TEXT,
        image_style TEXT NOT NULL,
        language    TEXT NOT NULL,
        hour        INTEGER NOT NULL,
        minute      INTEGER NOT NULL,
        is_active   INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS generation_limits (
        user_id   BIGINT PRIMARY KEY,
        day_utc   TEXT NOT NULL,
        count     INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS generation_history (
        id                      BIGSERIAL PRIMARY KEY,
        telegram_user_id        BIGINT NOT NULL,
        created_at              TEXT NOT NULL,
        request_type            TEXT NOT NULL,
        focus_title             TEXT,
        theme_category          TEXT,
        affirmations_json       TEXT,
        soft_action             TEXT,
        text_model              TEXT,
        scene_model             TEXT,
        image_model             TEXT,
        image_prompt            TEXT,
        telegram_image_file_id  TEXT,
        status                  TEXT NOT NULL DEFAULT 'success',
        error_message           TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS visual_history (
        id                  BIGSERIAL PRIMARY KEY,
        generation_id       BIGINT,
        telegram_user_id    BIGINT NOT NULL,
        created_at          TEXT NOT NULL,
        scene_type          TEXT,
        human_presence      TEXT,
        visual_motifs_json  TEXT,
        FOREIGN KEY (generation_id) REFERENCES generation_history(id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_generation_history_user_created_at
    ON generation_history(telegram_user_id, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_visual_history_user_created_at
    ON visual_history(telegram_user_id, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_visual_history_scene_type
    ON visual_history(scene_type)
    """,
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_json(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _deserialize_json(value: Optional[str]) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None


def _is_missing_table_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "no such table" in message or "relation" in message and "does not exist" in message


def _is_postgres_url(url: Optional[str]) -> bool:
    value = (url or "").strip().lower()
    return value.startswith(_POSTGRES_PREFIXES)


def get_database_backend_name() -> str:
    return "postgresql" if _is_postgres_url(get_database_url()) else "sqlite"


def _resolve_sqlite_db_path() -> str:
    override = os.getenv("SQLITE_DB_PATH", "").strip()
    if override:
        return override
    return DB_PATH


def _prepare_sqlite_db_path() -> str:
    path = _resolve_sqlite_db_path()
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    return path


def _convert_sql_placeholders_for_postgres(query: str) -> str:
    counter = 1
    parts: list[str] = []
    in_single_quote = False
    in_double_quote = False
    index = 0
    length = len(query)

    while index < length:
        ch = query[index]

        if ch == "'" and not in_double_quote:
            parts.append(ch)
            if in_single_quote and index + 1 < length and query[index + 1] == "'":
                parts.append(query[index + 1])
                index += 2
                continue
            in_single_quote = not in_single_quote
            index += 1
            continue

        if ch == '"' and not in_single_quote:
            parts.append(ch)
            if in_double_quote and index + 1 < length and query[index + 1] == '"':
                parts.append(query[index + 1])
                index += 2
                continue
            in_double_quote = not in_double_quote
            index += 1
            continue

        if ch == "?" and not in_single_quote and not in_double_quote:
            parts.append(f"${counter}")
            counter += 1
        else:
            parts.append(ch)
        index += 1

    return "".join(parts)


def _postgres_query(query: str) -> str:
    return _convert_sql_placeholders_for_postgres(query)


def _require_asyncpg() -> None:
    if asyncpg is None:
        raise RuntimeError("asyncpg is required for PostgreSQL backend but is not installed.")


async def _connect_postgres():
    _require_asyncpg()
    db_url = get_database_url()
    if not _is_postgres_url(db_url):
        raise RuntimeError("PostgreSQL backend requested, but DATABASE_URL is missing or invalid.")
    return await asyncpg.connect(db_url)


async def _fetchone(query: str, params: tuple[Any, ...] = ()) -> Any:
    if get_database_backend_name() == "postgresql":
        conn = await _connect_postgres()
        try:
            return await conn.fetchrow(_postgres_query(query), *params)
        finally:
            await conn.close()

    async with aiosqlite.connect(_prepare_sqlite_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(query, params)
        row = await cur.fetchone()
        await cur.close()
    return row


async def _fetchall(query: str, params: tuple[Any, ...] = ()) -> list[Any]:
    if get_database_backend_name() == "postgresql":
        conn = await _connect_postgres()
        try:
            return await conn.fetch(_postgres_query(query), *params)
        finally:
            await conn.close()

    async with aiosqlite.connect(_prepare_sqlite_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(query, params)
        rows = await cur.fetchall()
        await cur.close()
    return rows


async def _execute(query: str, params: tuple[Any, ...] = ()) -> str | None:
    if get_database_backend_name() == "postgresql":
        conn = await _connect_postgres()
        try:
            return await conn.execute(_postgres_query(query), *params)
        finally:
            await conn.close()

    async with aiosqlite.connect(_prepare_sqlite_db_path()) as db:
        await db.execute(query, params)
        await db.commit()
    return None


async def _execute_insert_returning_id(query: str, params: tuple[Any, ...] = (), *, id_column: str) -> int:
    if get_database_backend_name() == "postgresql":
        conn = await _connect_postgres()
        try:
            returning_query = f"{query.rstrip().rstrip(';')} RETURNING {id_column}"
            row = await conn.fetchrow(_postgres_query(returning_query), *params)
            if row is None:
                raise RuntimeError(f"Insert did not return {id_column}.")
            return int(row[id_column])
        finally:
            await conn.close()

    async with aiosqlite.connect(_prepare_sqlite_db_path()) as db:
        cur = await db.execute(query, params)
        inserted_id = int(cur.lastrowid)
        await cur.close()
        await db.commit()
    return inserted_id


async def add_column_if_missing(db: Any, table: str, column: str, definition: str) -> None:
    if get_database_backend_name() == "postgresql":
        query = """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1 AND column_name = $2
            LIMIT 1
        """
        exists = await db.fetchval(query, table, column)
        if not exists:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        return

    cur = await db.execute(f"PRAGMA table_info({table})")
    rows = await cur.fetchall()
    await cur.close()
    existing = {row[1] for row in rows}
    if column not in existing:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


async def init_db() -> None:
    """
    Инициализация схемы БД (если таблиц ещё нет).
    """
    if get_database_backend_name() == "postgresql":
        conn = await _connect_postgres()
        try:
            for statement in _POSTGRES_SCHEMA_STATEMENTS:
                await conn.execute(statement)
            await add_column_if_missing(conn, "subscriptions", "subscription_mode", "TEXT DEFAULT 'weekly_balance'")
            await add_column_if_missing(conn, "subscriptions", "subscription_sphere", "TEXT")
            await add_column_if_missing(conn, "subscriptions", "subscription_style_mode", "TEXT DEFAULT 'auto'")
            await add_column_if_missing(conn, "subscriptions", "visual_mode", "TEXT DEFAULT 'illustration'")
        finally:
            await conn.close()
        logger.info("Database initialized")
        return

    async with aiosqlite.connect(_prepare_sqlite_db_path()) as db:
        await db.executescript(";\n".join(statement.strip().rstrip(";") for statement in _SQLITE_SCHEMA_STATEMENTS) + ";")
        await add_column_if_missing(db, "subscriptions", "subscription_mode", "TEXT DEFAULT 'weekly_balance'")
        await add_column_if_missing(db, "subscriptions", "subscription_sphere", "TEXT")
        await add_column_if_missing(db, "subscriptions", "subscription_style_mode", "TEXT DEFAULT 'auto'")
        await add_column_if_missing(db, "subscriptions", "visual_mode", "TEXT DEFAULT 'illustration'")
        await db.commit()
    logger.info("Database initialized")


def _utc_today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


async def save_generation_history(
    telegram_user_id: int,
    request_type: str,
    focus_title: str | None = None,
    theme_category: str | None = None,
    affirmations: list[str] | None = None,
    soft_action: str | None = None,
    text_model: str | None = None,
    scene_model: str | None = None,
    image_model: str | None = None,
    image_prompt: str | None = None,
    telegram_image_file_id: str | None = None,
    status: str = "success",
    error_message: str | None = None,
) -> int:
    created_at = _utc_now_iso()
    affirmations_json = _serialize_json(affirmations)
    return await _execute_insert_returning_id(
        """
        INSERT INTO generation_history (
            telegram_user_id, created_at, request_type, focus_title, theme_category,
            affirmations_json, soft_action, text_model, scene_model, image_model,
            image_prompt, telegram_image_file_id, status, error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            telegram_user_id,
            created_at,
            request_type,
            focus_title,
            theme_category,
            affirmations_json,
            soft_action,
            text_model,
            scene_model,
            image_model,
            image_prompt,
            telegram_image_file_id,
            status,
            error_message,
        ),
        id_column="id",
    )


async def save_visual_history(
    telegram_user_id: int,
    generation_id: int | None = None,
    scene_type: str | None = None,
    human_presence: str | None = None,
    visual_motifs: dict | list | None = None,
) -> int:
    created_at = _utc_now_iso()
    visual_motifs_json = _serialize_json(visual_motifs)
    return await _execute_insert_returning_id(
        """
        INSERT INTO visual_history (
            generation_id, telegram_user_id, created_at, scene_type, human_presence, visual_motifs_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            generation_id,
            telegram_user_id,
            created_at,
            scene_type,
            human_presence,
            visual_motifs_json,
        ),
        id_column="id",
    )


async def get_recent_visual_history(telegram_user_id: int, limit: int = 10) -> list[dict]:
    try:
        rows = await _fetchall(
            """
            SELECT *
            FROM visual_history
            WHERE telegram_user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (telegram_user_id, limit),
        )
    except Exception as exc:
        if _is_missing_table_error(exc):
            logger.warning("visual_history table is missing; returning empty visual history.")
            return []
        raise
    history = []
    for row in rows:
        item = dict(row)
        item["visual_motifs"] = _deserialize_json(item.pop("visual_motifs_json", None))
        history.append(item)
    return history


async def get_recent_generation_history(telegram_user_id: int, limit: int = 10) -> list[dict]:
    try:
        rows = await _fetchall(
            """
            SELECT *
            FROM generation_history
            WHERE telegram_user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (telegram_user_id, limit),
        )
    except Exception as exc:
        if _is_missing_table_error(exc):
            logger.warning("generation_history table is missing; returning empty generation history.")
            return []
        raise
    history = []
    for row in rows:
        item = dict(row)
        affirmations = _deserialize_json(item.pop("affirmations_json", None))
        item["affirmations"] = affirmations if isinstance(affirmations, list) else None
        history.append(item)
    return history


async def get_generation_usage_today(user_id: int) -> int:
    today = _utc_today_iso()
    row = await _fetchone(
        "SELECT count FROM generation_limits WHERE user_id = ? AND day_utc = ?",
        (user_id, today),
    )
    return int(row[0]) if row else 0


async def can_start_interactive_generation(user_id: int, daily_limit: int) -> Tuple[bool, int]:
    if daily_limit <= 0:
        return True, 0
    used = await get_generation_usage_today(user_id)
    return used < daily_limit, used


async def record_interactive_generation(user_id: int) -> None:
    today = _utc_today_iso()
    query = """
        INSERT INTO generation_limits (user_id, day_utc, count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id) DO UPDATE SET
            day_utc = CASE
                WHEN generation_limits.day_utc = excluded.day_utc THEN generation_limits.day_utc
                ELSE excluded.day_utc
            END,
            count = CASE
                WHEN generation_limits.day_utc = excluded.day_utc THEN generation_limits.count + 1
                ELSE 1
            END
    """
    if get_database_backend_name() == "postgresql":
        conn = await _connect_postgres()
        try:
            async with conn.transaction():
                await conn.execute(_postgres_query(query), user_id, today)
        finally:
            await conn.close()
        return

    async with aiosqlite.connect(_prepare_sqlite_db_path()) as db:
        await db.execute(query, (user_id, today))
        await db.commit()


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    row = await _fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return dict(row) if row else None


async def create_or_update_user(
    user_id: int,
    username: Optional[str],
    name: Optional[str] = None,
    gender: Optional[str] = None,
    language: str = "ru",
) -> None:
    now = _utc_now_iso()
    await _execute(
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


async def update_user_profile(user_id: int, name: Optional[str] = None, gender: Optional[str] = None) -> None:
    if name is not None:
        await _execute("UPDATE users SET name = ? WHERE user_id = ?", (name, user_id))
    if gender is not None:
        await _execute("UPDATE users SET gender = ? WHERE user_id = ?", (gender, user_id))


async def update_user_language(user_id: int, language: str) -> None:
    await _execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))


async def get_subscription(user_id: int) -> Optional[Dict[str, Any]]:
    row = await _fetchone(
        "SELECT * FROM subscriptions WHERE user_id = ? AND is_active = 1 ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    return dict(row) if row else None


async def get_active_subscriptions(user_id: int) -> List[Dict[str, Any]]:
    rows = await _fetchall(
        "SELECT * FROM subscriptions WHERE user_id = ? AND is_active = 1 ORDER BY hour, minute, id",
        (user_id,),
    )
    return [dict(row) for row in rows]


async def count_active_subscriptions(user_id: int) -> int:
    row = await _fetchone(
        "SELECT COUNT(*) FROM subscriptions WHERE user_id = ? AND is_active = 1",
        (user_id,),
    )
    return int(row[0]) if row else 0


async def get_subscription_by_id(subscription_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    row = await _fetchone(
        "SELECT * FROM subscriptions WHERE id = ? AND user_id = ? AND is_active = 1",
        (subscription_id, user_id),
    )
    return dict(row) if row else None


async def create_subscription(
    user_id: int,
    sphere: str,
    subsphere: Optional[str],
    image_style: str,
    language: str,
    hour: int,
    minute: int,
    subscription_mode: str = "weekly_balance",
    subscription_sphere: Optional[str] = None,
    subscription_style_mode: str = "auto",
    visual_mode: str = "illustration",
) -> int:
    active_count = await count_active_subscriptions(user_id)
    if active_count >= MAX_ACTIVE_SUBSCRIPTIONS:
        raise ValueError("active_subscription_limit_reached")
    return await _execute_insert_returning_id(
        """
        INSERT INTO subscriptions (
            user_id, sphere, subsphere, image_style, language, hour, minute, is_active,
            subscription_mode, subscription_sphere, subscription_style_mode, visual_mode
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
        """,
        (
            user_id,
            sphere,
            subsphere,
            image_style,
            language,
            hour,
            minute,
            subscription_mode,
            subscription_sphere,
            subscription_style_mode,
            visual_mode,
        ),
        id_column="id",
    )


async def update_subscription(
    subscription_id: int,
    user_id: int,
    sphere: str,
    subsphere: Optional[str],
    image_style: str,
    language: str,
    hour: int,
    minute: int,
    subscription_mode: str = "weekly_balance",
    subscription_sphere: Optional[str] = None,
    subscription_style_mode: str = "auto",
    visual_mode: str = "illustration",
) -> bool:
    query = """
        UPDATE subscriptions
        SET sphere = ?, subsphere = ?, image_style = ?, language = ?, hour = ?, minute = ?,
            subscription_mode = ?, subscription_sphere = ?, subscription_style_mode = ?, visual_mode = ?
        WHERE id = ? AND user_id = ? AND is_active = 1
    """
    params = (
        sphere,
        subsphere,
        image_style,
        language,
        hour,
        minute,
        subscription_mode,
        subscription_sphere,
        subscription_style_mode,
        visual_mode,
        subscription_id,
        user_id,
    )

    if get_database_backend_name() == "postgresql":
        conn = await _connect_postgres()
        try:
            returning_query = f"{query.rstrip().rstrip(';')} RETURNING 1"
            row = await conn.fetchrow(_postgres_query(returning_query), *params)
            return row is not None
        finally:
            await conn.close()

    async with aiosqlite.connect(_prepare_sqlite_db_path()) as db:
        cur = await db.execute(query, params)
        changed = cur.rowcount > 0
        await cur.close()
        await db.commit()
    return changed


async def upsert_subscription(
    user_id: int,
    sphere: str,
    subsphere: Optional[str],
    image_style: str,
    language: str,
    hour: int,
    minute: int,
    subscription_mode: str = "weekly_balance",
    subscription_sphere: Optional[str] = None,
    subscription_style_mode: str = "auto",
    visual_mode: str = "illustration",
) -> int:
    return await create_subscription(
        user_id=user_id,
        sphere=sphere,
        subsphere=subsphere,
        image_style=image_style,
        language=language,
        hour=hour,
        minute=minute,
        subscription_mode=subscription_mode,
        subscription_sphere=subscription_sphere,
        subscription_style_mode=subscription_style_mode,
        visual_mode=visual_mode,
    )


async def deactivate_subscription(user_id: int, subscription_id: Optional[int] = None) -> None:
    if subscription_id is None:
        await _execute("UPDATE subscriptions SET is_active = 0 WHERE user_id = ?", (user_id,))
        return
    await _execute(
        "UPDATE subscriptions SET is_active = 0 WHERE id = ? AND user_id = ?",
        (subscription_id, user_id),
    )


async def get_due_subscriptions(now: dt.datetime) -> List[Dict[str, Any]]:
    hour = now.hour
    minute = now.minute
    rows = await _fetchall(
        """
        SELECT s.*, u.language AS user_language, u.gender AS user_gender, u.name AS user_name
        FROM subscriptions s
        JOIN users u ON u.user_id = s.user_id
        WHERE s.is_active = 1 AND s.hour = ? AND s.minute = ?
        """,
        (hour, minute),
    )
    return [dict(r) for r in rows]


async def delete_user_completely(user_id: int) -> None:
    if get_database_backend_name() == "postgresql":
        conn = await _connect_postgres()
        try:
            async with conn.transaction():
                await conn.execute(_postgres_query("DELETE FROM subscriptions WHERE user_id = ?"), user_id)
                await conn.execute(_postgres_query("DELETE FROM users WHERE user_id = ?"), user_id)
        finally:
            await conn.close()
        return

    async with aiosqlite.connect(_resolve_sqlite_db_path()) as db:
        await db.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()
