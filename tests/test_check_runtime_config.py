from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


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


def test_empty_explicit_environment_reports_actual_defaults_without_ambient_env():
    module = _load_script_module()
    report = module.build_runtime_config_report({})
    assert report["openai"]["OPENAI_TEXT_MODEL"] == "gpt-6-luna"
    assert report["openai"]["OPENAI_IMAGE_MODEL"] == "gpt-image-2.5-flare"
    assert report["openai"]["OPENAI_API_KEY"] == "unset"
    assert report["openai"]["OPENAI_TEXT_MODEL_SOURCE"] == "code_default"
    assert any("effective code default 'gpt-6-luna'" in warning for warning in report["warnings"])
    assert report["status"].startswith("CONFIG WARNINGS")


@pytest.mark.parametrize("text,primary,legacy", [
    (None, None, None), ("", "", ""), ("   ", "   ", "   "),
    (" gpt-6-luna ", " gpt-image-2.5-flare ", "gpt-image-1"),
    (" gpt-6.1-terra ", "", " gpt-image-1 "),
    (" gpt-4o-mini ", None, "gpt-image-1"),
])
def test_report_model_resolution_matches_application_config(monkeypatch, text, primary, legacy):
    from config import get_image_provider_config, get_text_provider_config

    env = {}
    for name, value in [("OPENAI_TEXT_MODEL", text), ("OPENAI_IMAGE_MODEL", primary), ("IMAGE_MODEL", legacy)]:
        monkeypatch.delenv(name, raising=False)
        if value is not None:
            monkeypatch.setenv(name, value)
            env[name] = value
    report = _load_script_module().build_runtime_config_report(env)
    assert report["openai"]["OPENAI_TEXT_MODEL"] == get_text_provider_config().model
    assert report["openai"]["OPENAI_IMAGE_MODEL"] == get_image_provider_config().model
    assert report["openai"]["OPENAI_TEXT_MODEL_SOURCE"] == ("explicit" if text and text.strip() else "code_default")


@pytest.mark.parametrize("effort", ["minimal", "typo", "low medium", "0"])
@pytest.mark.parametrize("model", ["gpt-4o-mini", "gpt-6-luna", "gpt-6.1-terra"])
def test_bad_reasoning_effort_is_a_runtime_config_error(model, effort):
    report = _load_script_module().build_runtime_config_report({
        "OPENAI_TEXT_MODEL": model, "OPENAI_TEXT_REASONING_EFFORT": effort,
    })
    assert any("OPENAI_TEXT_REASONING_EFFORT" in error for error in report["errors"])


@pytest.mark.parametrize("effort", ["NONE", " LOW ", "medium", "high", "xhigh", "max", "", "   "])
def test_report_normalizes_supported_reasoning_effort(effort):
    report = _load_script_module().build_runtime_config_report({"OPENAI_TEXT_REASONING_EFFORT": effort})
    assert report["errors"] == []
    assert report["openai"]["OPENAI_TEXT_REASONING_EFFORT"] == (effort.strip().lower() or "none")


@pytest.mark.parametrize("value", ["0", "-1", "nope", "1.5"])
def test_bad_completion_budget_is_a_runtime_config_error(value):
    report = _load_script_module().build_runtime_config_report({"OPENAI_TEXT_MAX_COMPLETION_TOKENS": value})
    assert any("OPENAI_TEXT_MAX_COMPLETION_TOKENS" in error for error in report["errors"])


@pytest.mark.parametrize("model", ["gpt-6 luna", "gpt-6-luna-unverified-snapshot", "gpt-6.1-terra-unverified-snapshot"])
def test_bad_model_identifier_is_a_runtime_config_error(model):
    report = _load_script_module().build_runtime_config_report({"OPENAI_TEXT_MODEL": model})
    assert any("OPENAI_TEXT_MODEL" in error for error in report["errors"])
