from __future__ import annotations

import re

from services.text_memory import (
    extract_abstract_word_patterns,
    extract_affirmation_opening,
    extract_soft_action_patterns,
    extract_soft_action_structures,
)
from utils import infer_gender_from_hint, normalize_gender

_FEMALE_MISMATCH_PATTERNS = [
    "я открыт",
    "я готов",
    "я уверен",
    "я спокоен",
    "я сосредоточен",
    "я настроен",
    "я благодарен",
    "я принимаю себя таким какой я есть",
]

_MALE_MISMATCH_PATTERNS = [
    "я открыта",
    "я готова",
    "я уверена",
    "я спокойна",
    "я сосредоточена",
    "я настроена",
    "я благодарна",
    "я принимаю себя такой какая я есть",
]

_GENERIC_PATTERNS = [
    "я позволяю себе",
    "я выбираю",
    "я принимаю",
    "я создаю",
    "я нахожу",
    "маленький шаг",
    "без чувства вины",
]

_PRESSURE_PATTERNS = [
    "должна",
    "обязана",
    "должен",
    "обязан",
    "надо обязательно",
    "срочно",
    "заставь себя",
]

_PRODUCTIVITY_PATTERNS = [
    "будь продуктивнее",
    "максимальная эффективность",
    "выжми максимум",
    "выжму максимум",
]

_LANGUAGE_MISMATCH_PATTERNS = [
    "choose a phrase",
    "take one small step",
    "i choose",
    "i accept",
    "i allow",
]

_TOO_GENERIC_WORDS = [
    "спокойствие",
    "ясность",
    "устойчивость",
    "достаточность",
    "гармония",
    "стабильность",
    "страх",
]


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _normalize_match_text(value: str | None) -> str:
    text = _clean_text(value).lower().replace("ё", "е")
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _dedupe_stable(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = _clean_text(item)
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _resolve_gender(gender_hint: str | None) -> str | None:
    return normalize_gender(gender_hint) or infer_gender_from_hint(gender_hint)


def _first_opening(text: str) -> str:
    detected = extract_affirmation_opening(text)
    if detected:
        return detected
    normalized = _normalize_match_text(text)
    parts = normalized.split()
    return " ".join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else "")


def _pattern_hits(texts: list[str], patterns: list[str], *, repeated_only: bool = False) -> list[str]:
    counts: dict[str, int] = {}
    combined = "\n".join(_normalize_match_text(text) for text in texts if _clean_text(text))
    for pattern in patterns:
        count = combined.count(pattern)
        if count:
            counts[pattern] = count
    result: list[str] = []
    for pattern in patterns:
        count = counts.get(pattern, 0)
        if repeated_only and count < 2:
            continue
        if count:
            result.append(pattern)
    return result


def _contains_exact_phrase(text: str, phrase: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text))


def _language_mismatch(texts: list[str], language: str) -> bool:
    if language != "ru":
        return False
    combined = "\n".join(_normalize_match_text(text) for text in texts if _clean_text(text))
    return any(pattern in combined for pattern in _LANGUAGE_MISMATCH_PATTERNS)


def _overused_affirmation_openings(safe_affirmations: list[str], text_memory_context: dict | None) -> bool:
    opening_counts: dict[str, int] = {}
    current_openings: set[str] = set()
    for item in safe_affirmations:
        opening = _first_opening(item)
        if not opening:
            continue
        current_openings.add(opening)
        opening_counts[opening] = opening_counts.get(opening, 0) + 1
    if any(count >= 2 for count in opening_counts.values()):
        return True
    memory = text_memory_context if isinstance(text_memory_context, dict) else {}
    avoid_openings = {
        _clean_text(item) for item in (memory.get("avoid_affirmation_openings") or []) if _clean_text(item)
    }
    overused_openings = {
        _clean_text(item) for item in (memory.get("overused_affirmation_openings") or []) if _clean_text(item)
    }
    return bool(current_openings & avoid_openings) or bool(current_openings & overused_openings)


def _too_generic(safe_affirmations: list[str], language: str) -> bool:
    if language != "ru" or len(safe_affirmations) < 2:
        return False
    combined = "\n".join(_normalize_match_text(text) for text in safe_affirmations)
    generic_hits = sum(1 for word in _TOO_GENERIC_WORDS if word in combined)
    abstract_pattern_hits = len(set().union(*(set(extract_abstract_word_patterns(text)) for text in safe_affirmations)))
    return generic_hits >= 3 or abstract_pattern_hits >= 3


def _is_soft_action_repeated(soft_action: str | None, text_memory_context: dict | None) -> bool:
    action = _normalize_match_text(soft_action)
    if not action:
        return False
    memory = text_memory_context if isinstance(text_memory_context, dict) else {}
    current_patterns = set(extract_soft_action_patterns(soft_action))
    avoid_pattern_keys = {
        _clean_text(item) for item in (memory.get("avoid_soft_action_patterns") or []) if _clean_text(item)
    }
    overused_pattern_keys = {
        _clean_text(item) for item in (memory.get("overused_soft_action_patterns") or []) if _clean_text(item)
    }
    if current_patterns & avoid_pattern_keys:
        return True
    if current_patterns & overused_pattern_keys:
        return True
    for candidate in memory.get("avoid_soft_actions") or []:
        normalized_candidate = _normalize_match_text(candidate)
        if not normalized_candidate:
            continue
        if action == normalized_candidate:
            return True
        action_tokens = set(action.split())
        candidate_tokens = set(normalized_candidate.split())
        if action_tokens and candidate_tokens:
            overlap = len(action_tokens & candidate_tokens) / max(len(action_tokens), len(candidate_tokens))
            if overlap >= 0.7:
                return True
    return False


def _is_soft_action_structure_repeated(soft_action: str | None, text_memory_context: dict | None) -> bool:
    structures = set(extract_soft_action_structures(soft_action))
    if not structures:
        return False
    memory = text_memory_context if isinstance(text_memory_context, dict) else {}
    avoid_structures = {
        _clean_text(item) for item in (memory.get("avoid_soft_action_structures") or []) if _clean_text(item)
    }
    overused_structures = {
        _clean_text(item) for item in (memory.get("overused_soft_action_structures") or []) if _clean_text(item)
    }
    return bool(structures & avoid_structures) or bool(structures & overused_structures)


def _has_abstract_contrast_formula(soft_action: str | None) -> bool:
    normalized = _normalize_match_text(soft_action)
    if not normalized or "а не из" not in normalized:
        return False
    return bool(extract_abstract_word_patterns(soft_action))


def _avoid_words_used(texts: list[str], profile_preferences: dict | None) -> list[str]:
    preferences = profile_preferences if isinstance(profile_preferences, dict) else {}
    avoid_words = preferences.get("avoid_words")
    if not isinstance(avoid_words, list):
        return []
    combined = "\n".join(_normalize_match_text(text) for text in texts if _clean_text(text))
    hits: list[str] = []
    for item in avoid_words:
        normalized = _normalize_match_text(item)
        stem = normalized[:-2] if len(normalized) >= 6 else ""
        if normalized and (
            _contains_exact_phrase(combined, normalized)
            or (len(normalized) >= 5 and normalized in combined)
            or (stem and stem in combined)
        ):
            hits.append(str(item).strip())
    return _dedupe_stable(hits)


def review_generated_text(
    *,
    affirmations: list[str] | None,
    soft_action: str | None = None,
    focus_title: str | None = None,
    language: str = "ru",
    gender_hint: str | None = None,
    text_plan: dict | None = None,
    text_memory_context: dict | None = None,
    profile_preferences: dict | None = None,
) -> dict:
    safe_affirmations = [item.strip() for item in (affirmations or []) if isinstance(item, str) and item.strip()]
    safe_soft_action = _clean_text(soft_action)
    texts = safe_affirmations + ([safe_soft_action] if safe_soft_action else [])

    effective_gender = _resolve_gender(gender_hint)
    combined = "\n".join(_normalize_match_text(text) for text in texts)

    if language == "ru" and effective_gender == "female":
        gender_mismatch = any(_contains_exact_phrase(combined, pattern) for pattern in _FEMALE_MISMATCH_PATTERNS)
    elif language == "ru" and effective_gender == "male":
        gender_mismatch = any(_contains_exact_phrase(combined, pattern) for pattern in _MALE_MISMATCH_PATTERNS)
    else:
        gender_mismatch = False

    opening_counts: dict[str, int] = {}
    for item in safe_affirmations:
        opening = _first_opening(item)
        if opening:
            opening_counts[opening] = opening_counts.get(opening, 0) + 1
    repeated_openings = any(count >= 2 for count in opening_counts.values())
    overused_affirmation_openings = _overused_affirmation_openings(safe_affirmations, text_memory_context)
    generic_patterns = _pattern_hits(texts, _GENERIC_PATTERNS, repeated_only=True)
    soft_action_repeated = _is_soft_action_repeated(safe_soft_action, text_memory_context)
    repeated_soft_action_structure = _is_soft_action_structure_repeated(safe_soft_action, text_memory_context)
    pressure_language = bool(_pattern_hits(texts, _PRESSURE_PATTERNS))
    too_productivity_framed = bool(_pattern_hits(texts, _PRODUCTIVITY_PATTERNS))
    language_mismatch = _language_mismatch(texts, language)
    too_generic = _too_generic(safe_affirmations, language)
    abstract_contrast_formula = _has_abstract_contrast_formula(safe_soft_action)
    avoid_words_used = _avoid_words_used(texts, profile_preferences)

    checks = {
        "gender_mismatch": gender_mismatch,
        "repeated_openings": repeated_openings,
        "overused_affirmation_openings": overused_affirmation_openings,
        "generic_patterns": generic_patterns,
        "soft_action_repeated": soft_action_repeated,
        "repeated_soft_action_structure": repeated_soft_action_structure,
        "pressure_language": pressure_language,
        "too_productivity_framed": too_productivity_framed,
        "language_mismatch": language_mismatch,
        "too_generic": too_generic,
        "abstract_contrast_formula": abstract_contrast_formula,
        "avoid_words_used": avoid_words_used,
    }

    warnings: list[str] = []
    if gender_mismatch:
        warnings.append("gender_mismatch")
    if repeated_openings:
        warnings.append("repeated_openings")
    if overused_affirmation_openings:
        warnings.append("overused_affirmation_openings")
    if generic_patterns:
        warnings.append("generic_patterns: " + ", ".join(generic_patterns))
    if soft_action_repeated:
        warnings.append("soft_action_repeated")
    if repeated_soft_action_structure:
        warnings.append("repeated_soft_action_structure")
    if pressure_language:
        warnings.append("pressure_language")
    if too_productivity_framed:
        warnings.append("too_productivity_framed")
    if language_mismatch:
        warnings.append("language_mismatch")
    if too_generic:
        warnings.append("too_generic")
    if abstract_contrast_formula:
        warnings.append("abstract_contrast_formula")
    if avoid_words_used:
        warnings.append("avoid_words_used: " + ", ".join(avoid_words_used))
    if not texts:
        warnings.append("empty_generated_text")

    score = 1.0
    score -= 0.2 if gender_mismatch else 0.0
    score -= 0.15 if repeated_openings else 0.0
    score -= 0.1 if overused_affirmation_openings else 0.0
    score -= 0.1 if soft_action_repeated else 0.0
    score -= 0.1 if repeated_soft_action_structure else 0.0
    score -= 0.1 if pressure_language else 0.0
    score -= 0.1 if too_productivity_framed else 0.0
    score -= 0.1 if language_mismatch else 0.0
    score -= 0.05 if too_generic else 0.0
    score -= 0.05 if abstract_contrast_formula else 0.0
    score -= min(0.1, 0.03 * len(avoid_words_used))
    score -= min(0.2, 0.05 * len(generic_patterns))
    if not texts:
        score -= 0.1
    score = max(0.0, min(1.0, round(score, 2)))

    return {
        "enabled": True,
        "language": language,
        "checks": checks,
        "warnings": _dedupe_stable(warnings),
        "score": score,
    }
