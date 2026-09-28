"""Stage 7B corrective: deploy preflight must run on a clean deployment host with
system Python only - no project virtualenv, no python-dotenv, no application
dependencies (those live inside the Docker image; see scripts/preflight_check.py's
module docstring). It must therefore not import config.py, and instead parses .env
itself with a small stdlib parser, then reuses check_runtime_config's consistency
checks (e.g. a malformed DATABASE_URL) against the merged env.

Exercised in-process with monkeypatch, matching the pattern in tests/test_config.py.
`DOTENV_PATH` is always redirected to a path outside the repo so these tests never
read the developer's real (gitignored) .env - see test_preflight_dependency_free.py
for the actual .env-file-parsing path and the dependency-free proof.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "preflight_check.py"


def _load_script_module(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("preflight_check_script", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "DOTENV_PATH", tmp_path / "unused-no-such.env")
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


def test_missing_bot_token_fails_preflight(monkeypatch, tmp_path, capsys):
    module = _load_script_module(monkeypatch, tmp_path)
    _set_required_env(monkeypatch)
    monkeypatch.delenv("BOT_TOKEN", raising=False)

    exit_code = module.main([])

    assert exit_code == 1
    assert "BOT_TOKEN" in capsys.readouterr().err


def test_complete_config_passes_preflight(monkeypatch, tmp_path):
    module = _load_script_module(monkeypatch, tmp_path)
    _set_required_env(monkeypatch)

    exit_code = module.main([])

    assert exit_code == 0


def test_malformed_database_url_fails_preflight(monkeypatch, tmp_path, capsys):
    module = _load_script_module(monkeypatch, tmp_path)
    _set_required_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "not-a-valid-url")

    exit_code = module.main([])

    assert exit_code == 1
    assert "CONFIG ERRORS" in capsys.readouterr().out


def test_env_file_values_are_used_when_process_env_is_unset(monkeypatch, tmp_path, capsys):
    """The whole point of this corrective stage: on a clean host, required values
    live only in .env, not in the shell's process environment."""
    module = _load_script_module(monkeypatch, tmp_path)
    for name in (
        "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_TEXT_MODEL", "OPENAI_IMAGE_MODEL",
        "OPENAI_TTS_MODEL", "OPENAI_STT_MODEL", "BOT_TOKEN", "DATABASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "BOT_TOKEN=file-token\n"
        "OPENAI_API_KEY=file-openai-key\n"
        "DATABASE_URL=postgresql://rise:rise@postgres:5432/rise_bot\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "DOTENV_PATH", env_file)

    exit_code = module.main([])

    assert exit_code == 0
    assert "CONFIG OK" in capsys.readouterr().out


def test_process_env_overrides_env_file(monkeypatch, tmp_path):
    """Matches python-dotenv's default (override=False): an already-set process
    env var wins over the .env file value for that same key."""
    module = _load_script_module(monkeypatch, tmp_path)
    _set_required_env(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text("BOT_TOKEN=file-token-should-be-ignored\n", encoding="utf-8")
    monkeypatch.setattr(module, "DOTENV_PATH", env_file)

    effective = module.build_effective_env()

    assert effective["BOT_TOKEN"] == "test-token"
