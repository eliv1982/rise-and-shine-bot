import asyncio
import base64
import json
import os

import services.openai_image as openai_image
from handlers.generation import _build_image_debug_block
from services.openai_image import _build_image_prompt, _ensure_no_text_clause, _style_to_phrase, generate_image
from services.ritual_config import STYLE_LABELS


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
    assert "cash" in prompt
    assert "banknotes" in prompt
    assert "currency symbols" in prompt
    assert "charts" in prompt
    assert "piggy banks" in prompt
    assert "payment cards" in prompt
    assert "do not show money literally" in prompt


def test_old_style_keys_still_work():
    for style in ("realistic", "cartoon", "mandala", "sacred_geometry", "nature", "cosmos", "abstract"):
        assert _style_to_phrase(style)


def test_new_style_keys_return_non_empty_phrases():
    for style in (
        "soft_editorial",
        "sunny_photo_scene",
        "living_nature_photo",
        "sea_coast_photo",
        "bright_ocean_coast_photo",
        "calm_lifestyle_photo",
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


def test_bright_ocean_coast_style_has_localized_labels():
    assert STYLE_LABELS["bright_ocean_coast_photo"]["ru"] == "🌊 Яркое океанское побережье"
    assert STYLE_LABELS["bright_ocean_coast_photo"]["en"] == "🌊 Bright ocean coast"


def test_photo_prompt_contains_photo_direction_and_negatives():
    prompt = _build_image_prompt(
        style="auto",
        sphere="health",
        subsphere=None,
        user_text=None,
        custom_style_description=None,
        visual_mode="photo",
    ).lower()
    assert "realistic photography" in prompt
    assert "real photo" in prompt
    assert "genuine realistic photo" in prompt
    assert "lifestyle or editorial photo aesthetic" in prompt
    assert "camera-like realism" in prompt
    assert "natural daylight or believable indoor daylight" in prompt
    assert "realistic lens optics" in prompt
    assert "believable depth of field" in prompt
    assert "authentic photographic detail" in prompt
    assert "physically photographed" in prompt
    assert "photo scene preset:" in prompt
    assert "subtle imperfections of real photography" in prompt
    assert "clean but real composition" in prompt
    assert "no illustration" in prompt
    assert "no painting" in prompt
    assert "no painterly" in prompt
    assert "no brushstrokes" in prompt
    assert "no watercolor" in prompt
    assert "no canvas texture" in prompt
    assert "no digital art" in prompt
    assert "no digital painting" in prompt
    assert "no poster-like image" in prompt
    assert "no greeting card art" in prompt
    assert "no greeting card illustration" in prompt
    assert "no soft painterly haze" in prompt
    assert "not stylized artwork" in prompt
    assert "not a painting-like scene" in prompt
    assert "not an art print" in prompt
    assert "not a drawn scene" in prompt


def test_image_debug_block_contains_safe_routing_fields():
    block = _build_image_debug_block(
        {
            "visual_mode": "photo",
            "requested_style": "auto",
            "selected_style": "light_interior_photo",
            "prompt_branch": "photo",
            "scene_preset": "window_still_life",
            "text_provider": "yandex",
            "image_provider": "proxiapi",
            "tts_provider": "yandex",
            "text_model": "yandexgpt-lite/latest",
            "model": "gpt-image-1",
            "tts_model": "general",
            "voice": "oksana",
            "image_size": "1024x1024",
        },
        model="fallback-model",
        image_size="512x512",
    )
    assert "visual_mode: photo" in block
    assert "requested_style: auto" in block
    assert "selected_style: light_interior_photo" in block
    assert "prompt_branch: photo" in block
    assert "scene_preset: window_still_life" in block
    assert "text_provider: yandex" in block
    assert "image_provider: proxiapi" in block
    assert "tts_provider: yandex" in block
    assert "text_model: yandexgpt-lite/latest" in block
    assert "model: gpt-image-1" in block
    assert "tts_model: general" in block
    assert "voice: oksana" in block
    assert "image_size: 1024x1024" in block
    assert "final_prompt" not in block.lower()


def test_mixed_photo_style_uses_photo_prompt_branch():
    prompt = _build_image_prompt(
        style="living_nature_photo",
        sphere="inner_peace",
        subsphere=None,
        user_text=None,
        custom_style_description=None,
        visual_mode="mixed",
    ).lower()
    assert "photo branch only" in prompt
    assert "realistic nature photography" in prompt
    assert "no illustration" in prompt
    assert "no digital art" in prompt


def test_photo_prompt_uses_concrete_photographable_scenes():
    prompt = _build_image_prompt(
        style="calm_lifestyle_photo",
        sphere="money",
        subsphere=None,
        user_text=None,
        custom_style_description=None,
        visual_mode="photo",
    ).lower()
    assert "realistic interior still life photo" in prompt
    assert "bright organized desk" in prompt
    assert "table still life that looks photographed" in prompt


def test_money_photo_auto_uses_workspace_or_interior_scene_preset():
    prompt = _build_image_prompt(
        style="auto",
        sphere="money",
        subsphere=None,
        user_text=None,
        custom_style_description=None,
        visual_mode="photo",
    ).lower()
    assert "photo scene preset:" in prompt
    assert "calm_workspace" in prompt or "window_still_life" in prompt or "botanical_corner" in prompt
    assert "realistic clean workspace" in prompt or "realistic still life by a window" in prompt or "real plant or branches" in prompt
    assert "meadow edge" not in prompt


def test_photo_override_prompt_is_augmented_with_scene_and_negatives():
    prompt = openai_image._augment_photo_override_prompt(
        "A calm bright scene. No text.",
        "Photo scene preset: window_still_life. Realistic still life by a window.",
        "Photo negative prompt: no illustration, no painting, no digital art.",
    ).lower()
    assert "strict photo branch" in prompt
    assert "window_still_life" in prompt
    assert "no illustration" in prompt
    assert "no painting" in prompt


def test_relationships_photo_auto_uses_concrete_relationship_scene():
    prompt = _build_image_prompt(
        style="auto",
        sphere="relationships",
        subsphere=None,
        user_text=None,
        custom_style_description=None,
        visual_mode="photo",
    ).lower()
    assert "photo scene preset:" in prompt
    assert "relationship_table_scene" in prompt or "window_still_life" in prompt or "botanical_corner" in prompt
    assert "two cups" in prompt or "two chairs" in prompt or "realistic intimate" in prompt


def test_photo_nature_prompt_is_documentary_not_painterly():
    prompt = _build_image_prompt(
        style="living_nature_photo",
        sphere="inner_peace",
        subsphere=None,
        user_text=None,
        custom_style_description=None,
        visual_mode="photo",
        photo_scene_preset="outdoor_path",
    ).lower()
    assert "real nature photograph" in prompt
    assert "documentary-style natural scene" in prompt
    assert "real lens rendering" in prompt
    assert "crisp natural detail" in prompt
    assert "not painted" in prompt
    assert "not dreamy illustration" in prompt


def test_sea_coast_photo_prompt_contains_coastal_realism():
    prompt = _build_image_prompt(
        style="sea_coast_photo",
        sphere="inner_peace",
        subsphere=None,
        user_text=None,
        custom_style_description=None,
        visual_mode="photo",
        photo_scene_preset="ocean_sunrise",
    ).lower()
    assert "real coastal photograph" in prompt
    assert "sea or ocean coastline photography" in prompt
    assert "realistic sky and cloud formations" in prompt
    assert "believable wave and water behavior" in prompt
    assert "natural atmospheric perspective" in prompt
    assert "camera realism" in prompt
    assert "ocean_sunrise" in prompt
    assert "no watercolor" in prompt
    assert "no canvas texture" in prompt
    assert "no greeting card art" in prompt
    assert "no painterly" in prompt
    assert "visible shoreline" in prompt
    assert "open horizon over water" in prompt
    assert "waves, surf or sea foam" in prompt
    assert "desk scenes" in prompt
    assert "laptops" in prompt
    assert "notebooks" in prompt
    assert "cups" in prompt
    assert "tables" in prompt
    assert "interior window scenes" in prompt


def test_photo_auto_with_coastal_user_intent_prefers_coastal_constraints():
    prompt = _build_image_prompt(
        style="auto",
        sphere="inner_peace",
        subsphere=None,
        user_text="walk by the ocean coast at sunset",
        custom_style_description=None,
        visual_mode="photo",
    ).lower()
    assert "real coastal photograph" in prompt
    assert "visible shoreline" in prompt
    assert "avoid inland lakes" in prompt
    assert "not a lake" in prompt or "avoid inland lakes" in prompt
    assert "not a river" in prompt or "rivers" in prompt
    assert "interior window" in prompt
    assert "botanical still life" in prompt
    assert "canoe or boat in a calm river" in prompt
    assert "open horizon over water" in prompt
    assert "waves, surf or sea foam" in prompt
    assert "higher brightness" in prompt
    assert "natural saturation" in prompt
    assert "strong clarity" in prompt


def test_bright_ocean_coast_has_same_coastal_safety_markers_as_sea_coast():
    sea_prompt = _build_image_prompt(
        style="sea_coast_photo",
        sphere="inner_peace",
        subsphere=None,
        user_text=None,
        custom_style_description=None,
        visual_mode="photo",
    ).lower()
    bright_prompt = _build_image_prompt(
        style="bright_ocean_coast_photo",
        sphere="inner_peace",
        subsphere=None,
        user_text=None,
        custom_style_description=None,
        visual_mode="photo",
    ).lower()

    coastal_safety_markers = [
        "coastal realism is mandatory",
        "open ocean or open sea coast",
        "open horizon over water",
        "visible shoreline",
        "waves, surf or sea foam",
        "desk scenes",
        "laptops",
        "notebooks",
        "cups",
        "tables",
        "interior window scenes",
        "botanical still life",
    ]
    for marker in coastal_safety_markers:
        assert marker in sea_prompt
        assert marker in bright_prompt


def test_bright_ocean_coast_prompt_excludes_interior_workspace_items():
    prompt = _build_image_prompt(
        style="bright_ocean_coast_photo",
        sphere="career",
        subsphere=None,
        user_text="медитация на побережье океана",
        custom_style_description=None,
        visual_mode="photo",
    ).lower()
    assert "open ocean or open sea coast" in prompt
    assert "open horizon over water" in prompt
    assert "visible shoreline" in prompt
    assert "waves, surf or sea foam" in prompt
    assert "no desk" in prompt or "desk scenes" in prompt
    assert "no laptop" in prompt or "laptops" in prompt
    assert "no notebook" in prompt or "notebooks" in prompt
    assert "no cup" in prompt or "cups" in prompt
    assert "no table" in prompt or "tables" in prompt
    assert "interior window" in prompt
    assert "vase still-life" in prompt or "vase still life" in prompt


def test_custom_style_coastal_text_does_not_force_deterministic_coastal_routing():
    prompt = _build_image_prompt(
        style="auto",
        sphere="career",
        subsphere=None,
        user_text=None,
        custom_style_description="bright ocean coast with waves",
        visual_mode="photo",
    ).lower()

    assert "additional: bright ocean coast with waves" in prompt
    assert "realistic editorial photo of a bright workspace" in prompt
    assert "coastal realism is mandatory" not in prompt
    assert "avoid inland lakes" not in prompt
    assert "desk scenes" not in prompt


def _cleanup_generated_image(image_path):
    for path in (image_path, image_path.replace(".png", "_meta.json")):
        if path and os.path.exists(path):
            os.remove(path)
    output_dir = os.path.dirname(image_path)
    if output_dir and os.path.isdir(output_dir) and not os.listdir(output_dir):
        os.rmdir(output_dir)


def test_generate_image_coastal_override_path_uses_scene_and_generic_photo_safety(monkeypatch):
    monkeypatch.setenv("YANDEX_API_KEY", "test")
    monkeypatch.setenv("YANDEX_FOLDER_ID", "test")
    monkeypatch.setenv("PROXI_API_KEY", "test")
    monkeypatch.setenv("BOT_TOKEN", "test")
    monkeypatch.setenv("IMAGE_MODEL", "gpt-image-1")
    monkeypatch.setenv("IMAGE_SIZE", "1024x1024")

    captured = {}

    class FakeResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def json(self):
            return {"data": [{"b64_json": base64.b64encode(b"png").decode("ascii")}]}

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        def post(self, *args, **kwargs):
            captured["payload"] = kwargs["json"]
            return FakeResponse()

    monkeypatch.setattr(openai_image.aiohttp, "ClientSession", FakeSession)

    image_path = None
    try:
        image_path = asyncio.run(
            generate_image(
                style="auto",
                sphere="inner_peace",
                output_dir="test_outputs_phase42",
                file_basename="coastal_override",
                prompt_override="Real coastal photograph with ocean waves. No text.",
                resolved_style_override="sea_coast_photo",
                visual_mode="photo",
                focus_key="calm_breath",
            )
        )

        final_prompt = captured["payload"]["prompt"].lower()
        assert "real coastal photograph with ocean waves" in final_prompt
        assert "photo scene preset:" in final_prompt
        assert "strict photo branch" in final_prompt
        assert "no illustration" in final_prompt
        assert "no painting" in final_prompt
        assert "coastal realism is mandatory" in final_prompt
        assert "desk scenes" in final_prompt
        assert "interior window scenes" in final_prompt

        with open(image_path.replace(".png", "_meta.json"), "r", encoding="utf-8") as f:
            meta = json.load(f)
        assert meta["selected_style"] == "sea_coast_photo"
        assert meta["prompt_branch"] == "photo"
        assert meta["scene_preset"] in {
            "ocean_sunrise",
            "seaside_sunset",
            "quiet_beach_morning",
            "rocky_coast",
            "dunes_and_seabirds",
            "coastal_path",
        }
    finally:
        if image_path:
            _cleanup_generated_image(image_path)


def test_generate_image_non_coastal_override_keeps_generic_photo_safety_only(monkeypatch):
    monkeypatch.setenv("YANDEX_API_KEY", "test")
    monkeypatch.setenv("YANDEX_FOLDER_ID", "test")
    monkeypatch.setenv("PROXI_API_KEY", "test")
    monkeypatch.setenv("BOT_TOKEN", "test")
    monkeypatch.setenv("IMAGE_MODEL", "gpt-image-1")
    monkeypatch.setenv("IMAGE_SIZE", "1024x1024")

    captured = {}

    class FakeResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def json(self):
            return {"data": [{"b64_json": base64.b64encode(b"png").decode("ascii")}]}

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        def post(self, *args, **kwargs):
            captured["payload"] = kwargs["json"]
            return FakeResponse()

    monkeypatch.setattr(openai_image.aiohttp, "ClientSession", FakeSession)

    image_path = None
    try:
        image_path = asyncio.run(
            generate_image(
                style="auto",
                sphere="money",
                output_dir="test_outputs_phase42",
                file_basename="non_coastal_override",
                prompt_override="A realistic bright desk scene. No text.",
                resolved_style_override="light_interior_photo",
                visual_mode="photo",
                focus_key="order_and_clarity",
            )
        )

        final_prompt = captured["payload"]["prompt"].lower()
        assert "a realistic bright desk scene" in final_prompt
        assert "photo scene preset:" in final_prompt
        assert "strict photo branch" in final_prompt
        assert "no illustration" in final_prompt
        assert "no painting" in final_prompt
        assert "coastal realism is mandatory" not in final_prompt
        assert "open ocean or open sea coast" not in final_prompt
        assert "interior window scenes" not in final_prompt
    finally:
        if image_path:
            _cleanup_generated_image(image_path)


def test_generate_image_meta_contains_debug_fields(monkeypatch):
    monkeypatch.setenv("YANDEX_API_KEY", "test")
    monkeypatch.setenv("YANDEX_FOLDER_ID", "test")
    monkeypatch.setenv("PROXI_API_KEY", "test")
    monkeypatch.setenv("BOT_TOKEN", "test")
    monkeypatch.setenv("IMAGE_MODEL", "gpt-image-1")
    monkeypatch.setenv("IMAGE_SIZE", "1024x1024")

    class FakeResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def json(self):
            return {"data": [{"b64_json": base64.b64encode(b"png").decode("ascii")}]}

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(openai_image.aiohttp, "ClientSession", FakeSession)

    image_path = None
    try:
        image_path = asyncio.run(
            generate_image(
                style="auto",
                sphere="money",
                output_dir="test_outputs_phase42",
                file_basename="debug_meta",
                prompt_override="A realistic photo. No text.",
                resolved_style_override="light_interior_photo",
                visual_mode="photo",
                focus_key="order_and_clarity",
            )
        )
        meta_path = image_path.replace(".png", "_meta.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        assert meta["visual_mode"] == "photo"
        assert meta["requested_style"] == "auto"
        assert meta["selected_style"] == "light_interior_photo"
        assert meta["prompt_branch"] == "photo"
        assert meta["scene_preset"]
        assert meta["model"] == "gpt-image-1"
        assert meta["image_size"] == "1024x1024"
        assert meta["image_provider"] == "proxiapi"
        assert "final_prompt" in meta
    finally:
        if image_path:
            _cleanup_generated_image(image_path)
