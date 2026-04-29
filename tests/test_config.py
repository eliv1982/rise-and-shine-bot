from pathlib import Path

from config import (
    get_image_provider_config,
    get_settings,
    get_stt_provider_config,
    get_text_provider_config,
    get_tts_provider_config,
)


def _set_required_env(monkeypatch):
    monkeypatch.setenv("YANDEX_API_KEY", "test")
    monkeypatch.setenv("YANDEX_FOLDER_ID", "test")
    monkeypatch.setenv("PROXI_API_KEY", "test")
    monkeypatch.setenv("BOT_TOKEN", "test")


def test_daily_generation_limit_defaults_to_five(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.delenv("DAILY_GENERATION_LIMIT", raising=False)
    monkeypatch.delenv("GENERATION_DAILY_LIMIT", raising=False)
    monkeypatch.delenv("DISABLE_DAILY_GENERATION_LIMIT", raising=False)
    monkeypatch.delenv("SHOW_IMAGE_DEBUG", raising=False)

    settings = get_settings()

    assert settings.generation_daily_limit == 5
    assert settings.disable_daily_generation_limit is False
    assert settings.show_image_debug is False


def test_daily_generation_limit_zero_means_no_limit(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("DAILY_GENERATION_LIMIT", "0")

    settings = get_settings()

    assert settings.generation_daily_limit == 0


def test_disable_daily_generation_limit_env(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("DAILY_GENERATION_LIMIT", "5")
    monkeypatch.setenv("DISABLE_DAILY_GENERATION_LIMIT", "true")

    settings = get_settings()

    assert settings.generation_daily_limit == 5
    assert settings.disable_daily_generation_limit is True


def test_show_image_debug_env(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("SHOW_IMAGE_DEBUG", "true")

    settings = get_settings()

    assert settings.show_image_debug is True


def test_capability_provider_defaults_are_backward_compatible(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.delenv("TEXT_PROVIDER", raising=False)
    monkeypatch.delenv("IMAGE_PROVIDER", raising=False)
    monkeypatch.delenv("TTS_PROVIDER", raising=False)

    settings = get_settings()
    text_cfg = get_text_provider_config()
    image_cfg = get_image_provider_config()
    tts_cfg = get_tts_provider_config()

    assert settings.text_provider == "yandex"
    assert settings.image_provider == "proxiapi"
    assert settings.tts_provider == "yandex"
    assert text_cfg.provider == "yandex"
    assert image_cfg.provider == "proxiapi"
    assert tts_cfg.provider == "yandex"
    assert get_stt_provider_config().provider == "yandex"


def test_foreign_server_profile_uses_openai_for_all_capabilities(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "test")
    monkeypatch.setenv("TEXT_PROVIDER", "openai")
    monkeypatch.setenv("IMAGE_PROVIDER", "openai")
    monkeypatch.setenv("TTS_PROVIDER", "openai")
    monkeypatch.setenv("STT_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
    monkeypatch.setenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    monkeypatch.delenv("YANDEX_API_KEY", raising=False)
    monkeypatch.delenv("YANDEX_FOLDER_ID", raising=False)
    monkeypatch.delenv("PROXI_API_KEY", raising=False)

    settings = get_settings()
    assert settings.text_provider == "openai"
    assert settings.image_provider == "openai"
    assert settings.tts_provider == "openai"
    assert get_text_provider_config().provider == "openai"
    assert get_image_provider_config().provider == "openai"
    assert get_tts_provider_config().provider == "openai"
    assert settings.stt_provider == "openai"
    assert get_stt_provider_config().provider == "openai"


def test_russian_server_profile_uses_proxiapi_and_yandex(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("TEXT_PROVIDER", "proxiapi")
    monkeypatch.setenv("IMAGE_PROVIDER", "proxiapi")
    monkeypatch.setenv("TTS_PROVIDER", "yandex")
    monkeypatch.setenv("STT_PROVIDER", "yandex")
    monkeypatch.setenv("PROXI_TEXT_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("PROXI_IMAGE_MODEL", "gpt-image-1")
    monkeypatch.setenv("YANDEX_TTS_MODEL", "general")

    settings = get_settings()
    assert settings.text_provider == "proxiapi"
    assert settings.image_provider == "proxiapi"
    assert settings.tts_provider == "yandex"
    assert settings.stt_provider == "yandex"
    assert get_text_provider_config().provider == "proxiapi"
    assert get_image_provider_config().provider == "proxiapi"
    assert get_tts_provider_config().provider == "yandex"
    assert get_stt_provider_config().provider == "yandex"


def test_stt_provider_yandex_config(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("STT_PROVIDER", "yandex")
    monkeypatch.setenv("YANDEX_STT_MODEL", "general")
    monkeypatch.setenv("YANDEX_STT_LANGUAGE", "ru-RU")
    monkeypatch.setenv("YANDEX_STT_TIMEOUT_SECONDS", "120")

    cfg = get_stt_provider_config()
    assert cfg.provider == "yandex"
    assert cfg.model == "general"
    assert cfg.language == "ru-RU"
    assert cfg.timeout_seconds == 120


def test_stt_provider_openai_config(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("STT_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test")
    monkeypatch.setenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
    monkeypatch.setenv("OPENAI_STT_LANGUAGE", "en")
    monkeypatch.setenv("OPENAI_STT_TIMEOUT_SECONDS", "120")

    cfg = get_stt_provider_config()
    assert cfg.provider == "openai"
    assert cfg.model == "gpt-4o-mini-transcribe"
    assert cfg.language == "en"
    assert cfg.timeout_seconds == 120


def test_stt_provider_openai_requires_api_key(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("STT_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    try:
        get_stt_provider_config()
        assert False, "Expected RuntimeError for missing OPENAI_API_KEY"
    except RuntimeError as exc:
        assert "OPENAI_API_KEY" in str(exc)


def test_deployment_profile_examples_include_stt_provider():
    root = Path(__file__).resolve().parents[1]
    ru_profile = (root / ".env.russian.example").read_text(encoding="utf-8")
    foreign_profile = (root / ".env.foreign.example").read_text(encoding="utf-8")
    assert "STT_PROVIDER=yandex" in ru_profile
    assert "TEXT_PROVIDER=yandex" in ru_profile
    assert "IMAGE_PROVIDER=proxiapi" in ru_profile
    assert "TTS_PROVIDER=yandex" in ru_profile
    assert "STT_PROVIDER=openai" in foreign_profile
    assert "TEXT_PROVIDER=openai" in foreign_profile
    assert "IMAGE_PROVIDER=openai" in foreign_profile
    assert "TTS_PROVIDER=openai" in foreign_profile
