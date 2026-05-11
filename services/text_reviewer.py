from __future__ import annotations

import re

from services.text_memory import extract_soft_action_patterns
from utils import infer_gender_from_hint, normalize_gender

_FEMALE_MISMATCH_PATTERNS = [
    "я открыт",
    "я готов",
    "я уверен",
    "я спокоен",
    "я сосредоточен",
    "я настроен",
    "я благодарен",
]

_MALE_MISMATCH_PATTERNS = [
    "я открыта",
    "я готова",
    "я уверена",
    "я спокойна",
    "я сосредоточена",
    "я настроена",
    "я благодарна",
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


def review_generated_text(
    *,
    affirmations: list[str] | None,
    soft_action: str | None = None,
    focus_title: str | None = None,
    language: str = "ru",
    gender_hint: str | None = None,
    text_plan: dict | None = None,
    text_memory_context: dict | None = None,
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
    generic_patterns = _pattern_hits(texts, _GENERIC_PATTERNS, repeated_only=True)
    soft_action_repeated = _is_soft_action_repeated(safe_soft_action, text_memory_context)
    pressure_language = bool(_pattern_hits(texts, _PRESSURE_PATTERNS))
    too_productivity_framed = bool(_pattern_hits(texts, _PRODUCTIVITY_PATTERNS))

    checks = {
        "gender_mismatch": gender_mismatch,
        "repeated_openings": repeated_openings,
        "generic_patterns": generic_patterns,
        "soft_action_repeated": soft_action_repeated,
        "pressure_language": pressure_language,
        "too_productivity_framed": too_productivity_framed,
    }

    warnings: list[str] = []
    if gender_mismatch:
        warnings.append("gender_mismatch")
    if repeated_openings:
        warnings.append("repeated_openings")
    if generic_patterns:
        warnings.append("generic_patterns: " + ", ".join(generic_patterns))
    if soft_action_repeated:
        warnings.append("soft_action_repeated")
    if pressure_language:
        warnings.append("pressure_language")
    if too_productivity_framed:
        warnings.append("too_productivity_framed")
    if not texts:
        warnings.append("empty_generated_text")

    score = 1.0
    score -= 0.2 if gender_mismatch else 0.0
    score -= 0.15 if repeated_openings else 0.0
    score -= 0.1 if soft_action_repeated else 0.0
    score -= 0.1 if pressure_language else 0.0
    score -= 0.1 if too_productivity_framed else 0.0
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
