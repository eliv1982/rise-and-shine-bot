from pathlib import Path

from config import (
    get_database_url,
    get_image_provider_config,
    get_settings,
    get_sqlite_db_path,
    get_stt_provider_config,
    get_text_provider_config,
    get_tts_provider_config,
)


def _set_required_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
    monkeypatch.setenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    monkeypatch.setenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
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


def test_database_url_defaults_to_none(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert get_database_url() is None


def test_database_url_reads_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/rise")

    assert get_database_url() == "postgresql://user:pass@localhost:5432/rise"


def test_sqlite_db_path_defaults_to_bot_db(monkeypatch):
    monkeypatch.delenv("SQLITE_DB_PATH", raising=False)
    monkeypatch.delenv("BOT_DATA_DIR", raising=False)

    assert get_sqlite_db_path() == "bot.db"


def test_sqlite_db_path_respects_override(monkeypatch):
    monkeypatch.setenv("SQLITE_DB_PATH", "data/local-dev.db")

    assert get_sqlite_db_path() == "data/local-dev.db"


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


def test_scene_planner_shadow_disabled_by_default(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.delenv("SCENE_PLANNER_SHADOW_ENABLED", raising=False)

    settings = get_settings()

    assert settings.scene_planner_shadow_enabled is False


def test_scene_planner_shadow_enabled_env(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("SCENE_PLANNER_SHADOW_ENABLED", "true")

    settings = get_settings()

    assert settings.scene_planner_shadow_enabled is True


def test_scene_planner_image_prompt_disabled_by_default(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.delenv("SCENE_PLANNER_IMAGE_PROMPT_ENABLED", raising=False)

    settings = get_settings()

    assert settings.scene_planner_image_prompt_enabled is False


def test_text_planner_shadow_disabled_by_default(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.delenv("TEXT_PLANNER_SHADOW_ENABLED", raising=False)

    settings = get_settings()

    assert settings.text_planner_shadow_enabled is False


def test_text_planner_shadow_enabled_env(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("TEXT_PLANNER_SHADOW_ENABLED", "true")

    settings = get_settings()

    assert settings.text_planner_shadow_enabled is True


def test_text_planner_controlled_disabled_by_default(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.delenv("TEXT_PLANNER_CONTROLLED_ENABLED", raising=False)

    settings = get_settings()

    assert settings.text_planner_controlled_enabled is False


def test_text_planner_controlled_enabled_env(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("TEXT_PLANNER_CONTROLLED_ENABLED", "true")

    settings = get_settings()

    assert settings.text_planner_controlled_enabled is True


def test_text_memory_context_disabled_by_default(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.delenv("TEXT_MEMORY_CONTEXT_ENABLED", raising=False)

    settings = get_settings()

    assert settings.text_memory_context_enabled is False


def test_text_memory_context_enabled_env(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("TEXT_MEMORY_CONTEXT_ENABLED", "true")

    settings = get_settings()

    assert settings.text_memory_context_enabled is True


def test_text_reviewer_shadow_disabled_by_default(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.delenv("TEXT_REVIEWER_SHADOW_ENABLED", raising=False)

    settings = get_settings()

    assert settings.text_reviewer_shadow_enabled is False


def test_text_reviewer_shadow_enabled_env(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("TEXT_REVIEWER_SHADOW_ENABLED", "true")

    settings = get_settings()

    assert settings.text_reviewer_shadow_enabled is True


def test_orchestrator_shadow_disabled_by_default(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.delenv("ORCHESTRATOR_SHADOW_ENABLED", raising=False)

    settings = get_settings()

    assert settings.orchestrator_shadow_enabled is False


def test_orchestrator_shadow_enabled_env(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("ORCHESTRATOR_SHADOW_ENABLED", "true")

    settings = get_settings()

    assert settings.orchestrator_shadow_enabled is True


def test_scene_planner_image_prompt_enabled_env(monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("SCENE_PLANNER_IMAGE_PROMPT_ENABLED", "true")

    settings = get_settings()

    assert settings.scene_planner_image_prompt_enabled is True


def test_capability_provider_defaults_use_openai_direct_profile(monkeypatch):
    _set_required_env(monkeypatch)

    settings = get_settings()
    text_cfg = get_text_provider_config()
    image_cfg = get_image_provider_config()
    tts_cfg = get_tts_provider_config()

    assert settings.text_provider == "openai"
    assert settings.image_provider == "openai"
    assert settings.tts_provider == "openai"
    assert settings.stt_provider == "openai"
    assert text_cfg.provider == "openai"
    assert image_cfg.provider == "openai"
    assert tts_cfg.provider == "openai"
    assert get_stt_provider_config().provider == "openai"
    assert image_cfg.base_url == "https://api.openai.com/v1"
    assert image_cfg.model == "gpt-image-1"


def test_legacy_provider_env_vars_are_ignored_without_breaking_startup(monkeypatch):
    """Stage 6: Yandex/Proxi and the TEXT_PROVIDER/IMAGE_PROVIDER/TTS_PROVIDER/STT_PROVIDER
    selection knobs are gone from the supported runtime path. A live .env that still has
    them from before Stage 6 must keep starting cleanly and resolve to OpenAI everywhere,
    with no error and no dependency on the legacy values being valid."""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("TEXT_PROVIDER", "yandex")
    monkeypatch.setenv("IMAGE_PROVIDER", "proxiapi")
    monkeypatch.setenv("TTS_PROVIDER", "yandex")
    monkeypatch.setenv("STT_PROVIDER", "yandex")
    monkeypatch.setenv("YANDEX_API_KEY", "stale-yandex-key")
    monkeypatch.setenv("YANDEX_FOLDER_ID", "stale-folder")
    monkeypatch.setenv("PROXI_API_KEY", "stale-proxi-key")

    settings = get_settings()

    assert settings.text_provider == "openai"
    assert settings.image_provider == "openai"
    assert settings.tts_provider == "openai"
    assert settings.stt_provider == "openai"
    assert get_text_provider_config().provider == "openai"
    assert get_image_provider_config().provider == "openai"
    assert get_tts_provider_config().provider == "openai"
    assert get_stt_provider_config().provider == "openai"


def test_stt_provider_openai_config(monkeypatch):
    _set_required_env(monkeypatch)
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
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    try:
        get_stt_provider_config()
        assert False, "Expected RuntimeError for missing OPENAI_API_KEY"
    except RuntimeError as exc:
        assert "OPENAI_API_KEY" in str(exc)


def test_env_example_is_openai_only_and_has_no_legacy_provider_vars():
    root = Path(__file__).resolve().parents[1]
    example = (root / ".env.example").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" in example
    assert "DATABASE_URL" in example
    for legacy_token in ("YANDEX", "PROXI", "TEXT_PROVIDER", "IMAGE_PROVIDER", "TTS_PROVIDER", "STT_PROVIDER"):
        assert legacy_token not in example
