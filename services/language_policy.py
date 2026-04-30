import re
from typing import Optional


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
