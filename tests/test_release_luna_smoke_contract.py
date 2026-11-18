"""Self-contained release contract: no ignored scripts, credentials or paid calls."""
import json

import pytest

from services.yandex_gpt import GeneratedCardText, ProviderOutputValidationError, _parse_card_text


@pytest.mark.parametrize("language,focus,affirmation", [
    ("ru", "Спокойный рост", "Мой опыт важен"),
    ("en", "Gentle growth", "My experience matters"),
])
@pytest.mark.parametrize("fenced", [False, True])
def test_release_card_contract_uses_production_parser(language, focus, affirmation, fenced):
    payload = {"focus": focus, "affirmations": [affirmation] * 4, "gentle_step": "ignored"}
    raw = json.dumps(payload, ensure_ascii=False)
    if fenced:
        raw = f"```json\n{raw}\n```"
    card = _parse_card_text(raw, language)
    assert card == GeneratedCardText(focus, [affirmation] * 4)
    assert not hasattr(card, "gentle_step")


@pytest.mark.parametrize("payload", [
    ["Мой опыт важен"] * 4,
    {"focus": "Спокойный рост", "affirmations": ["Мой опыт важен"] * 3},
    {"focus": "Calm growth", "affirmations": ["Мой опыт важен"] * 4},
])
def test_release_card_contract_rejects_legacy_and_invalid_outputs(payload):
    with pytest.raises(ProviderOutputValidationError):
        _parse_card_text(json.dumps(payload, ensure_ascii=False), "ru")
