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
    disable_daily_generation_limit: bool
    output_max_age_days: int
    llm_image_prompt_enabled: bool
    image_model: str
    image_size: str
    image_api_timeout_seconds: int
    show_image_debug: bool
    yandex_completion_model: str
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
    options: dict[str, str | int | float | bool | None]


@dataclass
class ImageProviderConfig:
    provider: str
    base_url: str
    api_key: str
    model: str
    size: str
    timeout_seconds: int
    options: dict[str, str | int | float | bool | None]


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


def get_outputs_dir() -> str:
    """Каталог для сгенерированных файлов (картинки, TTS)."""
    d = get_bot_data_dir()
    return os.path.join(d, "outputs") if d else "outputs"


def _normalize_provider(raw_value: str, *, allowed: tuple[str, ...], default: str, env_name: str) -> str:
    value = (raw_value or "").strip().lower()
    if not value:
        return default
    if value in allowed:
        return value
    logger.warning("Unsupported provider %s=%r, using default=%s", env_name, raw_value, default)
    return default


def _get_text_provider_name() -> str:
    # Backward compatible: text historically lived on Yandex.
    return _normalize_provider(
        os.getenv("TEXT_PROVIDER", ""),
        allowed=("proxiapi", "openai", "yandex"),
        default="yandex",
        env_name="TEXT_PROVIDER",
    )


def _get_image_provider_name() -> str:
    # Backward compatible: image historically used ProxiAPI OpenAI-compatible endpoint.
    return _normalize_provider(
        os.getenv("IMAGE_PROVIDER", ""),
        allowed=("proxiapi", "openai"),
        default="proxiapi",
        env_name="IMAGE_PROVIDER",
    )


def _get_tts_provider_name() -> str:
    # Backward compatible: TTS historically used Yandex SpeechKit.
    return _normalize_provider(
        os.getenv("TTS_PROVIDER", ""),
        allowed=("yandex", "openai"),
        default="yandex",
        env_name="TTS_PROVIDER",
    )


def _get_stt_provider_name() -> str:
    # Backward compatible: STT historically used Yandex SpeechKit.
    return _normalize_provider(
        os.getenv("STT_PROVIDER", ""),
        allowed=("yandex", "openai"),
        default="yandex",
        env_name="STT_PROVIDER",
    )


def get_text_provider_config() -> TextProviderConfig:
    provider = _get_text_provider_name()
    if provider == "yandex":
        return TextProviderConfig(
            provider=provider,
            base_url=None,
            api_key=_get_env_var("YANDEX_API_KEY"),
            model=_get_env_var("YANDEX_TEXT_MODEL", required=False, default=os.getenv("YANDEX_COMPLETION_MODEL", "yandexgpt-lite/latest"))
            or "yandexgpt-lite/latest",
            timeout_seconds=_get_env_int("YANDEX_TEXT_TIMEOUT_SECONDS", 60),
            options={"folder_id": _get_env_var("YANDEX_FOLDER_ID")},
        )
    if provider == "proxiapi":
        return TextProviderConfig(
            provider=provider,
            base_url=_get_env_var("PROXI_BASE_URL", required=False, default="https://api.proxyapi.ru/openai/v1"),
            api_key=_get_env_var("PROXI_API_KEY"),
            model=_get_env_var("PROXI_TEXT_MODEL", required=False, default="gpt-4o-mini") or "gpt-4o-mini",
            timeout_seconds=_get_env_int("PROXI_TEXT_TIMEOUT_SECONDS", 60),
            options={},
        )
    return TextProviderConfig(
        provider=provider,
        base_url=_get_env_var("OPENAI_BASE_URL", required=False, default="https://api.openai.com/v1"),
        api_key=_get_env_var("OPENAI_API_KEY"),
        model=_get_env_var("OPENAI_TEXT_MODEL", required=False, default="gpt-4o-mini") or "gpt-4o-mini",
        timeout_seconds=_get_env_int("OPENAI_TEXT_TIMEOUT_SECONDS", 60),
        options={},
    )


def get_image_provider_config() -> ImageProviderConfig:
    provider = _get_image_provider_name()
    if provider == "proxiapi":
        return ImageProviderConfig(
            provider=provider,
            base_url=_get_env_var("PROXI_BASE_URL", required=False, default="https://api.proxyapi.ru/openai/v1") or "https://api.proxyapi.ru/openai/v1",
            api_key=_get_env_var("PROXI_API_KEY"),
            model=_get_env_var("PROXI_IMAGE_MODEL", required=False, default=os.getenv("IMAGE_MODEL", "gpt-image-1")) or "gpt-image-1",
            size=_get_env_var("PROXI_IMAGE_SIZE", required=False, default=os.getenv("IMAGE_SIZE", "1024x1024")) or "1024x1024",
            timeout_seconds=_get_env_int("PROXI_IMAGE_TIMEOUT_SECONDS", _get_env_int("IMAGE_API_TIMEOUT_SECONDS", 240)),
            options={},
        )
    return ImageProviderConfig(
        provider=provider,
        base_url=_get_env_var("OPENAI_BASE_URL", required=False, default="https://api.openai.com/v1") or "https://api.openai.com/v1",
        api_key=_get_env_var("OPENAI_API_KEY"),
        model=_get_env_var("OPENAI_IMAGE_MODEL", required=False, default=os.getenv("IMAGE_MODEL", "gpt-image-1")) or "gpt-image-1",
        size=_get_env_var("OPENAI_IMAGE_SIZE", required=False, default=os.getenv("IMAGE_SIZE", "1024x1024")) or "1024x1024",
        timeout_seconds=_get_env_int("OPENAI_IMAGE_TIMEOUT_SECONDS", _get_env_int("IMAGE_API_TIMEOUT_SECONDS", 240)),
        options={},
    )


def get_tts_provider_config() -> TtsProviderConfig:
    provider = _get_tts_provider_name()
    if provider == "yandex":
        return TtsProviderConfig(
            provider=provider,
            base_url=None,
            api_key=_get_env_var("YANDEX_SPEECHKIT_API_KEY", required=False, default=os.getenv("YANDEX_API_KEY"))
            or "",
            model=_get_env_var("YANDEX_TTS_MODEL", required=False, default="general") or "general",
            voice=_get_env_var("YANDEX_TTS_VOICE", required=False, default="") or "",
            timeout_seconds=_get_env_int("YANDEX_TTS_TIMEOUT_SECONDS", 60),
            options={"folder_id": _get_env_var("YANDEX_FOLDER_ID")},
        )
    return TtsProviderConfig(
        provider=provider,
        base_url=_get_env_var("OPENAI_BASE_URL", required=False, default="https://api.openai.com/v1"),
        api_key=_get_env_var("OPENAI_API_KEY"),
        model=_get_env_var("OPENAI_TTS_MODEL", required=False, default="gpt-4o-mini-tts") or "gpt-4o-mini-tts",
        voice=_get_env_var("OPENAI_TTS_VOICE", required=False, default="alloy") or "alloy",
        timeout_seconds=_get_env_int("OPENAI_TTS_TIMEOUT_SECONDS", 240),
        options={"response_format": "opus"},
    )


def get_stt_provider_config() -> SttProviderConfig:
    provider = _get_stt_provider_name()
    if provider == "yandex":
        return SttProviderConfig(
            provider=provider,
            base_url=None,
            api_key=_get_env_var("YANDEX_SPEECHKIT_API_KEY", required=False, default=os.getenv("YANDEX_API_KEY")) or "",
            model=_get_env_var("YANDEX_STT_MODEL", required=False, default="general") or "general",
            language=_get_env_var("YANDEX_STT_LANGUAGE", required=False, default="ru-RU") or "ru-RU",
            timeout_seconds=_get_env_int("YANDEX_STT_TIMEOUT_SECONDS", 120),
            options={"folder_id": _get_env_var("YANDEX_FOLDER_ID", required=False, default="") or ""},
        )
    return SttProviderConfig(
        provider=provider,
        base_url=_get_env_var("OPENAI_BASE_URL", required=False, default="https://api.openai.com/v1"),
        api_key=_get_env_var("OPENAI_API_KEY"),
        model=_get_env_var("OPENAI_STT_MODEL", required=False, default="gpt-4o-mini-transcribe") or "gpt-4o-mini-transcribe",
        language=_get_env_var("OPENAI_STT_LANGUAGE", required=False, default="") or "",
        timeout_seconds=_get_env_int("OPENAI_STT_TIMEOUT_SECONDS", 120),
        options={},
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
        yandex_api_key=_get_env_var("YANDEX_API_KEY", required=False, default="") or "",
        yandex_folder_id=_get_env_var("YANDEX_FOLDER_ID", required=False, default="") or "",
        yandex_speechkit_api_key=_get_env_var("YANDEX_SPEECHKIT_API_KEY", required=False, default=os.getenv("YANDEX_API_KEY", "")) or "",
        proxi_api_key=_get_env_var("PROXI_API_KEY", required=False, default="") or "",
        proxi_base_url=_get_env_var("PROXI_BASE_URL", required=False, default="https://api.proxyapi.ru/openai/v1"),
        bot_token=_get_env_var("BOT_TOKEN"),
        generation_daily_limit=daily_limit,
        disable_daily_generation_limit=_get_env_bool("DISABLE_DAILY_GENERATION_LIMIT", False),
        output_max_age_days=_get_env_int("OUTPUT_MAX_AGE_DAYS", 7),
        llm_image_prompt_enabled=_get_env_bool("LLM_IMAGE_PROMPT_ENABLED", True),
        image_model=image_cfg.model,
        image_size=image_cfg.size,
        image_api_timeout_seconds=image_cfg.timeout_seconds,
        show_image_debug=_get_env_bool("SHOW_IMAGE_DEBUG", False),
        yandex_completion_model=text_cfg.model if text_cfg.provider == "yandex" else (_get_env_var("YANDEX_COMPLETION_MODEL", required=False, default="yandexgpt-lite/latest") or "yandexgpt-lite/latest"),
        text_provider=text_cfg.provider,
        image_provider=image_cfg.provider,
        tts_provider=tts_cfg.provider,
        stt_provider=stt_cfg.provider,
    )

