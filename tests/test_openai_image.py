from services.openai_image import _build_image_prompt, _ensure_no_text_clause


def test_ensure_no_text_clause_adds_suffix():
    p = _ensure_no_text_clause("A serene landscape at dawn")
    assert "No text, no words on the image" in p


def test_ensure_no_text_clause_idempotent():
    p = "Scene. No text, no words on the image."
    assert _ensure_no_text_clause(p) == p


def test_build_image_prompt_contains_sphere_and_no_text():
    prompt = _build_image_prompt(
        style="nature",
        sphere="inner_peace",
        subsphere=None,
        user_text="спокойствие",
        custom_style_description=None,
        color_mood="soft blue tones",
        composition_hint="wide horizon",
    )
    assert "inner_peace" in prompt or "affirmation" in prompt.lower()
    assert "no text" in prompt.lower()
