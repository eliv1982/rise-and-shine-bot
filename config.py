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
    yandex_api_key: str
    yandex_folder_id: str
    yandex_speechkit_api_key: str
    proxi_api_key: str
    proxi_base_url: str
    bot_token: str
    generation_daily_limit: int
    output_max_age_days: int
    llm_image_prompt_enabled: bool
    image_model: str
    image_size: str
    image_api_timeout_seconds: int
    yandex_completion_model: str


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


def get_outputs_dir() -> str:
    """Каталог для сгенерированных файлов (картинки, TTS)."""
    d = get_bot_data_dir()
    return os.path.join(d, "outputs") if d else "outputs"


def get_settings() -> Settings:
    """
    Централизованная загрузка и валидация конфигурации.
    """
    return Settings(
        yandex_api_key=_get_env_var("YANDEX_API_KEY"),
        yandex_folder_id=_get_env_var("YANDEX_FOLDER_ID"),
        yandex_speechkit_api_key=_get_env_var("YANDEX_SPEECHKIT_API_KEY", required=False, default=os.getenv("YANDEX_API_KEY")),
        proxi_api_key=_get_env_var("PROXI_API_KEY"),
        proxi_base_url=_get_env_var("PROXI_BASE_URL", required=False, default="https://api.proxyapi.ru/openai/v1"),
        bot_token=_get_env_var("BOT_TOKEN"),
        generation_daily_limit=_get_env_int("GENERATION_DAILY_LIMIT", 5),
        output_max_age_days=_get_env_int("OUTPUT_MAX_AGE_DAYS", 7),
        llm_image_prompt_enabled=_get_env_bool("LLM_IMAGE_PROMPT_ENABLED", True),
        image_model=_get_env_var("IMAGE_MODEL", required=False, default="gpt-image-1-mini") or "gpt-image-1-mini",
        image_size=_get_env_var("IMAGE_SIZE", required=False, default="1024x1024") or "1024x1024",
        image_api_timeout_seconds=_get_env_int("IMAGE_API_TIMEOUT_SECONDS", 240),
        yandex_completion_model=_get_env_var("YANDEX_COMPLETION_MODEL", required=False, default="yandexgpt-lite/latest") or "yandexgpt-lite/latest",
    )

