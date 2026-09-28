from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Mapping
from urllib.parse import urlsplit


OFFICIAL_OPENAI_BASE_URL = "https://api.openai.com/v1"
_POSTGRES_URL_PREFIXES = ("postgres://", "postgresql://")
_CONTAINER_UNREACHABLE_DB_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _env(env: Mapping[str, str], name: str, default: str = "") -> str:
    return (env.get(name) or default or "").strip()


def _env_bool(env: Mapping[str, str], name: str, default: bool = False) -> bool:
    raw = _env(env, name).lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def _env_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = _env(env, name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


_LEGACY_ENV_NAMES = (
    "TEXT_PROVIDER",
    "IMAGE_PROVIDER",
    "TTS_PROVIDER",
    "STT_PROVIDER",
    "PROXI_API_KEY",
    "PROXI_BASE_URL",
    "PROXI_TEXT_MODEL",
    "PROXI_IMAGE_MODEL",
    "PROXI_IMAGE_SIZE",
    "PROXI_TEXT_TIMEOUT_SECONDS",
    "PROXI_IMAGE_TIMEOUT_SECONDS",
    "YANDEX_API_KEY",
    "YANDEX_FOLDER_ID",
    "YANDEX_SPEECHKIT_API_KEY",
    "YANDEX_TEXT_MODEL",
    "YANDEX_COMPLETION_MODEL",
    "YANDEX_TTS_MODEL",
    "YANDEX_TTS_VOICE",
    "YANDEX_TTS_TIMEOUT_SECONDS",
    "YANDEX_STT_MODEL",
    "YANDEX_STT_LANGUAGE",
    "YANDEX_STT_TIMEOUT_SECONDS",
    "STT_PREFER_LANGUAGE",
)


def _ignored_legacy_env_present(env: Mapping[str, str]) -> list[str]:
    """Names of pre-Stage-6 provider env vars still set but no longer read by the app.

    Safe to leave in a live .env (see docs/production_env.md); listed here only so an
    operator can clean them up later without guessing which old vars are dead.
    """
    return sorted(name for name in _LEGACY_ENV_NAMES if _env(env, name))


def _mask_secret(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return "unset"
    if len(raw) <= 8:
        return "set"
    return f"{raw[:4]}...{raw[-4:]}"


def _count_enabled(flags: list[bool]) -> int:
    return sum(1 for flag in flags if flag)


def _database_backend_report(env: Mapping[str, str]) -> dict[str, Any]:
    database_url = _env(env, "DATABASE_URL")
    looks_postgres = database_url.startswith(_POSTGRES_URL_PREFIXES)
    backend = "postgresql" if looks_postgres else "sqlite"
    host = None
    if looks_postgres:
        try:
            host = urlsplit(database_url).hostname
        except ValueError:
            host = None
    return {
        "backend": backend,
        "database_url_set": bool(database_url),
        "database_url_looks_valid": (not database_url) or looks_postgres,
        "database_url_host": host,
        "sqlite_db_path": _env(env, "SQLITE_DB_PATH") or "(default)",
    }


def _build_errors(report: dict[str, Any], env: Mapping[str, str]) -> list[str]:
    """Problems severe enough that a deploy preflight should refuse to proceed."""
    errors: list[str] = []
    database = report["database"]
    if database["database_url_set"] and not database["database_url_looks_valid"]:
        errors.append(
            "DATABASE_URL is set but does not start with postgres:// or postgresql://; "
            "the bot will silently fall back to SQLite instead of the intended PostgreSQL database."
        )
    return errors


def _build_warnings(report: dict[str, Any], env: Mapping[str, str]) -> list[str]:
    warnings: list[str] = []

    database = report["database"]
    if database["backend"] == "postgresql" and database["database_url_host"] in _CONTAINER_UNREACHABLE_DB_HOSTS:
        warnings.append(
            f"DATABASE_URL host is {database['database_url_host']!r}; inside a Docker container "
            "(without network_mode: host) this resolves to the container itself, not a reachable "
            "Postgres. With docker-compose.yml's postgres service, use hostname 'postgres' "
            "(Compose DNS); otherwise point it at a docker-reachable host/IP or use extra_hosts."
        )

    openai = report["openai"]
    flags = report["flags"]

    if openai["OPENAI_BASE_URL"] != OFFICIAL_OPENAI_BASE_URL:
        warnings.append(
            f"OPENAI_BASE_URL differs from the official {OFFICIAL_OPENAI_BASE_URL}; "
            "this project's direction is official OpenAI endpoints only."
        )

    if flags["SCENE_PLANNER_IMAGE_PROMPT_ENABLED"] and not flags["SCENE_PLANNER_SHADOW_ENABLED"]:
        warnings.append("SCENE_PLANNER_IMAGE_PROMPT_ENABLED=true while SCENE_PLANNER_SHADOW_ENABLED=false.")

    if flags["TEXT_MEMORY_CONTEXT_ENABLED"] and not flags["TEXT_PLANNER_CONTROLLED_ENABLED"]:
        warnings.append("TEXT_MEMORY_CONTEXT_ENABLED=true while TEXT_PLANNER_CONTROLLED_ENABLED=false.")

    if flags["ORCHESTRATOR_SHADOW_ENABLED"]:
        role_count = _count_enabled(
            [
                flags["TEXT_PLANNER_SHADOW_ENABLED"] or flags["TEXT_PLANNER_CONTROLLED_ENABLED"],
                flags["TEXT_REVIEWER_SHADOW_ENABLED"],
                flags["SCENE_PLANNER_SHADOW_ENABLED"] or flags["SCENE_PLANNER_IMAGE_PROMPT_ENABLED"],
            ]
        )
        if role_count <= 1:
            warnings.append("ORCHESTRATOR_SHADOW_ENABLED=true while most text/scene reviewer roles are disabled.")

    production_like = bool(_env(env, "BOT_TOKEN")) and bool(_env(env, "OPENAI_API_KEY"))
    if flags["DISABLE_DAILY_GENERATION_LIMIT"] and production_like:
        warnings.append("DISABLE_DAILY_GENERATION_LIMIT=true in a production-like environment.")

    return warnings


def build_runtime_config_report(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    safe_env = env or os.environ

    report: dict[str, Any] = {
        "provider": "openai",
        "openai": {
            "OPENAI_BASE_URL": _env(safe_env, "OPENAI_BASE_URL", OFFICIAL_OPENAI_BASE_URL),
            "OPENAI_TEXT_MODEL": _env(safe_env, "OPENAI_TEXT_MODEL", "gpt-4o-mini"),
            "OPENAI_IMAGE_MODEL": _env(safe_env, "OPENAI_IMAGE_MODEL", _env(safe_env, "IMAGE_MODEL", "gpt-image-1")),
            "OPENAI_IMAGE_SIZE": _env(safe_env, "OPENAI_IMAGE_SIZE", _env(safe_env, "IMAGE_SIZE", "1024x1024")),
            "OPENAI_TTS_MODEL": _env(safe_env, "OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
            "OPENAI_STT_MODEL": _env(safe_env, "OPENAI_STT_MODEL", "gpt-4o-mini-transcribe"),
            "OPENAI_API_KEY": _mask_secret(_env(safe_env, "OPENAI_API_KEY")),
        },
        "ignored_legacy_env": _ignored_legacy_env_present(safe_env),
        "flags": {
            "TEXT_PLANNER_SHADOW_ENABLED": _env_bool(safe_env, "TEXT_PLANNER_SHADOW_ENABLED", False),
            "TEXT_PLANNER_CONTROLLED_ENABLED": _env_bool(safe_env, "TEXT_PLANNER_CONTROLLED_ENABLED", False),
            "TEXT_MEMORY_CONTEXT_ENABLED": _env_bool(safe_env, "TEXT_MEMORY_CONTEXT_ENABLED", False),
            "TEXT_REVIEWER_SHADOW_ENABLED": _env_bool(safe_env, "TEXT_REVIEWER_SHADOW_ENABLED", False),
            "SCENE_PLANNER_SHADOW_ENABLED": _env_bool(safe_env, "SCENE_PLANNER_SHADOW_ENABLED", False),
            "SCENE_PLANNER_IMAGE_PROMPT_ENABLED": _env_bool(safe_env, "SCENE_PLANNER_IMAGE_PROMPT_ENABLED", False),
            "ORCHESTRATOR_SHADOW_ENABLED": _env_bool(safe_env, "ORCHESTRATOR_SHADOW_ENABLED", False),
            "DISABLE_DAILY_GENERATION_LIMIT": _env_bool(safe_env, "DISABLE_DAILY_GENERATION_LIMIT", False),
            "SHOW_IMAGE_DEBUG": _env_bool(safe_env, "SHOW_IMAGE_DEBUG", False),
        },
        "limits": {
            "GENERATION_DAILY_LIMIT": _env_int(
                safe_env,
                "DAILY_GENERATION_LIMIT",
                _env_int(safe_env, "GENERATION_DAILY_LIMIT", 5),
            ),
        },
        "database": _database_backend_report(safe_env),
    }

    report["errors"] = _build_errors(report, safe_env)
    report["warnings"] = _build_warnings(report, safe_env)
    if report["errors"]:
        report["status"] = f"CONFIG ERRORS: {len(report['errors'])}"
    elif report["warnings"]:
        report["status"] = f"CONFIG WARNINGS: {len(report['warnings'])}"
    else:
        report["status"] = "CONFIG OK"
    return report


def _format_human_report(report: dict[str, Any]) -> str:
    lines = [report["status"], ""]

    lines.append(f"Provider: {report['provider']} (text/image/TTS/STT; fixed, not configurable)")

    lines.append("")
    lines.append("OpenAI direct:")
    for key in [
        "OPENAI_BASE_URL",
        "OPENAI_TEXT_MODEL",
        "OPENAI_IMAGE_MODEL",
        "OPENAI_IMAGE_SIZE",
        "OPENAI_TTS_MODEL",
        "OPENAI_STT_MODEL",
        "OPENAI_API_KEY",
    ]:
        lines.append(f"- {key}: {report['openai'][key]}")

    if report["ignored_legacy_env"]:
        lines.append("")
        lines.append("Ignored legacy env vars (pre-Stage-6 Yandex/Proxi/provider-selection; not read by the app, safe to remove):")
        for name in report["ignored_legacy_env"]:
            lines.append(f"- {name}")

    lines.append("")
    lines.append("Role flags:")
    for key in [
        "TEXT_PLANNER_SHADOW_ENABLED",
        "TEXT_PLANNER_CONTROLLED_ENABLED",
        "TEXT_MEMORY_CONTEXT_ENABLED",
        "TEXT_REVIEWER_SHADOW_ENABLED",
        "SCENE_PLANNER_SHADOW_ENABLED",
        "SCENE_PLANNER_IMAGE_PROMPT_ENABLED",
        "ORCHESTRATOR_SHADOW_ENABLED",
    ]:
        lines.append(f"- {key}: {str(report['flags'][key]).lower()}")

    lines.append("")
    lines.append("Limit and debug flags:")
    lines.append(f"- GENERATION_DAILY_LIMIT: {report['limits']['GENERATION_DAILY_LIMIT']}")
    lines.append(f"- DISABLE_DAILY_GENERATION_LIMIT: {str(report['flags']['DISABLE_DAILY_GENERATION_LIMIT']).lower()}")
    lines.append(f"- SHOW_IMAGE_DEBUG: {str(report['flags']['SHOW_IMAGE_DEBUG']).lower()}")

    lines.append("")
    lines.append("Database:")
    database = report["database"]
    lines.append(f"- backend: {database['backend']}")
    lines.append(f"- DATABASE_URL set: {str(database['database_url_set']).lower()}")
    if database["backend"] == "sqlite":
        lines.append(f"- SQLITE_DB_PATH: {database['sqlite_db_path']}")

    if report["errors"]:
        lines.append("")
        lines.append("Errors:")
        for error in report["errors"]:
            lines.append(f"- {error}")

    if report["warnings"]:
        lines.append("")
        lines.append("Warnings:")
        for warning in report["warnings"]:
            lines.append(f"- {warning}")

    return "\n".join(lines)


def main(argv: list[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    """`env` lets a caller (scripts/preflight_check.py) supply a merged view of
    process env + parsed .env file, since this module itself only reads os.environ
    by default. Optional and defaulted to preserve standalone/in-container use."""
    parser = argparse.ArgumentParser(description="Read-only runtime configuration doctor for Rise and Shine bot.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON report")
    args = parser.parse_args(argv)

    report = build_runtime_config_report(env)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_format_human_report(report))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
