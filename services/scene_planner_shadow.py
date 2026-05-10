import logging

from config import get_settings
from services.scene_planner import (
    build_fallback_scene_plan,
    build_scene_image_prompt,
    build_scene_planner_prompt,
    normalize_scene_plan,
)
from services.visual_memory import get_visual_memory_context

logger = logging.getLogger(__name__)
_MAX_SCENE_IMAGE_BRIEF_LENGTH = 1000


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


def is_scene_planner_shadow_enabled(settings: object | None = None) -> bool:
    try:
        effective_settings = settings or get_settings()
        value = getattr(effective_settings, "scene_planner_shadow_enabled", False)
        return _coerce_bool(value)
    except Exception:
        return False


def build_scene_plan_shadow_payload(
    *,
    scene_plan: dict,
    visual_memory_context: dict | None = None,
    scene_image_brief: str | None = None,
) -> dict:
    memory = _safe_dict(visual_memory_context)
    brief = (scene_image_brief or "").strip()
    if len(brief) > _MAX_SCENE_IMAGE_BRIEF_LENGTH:
        brief = brief[:_MAX_SCENE_IMAGE_BRIEF_LENGTH].rstrip() + "..."

    return {
        "enabled": True,
        "mode": "local_fallback",
        "llm_used": False,
        "scene_plan": normalize_scene_plan(scene_plan, visual_memory_context=memory),
        "scene_image_brief": brief or None,
        "visual_memory_summary": {
            "recent_scene_types": list(memory.get("recent_scene_types") or []),
            "hard_avoid_today": list(memory.get("hard_avoid_today") or []),
            "prefer_scene_types": list(memory.get("prefer_scene_types") or []),
            "overused_motifs": list(memory.get("overused_motifs") or []),
        },
    }


async def build_scene_plan_shadow_best_effort(
    *,
    telegram_user_id: int,
    focus_title: str | None,
    affirmations: list[str] | None,
    soft_action: str | None,
    language: str = "ru",
    settings: object | None = None,
) -> dict | None:
    if not is_scene_planner_shadow_enabled(settings):
        return None

    try:
        visual_memory_context = await get_visual_memory_context(telegram_user_id, limit=10)
        # Build the planner prompt to verify prompt assembly path, but do not persist the full prompt.
        build_scene_planner_prompt(
            focus_title=focus_title,
            affirmations=affirmations,
            soft_action=soft_action,
            visual_memory_context=visual_memory_context,
            language=language,
        )
        scene_plan = build_fallback_scene_plan(
            focus_title=focus_title,
            visual_memory_context=visual_memory_context,
        )
        normalized_scene_plan = normalize_scene_plan(
            scene_plan,
            visual_memory_context=visual_memory_context,
        )
        scene_image_brief = build_scene_image_prompt(normalized_scene_plan, language=language)
        return build_scene_plan_shadow_payload(
            scene_plan=normalized_scene_plan,
            visual_memory_context=visual_memory_context,
            scene_image_brief=scene_image_brief,
        )
    except Exception:
        logger.exception("Scene planner shadow mode failed for user %s", telegram_user_id)
        return None


def attach_scene_plan_shadow_to_visual_motifs(
    visual_motifs: dict | None,
    scene_plan_shadow_payload: dict | None,
) -> dict:
    result = dict(visual_motifs) if isinstance(visual_motifs, dict) else {}
    if scene_plan_shadow_payload is not None:
        result["scene_plan_shadow"] = scene_plan_shadow_payload
    return result
