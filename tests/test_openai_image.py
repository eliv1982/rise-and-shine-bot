from services.openai_image import _build_image_prompt, _ensure_no_text_clause, _style_to_phrase


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
    assert "bright daily affirmation image" in prompt.lower()
    assert "phone screen" in prompt.lower()
    assert "no logos" in prompt.lower()


def test_build_image_prompt_avoids_literal_money_symbols():
    prompt = _build_image_prompt(
        style="soft_editorial",
        sphere="money",
        subsphere=None,
        user_text=None,
        custom_style_description=None,
        color_mood="champagne gold and ivory",
        composition_hint="editorial card composition with calm negative space",
    ).lower()
    assert "no text" in prompt
    assert "dollar signs" in prompt
    assert "coins" in prompt
    assert "charts" in prompt
    assert "piggy banks" in prompt


def test_old_style_keys_still_work():
    for style in ("realistic", "cartoon", "mandala", "sacred_geometry", "nature", "cosmos", "abstract"):
        assert _style_to_phrase(style)


def test_new_style_keys_return_non_empty_phrases():
    for style in (
        "soft_editorial",
        "bright_photo_card",
        "sunny_nature_photo",
        "light_interior_photo",
        "cinematic_real_photo",
        "bright_nature_card",
        "dreamy_painterly",
        "quiet_interior",
        "minimal_botanical",
        "cinematic_light",
        "ethereal_landscape",
        "symbolic_luxe",
        "textured_collage",
    ):
        assert _style_to_phrase(style)


def test_photo_prompt_contains_photo_direction_and_negatives():
    prompt = _build_image_prompt(
        style="auto",
        sphere="health",
        subsphere=None,
        user_text=None,
        custom_style_description=None,
        visual_mode="photo",
    ).lower()
    assert "photorealistic" in prompt
    assert "real high-quality photo" in prompt
    assert "no illustration" in prompt
    assert "no painting" in prompt
