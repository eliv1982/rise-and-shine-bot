import os
import logging
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid int for %s=%r, using default=%s", name, raw, default)
        return default


def _get_env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return default


@dataclass
class Settings:
    bot_token: str
    generation_daily_limit: int
    disable_daily_generation_limit: bool
    smalltalk_daily_limit: int
    output_max_age_days: int
    llm_image_prompt_enabled: bool
    image_model: str
    image_size: str
    image_api_timeout_seconds: int
    show_image_debug: bool
    scene_planner_shadow_enabled: bool
    text_planner_shadow_enabled: bool
    scene_planner_image_prompt_enabled: bool
    text_planner_controlled_enabled: bool
    text_memory_context_enabled: bool
    text_reviewer_shadow_enabled: bool
    orchestrator_shadow_enabled: bool
    text_provider: str
    image_provider: str
    tts_provider: str
    stt_provider: str


@dataclass
class TextProviderConfig:
    provider: str
    base_url: str | None
    api_key: str
    model: str
    timeout_seconds: int


@dataclass
class ImageProviderConfig:
    provider: str
    base_url: str
    api_key: str
    model: str
    size: str
    timeout_seconds: int


@dataclass
class TtsProviderConfig:
    provider: str
    base_url: str | None
    api_key: str
    model: str
    voice: str
    timeout_seconds: int
    options: dict[str, str | int | float | bool | None]


@dataclass
class SttProviderConfig:
    provider: str
    base_url: str | None
    api_key: str
    model: str
    language: str
    timeout_seconds: int
    options: dict[str, str | int | float | bool | None]


def _get_env_var(name: str, required: bool = True, default: str | None = None) -> str | None:
    """
    Возвращает значение переменной окружения или поднимает ошибку, если её нет и она обязательна.
    """
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Environment variable {name} is required but not set.")
    if not value:
        logger.warning("Environment variable %s is not set, using default=%s", name, default)
    return value


def get_bot_data_dir() -> str:
    """Каталог для БД, логов и outputs (в Docker: BOT_DATA_DIR=/app/data)."""
    return os.getenv("BOT_DATA_DIR", "").strip()


def get_database_url() -> str | None:
    """PostgreSQL URL for production/beta; when absent, SQLite remains the default backend."""
    value = os.getenv("DATABASE_URL", "").strip()
    return value or None


def get_sqlite_db_path() -> str:
    """Local SQLite path override; falls back to BOT_DATA_DIR/bot.db or plain bot.db."""
    override = os.getenv("SQLITE_DB_PATH", "").strip()
    if override:
        return override
    d = get_bot_data_dir()
    return os.path.join(d, "bot.db") if d else "bot.db"


def get_scheduler_max_concurrency() -> int:
    """How many due subscriptions the scheduler processes at once (paid external APIs: keep low)."""
    return max(1, _get_env_int("SCHEDULER_MAX_CONCURRENCY", 3))


def get_outputs_dir() -> str:
    """Каталог для сгенерированных файлов (картинки, TTS)."""
    d = get_bot_data_dir()
    return os.path.join(d, "outputs") if d else "outputs"


def get_heartbeat_path() -> str:
    """File touched on every scheduler tick; Docker's HEALTHCHECK (scripts/healthcheck.py)
    checks its age as a cheap liveness signal that the event loop/scheduler isn't wedged."""
    d = get_bot_data_dir()
    return os.path.join(d, "heartbeat") if d else "heartbeat"


def get_text_provider_config() -> TextProviderConfig:
    """OpenAI is the only supported text provider; see docs/production_env.md."""
    return TextProviderConfig(
        provider="openai",
        base_url=_get_env_var("OPENAI_BASE_URL", required=False, default="https://api.openai.com/v1"),
        api_key=_get_env_var("OPENAI_API_KEY"),
        model=_get_env_var("OPENAI_TEXT_MODEL", required=False, default="gpt-4o-mini") or "gpt-4o-mini",
        timeout_seconds=_get_env_int("OPENAI_TEXT_TIMEOUT_SECONDS", 60),
    )


def get_image_provider_config() -> ImageProviderConfig:
    """OpenAI is the only supported image provider; see docs/production_env.md."""
    return ImageProviderConfig(
        provider="openai",
        base_url=_get_env_var("OPENAI_BASE_URL", required=False, default="https://api.openai.com/v1") or "https://api.openai.com/v1",
        api_key=_get_env_var("OPENAI_API_KEY"),
        model=_get_env_var("OPENAI_IMAGE_MODEL", required=False, default=os.getenv("IMAGE_MODEL", "gpt-image-1")) or "gpt-image-1",
        size=_get_env_var("OPENAI_IMAGE_SIZE", required=False, default=os.getenv("IMAGE_SIZE", "1024x1024")) or "1024x1024",
        timeout_seconds=_get_env_int("OPENAI_IMAGE_TIMEOUT_SECONDS", _get_env_int("IMAGE_API_TIMEOUT_SECONDS", 240)),
    )


def get_tts_provider_config() -> TtsProviderConfig:
    """OpenAI is the only supported TTS provider; see docs/production_env.md."""
    return TtsProviderConfig(
        provider="openai",
        base_url=_get_env_var("OPENAI_BASE_URL", required=False, default="https://api.openai.com/v1"),
        api_key=_get_env_var("OPENAI_API_KEY"),
        model=_get_env_var("OPENAI_TTS_MODEL", required=False, default="gpt-4o-mini-tts") or "gpt-4o-mini-tts",
        voice=_get_env_var("OPENAI_TTS_VOICE", required=False, default="alloy") or "alloy",
        timeout_seconds=_get_env_int("OPENAI_TTS_TIMEOUT_SECONDS", 240),
        options={"response_format": "opus"},
    )


def get_stt_provider_config() -> SttProviderConfig:
    """OpenAI is the only supported STT provider; see docs/production_env.md."""
    return SttProviderConfig(
        provider="openai",
        base_url=_get_env_var("OPENAI_BASE_URL", required=False, default="https://api.openai.com/v1"),
        api_key=_get_env_var("OPENAI_API_KEY"),
        model=_get_env_var("OPENAI_STT_MODEL", required=False, default="gpt-4o-mini-transcribe") or "gpt-4o-mini-transcribe",
        language=_get_env_var("OPENAI_STT_LANGUAGE", required=False, default="") or "",
        timeout_seconds=_get_env_int("OPENAI_STT_TIMEOUT_SECONDS", 120),
        options={
            "allow_cross_language_stt_fallback": _get_env_bool("ALLOW_CROSS_LANGUAGE_STT_FALLBACK", False),
        },
    )


def get_settings() -> Settings:
    """
    Централизованная загрузка и валидация конфигурации.
    """
    daily_limit = _get_env_int("DAILY_GENERATION_LIMIT", _get_env_int("GENERATION_DAILY_LIMIT", 5))
    image_cfg = get_image_provider_config()
    text_cfg = get_text_provider_config()
    tts_cfg = get_tts_provider_config()
    stt_cfg = get_stt_provider_config()
    return Settings(
        bot_token=_get_env_var("BOT_TOKEN"),
        generation_daily_limit=daily_limit,
        disable_daily_generation_limit=_get_env_bool("DISABLE_DAILY_GENERATION_LIMIT", False),
        smalltalk_daily_limit=_get_env_int("SMALLTALK_DAILY_LIMIT", 20),
        output_max_age_days=_get_env_int("OUTPUT_MAX_AGE_DAYS", 7),
        llm_image_prompt_enabled=_get_env_bool("LLM_IMAGE_PROMPT_ENABLED", True),
        image_model=image_cfg.model,
        image_size=image_cfg.size,
        image_api_timeout_seconds=image_cfg.timeout_seconds,
        show_image_debug=_get_env_bool("SHOW_IMAGE_DEBUG", False),
        scene_planner_shadow_enabled=_get_env_bool("SCENE_PLANNER_SHADOW_ENABLED", False),
        text_planner_shadow_enabled=_get_env_bool("TEXT_PLANNER_SHADOW_ENABLED", False),
        scene_planner_image_prompt_enabled=_get_env_bool("SCENE_PLANNER_IMAGE_PROMPT_ENABLED", False),
        text_planner_controlled_enabled=_get_env_bool("TEXT_PLANNER_CONTROLLED_ENABLED", False),
        text_memory_context_enabled=_get_env_bool("TEXT_MEMORY_CONTEXT_ENABLED", False),
        text_reviewer_shadow_enabled=_get_env_bool("TEXT_REVIEWER_SHADOW_ENABLED", False),
        orchestrator_shadow_enabled=_get_env_bool("ORCHESTRATOR_SHADOW_ENABLED", False),
        text_provider=text_cfg.provider,
        image_provider=image_cfg.provider,
        tts_provider=tts_cfg.provider,
        stt_provider=stt_cfg.provider,
    )

