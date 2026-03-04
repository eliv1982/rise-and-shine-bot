import re
from typing import Optional


def extract_name_from_introduction(text: str) -> Optional[str]:
    """
    Извлекает имя из фразы представления. Старается аккуратно вырезать
    только имя, даже если вокруг есть эмодзи и знаки препинания.
    """
    if not text or not (s := text.strip()):
        return None

    def _clean(raw: str) -> Optional[str]:
        # Убираем не-буквенные символы по краям (включая эмодзи и смайлики)
        cleaned = re.sub(r"^[^A-Za-zА-Яа-яЁё]+|[^A-Za-zА-Яа-яЁё]+$", "", raw.strip())
        if len(cleaned) < 2:
            return None
        # Первая буква заглавная, остальные оставляем как есть
        return cleaned[0].upper() + cleaned[1:]

    # Русские паттерны — берём с оригинальной строки, а не с lower,
    # чтобы сохранить регистр и корректно обрезать.
    ru_patterns = [
        r"(?:меня|тебя)\s+зовут\s+([А-Яа-яЁёA-Za-z][^,.!?\n]*)",
        r"зовут\s+([А-Яа-яЁёA-Za-z][^,.!?\n]*)",
        r"я\s*[—-]\s*([А-Яа-яЁёA-Za-z][^,.!?\n]*)",
        r"меня\s+([А-Яа-яЁё][^,.!?\n]*)",
    ]
    for pattern in ru_patterns:
        m = re.search(pattern, s, re.IGNORECASE)
        if m:
            candidate = _clean(m.group(1))
            if candidate:
                return candidate

    # Английские паттерны
    en_patterns = [
        r"(?:my name is|i'm|i am)\s+([A-Za-z][^,.!?\n]*)",
        r"name['`’]s?\s+([A-Za-z][^,.!?\n]*)",
        r"call me\s+([A-Za-z][^,.!?\n]*)",
    ]
    for pattern in en_patterns:
        m = re.search(pattern, s, re.IGNORECASE)
        if m:
            candidate = _clean(m.group(1))
            if candidate:
                return candidate

    # Если фраза короткая (одно или два слова) — вероятно, это имя
    words = [w for w in re.split(r"\s+", s) if w.strip()]
    if len(words) == 1:
        candidate = _clean(words[0])
        if candidate:
            return candidate
    if len(words) == 2 and words[0].lower().strip(".,!?") in ("я", "i", "меня", "это", "it's"):
        candidate = _clean(words[1])
        if candidate:
            return candidate

    # Последнее слово часто бывает именем в "Привет, меня зовут Лена 🙂"
    if len(words) >= 2:
        candidate = _clean(words[-1])
        if candidate:
            return candidate

    return None


def gender_display(gender: Optional[str], language: str = "ru") -> str:
    """
    Возвращает строку для описания рода в промпте.
    """
    if language == "en":
        mapping = {
            "male": "for a man",
            "female": "for a woman",
        }
    else:
        mapping = {
            "male": "для мужчины",
            "female": "для женщины",
        }
    return mapping.get(gender or "", mapping.get("male", "for a man"))

