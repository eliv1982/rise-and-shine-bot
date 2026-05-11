from config import get_settings
from services.text_planner import normalize_text_plan
from utils import infer_gender_from_hint


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
    gender_hint: str | None = None,
    text_memory_context: dict | None = None,
) -> str | None:
    if not isinstance(text_plan, dict) or not text_plan:
        return None

    normalized = normalize_text_plan(text_plan, language=language)
    affirmation_angles = ", ".join(normalized["affirmation_angles"]) or "—"
    avoid = ", ".join(normalized["avoid"]) or "—"
    output_language = "Russian" if normalized["language"] == "ru" else "English"
    gender_lines: list[str] = []
    if normalized["language"] == "ru":
        normalized_gender = infer_gender_from_hint(gender_hint)
        if gender_hint:
            if normalized_gender == "female":
                gender_lines = [
                    "Respect the user's Russian grammatical gender: feminine.",
                    "Use feminine forms when needed: готова, выбрала, уверена, открыта, спокойна, сосредоточена.",
                    "Avoid masculine forms when feminine agreement is required: готов, выбрал, уверен, открыт, спокоен, сосредоточен.",
                ]
            elif normalized_gender == "male":
                gender_lines = [
                    "Respect the user's Russian grammatical gender: masculine.",
                    "Use masculine forms when needed: готов, выбрал, уверен, открыт, спокоен, сосредоточен.",
                    "Avoid feminine forms when masculine agreement is required: готова, выбрала, уверена, открыта, спокойна, сосредоточена.",
                ]
            else:
                gender_lines = [
                    "Respect the user's Russian grammatical gender carefully.",
                    "Prefer gender-neutral Russian wording where possible.",
                ]
    memory = text_memory_context if isinstance(text_memory_context, dict) else {}
    memory_lines: list[str] = []
    if memory:
        recent_focus_titles = ", ".join(memory.get("recent_focus_titles") or []) or "—"
        overused_text_patterns = ", ".join(memory.get("overused_text_patterns") or []) or "—"
        avoid_soft_actions = ", ".join(memory.get("avoid_soft_actions") or []) or "—"
        avoid_soft_action_patterns = ", ".join(memory.get("avoid_soft_action_patterns") or []) or "—"
        avoid_phrases = ", ".join(memory.get("avoid_phrases") or []) or "—"
        style_guidance = "; ".join(memory.get("style_guidance") or []) or "—"
        memory_lines = [
            "Text memory / anti-repeat guidance:",
            f"- recent_focus_titles: {recent_focus_titles}",
            f"- overused_text_patterns: {overused_text_patterns}",
            f"- avoid_soft_actions: {avoid_soft_actions}",
            f"- avoid_soft_action_patterns: {avoid_soft_action_patterns}",
            f"- avoid_phrases: {avoid_phrases}",
            f"- style_guidance: {style_guidance}",
            "- Avoid repeating recent affirmation openings and vary wording.",
            "- Do not reuse recent soft action verbatim.",
            "- Do not reuse recent soft action structure.",
            "- If recent actions asked the user to name three things, choose a different action type.",
            "- Vary the soft action verb and structure.",
        ]

    return "\n".join(
        [
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
        ]
        + gender_lines
        + memory_lines
    )
