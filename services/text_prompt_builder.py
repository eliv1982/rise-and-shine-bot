from config import get_settings
from services.language_policy import normalize_language
from services.text_planner import normalize_text_plan
from utils import infer_gender_from_hint


PROFILE_GUIDANCE_MAX_CHARS = 2000


class ProfileGuidanceBudgetError(ValueError):
    """Exclusions cannot fit intact; never send a partially applied avoid list."""


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


def _clean_profile_scalar(value) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    return text or None


def _clean_profile_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        cleaned = _clean_profile_scalar(item)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def normalize_profile_text_preferences(preferences) -> dict:
    """Defend generation against malformed legacy data without stringifying it."""
    if not isinstance(preferences, dict):
        return {}
    result = {}
    for key in ("tone_preference", "support_style", "text_length_preference", "current_focus"):
        value = _clean_profile_scalar(preferences.get(key))
        if value:
            result[key] = value
    for key in ("life_areas", "avoid_topics", "avoid_words"):
        value = _clean_profile_list(preferences.get(key))
        if value:
            result[key] = value
    return result


def build_profile_text_guidance(
    *,
    preferences: dict | None,
    language: str = "ru",
) -> str | None:
    preferences = normalize_profile_text_preferences(preferences)
    if not preferences:
        return None

    # Language, gender, voice and JSON rules belong to the provider's base prompt.
    # Keep only Profile-specific guidance here, with explicit planner precedence.
    lines = [
        "Profile preference guidance:",
        "- Apply saved preferences within the required language, grammatical gender, four short affirmations and JSON format.",
        "- Profile exclusions and tone/support/length preferences override planner suggestions.",
    ]
    for key in ("avoid_topics", "avoid_words"):
        if preferences.get(key):
            lines.append(f"- {key}: {', '.join(preferences[key])}")
    if preferences.get("avoid_topics") or preferences.get("avoid_words"):
        lines.append("- Do not center the text on avoid_topics or use avoid_words verbatim.")
    if len("\n".join(lines)) > PROFILE_GUIDANCE_MAX_CHARS:
        raise ProfileGuidanceBudgetError("Profile avoid-topic/avoid-word constraints exceed the prompt budget")

    # Exclusions are never clipped. Then allocate remaining space in a stable
    # order, with per-field caps so a long focus cannot consume every preference.
    for key, label, cap in (
        ("tone_preference", "preferred_tone", 100),
        ("support_style", "preferred_support_style", 100),
        ("text_length_preference", "preferred_text_length", 60),
        ("current_focus", "current_focus_context", 400),
        ("life_areas", "life_areas", 200),
    ):
        value = preferences.get(key)
        if not value:
            continue
        if isinstance(value, list):
            value = ", ".join(value)
        prefix = f"- {label}: "
        available = min(cap, PROFILE_GUIDANCE_MAX_CHARS - len("\n".join(lines)) - 1 - len(prefix))
        if available < 2:
            continue
        if len(value) > available:
            value = value[: available - 1].rstrip() + "…"
        lines.append(prefix + value)
    return "\n".join(lines)


def build_text_generation_guidance(
    *,
    text_plan: dict | None,
    language: str = "ru",
    gender_hint: str | None = None,
    text_memory_context: dict | None = None,
) -> str | None:
    if not isinstance(text_plan, dict) or not text_plan:
        return None

    language = normalize_language(language)
    normalized = normalize_text_plan({**text_plan, "language": language}, language=language)
    affirmation_angles = ", ".join(normalized["affirmation_angles"]) or "—"
    avoid = ", ".join(normalized["avoid"]) or "—"
    output_language = "Russian" if normalized["language"] == "ru" else "English"
    language_rules = (
        "- For Russian output, keep the surrounding prose in Russian.\n"
        "- Translate English prose and action phrases in focus and affirmations; preserve proper nouns, brands, abbreviations and technical terms in their original spelling.\n"
        if language == "ru" else
        "- Keep the surrounding prose in English.\n"
        "- Render Russian source prose in English, preserving meaning and the original spelling of proper nouns, brands, abbreviations and technical terms.\n"
    )
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
        f"{language_rules}"
        "- Keep the final text gentle, grounded and emotionally precise.\n"
        "- Avoid toxic positivity, pressure, moralizing and repetitive generic affirmations.\n"
        "- Use varied affirmation openings and keep wording warm, natural and personal.\n"
        "- Keep soft actions warm and personal, not dry, bureaucratic or overly instructional.\n"
        ]
        + gender_lines
        + voice_lines
        + memory_lines
    )
