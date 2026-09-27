"""Stage 5 item B: deploy preflight must stop on missing/inconsistent runtime config.

preflight_check.py reuses config.get_settings() (the app's own startup validation)
as the single source of truth for required env vars, then runs check_runtime_config's
consistency checks (e.g. a malformed DATABASE_URL). Both are exercised in-process with
monkeypatch, matching the pattern in tests/test_config.py.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "preflight_check.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("preflight_check_script", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _set_required_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
    monkeypatch.setenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    monkeypatch.setenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("PROXI_API_KEY", raising=False)
    monkeypatch.delenv("YANDEX_API_KEY", raising=False)
    monkeypatch.delenv("YANDEX_FOLDER_ID", raising=False)


def test_missing_bot_token_fails_preflight(monkeypatch, capsys):
    module = _load_script_module()
    _set_required_env(monkeypatch)
    monkeypatch.delenv("BOT_TOKEN", raising=False)

    exit_code = module.main([])

    assert exit_code == 1
    assert "BOT_TOKEN" in capsys.readouterr().err


def test_complete_config_passes_preflight(monkeypatch):
    module = _load_script_module()
    _set_required_env(monkeypatch)

    exit_code = module.main([])

    assert exit_code == 0


def test_malformed_database_url_fails_preflight(monkeypatch, capsys):
    module = _load_script_module()
    _set_required_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "not-a-valid-url")

    exit_code = module.main([])

    assert exit_code == 1
    assert "CONFIG ERRORS" in capsys.readouterr().out
