from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Mapping


OFFICIAL_OPENAI_BASE_URL = "https://api.openai.com/v1"


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


def _normalize_provider(raw_value: str, *, allowed: tuple[str, ...], default: str) -> str:
    value = (raw_value or "").strip().lower()
    if not value:
        return default
    if value in allowed:
        return value
    return default


def _mask_secret(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return "unset"
    if len(raw) <= 8:
        return "set"
    return f"{raw[:4]}...{raw[-4:]}"


def _count_enabled(flags: list[bool]) -> int:
    return sum(1 for flag in flags if flag)


def _build_warnings(report: dict[str, Any], env: Mapping[str, str]) -> list[str]:
    warnings: list[str] = []

    providers = report["providers"]
    openai = report["openai"]
    flags = report["flags"]

    if providers["IMAGE_PROVIDER"] == "proxiapi":
        warnings.append("IMAGE_PROVIDER=proxiapi while direct OpenAI image profile is expected.")

    if providers["IMAGE_PROVIDER"] == "openai" and openai["OPENAI_BASE_URL"] != OFFICIAL_OPENAI_BASE_URL:
        warnings.append("OPENAI_BASE_URL differs from https://api.openai.com/v1 while IMAGE_PROVIDER=openai.")

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

    production_like = bool(_env(env, "BOT_TOKEN")) and (
        bool(_env(env, "OPENAI_API_KEY")) or providers["IMAGE_PROVIDER"] == "proxiapi"
    )
    if flags["DISABLE_DAILY_GENERATION_LIMIT"] and production_like:
        warnings.append("DISABLE_DAILY_GENERATION_LIMIT=true in a production-like environment.")

    return warnings


def build_runtime_config_report(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    safe_env = env or os.environ

    text_provider = _normalize_provider(
        _env(safe_env, "TEXT_PROVIDER"),
        allowed=("proxiapi", "openai", "yandex"),
        default="openai",
    )
    image_provider = _normalize_provider(
        _env(safe_env, "IMAGE_PROVIDER"),
        allowed=("proxiapi", "openai"),
        default="openai",
    )
    tts_provider = _normalize_provider(
        _env(safe_env, "TTS_PROVIDER"),
        allowed=("yandex", "openai"),
        default="openai",
    )
    stt_provider = _normalize_provider(
        _env(safe_env, "STT_PROVIDER"),
        allowed=("yandex", "openai"),
        default="openai",
    )

    report: dict[str, Any] = {
        "providers": {
            "TEXT_PROVIDER": text_provider,
            "IMAGE_PROVIDER": image_provider,
            "TTS_PROVIDER": tts_provider,
            "STT_PROVIDER": stt_provider,
        },
        "openai": {
            "OPENAI_BASE_URL": _env(safe_env, "OPENAI_BASE_URL", OFFICIAL_OPENAI_BASE_URL),
            "OPENAI_TEXT_MODEL": _env(safe_env, "OPENAI_TEXT_MODEL", "gpt-4o-mini"),
            "OPENAI_IMAGE_MODEL": _env(safe_env, "OPENAI_IMAGE_MODEL", _env(safe_env, "IMAGE_MODEL", "gpt-image-1")),
            "OPENAI_IMAGE_SIZE": _env(safe_env, "OPENAI_IMAGE_SIZE", _env(safe_env, "IMAGE_SIZE", "1024x1024")),
            "OPENAI_TTS_MODEL": _env(safe_env, "OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
            "OPENAI_STT_MODEL": _env(safe_env, "OPENAI_STT_MODEL", "gpt-4o-mini-transcribe"),
            "OPENAI_API_KEY": _mask_secret(_env(safe_env, "OPENAI_API_KEY")),
        },
        "legacy": {
            "PROXI_API_KEY": _mask_secret(_env(safe_env, "PROXI_API_KEY")),
            "YANDEX_API_KEY": _mask_secret(_env(safe_env, "YANDEX_API_KEY")),
            "YANDEX_FOLDER_ID": _mask_secret(_env(safe_env, "YANDEX_FOLDER_ID")),
        },
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
    }

    report["warnings"] = _build_warnings(report, safe_env)
    report["status"] = "CONFIG OK" if not report["warnings"] else f"CONFIG WARNINGS: {len(report['warnings'])}"
    return report


def _format_human_report(report: dict[str, Any]) -> str:
    lines = [report["status"], ""]

    lines.append("Provider profile:")
    for key, value in report["providers"].items():
        lines.append(f"- {key}: {value}")

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

    lines.append("")
    lines.append("Legacy provider status:")
    for key, value in report["legacy"].items():
        lines.append(f"- {key}: {value}")

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

    if report["warnings"]:
        lines.append("")
        lines.append("Warnings:")
        for warning in report["warnings"]:
            lines.append(f"- {warning}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only runtime configuration doctor for Rise and Shine bot.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON report")
    args = parser.parse_args(argv)

    report = build_runtime_config_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_format_human_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
