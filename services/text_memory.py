from __future__ import annotations

from collections import Counter

from database import get_recent_generation_history

TEXT_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("я позволяю", ("я позволяю",)),
    ("я выбираю", ("я выбираю", "и выбираю")),
    ("я принимаю", ("я принимаю", "и принимаю")),
    ("я создаю", ("я создаю", "и создаю")),
    ("я нахожу", ("я нахожу", "и нахожу")),
    ("маленький шаг", ("маленький шаг", "small step")),
    ("без чувства вины", ("без чувства вины", "without guilt", "guilt-free")),
    ("спокойствие", ("спокойствие", "calm")),
    ("устойчивость", ("устойчивость", "stability")),
    ("ясность", ("ясность", "clarity")),
    ("достаточность", ("достаточность", "enoughness")),
    ("я могу", ("я могу", "i can")),
    ("я доверяю", ("я доверяю", "i trust")),
    ("я возвращаюсь", ("я возвращаюсь", "i return")),
    ("мягко", ("мягко", "gently")),
]

AFFIRMATION_OPENING_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("я выбираю", ("я выбираю",)),
    ("я принимаю", ("я принимаю",)),
    ("я позволяю", ("я позволяю",)),
    ("я нахожу", ("я нахожу",)),
    ("я создаю", ("я создаю",)),
    ("я доверяю", ("я доверяю",)),
    ("я замечаю", ("я замечаю",)),
    ("я чувствую", ("я чувствую",)),
    ("сегодня я", ("сегодня я",)),
    ("мой путь", ("мой путь",)),
    ("моя ценность", ("моя ценность",)),
]

SOFT_ACTION_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("name_three_things", ("назови три", "найди три", "заметь три")),
    ("choose_one_action", ("выбери одно", "выбери один")),
    ("take_short_step", ("сделай короткий", "сделай маленький", "сделай один короткий", "сделай один маленький")),
    ("pause_breathe", ("остановись", "подыши", "сделай вдох")),
    ("write_note", ("запиши", "напиши")),
    ("body_movement", ("движение", "потянись", "разомнись")),
]


def _clean_str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dedupe_stable(items: list[str]) -> list[str]:
    seen = set()
    result: list[str] = []
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


def _safe_affirmations(value) -> list[str]:
    if isinstance(value, list):
        return [text for text in (_clean_str(item) for item in value) if text]
    if isinstance(value, str):
        lines = [line.strip() for line in value.splitlines()]
        return [line for line in lines if line]
    return []


def extract_text_patterns(text: str | None) -> list[str]:
    cleaned = _clean_str(text)
    if not cleaned:
        return []
    lowered = cleaned.lower()
    found: list[str] = []
    for label, markers in TEXT_PATTERNS:
        if any(marker in lowered for marker in markers):
            found.append(label)
    return _dedupe_stable(found)


def extract_soft_action_patterns(text: str | None) -> list[str]:
    cleaned = _clean_str(text)
    if not cleaned:
        return []
    lowered = cleaned.lower()
    found: list[str] = []
    for label, markers in SOFT_ACTION_PATTERNS:
        if any(marker in lowered for marker in markers):
            found.append(label)
    return _dedupe_stable(found)


def extract_affirmation_opening(text: str | None) -> str | None:
    cleaned = _clean_str(text)
    if not cleaned:
        return None
    lowered = cleaned.lower()
    for label, markers in AFFIRMATION_OPENING_PATTERNS:
        if any(lowered.startswith(marker) for marker in markers):
            return label
    return None


def build_text_memory_context(
    recent_generations: list[dict] | None,
    limit: int = 10,
) -> dict:
    safe_generations = recent_generations if isinstance(recent_generations, list) else []
    recent_items = safe_generations[:limit]

    recent_focus_titles = _dedupe_stable([
        _clean_str(item.get("focus_title"))
        for item in recent_items
        if isinstance(item, dict)
    ])
    recent_soft_actions = _dedupe_stable([
        _clean_str(item.get("soft_action"))
        for item in recent_items
        if isinstance(item, dict)
    ])
    recent_soft_action_patterns: list[str] = []
    soft_action_pattern_counter: Counter[str] = Counter()

    pattern_counter: Counter[str] = Counter()
    recent_affirmation_patterns: list[str] = []
    recent_affirmation_openings: list[str] = []
    affirmation_opening_counter: Counter[str] = Counter()
    recent_short_phrases: list[str] = []

    for item in recent_items:
        if not isinstance(item, dict):
            continue
        soft_action_patterns = extract_soft_action_patterns(item.get("soft_action"))
        recent_soft_action_patterns.extend(soft_action_patterns)
        soft_action_pattern_counter.update(soft_action_patterns)
        affirmations = _safe_affirmations(item.get("affirmations"))
        item_patterns: list[str] = []
        for affirmation in affirmations:
            item_patterns.extend(extract_text_patterns(affirmation))
            opening = extract_affirmation_opening(affirmation)
            if opening:
                recent_affirmation_openings.append(opening)
                affirmation_opening_counter.update([opening])
            cleaned_affirmation = _clean_str(affirmation)
            if cleaned_affirmation and len(cleaned_affirmation) <= 90:
                recent_short_phrases.append(cleaned_affirmation)
        deduped_item_patterns = _dedupe_stable(item_patterns)
        recent_affirmation_patterns.extend(deduped_item_patterns)
        pattern_counter.update(deduped_item_patterns)

    recent_affirmation_patterns = _dedupe_stable(recent_affirmation_patterns)
    recent_affirmation_openings = _dedupe_stable(recent_affirmation_openings)
    recent_soft_action_patterns = _dedupe_stable(recent_soft_action_patterns)
    pattern_counts = {key: pattern_counter[key] for key in recent_affirmation_patterns}
    overused_text_patterns = [key for key in recent_affirmation_patterns if pattern_counter[key] >= 2]
    overused_affirmation_openings = [
        key for key in recent_affirmation_openings if affirmation_opening_counter[key] >= 2
    ]
    overused_soft_action_patterns = [
        key for key in recent_soft_action_patterns if soft_action_pattern_counter[key] >= 2
    ]
    avoid_phrases = _dedupe_stable(recent_short_phrases)[:5]
    avoid_soft_actions = recent_soft_actions[:3]
    avoid_affirmation_openings = recent_affirmation_openings[:4]
    avoid_soft_action_patterns = recent_soft_action_patterns[:3]

    style_guidance = [
        "avoid repeating recent affirmation openings",
        "vary sentence rhythm",
        "do not reuse recent soft action verbatim",
        "do not reuse recent soft action structure",
        "keep wording natural and specific",
    ]
    if overused_text_patterns:
        style_guidance.append("reduce repeated generic reassurance patterns")
    if overused_affirmation_openings:
        style_guidance.append("do not start multiple affirmations with the same opening")
    if overused_soft_action_patterns:
        style_guidance.append("switch to a different soft action family when recent patterns repeat")
    variation_guidance = [
        "vary affirmation openings",
        "avoid repeating the same first-person verb structure",
        "mix sentence rhythm and phrasing",
    ]
    if overused_affirmation_openings:
        variation_guidance.append("switch away from overused recent affirmation openings")

    return {
        "limit": limit,
        "recent_focus_titles": recent_focus_titles,
        "recent_soft_actions": recent_soft_actions,
        "recent_soft_action_patterns": recent_soft_action_patterns,
        "recent_affirmation_patterns": recent_affirmation_patterns,
        "recent_affirmation_openings": recent_affirmation_openings,
        "overused_text_patterns": overused_text_patterns,
        "overused_affirmation_openings": overused_affirmation_openings,
        "overused_soft_action_patterns": overused_soft_action_patterns,
        "avoid_phrases": avoid_phrases,
        "avoid_affirmation_openings": avoid_affirmation_openings,
        "avoid_soft_actions": avoid_soft_actions,
        "avoid_soft_action_patterns": avoid_soft_action_patterns,
        "style_guidance": _dedupe_stable(style_guidance),
        "variation_guidance": _dedupe_stable(variation_guidance),
        "pattern_counts": pattern_counts,
    }


async def get_text_memory_context(
    telegram_user_id: int,
    limit: int = 10,
) -> dict:
    try:
        recent_generations = await get_recent_generation_history(telegram_user_id, limit=limit)
        return build_text_memory_context(recent_generations, limit=limit)
    except Exception:
        return build_text_memory_context([], limit=limit)
