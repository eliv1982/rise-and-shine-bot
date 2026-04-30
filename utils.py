import re
from typing import Literal, Optional

GenderKey = Literal["male", "female"]


def normalize_gender(gender: Optional[str]) -> Optional[GenderKey]:
    """
    Приводит значение пола из БД/интерфейса к 'male' | 'female'.
    Любой другой ввод — None (тогда можно опереться только на gender_hint).
    """
    if not gender:
        return None
    g = str(gender).strip().lower()
    if g in ("female", "f", "woman", "женский", "жен", "девушка"):
        return "female"
    if g in ("male", "m", "man", "мужской", "муж", "парень"):
        return "male"
    return None


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
    Не возвращает пустую строку: при неизвестном поле — формулировка для мужского рода (как запасной вариант).
    """
    g = normalize_gender(gender)
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
    return mapping.get(g or "male", mapping["male"])


def build_focus_of_day(sphere: str, language: str = "ru", subsphere: Optional[str] = None) -> str:
    """
    Возвращает короткий фокус дня без дополнительного LLM-вызова.
    """
    from services.ritual_config import get_focuses

    focuses = get_focuses((sphere or "").lower())
    options = [focus.get(language, focus["ru"]) for focus in focuses]
    seed = f"{sphere}:{subsphere or ''}:{language}"
    idx = sum(ord(ch) for ch in seed) % len(options)
    return options[idx]


_CYR_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def transliterate_ru_to_en(text: str) -> str:
    out = []
    for ch in text:
        lower = ch.lower()
        mapped = _CYR_TO_LAT.get(lower)
        if mapped is None:
            out.append(ch)
            continue
        if ch.isupper() and mapped:
            out.append(mapped[0].upper() + mapped[1:])
        else:
            out.append(mapped)
    return "".join(out)


def display_name_for_language(name: Optional[str], language: str) -> Optional[str]:
    if not name:
        return name
    if language != "en":
        return name
    try:
        has_cyr = any("а" <= ch.lower() <= "я" or ch.lower() == "ё" for ch in name)
        if not has_cyr:
            return name
        translit = transliterate_ru_to_en(name).strip()
        return translit or name
    except Exception:
        return name


def is_gibberish_text(text: Optional[str]) -> bool:
    t = (text or "").strip()
    if len(t) < 4:
        return True
    low = t.lower()
    suspicious = ("weh weh", "do stoint", "sosday", "nstra", "divertuz")
    if any(token in low for token in suspicious):
        return True
    words = re.findall(r"[A-Za-zА-Яа-яЁё]+", t)
    if len(words) < 2:
        return True
    unique_ratio = len(set(w.lower() for w in words)) / max(1, len(words))
    if unique_ratio < 0.34:
        return True
    consonant_heavy = 0
    for w in words:
        lw = w.lower()
        if len(lw) >= 6 and not re.search(r"[aeiouyаеёиоуыэюя]", lw):
            consonant_heavy += 1
    if words and consonant_heavy / len(words) > 0.45:
        return True
    return False


def is_input_language_compatible(text: Optional[str], ui_language: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    if t.startswith("/"):
        return True
    cyr = len(re.findall(r"[А-Яа-яЁё]", t))
    lat = len(re.findall(r"[A-Za-z]", t))
    if cyr == 0 and lat == 0:
        return True
    if ui_language == "ru":
        return cyr >= lat
    return lat >= cyr

