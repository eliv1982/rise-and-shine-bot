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
    voice_lines: list[str] = []
    if normalized["language"] == "ru":
        voice_lines = [
            "Preserve warm informal singular Russian address: use «ты», not «Вы/вы».",
            "Soft action should use informal singular imperative.",
            "Avoid formal/plural imperatives like: выберите, назовите, сделайте, примите, упростите, запишите, заметьте, позвольте.",
            "Use forms like: выбери, назови, сделай, прими, упрости, запиши, заметь, позволь себе.",
        ]
        normalized_gender = infer_gender_from_hint(gender_hint)
        if gender_hint:
            if normalized_gender == "female":
                gender_lines = [
                    "Respect the user's Russian grammatical gender: feminine.",
                    "Use feminine forms when needed: готова, выбрала, уверена, открыта, спокойна, сосредоточена.",
                    "Avoid masculine forms when feminine agreement is required: готов, выбрал, уверен, открыт, спокоен, сосредоточен.",
                    "Avoid masculine self-reference like: таким, какой я есть.",
                    "Prefer feminine or neutral wording when needed: такой, какая я есть; or a neutral rewrite.",
                ]
            elif normalized_gender == "male":
                gender_lines = [
                    "Respect the user's Russian grammatical gender: masculine.",
                    "Use masculine forms when needed: готов, выбрал, уверен, открыт, спокоен, сосредоточен.",
                    "Avoid feminine forms when masculine agreement is required: готова, выбрала, уверена, открыта, спокойна, сосредоточена.",
                    "Use masculine self-reference when such wording is needed: таким, какой я есть.",
                ]
            else:
                gender_lines = [
                    "Respect the user's Russian grammatical gender carefully.",
                    "Prefer gender-neutral Russian wording where possible.",
                    "Avoid gendered self-descriptions when neutral wording can work better.",
                    "Prefer neutral rewrites like: Я принимаю себя без необходимости что-то доказывать.",
                ]
    memory = text_memory_context if isinstance(text_memory_context, dict) else {}
    memory_lines: list[str] = []
    if memory:
        recent_focus_titles = ", ".join(memory.get("recent_focus_titles") or []) or "—"
        overused_text_patterns = ", ".join(memory.get("overused_text_patterns") or []) or "—"
        recent_affirmation_openings = ", ".join(memory.get("recent_affirmation_openings") or []) or "—"
        overused_affirmation_openings = ", ".join(memory.get("overused_affirmation_openings") or []) or "—"
        avoid_affirmation_openings = ", ".join(memory.get("avoid_affirmation_openings") or []) or "—"
        avoid_soft_actions = ", ".join(memory.get("avoid_soft_actions") or []) or "—"
        avoid_soft_action_patterns = ", ".join(memory.get("avoid_soft_action_patterns") or []) or "—"
        avoid_soft_action_structures = ", ".join(memory.get("avoid_soft_action_structures") or []) or "—"
        overused_soft_action_structures = ", ".join(memory.get("overused_soft_action_structures") or []) or "—"
        overused_abstract_words = ", ".join(memory.get("overused_abstract_words") or []) or "—"
        avoid_phrases = ", ".join(memory.get("avoid_phrases") or []) or "—"
        style_guidance = "; ".join(memory.get("style_guidance") or []) or "—"
        variation_guidance = "; ".join(memory.get("variation_guidance") or []) or "—"
        memory_lines = [
            "Text memory / anti-repeat guidance:",
            f"- recent_focus_titles: {recent_focus_titles}",
            f"- recent_affirmation_openings: {recent_affirmation_openings}",
            f"- overused_text_patterns: {overused_text_patterns}",
            f"- overused_affirmation_openings: {overused_affirmation_openings}",
            f"- avoid_affirmation_openings: {avoid_affirmation_openings}",
            f"- avoid_soft_actions: {avoid_soft_actions}",
            f"- avoid_soft_action_patterns: {avoid_soft_action_patterns}",
            f"- avoid_soft_action_structures: {avoid_soft_action_structures}",
            f"- overused_soft_action_structures: {overused_soft_action_structures}",
            f"- overused_abstract_words: {overused_abstract_words}",
            f"- avoid_phrases: {avoid_phrases}",
            f"- style_guidance: {style_guidance}",
            f"- variation_guidance: {variation_guidance}",
            "- Avoid repeating recent affirmation openings and vary wording.",
            "- Vary affirmation openings and sentence structures, not only the final noun.",
            "- Do not make every affirmation start with the same 'I + verb' pattern.",
            "- Do not reuse recent soft action verbatim.",
            "- Do not reuse recent soft action structure.",
            "- Avoid repeating recent soft action structures like 'Прими одно ... из ..., а не из ...'.",
            "- Avoid overusing the 'из X, а не из Y' contrast formula.",
            "- If recent actions asked the user to name three things, choose a different action type.",
            "- Vary the soft action verb and structure.",
            "- Prefer a concrete, grounded, small real-life action over stacked abstract nouns.",
            "- Mention an observable action or a practical context when possible.",
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
        "- For Russian output, keep all user-facing text strictly in Russian.\n"
        "- Do not leave English words or English action phrases in focus, affirmations, soft action or micro-step.\n"
        "- Keep the final text gentle, grounded and emotionally precise.\n"
        "- Avoid toxic positivity, pressure, moralizing and repetitive generic affirmations.\n"
        "- Use varied affirmation openings and keep wording warm, natural and personal.\n"
        "- Keep soft actions warm and personal, not dry, bureaucratic or overly instructional.\n"
        ]
        + gender_lines
        + voice_lines
        + memory_lines
    )
