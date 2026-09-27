from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_runtime_config.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("check_runtime_config_script", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _set_base_env(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123456:telegram-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-very-secret-value-1234")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
    monkeypatch.setenv("OPENAI_IMAGE_SIZE", "1024x1024")
    monkeypatch.setenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    monkeypatch.setenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
    monkeypatch.setenv("TEXT_PLANNER_SHADOW_ENABLED", "true")
    monkeypatch.setenv("TEXT_PLANNER_CONTROLLED_ENABLED", "true")
    monkeypatch.setenv("TEXT_MEMORY_CONTEXT_ENABLED", "true")
    monkeypatch.setenv("TEXT_REVIEWER_SHADOW_ENABLED", "true")
    monkeypatch.setenv("SCENE_PLANNER_SHADOW_ENABLED", "true")
    monkeypatch.setenv("SCENE_PLANNER_IMAGE_PROMPT_ENABLED", "true")
    monkeypatch.setenv("ORCHESTRATOR_SHADOW_ENABLED", "true")
    monkeypatch.setenv("GENERATION_DAILY_LIMIT", "5")
    monkeypatch.setenv("DISABLE_DAILY_GENERATION_LIMIT", "false")
    monkeypatch.setenv("SHOW_IMAGE_DEBUG", "false")
    for legacy_name in (
        "TEXT_PROVIDER", "IMAGE_PROVIDER", "TTS_PROVIDER", "STT_PROVIDER",
        "PROXI_API_KEY", "PROXI_BASE_URL", "YANDEX_API_KEY", "YANDEX_FOLDER_ID",
    ):
        monkeypatch.delenv(legacy_name, raising=False)


def test_human_readable_output_masks_secrets(monkeypatch, capsys):
    module = _load_script_module()
    _set_base_env(monkeypatch)

    exit_code = module.main([])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "CONFIG OK" in out
    assert "sk-test-very-secret-value-1234" not in out
    assert "123456:telegram-secret" not in out
    assert "sk-t...1234" in out


def test_json_output_parses(monkeypatch, capsys):
    module = _load_script_module()
    _set_base_env(monkeypatch)

    exit_code = module.main(["--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["provider"] == "openai"
    assert payload["status"] == "CONFIG OK"


def test_openai_direct_profile_has_no_warnings(monkeypatch):
    module = _load_script_module()
    _set_base_env(monkeypatch)

    report = module.build_runtime_config_report()

    assert report["warnings"] == []
    assert report["status"] == "CONFIG OK"


def test_custom_openai_base_url_warns(monkeypatch):
    module = _load_script_module()
    _set_base_env(monkeypatch)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.proxyapi.ru/openai/v1")

    report = module.build_runtime_config_report()

    assert any("OPENAI_BASE_URL differs" in warning for warning in report["warnings"])


def test_legacy_provider_env_vars_are_reported_as_ignored_not_active(monkeypatch, capsys):
    module = _load_script_module()
    _set_base_env(monkeypatch)
    monkeypatch.setenv("TEXT_PROVIDER", "yandex")
    monkeypatch.setenv("IMAGE_PROVIDER", "proxiapi")
    monkeypatch.setenv("YANDEX_API_KEY", "yandex-secret-value-4321")
    monkeypatch.setenv("PROXI_API_KEY", "proxy-secret-value-9876")

    report = module.build_runtime_config_report()

    assert report["provider"] == "openai"
    assert report["warnings"] == []
    assert set(report["ignored_legacy_env"]) >= {
        "TEXT_PROVIDER", "IMAGE_PROVIDER", "YANDEX_API_KEY", "PROXI_API_KEY",
    }

    module.main([])
    out = capsys.readouterr().out
    assert "yandex-secret-value-4321" not in out
    assert "proxy-secret-value-9876" not in out
    assert "Ignored legacy env vars" in out


def test_no_legacy_env_present_omits_ignored_section(monkeypatch, capsys):
    module = _load_script_module()
    _set_base_env(monkeypatch)

    report = module.build_runtime_config_report()
    assert report["ignored_legacy_env"] == []

    module.main([])
    out = capsys.readouterr().out
    assert "Ignored legacy env vars" not in out


def test_role_dependency_warnings_appear(monkeypatch):
    module = _load_script_module()
    _set_base_env(monkeypatch)
    monkeypatch.setenv("SCENE_PLANNER_SHADOW_ENABLED", "false")
    monkeypatch.setenv("TEXT_MEMORY_CONTEXT_ENABLED", "true")
    monkeypatch.setenv("TEXT_PLANNER_CONTROLLED_ENABLED", "false")
    monkeypatch.setenv("TEXT_PLANNER_SHADOW_ENABLED", "false")
    monkeypatch.setenv("TEXT_REVIEWER_SHADOW_ENABLED", "false")
    monkeypatch.setenv("SCENE_PLANNER_IMAGE_PROMPT_ENABLED", "false")
    monkeypatch.setenv("ORCHESTRATOR_SHADOW_ENABLED", "true")

    report = module.build_runtime_config_report()

    assert any("TEXT_MEMORY_CONTEXT_ENABLED=true while TEXT_PLANNER_CONTROLLED_ENABLED=false" in warning for warning in report["warnings"])
    assert any("ORCHESTRATOR_SHADOW_ENABLED=true while most text/scene reviewer roles are disabled" in warning for warning in report["warnings"])


def test_no_database_url_defaults_to_sqlite_backend(monkeypatch):
    module = _load_script_module()
    _set_base_env(monkeypatch)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    report = module.build_runtime_config_report()

    assert report["database"]["backend"] == "sqlite"
    assert report["database"]["database_url_set"] is False
    assert report["errors"] == []
    assert report["status"] == "CONFIG OK"


def test_malformed_database_url_is_a_blocking_error(monkeypatch, capsys):
    module = _load_script_module()
    _set_base_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgres-server:5432/rise_bot")

    report = module.build_runtime_config_report()

    assert report["database"]["backend"] == "sqlite"  # what the app would silently fall back to
    assert any("silently fall back to SQLite" in error for error in report["errors"])
    assert report["status"].startswith("CONFIG ERRORS")

    exit_code = module.main([])
    assert exit_code == 1
    assert "CONFIG ERRORS" in capsys.readouterr().out


def test_postgres_localhost_host_warns_about_container_networking(monkeypatch):
    module = _load_script_module()
    _set_base_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgresql://rise:rise@localhost:5434/rise_bot")

    report = module.build_runtime_config_report()

    assert report["database"]["backend"] == "postgresql"
    assert report["errors"] == []
    assert any("DATABASE_URL host is" in warning for warning in report["warnings"])


def test_postgres_with_reachable_host_has_no_database_warning(monkeypatch):
    module = _load_script_module()
    _set_base_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "postgresql://rise:rise@db.internal:5432/rise_bot")

    report = module.build_runtime_config_report()

    assert report["database"]["backend"] == "postgresql"
    assert report["errors"] == []
    assert report["warnings"] == []
