import re
import unicodedata
from typing import Optional


_CYR_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "y",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def normalize_language(value: object, default: str = "ru") -> str:
    return value if value in ("ru", "en") else default


def interface_language(user: Optional[dict]) -> str:
    """Only the user row owns the interface locale; FSM content choices do not."""
    return normalize_language((user or {}).get("language"))


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


# Output validation is deliberately separate from the accepted input/UI policy.
# These are prose signals, even when a model capitalizes a mixed-language clause.
_PROSE_WORDS = {
    "en": set("""i me my mine myself we us our you your yourself he she it they their
        the a an and or but if as at by for from in into of on to with without is am
        are was were be been being have has had do does did can could will would
        should must may might not no this that these those today tomorrow now
        feel feels feeling choose chooses choosing trust trusts trusting accept
        allow deserve believe enjoy read reading work working use using learn
        learning grow growing move moving forward calmly calm ready confident
        love need want take make find keep let give know support matters important
        always never enough more less very quietly slowly gently rest peace""".split()),
    "ru": set("""я мне меня мой моя моё мое мои мы нам нас наш наша ты тебе тебя
        твой твоя вы ваш он она они их это этот эта эти и или но если как а в во на
        с со к ко по из от до для без о об у за не ни да есть был была были быть
        буду будет могу может можно нужно надо сегодня завтра сейчас себя свой
        свою свои себе спокойно спокоен спокойна готов готова уверен
        уверена чувствую выбираю доверяю принимаю позволяю заслуживаю верю люблю
        читаю читать работаю работать учусь изучаю осваиваю использую использовать
        двигаюсь вперёд вперед расту хочу важно важен важна ценю берегу
        поддерживает поддержка отдых покой каждый всегда никогда достаточно""".split()),
}
_EMBEDDED_TERMS = set("""python chatgpt openai microsoft javascript typescript
    java kotlin rust golang it ai ui ux qa hr llm sql nosql html css api sdk http https url json xml yaml
    git github gitlab linux windows macos ios android docker kubernetes redis
    postgres postgresql sqlite numpy pandas pytorch tensorflow react node npm
    blockchain bitcoin ethereum mindfulness agile scrum kanban devops frontend
    backend fullstack software hardware wifi wi-fi bluetooth email e-mail онлайн
    офлайн интернет йога дзен""".split())
# Keep digits inside product names (GPT4o, GPT-4o, iPhone16) rather than splitting
# them into a capitalized name and an apparently foreign lowercase suffix.
_HYPHENS = "-‐‑"  # ASCII, Unicode hyphen and non-breaking hyphen; dashes separate words.
_WORD = re.compile(r"[^\W\d_][^\W_]*(?:[-‐‑'’][^\W_]+)*")
_HYPHEN = re.compile(f"[{_HYPHENS}]")
_QUOTE_PAIRS = {"«": "»", "“": "”", "„": "“", '"': '"', "‘": "’", "'": "'"}
_QUOTE_MARKS = set(_QUOTE_PAIRS) | set(_QUOTE_PAIRS.values())
_MAX_FOREIGN_QUOTES = 2
_MAX_QUOTE_WORDS = 6
_MAX_QUOTED_WORDS = 8
_MAX_QUOTE_CHARS = 80
_MIN_QUOTE_CONTEXT_WORDS = 2


def _card_words(text: str):
    """Keep apostrophes/product digits; inspect each hyphen segment separately."""
    for match in _WORD.finditer(text):
        whole = match.group()
        offset = match.start()
        for index, part in enumerate(_HYPHEN.split(whole)):
            yield part, offset + len(part), whole, index
            offset += len(part) + 1


def _quotation_spans(text: str) -> list[tuple[int, int]]:
    """Find flat paired quotes. Malformed/nested quotes grant no exemptions."""
    spans = []
    opening = None
    for index, char in enumerate(text):
        if char not in _QUOTE_MARKS:
            continue
        # Apostrophes in don't, I'm and O’Connor are part of words, not quotes.
        if char in "'’" and 0 < index < len(text) - 1 and text[index - 1].isalnum() and text[index + 1].isalnum():
            continue
        if opening is not None:
            start, closer = opening
            if char != closer:
                return []
            spans.append((start, index + 1))
            opening = None
        elif char in _QUOTE_PAIRS:
            opening = (index, _QUOTE_PAIRS[char])
        else:
            return []
    return [] if opening is not None else spans


def _word_scripts(token: str) -> set[str]:
    scripts = set()
    for char in token:
        if char.isalpha():
            name = unicodedata.name(char, "")
            scripts.add("en" if "LATIN" in name else "ru" if "CYRILLIC" in name else "other")
    return scripts


def is_card_language_compatible(text: str, language: str) -> bool:
    """Conservative RU/EN prose check, not semantic language identification.

    Require target-script prose; allow bounded foreign names/acronyms, known
    technical terms and short paired quotations with enough localized context.
    Foreign grammar/common prose words override capitalization outside quotations,
    so e.g. 'Я feel ready' cannot pass as a name. Unknown lowercase foreign words
    fail closed. Numbers/emoji have no language; card quality checks own them.
    See docs/localization_validation.md for the tradeoffs and blind spots.
    """
    language = normalize_language(language)
    text = unicodedata.normalize("NFC", text)
    foreign_language = "en" if language == "ru" else "ru"
    exempt_spans = []
    quoted_words = 0
    for start, end in _quotation_spans(text):
        quote = text[start + 1:end - 1]
        words = list(_card_words(quote))
        scripts = [script for word, *_ in words if (script := _word_scripts(word))]
        if not any(foreign_language in script for script in scripts):
            continue  # Same-language quotations still undergo ordinary validation.
        if (len(quote) > _MAX_QUOTE_CHARS or len(scripts) > _MAX_QUOTE_WORDS
                or "\n" in quote or "\r" in quote
                or any(script not in ({language}, {foreign_language}) for script in scripts)):
            return False
        quoted_words += len(scripts)
        exempt_spans.append((start, end))
    if len(exempt_spans) > _MAX_FOREIGN_QUOTES or quoted_words > _MAX_QUOTED_WORDS:
        return False
    # Mask only validated spans, preserving offsets and separation between words.
    for start, end in reversed(exempt_spans):
        text = text[:start] + " " * (end - start) + text[end:]
    target_count = 0
    has_letters = False
    foreign_run = 0
    for token, end, whole, segment_index in _card_words(text):
        scripts = _word_scripts(token)
        if not scripts:
            continue
        has_letters = True
        if scripts == {language}:
            target_count += 1
            foreign_run = 0
            continue
        # Do not silently drop other scripts or accept confusables inside a word.
        if scripts != {foreign_language}:
            return False
        lower = token.casefold()
        whole_term = _HYPHEN.sub("-", whole).casefold()
        known_compound = whole_term in _EMBEDDED_TERMS and _word_scripts(whole) == {foreign_language}
        product_suffix = token[0].isdecimal() and any(ch.isupper() for ch in whole) and _word_scripts(whole) == {foreign_language}
        # Preserve the existing word budget for known compounds and product
        # suffixes, while still inspecting every segment for script/prose errors.
        if not ((known_compound and segment_index > 0) or product_suffix):
            foreign_run += 1
        # Long foreign spans are unlikely to be a short embedded name/term.
        if foreign_run > 4:
            return False
        if lower in _EMBEDDED_TERMS or known_compound:
            continue
        if len(token) == 1 and token.isupper() and text[end:end + 1] == ".":
            continue  # A name initial, including Cyrillic initials in EN prose.
        if lower in _PROSE_WORDS[foreign_language]:
            return False
        # A title-case name, acronym or brand spelling (e.g. iPhone).
        if token[0].isupper() or any(ch.isupper() for ch in token[1:]):
            continue
        # A digit-led suffix in a single-script capitalized product, e.g. GPT-4o.
        if product_suffix:
            continue
        return False
    if exempt_spans and target_count < max(_MIN_QUOTE_CONTEXT_WORDS, quoted_words):
        return False
    return target_count > 0 or not has_letters
