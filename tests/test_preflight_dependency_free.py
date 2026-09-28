"""Stage 7B corrective: a real production host has Docker/Compose and system Python
but no project virtualenv and no `pip install`-ed application dependencies (that was
the actual production failure - preflight_check.py used to import config.py, which
imports python-dotenv, which is only installed inside the Docker image).

These tests copy scripts/preflight_check.py + scripts/check_runtime_config.py into an
isolated temp directory (no config.py, no requirements.txt, nothing importable beyond
the two scripts) and run preflight_check.py as a real subprocess with `-S` (site-packages
disabled), so third-party packages genuinely cannot be imported - not just unpatched
in-process. A passing run under `-S` with no config.py on disk is direct proof of the
dependency-free contract, independent of what happens to be pip-installed locally.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_CHECK = REPO_ROOT / "scripts" / "preflight_check.py"
CHECK_RUNTIME_CONFIG = REPO_ROOT / "scripts" / "check_runtime_config.py"

# Env vars whose ambient value (including conftest.py's process-wide test defaults)
# must never leak into these subprocesses - each test sets exactly what it needs via
# the temp .env file instead.
_RELEVANT_KEYS = (
    "BOT_TOKEN", "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_TEXT_MODEL",
    "OPENAI_IMAGE_MODEL", "OPENAI_TTS_MODEL", "OPENAI_STT_MODEL", "DATABASE_URL",
)


def _isolated_host(tmp_path: Path) -> Path:
    """A throwaway directory shaped like the deploy host's checkout: only the two
    scripts under test plus a .env - no config.py, no requirements.txt, no installed
    application dependencies reachable from here."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    shutil.copy(PREFLIGHT_CHECK, scripts_dir / "preflight_check.py")
    shutil.copy(CHECK_RUNTIME_CONFIG, scripts_dir / "check_runtime_config.py")
    return tmp_path


def _clean_subprocess_env() -> dict[str, str]:
    """Start from the real environment (so PATH/SystemRoot/etc. stay intact and the
    interpreter can actually start on every OS) but strip the specific keys these
    tests care about, so only what a test writes into .env is in effect."""
    base = os.environ.copy()
    for key in _RELEVANT_KEYS:
        base.pop(key, None)
    return base


def _run_preflight(host_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-S", str(host_dir / "scripts" / "preflight_check.py")],
        cwd=host_dir,
        env=_clean_subprocess_env(),
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_dependency_free_preflight_succeeds_with_valid_env(tmp_path):
    host = _isolated_host(tmp_path)
    (host / ".env").write_text(
        "BOT_TOKEN=host-token\n"
        "OPENAI_API_KEY=host-openai-key\n"
        "DATABASE_URL=postgresql://rise:rise@postgres:5432/rise_bot\n",
        encoding="utf-8",
    )

    result = _run_preflight(host)

    assert result.returncode == 0, result.stderr
    assert "CONFIG OK" in result.stdout
    assert not (host / "config.py").exists()  # nothing to import even if it tried


def test_missing_required_value_fails(tmp_path):
    host = _isolated_host(tmp_path)
    (host / ".env").write_text("OPENAI_API_KEY=host-openai-key\n", encoding="utf-8")  # no BOT_TOKEN

    result = _run_preflight(host)

    assert result.returncode == 1
    assert "BOT_TOKEN" in result.stderr


def test_invalid_database_url_fails(tmp_path):
    host = _isolated_host(tmp_path)
    (host / ".env").write_text(
        "BOT_TOKEN=host-token\nOPENAI_API_KEY=host-openai-key\nDATABASE_URL=not-a-valid-url\n",
        encoding="utf-8",
    )

    result = _run_preflight(host)

    assert result.returncode == 1
    assert "CONFIG ERRORS" in result.stdout


def test_localhost_postgres_url_warns_but_does_not_fail(tmp_path):
    host = _isolated_host(tmp_path)
    (host / ".env").write_text(
        "BOT_TOKEN=host-token\nOPENAI_API_KEY=host-openai-key\n"
        "DATABASE_URL=postgresql://rise:rise@localhost:5432/rise_bot\n",
        encoding="utf-8",
    )

    result = _run_preflight(host)

    assert result.returncode == 0, result.stderr
    assert "DATABASE_URL host is" in result.stdout


def test_compose_hostname_postgres_passes_cleanly(tmp_path):
    host = _isolated_host(tmp_path)
    (host / ".env").write_text(
        "BOT_TOKEN=host-token\nOPENAI_API_KEY=host-openai-key\n"
        "DATABASE_URL=postgresql://rise:rise@postgres:5432/rise_bot\n",
        encoding="utf-8",
    )

    result = _run_preflight(host)

    assert result.returncode == 0, result.stderr
    assert "DATABASE_URL host is" not in result.stdout


def test_secrets_are_not_echoed_on_failure(tmp_path):
    host = _isolated_host(tmp_path)
    secret_key = "sk-VERY-SECRET-OPENAI-KEY-VALUE"
    secret_token = "999999:VERY-SECRET-BOT-TOKEN-VALUE"
    (host / ".env").write_text(
        f"BOT_TOKEN={secret_token}\nOPENAI_API_KEY={secret_key}\nDATABASE_URL=not-a-valid-url\n",
        encoding="utf-8",
    )

    result = _run_preflight(host)

    assert result.returncode == 1
    combined = result.stdout + result.stderr
    assert secret_key not in combined
    assert secret_token not in combined


def test_static_source_has_no_third_party_or_config_imports():
    """Belt-and-suspenders alongside the subprocess proofs above: the source itself
    never actually imports dotenv or config.py (parsed via ast, not substring match,
    so the module docstring is free to mention them by name), so there is nothing
    for future edits to accidentally reintroduce without this test catching it."""
    import ast

    tree = ast.parse(PREFLIGHT_CHECK.read_text(encoding="utf-8"), filename=str(PREFLIGHT_CHECK))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module.split(".")[0])

    assert "dotenv" not in imported_modules
    assert "config" not in imported_modules
