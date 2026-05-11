from config import get_settings
from services.text_planner import normalize_text_plan


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


def is_text_planner_controlled_enabled(settings: object | None = None) -> bool:
    try:
        effective_settings = settings or get_settings()
        return _coerce_bool(getattr(effective_settings, "text_planner_controlled_enabled", False))
    except Exception:
        return False


def build_text_generation_guidance(
    *,
    text_plan: dict | None,
    language: str = "ru",
) -> str | None:
    if not isinstance(text_plan, dict) or not text_plan:
        return None

    normalized = normalize_text_plan(text_plan, language=language)
    affirmation_angles = ", ".join(normalized["affirmation_angles"]) or "—"
    avoid = ", ".join(normalized["avoid"]) or "—"
    output_language = "Russian" if normalized["language"] == "ru" else "English"

    return (
        "Text planner guidance:\n"
        f"- theme_category: {normalized['theme_category']}\n"
        f"- focus_title: {normalized['focus_title']}\n"
        f"- tone: {normalized['tone']}\n"
        f"- emotional_direction: {normalized['emotional_direction']}\n"
        f"- affirmation_intent: {normalized['affirmation_intent']}\n"
        f"- affirmation_angles: {affirmation_angles}\n"
        f"- soft_action_intent: {normalized['soft_action_intent']}\n"
        f"- soft_action_style: {normalized['soft_action_style']}\n"
        f"- avoid: {avoid}\n"
        f"- Output language: {output_language}\n"
        "- Keep the final text gentle, grounded and emotionally precise.\n"
        "- Avoid toxic positivity, pressure, moralizing and repetitive generic affirmations.\n"
    )
