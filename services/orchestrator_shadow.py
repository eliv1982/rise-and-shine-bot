import logging

from config import get_settings

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


def is_orchestrator_shadow_enabled(settings: object | None = None) -> bool:
    try:
        effective_settings = settings or get_settings()
        value = getattr(effective_settings, "orchestrator_shadow_enabled", False)
        return _coerce_bool(value)
    except Exception:
        return False


def _clean_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_orchestrator_shadow_payload(
    *,
    language: str = "ru",
    sphere: str | None = None,
    subsphere: str | None = None,
    focus_title: str | None = None,
    selected_style: str | None = None,
    visual_mode: str | None = None,
    text_plan_shadow: dict | None = None,
    text_prompt_controlled: dict | None = None,
    text_memory_context: dict | None = None,
    text_reviewer_shadow: dict | None = None,
    scene_plan_shadow: dict | None = None,
    scene_prompt_controlled: dict | None = None,
    profile_guidance_meta: dict | None = None,
) -> dict | None:
    route = {
        "text_planner": isinstance(text_plan_shadow, dict),
        "text_memory": isinstance(text_memory_context, dict) and bool(text_memory_context),
        "text_reviewer": isinstance(text_reviewer_shadow, dict),
        "scene_planner": isinstance(scene_plan_shadow, dict),
        "scene_prompt_controlled": isinstance(scene_prompt_controlled, dict),
        "profile_preferences": isinstance(profile_guidance_meta, dict) and bool(profile_guidance_meta),
    }
    if isinstance(text_prompt_controlled, dict):
        route["text_planner"] = True

    quality = {
        "text_reviewer_score": (text_reviewer_shadow or {}).get("score") if isinstance(text_reviewer_shadow, dict) else None,
        "text_warnings_count": len((text_reviewer_shadow or {}).get("warnings") or []) if isinstance(text_reviewer_shadow, dict) else 0,
        "text_memory_overused_count": (
            len((text_memory_context or {}).get("overused_text_patterns") or [])
            + len((text_memory_context or {}).get("overused_soft_action_patterns") or [])
        ) if isinstance(text_memory_context, dict) else 0,
        "profile_preferences_count": int((profile_guidance_meta or {}).get("profile_preferences_count") or 0)
        if isinstance(profile_guidance_meta, dict) else 0,
        "profile_avoid_constraints_count": int((profile_guidance_meta or {}).get("profile_avoid_constraints_count") or 0)
        if isinstance(profile_guidance_meta, dict) else 0,
    }

    decisions: list[str] = []
    if isinstance(text_prompt_controlled, dict) and text_prompt_controlled.get("guidance_used"):
        decisions.append("text planner guidance used")
    if route["text_memory"]:
        decisions.append("text memory anti-repeat used")
    if route["profile_preferences"]:
        decisions.append("profile preferences guidance used")
    if isinstance(text_reviewer_shadow, dict):
        decisions.append("text reviewer shadow used")
    if isinstance(scene_plan_shadow, dict):
        decisions.append("scene planner shadow used")
    if isinstance(scene_prompt_controlled, dict):
        decisions.append("scene controlled prompt used")

    return {
        "enabled": True,
        "mode": "shadow",
        "language": language,
        "route": route,
        "inputs": {
            "sphere": _clean_text(sphere),
            "subsphere": _clean_text(subsphere),
            "focus_title": _clean_text(focus_title),
            "selected_style": _clean_text(selected_style),
            "visual_mode": _clean_text(visual_mode),
            "profile_used": bool((profile_guidance_meta or {}).get("profile_used")) if isinstance(profile_guidance_meta, dict) else False,
            "profile_current_focus_used": bool((profile_guidance_meta or {}).get("profile_current_focus_used")) if isinstance(profile_guidance_meta, dict) else False,
        },
        "quality": quality,
        "decisions": decisions,
    }


def build_orchestrator_shadow_best_effort(
    *,
    settings: object | None = None,
    language: str = "ru",
    sphere: str | None = None,
    subsphere: str | None = None,
    focus_title: str | None = None,
    selected_style: str | None = None,
    visual_mode: str | None = None,
    text_plan_shadow: dict | None = None,
    text_prompt_controlled: dict | None = None,
    text_memory_context: dict | None = None,
    text_reviewer_shadow: dict | None = None,
    scene_plan_shadow: dict | None = None,
    scene_prompt_controlled: dict | None = None,
    profile_guidance_meta: dict | None = None,
) -> dict | None:
    if not is_orchestrator_shadow_enabled(settings):
        return None
    try:
        return build_orchestrator_shadow_payload(
            language=language,
            sphere=sphere,
            subsphere=subsphere,
            focus_title=focus_title,
            selected_style=selected_style,
            visual_mode=visual_mode,
            text_plan_shadow=text_plan_shadow,
            text_prompt_controlled=text_prompt_controlled,
            text_memory_context=text_memory_context,
            text_reviewer_shadow=text_reviewer_shadow,
            scene_plan_shadow=scene_plan_shadow,
            scene_prompt_controlled=scene_prompt_controlled,
            profile_guidance_meta=profile_guidance_meta,
        )
    except Exception:
        logger.exception("Orchestrator shadow mode failed for focus=%s", focus_title)
        return None


def attach_orchestrator_shadow_to_metadata(metadata: dict, payload: dict | None) -> dict:
    result = dict(metadata) if isinstance(metadata, dict) else {}
    if payload is not None:
        result["orchestrator_shadow"] = payload
    return result
