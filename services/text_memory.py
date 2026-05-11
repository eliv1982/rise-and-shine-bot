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

    pattern_counter: Counter[str] = Counter()
    recent_affirmation_patterns: list[str] = []
    recent_short_phrases: list[str] = []

    for item in recent_items:
        if not isinstance(item, dict):
            continue
        affirmations = _safe_affirmations(item.get("affirmations"))
        item_patterns: list[str] = []
        for affirmation in affirmations:
            item_patterns.extend(extract_text_patterns(affirmation))
            cleaned_affirmation = _clean_str(affirmation)
            if cleaned_affirmation and len(cleaned_affirmation) <= 90:
                recent_short_phrases.append(cleaned_affirmation)
        deduped_item_patterns = _dedupe_stable(item_patterns)
        recent_affirmation_patterns.extend(deduped_item_patterns)
        pattern_counter.update(deduped_item_patterns)

    recent_affirmation_patterns = _dedupe_stable(recent_affirmation_patterns)
    pattern_counts = {key: pattern_counter[key] for key in recent_affirmation_patterns}
    overused_text_patterns = [key for key in recent_affirmation_patterns if pattern_counter[key] >= 2]
    avoid_phrases = _dedupe_stable(recent_short_phrases)[:5]
    avoid_soft_actions = recent_soft_actions[:3]

    style_guidance = [
        "avoid repeating recent affirmation openings",
        "vary sentence rhythm",
        "do not reuse recent soft action verbatim",
        "keep wording natural and specific",
    ]
    if overused_text_patterns:
        style_guidance.append("reduce repeated generic reassurance patterns")

    return {
        "limit": limit,
        "recent_focus_titles": recent_focus_titles,
        "recent_soft_actions": recent_soft_actions,
        "recent_affirmation_patterns": recent_affirmation_patterns,
        "overused_text_patterns": overused_text_patterns,
        "avoid_phrases": avoid_phrases,
        "avoid_soft_actions": avoid_soft_actions,
        "style_guidance": _dedupe_stable(style_guidance),
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
