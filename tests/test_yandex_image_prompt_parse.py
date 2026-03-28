from services.yandex_gpt import parse_llm_image_prompt_json


def test_parse_json_object():
    raw = '{"prompt": "A calm sunrise over mountains, symbolic path forward."}'
    assert parse_llm_image_prompt_json(raw) == "A calm sunrise over mountains, symbolic path forward."


def test_parse_fenced_json():
    raw = """```json
{"prompt": "Soft abstract waves in pastel colors."}
```"""
    assert "pastel" in (parse_llm_image_prompt_json(raw) or "")


def test_parse_invalid_returns_none():
    assert parse_llm_image_prompt_json("not json") is None
