import json

VALID_TONES = {
    "soft_grounded",
    "calm_clear",
    "warm_confident",
    "gentle_practical",
    "quiet_encouraging",
}

DEFAULT_AVOID = [
    "toxic positivity",
    "pressure",
    "productivity framing",
    "moralizing",
]

THEME_DEFAULTS = {
    "inner_peace": {
        "theme_category": "inner_peace",
        "focus_title": "внутренний покой",
        "tone": "soft_grounded",
        "emotional_direction": "gentle return to inner steadiness",
        "affirmation_intent": "reduce internal pressure and support calm clarity",
        "affirmation_angles": [
            "breathing space",
            "inner steadiness",
            "permission to slow down",
        ],
        "soft_action_intent": "one small pause to return to yourself",
        "soft_action_style": "small_concrete_step",
    },
    "self_worth": {
        "theme_category": "self_worth",
        "focus_title": "самоценность",
        "tone": "warm_confident",
        "emotional_direction": "self-worth without proof or overexertion",
        "affirmation_intent": "strengthen dignity and reduce self-doubt",
        "affirmation_angles": [
            "worth without achievement",
            "self-loyalty",
            "gentle confidence",
        ],
        "soft_action_intent": "one small act of self-respect",
        "soft_action_style": "small_concrete_step",
    },
    "body_energy": {
        "theme_category": "body_energy",
        "focus_title": "энергия и тело",
        "tone": "gentle_practical",
        "emotional_direction": "care for the body without pressure",
        "affirmation_intent": "support restoration and kind body connection",
        "affirmation_angles": [
            "body care",
            "right to rest",
            "gentle restoration",
        ],
        "soft_action_intent": "one small restoring action for the body",
        "soft_action_style": "small_concrete_step",
    },
    "work_career": {
        "theme_category": "work_career",
        "focus_title": "дело и карьера",
        "tone": "calm_clear",
        "emotional_direction": "calm professional dignity and clear movement",
        "affirmation_intent": "support steady professional focus without strain",
        "affirmation_angles": [
            "clarity of direction",
            "professional dignity",
            "one meaningful step",
        ],
        "soft_action_intent": "one clear work step without rushing",
        "soft_action_style": "small_concrete_step",
    },
    "money_stability": {
        "theme_category": "money_stability",
        "focus_title": "деньги и устойчивость",
        "tone": "gentle_practical",
        "emotional_direction": "financial steadiness without fear or shame",
        "affirmation_intent": "reduce anxiety around money and support grounded clarity",
        "affirmation_angles": [
            "enoughness",
            "financial clarity",
            "stability without panic",
        ],
        "soft_action_intent": "one small calm step toward financial clarity",
        "soft_action_style": "small_concrete_step",
    },
    "relationships_boundaries": {
        "theme_category": "relationships_boundaries",
        "focus_title": "отношения и границы",
        "tone": "quiet_encouraging",
        "emotional_direction": "warmth with boundaries and self-respect",
        "affirmation_intent": "support safe closeness and honest boundaries",
        "affirmation_angles": [
            "clear yes and no",
            "respect for self and other",
            "safe contact",
        ],
        "soft_action_intent": "one small honest boundary or caring phrase",
        "soft_action_style": "small_concrete_step",
    },
    "creativity_self_expression": {
        "theme_category": "creativity_self_expression",
        "focus_title": "творчество и самореализация",
        "tone": "quiet_encouraging",
        "emotional_direction": "creative expression without perfection pressure",
        "affirmation_intent": "support visibility, curiosity and small creative courage",
        "affirmation_angles": [
            "permission to try",
            "creative voice",
            "small visible step",
        ],
        "soft_action_intent": "one small creative action without judging the result",
        "soft_action_style": "small_concrete_step",
    },
    "home_support": {
        "theme_category": "home_support",
        "focus_title": "дом и опора",
        "tone": "soft_grounded",
        "emotional_direction": "return to safety, comfort and everyday grounding",
        "affirmation_intent": "support home-based steadiness and soft recovery",
        "affirmation_angles": [
            "comfort and safety",
            "everyday support",
            "rest without guilt",
        ],
        "soft_action_intent": "one small home-supportive action that adds comfort or order",
        "soft_action_style": "small_concrete_step",
    },
    "custom": {
        "theme_category": "custom",
        "focus_title": "своя тема",
        "tone": "soft_grounded",
        "emotional_direction": "gentle support around the chosen topic",
        "affirmation_intent": "create emotionally supportive and grounded affirmations",
        "affirmation_angles": [
            "gentle clarity",
            "small support",
            "non-judgmental encouragement",
        ],
        "soft_action_intent": "one small concrete supportive step",
        "soft_action_style": "small_concrete_step",
    },
}

SPHERE_TO_THEME_CATEGORY = {
    "inner_peace": "inner_peace",
    "self_worth": "self_worth",
    "health": "body_energy",
    "career": "work_career",
    "money": "money_stability",
    "relationships": "relationships_boundaries",
    "self_realization": "creativity_self_expression",
    "home_support": "home_support",
}

SPHERE_DEFAULT_FOCUS = {
    "inner_peace": "внутренний покой",
    "self_worth": "самоценность",
    "health": "бережное восстановление",
    "career": "спокойная собранность",
    "money": "устойчивость и достаточность",
    "relationships": "тепло и границы",
    "self_realization": "свой голос",
    "home_support": "дом и опора",
}


def _safe_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _safe_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    return []


def _clean_str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dedupe_stable(items: list) -> list[str]:
    seen = set()
    result = []
    for item in items:
        text = _clean_str(item)
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(text)
    return result


def _normalize_tone(value) -> str:
    text = _clean_str(value)
    if text in VALID_TONES:
        return text
    return "soft_grounded"


def _normalize_language(value) -> str:
    text = _clean_str(value)
    if text and text.lower() == "en":
        return "en"
    return "ru"


def _theme_defaults(theme_category: str) -> dict:
    return dict(THEME_DEFAULTS.get(theme_category, THEME_DEFAULTS["custom"]))


def infer_theme_category(
    *,
    sphere: str | None = None,
    subsphere: str | None = None,
    focus_title: str | None = None,
    user_custom_topic: str | None = None,
) -> str:
    direct = SPHERE_TO_THEME_CATEGORY.get(_clean_str(sphere) or "")
    if direct:
        return direct

    haystack = " ".join(
        text.lower()
        for text in (
            _clean_str(subsphere),
            _clean_str(focus_title),
            _clean_str(user_custom_topic),
        )
        if text
    )
    if not haystack:
        return "custom"
    if any(token in haystack for token in ("money", "finance", "financial", "деньги", "финанс", "достаточ", "устойчив")):
        return "money_stability"
    if any(token in haystack for token in ("career", "work", "job", "professional", "карьер", "работ", "профессион")):
        return "work_career"
    if any(token in haystack for token in ("home", "house", "cozy", "comfort", "дом", "уют", "опор", "безопас")):
        return "home_support"
    if any(token in haystack for token in ("relationship", "partner", "boundary", "отнош", "границ", "близост")):
        return "relationships_boundaries"
    if any(token in haystack for token in ("creative", "creativity", "art", "voice", "творч", "самореал", "прояв")):
        return "creativity_self_expression"
    if any(token in haystack for token in ("body", "health", "rest", "energy", "тело", "здоров", "отдых", "энер")):
        return "body_energy"
    if any(token in haystack for token in ("worth", "confidence", "self-worth", "самоцен", "уверенн", "достоин")):
        return "self_worth"
    if any(token in haystack for token in ("peace", "calm", "stillness", "покой", "спокой", "тишин", "ясност")):
        return "inner_peace"
    return "custom"


def build_text_planner_prompt(
    *,
    sphere: str | None = None,
    subsphere: str | None = None,
    focus_title: str | None = None,
    user_custom_topic: str | None = None,
    language: str = "ru",
    recent_text_context: dict | None = None,
) -> str:
    recent = _safe_dict(recent_text_context)
    normalized_language = _normalize_language(language)
    return (
        "You are a Text Planner for a daily Telegram mood text.\n"
        "Return JSON only.\n"
        "Build a gentle, grounded text plan for affirmations and one soft action.\n"
        "Avoid toxic positivity, pressure, repetitive affirmations, productivity framing and moralizing.\n"
        "Soft action should be concrete, small and realistic.\n"
        f"Use {'Russian' if normalized_language == 'ru' else 'English'} output values where appropriate.\n\n"
        f"sphere: {_clean_str(sphere) or '—'}\n"
        f"subsphere: {_clean_str(subsphere) or '—'}\n"
        f"focus_title: {_clean_str(focus_title) or '—'}\n"
        f"user_custom_topic: {_clean_str(user_custom_topic) or '—'}\n"
        f"language: {normalized_language}\n"
        f"recent_text_context: {json.dumps(recent, ensure_ascii=False)}\n\n"
        "Expected JSON schema:\n"
        "{\n"
        '  "theme_category": "rest_self_care",\n'
        '  "focus_title": "право на отдых",\n'
        '  "tone": "soft_grounded",\n'
        '  "emotional_direction": "permission_to_rest_without_guilt",\n'
        '  "affirmation_intent": "reduce guilt and support recovery",\n'
        '  "affirmation_angles": ["body care", "permission to pause"],\n'
        '  "soft_action_intent": "one short guilt-free pause",\n'
        '  "soft_action_style": "small_concrete_step",\n'
        '  "avoid": ["toxic positivity", "pressure"],\n'
        '  "language": "ru"\n'
        "}\n"
    )


def parse_text_plan_response(raw_text: str | None) -> dict | None:
    text = _clean_str(raw_text)
    if not text:
        return None

    candidates = [text]
    if "```" in text:
        for chunk in text.split("```"):
            cleaned = chunk.strip()
            if not cleaned:
                continue
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
            candidates.append(cleaned)

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidates.append(text[first_brace:last_brace + 1].strip())

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def normalize_text_plan(plan: dict | None, *, language: str = "ru") -> dict:
    safe = _safe_dict(plan)
    normalized_language = _normalize_language(safe.get("language") or language)
    theme_category = _clean_str(safe.get("theme_category")) or "custom"
    defaults = _theme_defaults(theme_category)

    result = {
        "theme_category": theme_category,
        "focus_title": _clean_str(safe.get("focus_title")) or defaults["focus_title"],
        "tone": _normalize_tone(safe.get("tone") or defaults["tone"]),
        "emotional_direction": _clean_str(safe.get("emotional_direction")) or defaults["emotional_direction"],
        "affirmation_intent": _clean_str(safe.get("affirmation_intent")) or defaults["affirmation_intent"],
        "affirmation_angles": _dedupe_stable(_safe_list(safe.get("affirmation_angles")) or defaults["affirmation_angles"]),
        "soft_action_intent": _clean_str(safe.get("soft_action_intent")) or defaults["soft_action_intent"],
        "soft_action_style": _clean_str(safe.get("soft_action_style")) or defaults["soft_action_style"],
        "avoid": _dedupe_stable(_safe_list(safe.get("avoid")) + DEFAULT_AVOID),
        "language": normalized_language,
    }
    return result


def build_fallback_text_plan(
    *,
    sphere: str | None = None,
    subsphere: str | None = None,
    focus_title: str | None = None,
    user_custom_topic: str | None = None,
    language: str = "ru",
    recent_text_context: dict | None = None,
) -> dict:
    del recent_text_context
    theme_category = infer_theme_category(
        sphere=sphere,
        subsphere=subsphere,
        focus_title=focus_title,
        user_custom_topic=user_custom_topic,
    )
    defaults = _theme_defaults(theme_category)
    chosen_focus = (
        _clean_str(focus_title)
        or _clean_str(user_custom_topic)
        or SPHERE_DEFAULT_FOCUS.get(_clean_str(sphere) or "", defaults["focus_title"])
        or defaults["focus_title"]
    )
    fallback = {
        "theme_category": theme_category,
        "focus_title": chosen_focus,
        "tone": defaults["tone"],
        "emotional_direction": defaults["emotional_direction"],
        "affirmation_intent": defaults["affirmation_intent"],
        "affirmation_angles": list(defaults["affirmation_angles"]),
        "soft_action_intent": defaults["soft_action_intent"],
        "soft_action_style": defaults["soft_action_style"],
        "avoid": list(DEFAULT_AVOID),
        "language": _normalize_language(language),
    }
    return normalize_text_plan(fallback, language=language)


def build_text_plan_summary(text_plan: dict) -> str:
    plan = normalize_text_plan(text_plan)
    angles = ", ".join(plan["affirmation_angles"][:3]) or "—"
    avoid = ", ".join(plan["avoid"][:4]) or "—"
    return (
        f"theme_category: {plan['theme_category']}\n"
        f"focus_title: {plan['focus_title']}\n"
        f"tone: {plan['tone']}\n"
        f"affirmation_angles: {angles}\n"
        f"avoid: {avoid}"
    )
