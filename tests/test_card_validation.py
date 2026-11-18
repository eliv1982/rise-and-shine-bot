"""Offline FIX-04A/04B card contract and production/comparison parity regressions."""
import json
import unicodedata

import pytest

from scripts.compare_text_models import assess_response
from services.language_policy import is_card_language_compatible
from services.yandex_gpt import GeneratedCardText, ProviderOutputValidationError, _parse_card_text


def _payload(language="en"):
    return {
        "focus": "Gentle learning" if language == "en" else "Бережное обучение",
        "affirmations": ["My experience matters"] * 4 if language == "en" else ["Мой опыт важен"] * 4,
    }


def _set_field(payload, field, text):
    if field == "focus":
        payload["focus"] = text
    else:
        payload["affirmations"][field] = text


@pytest.mark.parametrize("field", ["focus", 0, 1, 2, 3])
@pytest.mark.parametrize("language,text", [
    ("ru", "Я спокойно осваиваю Python."),
    ("ru", "Я могу использовать ChatGPT в работе."),
    ("ru", "Мой опыт в IT имеет ценность."),
    ("en", "I enjoy reading Достоевский."),
    ("ru", "Я изучаю OpenAI и Microsoft с John Smith 18.11.2026 🌿."),
    ("en", "I explore OpenAI and Microsoft with Иван Петров on 2026-11-18 🌿."),
    ("en", "I enjoy reading А. С. Пушкин."),
    ("ru", "Я спокойно осваиваю kubernetes и redis."),
    ("ru", "Я работаю с José и iPhone."),
    ("ru", "Я осваиваю GPT4o и GPT-4o на iPhone16."),
    ("en", "I practise йога at my own pace."),
    ("ru", unicodedata.normalize("NFD", "Я берегу своё время с ChatGPT.")),
])
def test_names_brands_terms_and_unicode_survive_in_every_card_field(language, text, field):
    payload = _payload(language)
    _set_field(payload, field, text)
    raw = json.dumps(payload, ensure_ascii=False)
    card = _parse_card_text(raw, language)
    assert card == GeneratedCardText(payload["focus"], payload["affirmations"])
    assert assess_response(raw, {"language": language})["valid_four_strings"] is True


@pytest.mark.parametrize("field", ["focus", 0, 1, 2, 3])
@pytest.mark.parametrize("language,text", [
    ("ru", "I feel calm and trust my experience."),
    ("en", "Я спокойно доверяю своему опыту."),
    ("ru", "Я feel calm and trust своему опыту."),
    ("en", "I спокойно выбираю свой pace."),
    ("ru", "Я Feel Ready To Learn."),
    ("en", "I Чувствую Себя Спокойно."),
    ("ru", "Я спокойно work today."),
    ("en", "I trust себя today."),
    ("ru", "Я учу Pуthon."),  # Cyrillic у hidden inside a Latin brand.
    ("en", "I trust 我今天很平静."),
])
def test_wrong_or_clearly_mixed_prose_is_rejected_in_every_card_field(language, text, field):
    payload = _payload(language)
    _set_field(payload, field, text)
    raw = json.dumps(payload, ensure_ascii=False)
    with pytest.raises(ProviderOutputValidationError, match="language mismatch"):
        _parse_card_text(raw, language)
    assert assess_response(raw, {"language": language})["valid_four_strings"] is False


@pytest.mark.parametrize("language", ["ru", "en"])
@pytest.mark.parametrize("field", ["focus", 0, 1, 2, 3])
@pytest.mark.parametrize("text", ["2026-11-18", "🌿 😊", "١٢٣ Ⅻ ² 🙂"])
def test_numbers_and_emoji_are_language_neutral_but_not_card_prose(language, field, text):
    assert is_card_language_compatible(text, language)
    payload = _payload(language)
    _set_field(payload, field, text)
    with pytest.raises(ProviderOutputValidationError, match="without prose"):
        _parse_card_text(json.dumps(payload), language)


@pytest.mark.parametrize("language", ["ru", "en"])
@pytest.mark.parametrize("wrapper", ["{}", "```json\n{}\n```", "```\n{}\n```", " \n```json\r\n{}\r\n```\n "])
@pytest.mark.parametrize("extra", [False, True])
def test_valid_plain_and_complete_fenced_objects_share_one_parser(language, wrapper, extra):
    payload = _payload(language)
    if extra:
        payload.update(gentle_step={"untrusted": "ignore this"}, metadata=["harmless"], future_field=None)
    raw = wrapper.format(json.dumps(payload))
    card = _parse_card_text(raw, language)
    comparison = assess_response(raw, {"language": language})
    assert card == GeneratedCardText(payload["focus"], payload["affirmations"])
    assert comparison["valid_four_strings"] is True
    assert comparison["focus"] == card.focus
    assert comparison["affirmations"] == card.affirmations
    assert not hasattr(card, "gentle_step")


_VALID = json.dumps(_payload())


@pytest.mark.parametrize("raw", [
    "```json\n" + _VALID, _VALID + "\n```", "```json\n" + _VALID + "\n``",
    "```json\n" + _VALID + "\n```\ntrailing prose",
    "prefix\n```json\n" + _VALID + "\n```",
    "```python\n" + _VALID + "\n```",
    "```json\n```json\n" + _VALID + "\n```\n```",
    "```json\n" + _VALID + "\n```\n```\n{}\n```",
    _VALID + " trailing prose", _VALID + "{}", "```json\n{broken}\n```",
    '["a", "b", "c", "d"]', "null", "{}",
    '{"focus":"Rest","focus":"Calm","affirmations":["a","b","c","d"]}',
    _VALID[:-1] + ',"extra":NaN}', _VALID[:-1] + ',"extra":Infinity}',
    '{"focus":"Rest","extra":true}',
    '{"focus":17,"affirmations":["a","b","c","d"]}',
    '{"focus":"Rest","affirmations":["a","b","c",null],"extra":true}',
])
def test_comparison_and_production_reject_the_same_invalid_contract(raw):
    with pytest.raises(ProviderOutputValidationError):
        _parse_card_text(raw, "en")
    assert assess_response(raw, {"language": "en"})["valid_four_strings"] is False


@pytest.mark.parametrize("field", ["focus", 0, 1, 2, 3])
@pytest.mark.parametrize("hyphen", ["-", "‐", "‑"])
@pytest.mark.parametrize("text", [
    "Я работаю с IT-специалистом.",
    "Я Python-разработчик и это ценно.",
    "Я HR-менеджер и верю в себя.",
    "Я люблю ChatGPT-помощника.",
    "Я backend-разработчик и изучаю Wi-Fi и e-mail.",
    "Я работаю с José-специалистом и GPT-4o.",
    "Я использую GPT-4o, Wi-Fi, e-mail и IT.",
])
def test_hyphen_segments_accept_terminology_in_every_field(field, hyphen, text):
    payload = _payload("ru")
    _set_field(payload, field, text.replace("-", hyphen))
    raw = json.dumps(payload, ensure_ascii=False)
    assert _parse_card_text(raw, "ru") == GeneratedCardText(payload["focus"], payload["affirmations"])
    assert assess_response(raw, {"language": "ru"})["valid_four_strings"] is True


@pytest.mark.parametrize("field", ["focus", 0, 1, 2, 3])
@pytest.mark.parametrize("language,text", [
    ("ru", "Я работаю с Pуthon-разработчиком."),
    ("ru", "Я работаю с IT-специaлистом."),  # Latin a in the Cyrillic segment.
    ("ru", "Я учу Pуthon."),
    ("ru", "Я-I-feel-calm-and-trust-myself."),
    ("ru", "Я-Python-work-today."),
    ("ru", "Я Python-разработчик-feel-ready."),
    ("ru", "Я Python-неизвестный-unlistedword."),
    ("ru", "Я Alpha-Beta-Gamma-Delta-Epsilon."),
    ("ru", "Я Python, GPT-4o, Wi-Fi, e-mail, IT."),
    ("ru", "Я Feel-Ready-To-Learn."),
    ("en", "I-Я-чувствую-себя-спокойно."),
    ("en", "I-Достоевский-спокойно."),
    ("en", "I-Достоевский-неизвестноеслово."),
])
def test_hyphenation_does_not_hide_spoofing_or_foreign_prose(field, language, text):
    payload = _payload(language)
    _set_field(payload, field, text)
    raw = json.dumps(payload, ensure_ascii=False)
    with pytest.raises(ProviderOutputValidationError, match="language mismatch"):
        _parse_card_text(raw, language)
    assert assess_response(raw, {"language": language})["valid_four_strings"] is False


@pytest.mark.parametrize("field", ["focus", 0, 1, 2, 3])
@pytest.mark.parametrize("opening,closing", [("«", "»"), ('"', '"'), ("“", "”"), ("„", "“"), ("‘", "’"), ("'", "'")])
@pytest.mark.parametrize("language,template", [
    ("ru", "Я помню фразу {opening}I am calm{closing}."),
    ("en", "I repeat the words {opening}Я спокоен{closing} every morning."),
])
def test_bounded_foreign_quotations_in_every_field(field, opening, closing, language, template):
    payload = _payload(language)
    _set_field(payload, field, template.format(opening=opening, closing=closing))
    raw = json.dumps(payload, ensure_ascii=False)
    assert _parse_card_text(raw, language) == GeneratedCardText(payload["focus"], payload["affirmations"])
    assert assess_response(raw, {"language": language})["valid_four_strings"] is True


@pytest.mark.parametrize("field", ["focus", 0, 1, 2, 3])
@pytest.mark.parametrize("language,text", [
    ("ru", "«I am calm»"),
    ("en", '"Я спокоен"'),
    ("ru", "«Я помню фразу I am calm»"),
    ("en", "«I repeat the words Я спокоен every morning»"),
    ("ru", "Я «I am calm»."),
    ("en", "I «Я спокоен»."),
    ("ru", "Я помню фразу «I am calm», and I trust myself every morning."),
    ("en", "I repeat the words «Я спокоен», и я верю в себя каждое утро."),
    ("ru", "Я помню фразу I am calm."),
    ("en", "I repeat the words Я спокоен every morning."),
    ("ru", "Я помню фразу «I am calm."),
    ("ru", "Я помню фразу «I am calm”."),
    ("ru", "Я помню фразу «I am “calm”»."),
    ("en", 'I repeat the words "Я «спокоен»" every morning.'),
    ("ru", "Я помню фразу «I am\ncalm»."),
    ("ru", "Я помню фразу «I trust Pуthon»."),
    ("ru", "Я помню фразу «I trust 我»."),
    ("en", "I repeat the words «Я спокoен» every morning."),
    ("ru", "Я помню фразу «I am calm» и сегодня work calmly."),
    ("en", "I repeat «Я спокоен» every morning and чувствую покой."),
])
def test_quotation_bypasses_and_wrong_surrounding_prose_fail_in_every_field(field, language, text):
    payload = _payload(language)
    _set_field(payload, field, text)
    raw = json.dumps(payload, ensure_ascii=False)
    with pytest.raises(ProviderOutputValidationError, match="language mismatch"):
        _parse_card_text(raw, language)
    assert assess_response(raw, {"language": language})["valid_four_strings"] is False


@pytest.mark.parametrize("language,text,expected", [
    ("ru", "Я помню фразу «I am calm».", True),
    ("ru", "Помню фразу «I am calm».", False),
    ("ru", "Я каждый день спокойно повторяю эту фразу «I am calm and I learn».", True),
    ("ru", "Я каждый день спокойно повторяю эту добрую фразу «I am calm and I learn gently».", False),
    ("ru", "Я каждый день спокойно повторяю эти две добрые фразы «I am calm today» и «I trust my pace».", True),
    ("ru", "Я каждый день спокойно повторяю эти две добрые фразы «I am calm today» и «I trust my own pace».", False),
    ("ru", "Я помню три добрые фразы «calm», «peace» и «rest».", False),
    ("ru", "Я помню фразу «I am " + "x" * 75 + "».", True),  # 80 characters.
    ("ru", "Я помню фразу «I am " + "x" * 76 + "».", False),
    ("ru", "Я помню фразу: «I'm calm!», и берегу себя.", True),
    ("ru", "Я помню слова 'I'm calm' и берегу себя.", True),
    ("ru", "Я помню фразу «I’m calm…» — она помогает мне.", True),
    ("en", "I don't forget «Я спокоен!», and I trust O’Connor.", True),
    ("ru", "«Я спокоен». И я берегу свой ритм.", True),
    ("en", '"I am calm." I trust my pace.', True),
    ("ru", "Я изучаю «Python» и ChatGPT.", True),
    ("en", "I enjoy reading Иван-Петров and practise йога.", True),
])
def test_quotation_limits_punctuation_and_existing_terminology(language, text, expected):
    assert is_card_language_compatible(text, language) is expected


@pytest.mark.parametrize("language,foreign", [("ru", "I trust my own pace."), ("en", "Я доверяю своему ритму.")])
@pytest.mark.parametrize("wrapper", ["{}", "«{}»", '"{}"', "“{}”", "‘{}’", "'{}'"])
def test_entirely_wrong_language_cards_cannot_use_quotation_exemptions(language, foreign, wrapper):
    text = wrapper.format(foreign)
    raw = json.dumps({"focus": text, "affirmations": [text] * 4}, ensure_ascii=False)
    with pytest.raises(ProviderOutputValidationError, match="language mismatch"):
        _parse_card_text(raw, language)
    assert assess_response(raw, {"language": language})["valid_four_strings"] is False
