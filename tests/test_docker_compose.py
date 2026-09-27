"""Corrective pass: docker-compose.yml now models the real production Compose
topology - PostgreSQL is the `postgres` service in this same Compose project,
not a separate, self-managed service outside it (see docs/production_env.md).

These tests render the tracked file with the real `docker compose config` (no
containers started, no network/database access) so drift between the tracked
file and what Compose would actually do cannot silently reappear. Rendering
happens in an isolated temp copy with throwaway credentials - never the real
repo `.env`.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
DOCKERFILE = REPO_ROOT / "Dockerfile"
ENV_EXAMPLE = REPO_ROOT / ".env.example"

_TEST_POSTGRES_ENV = {
    "POSTGRES_USER": "test_user",
    "POSTGRES_PASSWORD": "test_password",
    "POSTGRES_DB": "test_db",
}


def _docker_compose_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            timeout=10,
            check=True,
        )
    except Exception:
        return False
    return True


def _render(tmp_path: Path, postgres_env: dict[str, str]) -> subprocess.CompletedProcess:
    """Copy docker-compose.yml into an isolated dir with a throwaway .env and
    render it with `docker compose config`. Isolated so this never reads or
    depends on the real repo `.env`."""
    work_dir = tmp_path / "compose"
    work_dir.mkdir()
    shutil.copy(COMPOSE_FILE, work_dir / "docker-compose.yml")
    env_text = "".join(f"{key}={value}\n" for key, value in postgres_env.items())
    (work_dir / ".env").write_text(env_text, encoding="utf-8")
    return subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        cwd=work_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.fixture(scope="module")
def rendered_config(tmp_path_factory):
    if not _docker_compose_available():
        pytest.skip("docker compose is not available in this environment")
    result = _render(tmp_path_factory.mktemp("compose"), _TEST_POSTGRES_ENV)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_postgres_service_present(rendered_config):
    assert "postgres" in rendered_config["services"]


def test_bot_depends_on_healthy_postgres(rendered_config):
    depends_on = rendered_config["services"]["bot"]["depends_on"]
    assert depends_on["postgres"]["condition"] == "service_healthy"


def test_postgres_data_volume_declared(rendered_config):
    volumes = rendered_config["volumes"]
    assert "postgres_data" in volumes
    assert "bot_data" in volumes  # Stage-5 volume preserved, not renamed/removed


def test_postgres_mounts_data_volume_at_pg_data_dir(rendered_config):
    mounts = rendered_config["services"]["postgres"]["volumes"]
    assert any(
        m["source"] == "postgres_data" and m["target"] == "/var/lib/postgresql/data"
        for m in mounts
    )


def test_no_host_port_exposure(rendered_config):
    assert not rendered_config["services"]["postgres"].get("ports")
    assert not rendered_config["services"]["bot"].get("ports")


def test_postgres_healthcheck_uses_container_env_not_hardcoded_credentials(rendered_config):
    test_cmd = " ".join(rendered_config["services"]["postgres"]["healthcheck"]["test"])
    assert "pg_isready" in test_cmd
    assert "POSTGRES_USER" in test_cmd and "POSTGRES_DB" in test_cmd
    assert _TEST_POSTGRES_ENV["POSTGRES_USER"] not in test_cmd
    assert _TEST_POSTGRES_ENV["POSTGRES_PASSWORD"] not in test_cmd


@pytest.mark.parametrize("missing_var", ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"])
def test_missing_postgres_env_fails_compose_config(tmp_path, missing_var):
    """Compose interpolation stops at the first missing required variable and
    does not necessarily report every missing one in a single invocation
    (observed on GitHub Actions' Compose version - it reports only the first).
    So each required var is tested in isolation, omitted from an otherwise
    complete/valid env, rather than asserting all three appear when all three
    are missing at once."""
    if not _docker_compose_available():
        pytest.skip("docker compose is not available in this environment")
    postgres_env = {k: v for k, v in _TEST_POSTGRES_ENV.items() if k != missing_var}
    result = _render(tmp_path, postgres_env=postgres_env)

    assert result.returncode != 0
    combined = result.stdout + result.stderr
    assert missing_var in combined


def test_production_env_example_uses_compose_hostname_for_database_url():
    content = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "@postgres:5432/" in content
    assert "@localhost:5432" not in content
    assert "@127.0.0.1:5432" not in content


def test_stage5_bot_hardening_preserved_in_compose_source():
    text = COMPOSE_FILE.read_text(encoding="utf-8")
    assert "container_name: rise-and-shine-bot" in text
    assert "stop_grace_period: 30s" in text
    assert "env_file: .env" in text
    assert "bot_data:/app/data" in text


def test_dockerfile_still_runs_bot_as_non_root_with_healthcheck():
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert "USER appuser" in text
    assert "HEALTHCHECK" in text
