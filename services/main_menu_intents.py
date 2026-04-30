import re
from typing import Optional


def _normalize_intent_text(text: str) -> str:
    low = (text or "").lower().strip()
    low = re.sub(r"[^\w\sа-яё-]", " ", low, flags=re.IGNORECASE)
    low = re.sub(r"\s+", " ", low).strip()
    return low


def detect_main_menu_intent(text: str, ui_language: str) -> Optional[str]:
    low = _normalize_intent_text(text)
    if not low:
        return None
    if ui_language == "ru":
        phrase_map = {
            "create_mood": ("создай настрой", "создать настрой", "новый настрой", "сделай настрой", "хочу настрой", "создай мне настрой", "настрой"),
            "manage_subscriptions": ("подписки", "покажи подписки", "мои подписки"),
            "profile": ("профиль", "мой профиль"),
            "language": ("язык", "поменять язык", "сменить язык"),
        }
    else:
        phrase_map = {
            "create_mood": ("create mood", "create focus", "new mood", "create new", "make a daily focus", "new focus", "create daily focus"),
            "manage_subscriptions": ("subscriptions", "show subscriptions", "manage subscriptions", "my subscriptions"),
            "profile": ("profile", "my profile", "account"),
            "language": ("language", "change language"),
        }
    for intent, phrases in phrase_map.items():
        if any(p in low for p in phrases):
            return intent
    if ui_language == "ru":
        if any(token in low for token in ("созд", "настрой", "ритуал", "sozday", "nastroi", "nastroj")):
            return "create_mood"
        if any(token in low for token in ("подпис",)):
            return "manage_subscriptions"
        if any(token in low for token in ("профил",)):
            return "profile"
        if "язык" in low:
            return "language"
    else:
        if any(token in low for token in ("mood", "focus", "create")):
            return "create_mood"
        if any(token in low for token in ("subscription", "subscribe", "subs")):
            return "manage_subscriptions"
        if any(token in low for token in ("profile", "account")):
            return "profile"
        if any(token in low for token in ("language", "lang")):
            return "language"
    return None
