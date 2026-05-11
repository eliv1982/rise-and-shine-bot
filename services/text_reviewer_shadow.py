import logging

from config import get_settings
from services.text_reviewer import review_generated_text

logger = logging.getLogger(__name__)


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


def is_text_reviewer_shadow_enabled(settings: object | None = None) -> bool:
    try:
        effective_settings = settings or get_settings()
        value = getattr(effective_settings, "text_reviewer_shadow_enabled", False)
        return _coerce_bool(value)
    except Exception:
        return False


def build_text_reviewer_shadow_payload(
    *,
    affirmations: list[str] | None,
    soft_action: str | None,
    focus_title: str | None,
    language: str = "ru",
    gender_hint: str | None = None,
    text_plan: dict | None = None,
    text_memory_context: dict | None = None,
) -> dict | None:
    report = review_generated_text(
        affirmations=affirmations,
        soft_action=soft_action,
        focus_title=focus_title,
        language=language,
        gender_hint=gender_hint,
        text_plan=text_plan,
        text_memory_context=text_memory_context,
    )
    return {
        "enabled": True,
        "language": report.get("language", language),
        "checks": report.get("checks", {}),
        "warnings": list(report.get("warnings") or [])[:5],
        "score": report.get("score", 1.0),
    }


def build_text_reviewer_shadow_best_effort(
    *,
    affirmations: list[str] | None,
    soft_action: str | None,
    focus_title: str | None,
    language: str = "ru",
    gender_hint: str | None = None,
    text_plan: dict | None = None,
    text_memory_context: dict | None = None,
    settings: object | None = None,
) -> dict | None:
    if not is_text_reviewer_shadow_enabled(settings):
        return None
    try:
        return build_text_reviewer_shadow_payload(
            affirmations=affirmations,
            soft_action=soft_action,
            focus_title=focus_title,
            language=language,
            gender_hint=gender_hint,
            text_plan=text_plan,
            text_memory_context=text_memory_context,
        )
    except Exception:
        logger.exception("Text reviewer shadow mode failed for focus=%s", focus_title)
        return None


def attach_text_reviewer_shadow_to_metadata(metadata: dict, payload: dict | None) -> dict:
    result = dict(metadata) if isinstance(metadata, dict) else {}
    if payload is not None:
        result["text_reviewer_shadow"] = payload
    return result
