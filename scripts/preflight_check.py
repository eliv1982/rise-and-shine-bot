"""Deploy preflight: validate required runtime configuration before scripts/deploy.sh
replaces the running container.

Runs on the deployment HOST, which has Docker/Compose and system Python but no
project virtualenv and no `pip install`-ed application dependencies (those live
inside the Docker image; docker-compose.yml's `env_file: .env` hands them to the
container at start). This script must therefore stay stdlib-only: it must NOT
import config.py (which imports python-dotenv) or any other third-party package.

Read-only. Never contacts Telegram/OpenAI/Postgres - only checks that the .env
file Compose will hand to the container is complete and internally consistent.
Parses .env directly with a small stdlib parser sufficient for this project's
documented .env syntax (.env.example: KEY=value lines, full-line '#' comments,
blank lines) - not a general python-dotenv replacement.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = REPO_ROOT / ".env"

# The only env vars config.get_settings() has ever treated as required (no
# `default=` given to _get_env_var): BOT_TOKEN and OPENAI_API_KEY (the latter
# required identically by each OpenAI-backed provider config).
REQUIRED_ENV_VARS = ("BOT_TOKEN", "OPENAI_API_KEY")


def parse_env_file(path: Path) -> dict[str, str]:
    """Minimal .env parser covering this project's documented syntax: KEY=value
    lines, blank lines, and full-line '#' comments, with optional matching quotes
    around the value. No escaping, multi-line values, or `export` prefixes - the
    project's .env never uses them (see .env.example)."""
    values: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return values
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def build_effective_env() -> dict[str, str]:
    """.env file values, overridden by any already-set process env var - the same
    precedence python-dotenv's default load_dotenv() (override=False) gives the
    app at container startup."""
    effective = parse_env_file(DOTENV_PATH)
    effective.update(os.environ)
    return effective


def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else sys.argv[1:]
    env = build_effective_env()

    missing = [name for name in REQUIRED_ENV_VARS if not (env.get(name) or "").strip()]
    if missing:
        for name in missing:
            print(
                f"[preflight] required configuration is missing: environment variable {name} is required but not set.",
                file=sys.stderr,
            )
        return 1

    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import check_runtime_config  # dependency-free (stdlib only), see that module

    return check_runtime_config.main(argv, env=env)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
