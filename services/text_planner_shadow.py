import logging

from config import get_settings
from services.text_planner import (
    build_fallback_text_plan,
    build_text_plan_summary,
    build_text_planner_prompt,
    normalize_text_plan,
)

logger = logging.getLogger(__name__)
_MAX_TEXT_PLAN_SUMMARY_LENGTH = 1000


def _safe_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off", ""):
            return False
    return bool(value)


def is_text_planner_shadow_enabled(settings: object | None = None) -> bool:
    try:
        effective_settings = settings or get_settings()
        value = getattr(effective_settings, "text_planner_shadow_enabled", False)
        return _coerce_bool(value)
    except Exception:
        return False


def build_text_plan_shadow_payload(
    *,
    text_plan: dict,
    text_plan_summary: str | None = None,
) -> dict:
    summary = (text_plan_summary or "").strip()
    if len(summary) > _MAX_TEXT_PLAN_SUMMARY_LENGTH:
        summary = summary[:_MAX_TEXT_PLAN_SUMMARY_LENGTH].rstrip() + "..."
    return {
        "enabled": True,
        "mode": "local_fallback",
        "llm_used": False,
        "text_plan": normalize_text_plan(text_plan),
        "text_plan_summary": summary or None,
    }


async def build_text_plan_shadow_best_effort(
    *,
    sphere: str | None = None,
    subsphere: str | None = None,
    focus_title: str | None = None,
    user_custom_topic: str | None = None,
    language: str = "ru",
    recent_text_context: dict | None = None,
    settings: object | None = None,
) -> dict | None:
    if not is_text_planner_shadow_enabled(settings):
        return None

    try:
        build_text_planner_prompt(
            sphere=sphere,
            subsphere=subsphere,
            focus_title=focus_title,
            user_custom_topic=user_custom_topic,
            language=language,
            recent_text_context=recent_text_context,
        )
        text_plan = build_fallback_text_plan(
            sphere=sphere,
            subsphere=subsphere,
            focus_title=focus_title,
            user_custom_topic=user_custom_topic,
            language=language,
            recent_text_context=recent_text_context,
        )
        normalized_text_plan = normalize_text_plan(text_plan, language=language)
        text_plan_summary = build_text_plan_summary(normalized_text_plan)
        return build_text_plan_shadow_payload(
            text_plan=normalized_text_plan,
            text_plan_summary=text_plan_summary,
        )
    except Exception:
        logger.exception("Text planner shadow mode failed for sphere=%s", sphere)
        return None


def attach_text_plan_shadow_to_metadata(
    metadata: dict | None,
    text_plan_shadow_payload: dict | None,
) -> dict:
    result = dict(metadata) if isinstance(metadata, dict) else {}
    if text_plan_shadow_payload is not None:
        result["text_plan_shadow"] = text_plan_shadow_payload
    return result
