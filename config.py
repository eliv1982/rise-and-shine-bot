import os
import logging
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    yandex_api_key: str
    yandex_folder_id: str
    yandex_speechkit_api_key: str
    proxi_api_key: str
    proxi_base_url: str
    bot_token: str


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
    )

