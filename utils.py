import re
from typing import Literal, Optional

from services.language_policy import display_name_for_language, is_input_language_compatible, transliterate_ru_to_en
from services.text_quality import is_gibberish_text

GenderKey = Literal["male", "female"]

_RUSSIAN_INFORMAL_ADDRESS_REPLACEMENTS: list[tuple[str, str]] = [
    ("Позвольте себе", "Позволь себе"),
    ("позвольте себе", "позволь себе"),
    ("Упростите", "Упрости"),
    ("упростите", "упрости"),
    ("Выберите", "Выбери"),
    ("выберите", "выбери"),
    ("Назовите", "Назови"),
    ("назовите", "назови"),
    ("Сделайте", "Сделай"),
    ("сделайте", "сделай"),
    ("Примите", "Прими"),
    ("примите", "прими"),
    ("Запишите", "Запиши"),
    ("запишите", "запиши"),
    ("Заметьте", "Заметь"),
    ("заметьте", "заметь"),
    ("Подумайте", "Подумай"),
    ("подумайте", "подумай"),
    ("Отметьте", "Отметь"),
    ("отметьте", "отметь"),
    ("Остановитесь", "Остановись"),
    ("остановитесь", "остановись"),
    ("Подышите", "Подыши"),
    ("подышите", "подыши"),
]


def normalize_gender(gender: Optional[str]) -> Optional[GenderKey]:
    """
    Приводит значение пола из БД/интерфейса к 'male' | 'female'.
    Любой другой ввод — None (тогда можно опереться только на gender_hint).
    """
    if not gender:
        return None
    g = str(gender).strip().lower()
    if g in ("female", "f", "woman", "girl", "feminine", "женский", "жен", "женщина", "девушка", "она"):
        return "female"
    if g in ("male", "m", "man", "boy", "masculine", "мужской", "муж", "мужчина", "парень", "он"):
        return "male"
    return None


def infer_gender_from_hint(gender_hint: Optional[str]) -> Optional[GenderKey]:
    if not gender_hint:
        return None
    normalized = normalize_gender(gender_hint)
    if normalized:
        return normalized

    text = str(gender_hint).strip().lower()
    if not text:
        return None

    words = set(re.findall(r"[A-Za-zА-Яа-яЁё]+", text))
    if "она" in words:
        return "female"
    if "он" in words:
        return "male"

    female_markers = ("femin", "woman", "girl", "жен", "девуш")
    male_markers = ("mascul", "man", "boy", "муж", "парен")
    if any(marker in text for marker in female_markers):
        return "female"
    if any(marker in text for marker in male_markers):
        return "male"
    return None


def normalize_russian_informal_address(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    normalized = text
    for formal, informal in _RUSSIAN_INFORMAL_ADDRESS_REPLACEMENTS:
        normalized = re.sub(
            rf"(?<!\w){re.escape(formal)}(?=[\s,.;:!?]|$)",
            informal,
            normalized,
        )
    return normalized


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
    Не возвращает пустую строку: при неизвестном поле — нейтральная формулировка.
    """
    g = normalize_gender(gender)
    if language == "en":
        mapping = {
            "male": "for a man",
            "female": "for a woman",
            None: "with gender-neutral wording where possible",
        }
    else:
        mapping = {
            "male": "для мужчины",
            "female": "для женщины",
            None: "по возможности в гендерно-нейтральной форме",
        }
    return mapping[g]


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

