"""FIX-03B-1: active photo descriptions and home/reading preset completeness.

Exercise real selectors, prompt builders and image handoffs; HTTP is mocked.
Broader family normalization and subject/avoid reconciliation belong to FIX-03B-2.
"""

import asyncio
import base64
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from services import openai_image, scene_planner, yandex_gpt
from services.ritual_config import (
    PHOTO_SCENE_PRESETS,
    PHOTO_STYLE_ALIASES,
    PHOTO_STYLE_KEYS,
    STYLE_DESCRIPTIONS,
    normalize_style_key,
)
from services.scene_prompt_builder import build_controlled_scene_prompt


PHOTO_IDENTITIES = [
    ("sunny_morning_photo", ("fresh sunny morning", "natural daylight", "camera realism")),
    ("urban_city_photo", ("city photography", "quiet street", "believable urban atmosphere")),
    ("cafe_terrace_photo", ("cafe terrace or city veranda", "awning", "planters", "facade details")),
    ("rural_calm_photo", ("rural morning photography", "cottage garden", "wooden porch", "countryside")),
]

NEW_PRESETS = [
    ("cozy_home_photo", "soft_blanket_corner", "cozy_home", ("blanket", "sofa")),
    ("cozy_home_photo", "morning_light_wall", "cozy_home", ("morning light", "wall")),
    ("book_nook_photo", "reading_chair", "book_nook", ("reading chair", "books", "lamp")),
]

AFFECTED_STYLES = [style for style, _ in PHOTO_IDENTITIES] + ["cozy_home_photo", "book_nook_photo"]
HOME_CANDIDATES = [
    (style, scene)
    for style in ("cozy_home_photo", "book_nook_photo")
    for scene in scene_planner.get_scene_candidates_for_style(selected_style=style, visual_mode="photo")
]


@pytest.mark.parametrize("style,anchors", PHOTO_IDENTITIES)
def test_active_photo_style_keeps_its_visual_identity(style, anchors):
    phrase = openai_image._style_to_phrase(style)
    assert phrase == STYLE_DESCRIPTIONS[style]
    assert openai_image._style_to_phrase(style.upper()) == phrase
    for anchor in anchors:
        assert anchor in phrase


@pytest.mark.parametrize("alias,canonical", [
    (alias, canonical) for alias, canonical in PHOTO_STYLE_ALIASES.items() if canonical in PHOTO_STYLE_KEYS
])
def test_legacy_photo_alias_keeps_canonical_description(alias, canonical):
    assert normalize_style_key(alias) == canonical
    assert openai_image._style_to_phrase(alias) == STYLE_DESCRIPTIONS[canonical]


@pytest.mark.parametrize("style", AFFECTED_STYLES)
def test_every_candidate_in_affected_pool_has_a_complete_definition(style):
    # These pools need no generic fallback: each selectable key owns a preset.
    candidates = scene_planner.get_scene_candidates_for_style(selected_style=style, visual_mode="photo")
    assert candidates
    for scene in candidates:
        assert scene in scene_planner.SCENE_PRESETS, (style, scene)
        preset = scene_planner.SCENE_PRESETS[scene]
        for field in ("setting", "main_subject", "composition", "lighting", "mood"):
            assert isinstance(preset[field], str) and preset[field].strip(), (scene, field)
        assert preset["visual_motifs"] and all(preset["visual_motifs"])


@pytest.mark.parametrize("style,scene,family,anchors", NEW_PRESETS)
def test_new_preset_resolves_in_its_intended_pool_and_family(style, scene, family, anchors):
    assert scene in scene_planner.get_scene_candidates_for_style(selected_style=style, visual_mode="photo")
    assert scene_planner.normalize_scene_family(scene) == family
    plan = scene_planner.normalize_scene_plan({"scene_type": scene})
    preset = scene_planner.SCENE_PRESETS[scene]
    for field in ("setting", "main_subject", "composition", "lighting", "mood", "visual_motifs"):
        assert plan[field] == preset[field]
    subject = f"{plan['setting']} {plan['main_subject']}".lower()
    for anchor in anchors:
        assert anchor in subject
    # New positive instructions must not require anything in the default avoid list.
    assert not set(plan["visual_motifs"]) & set(plan["avoid"])


@pytest.mark.parametrize("style,scene", HOME_CANDIDATES)
def test_each_home_or_reading_selection_keeps_its_interior(style, scene):
    candidates = scene_planner.get_scene_candidates_for_style(selected_style=style, visual_mode="photo")
    plan = scene_planner.build_fallback_scene_plan(
        focus_title=None, selected_style=style, resolved_style=style, visual_mode="photo",
        visual_memory_context={"recent_scene_types": [other for other in candidates if other != scene]},
    )
    assert plan["scene_type"] == scene
    preset = scene_planner.SCENE_PRESETS[scene]
    assert plan["setting"] == preset["setting"]
    assert plan["main_subject"] == preset["main_subject"]
    prompt = build_controlled_scene_prompt(
        scene_plan=plan, selected_style=style, resolved_style=style, visual_mode="photo",
    )
    assert f"Setting: {preset['setting']}." in prompt
    assert f"Main subject: {preset['main_subject']}." in prompt
    assert "quiet natural scene with soft light" not in prompt
    assert "quiet natural motifs" not in prompt
    assert "outdoor nature scene only" not in prompt
    assert "Scene type: forest_path." not in prompt


@pytest.fixture
def image_api(monkeypatch, tmp_path):
    capture = SimpleNamespace(images=[], texts=[], llm_prompt="")

    class Response:
        status = 200

        def __init__(self, data):
            self.data = data

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def json(self):
            return self.data

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        def post(self, url, **kwargs):
            payload = kwargs["json"]
            if url == "https://offline.invalid/v1/images/generations":
                capture.images.append(payload)
                return Response({"data": [{"b64_json": base64.b64encode(b"mock png").decode()}]})
            assert url == "https://offline.invalid/v1/chat/completions", url
            capture.texts.append(payload)
            return Response({"choices": [{"message": {"content": json.dumps({"prompt": capture.llm_prompt})}}]})

    monkeypatch.setattr(openai_image.aiohttp, "ClientSession", Session)
    monkeypatch.setattr(openai_image, "get_outputs_dir", lambda: str(tmp_path))
    monkeypatch.setattr(openai_image, "get_image_provider_config", lambda: SimpleNamespace(
        base_url="https://offline.invalid/v1", model="unchanged-test-image-model", size="1024x1024",
        api_key="fake", timeout_seconds=30, provider="mock",
    ))
    monkeypatch.setattr(yandex_gpt, "get_text_provider_config", lambda: SimpleNamespace(
        provider="openai", base_url="https://offline.invalid/v1", api_key="fake",
        model="unchanged-test-text-model", timeout_seconds=30,
    ))
    return capture


def assert_photo_contract(prompt, meta, style):
    assert meta["resolved_style"] == style
    assert meta["visual_mode"] == meta["prompt_branch"] == "photo"
    assert meta["final_prompt"] == prompt
    assert "realistic photo" in prompt.lower()
    assert "no text" in prompt.lower()
    for marker in ("mandala", "rosette", "radial symmetry", "decorative symbolic card"):
        assert marker not in prompt.lower()


@pytest.mark.parametrize("style,scene,family,anchors", NEW_PRESETS)
def test_new_interior_scene_survives_final_mocked_image_payload(image_api, style, scene, family, anchors):
    controlled = build_controlled_scene_prompt(
        scene_plan={"scene_type": scene}, selected_style=style, resolved_style=style, visual_mode="photo",
    )
    path = asyncio.run(openai_image.generate_image(
        style=style, resolved_style_override=style, sphere="inner_peace", visual_mode="photo",
        prompt_override=controlled, image_prompt_trace="scene_planner_local",
        color_mood="warm cream and walnut", composition_hint="quiet interior with gentle depth",
    ))
    prompt = image_api.images[0]["prompt"]
    meta = json.loads(Path(path).with_name(Path(path).stem + "_meta.json").read_text(encoding="utf-8"))
    assert_photo_contract(prompt, meta, style)
    assert prompt.startswith(controlled)
    assert meta["scene_type"] == meta["scene_preset"] == scene
    assert meta["photo_scene_preset"] is None
    assert not image_api.texts
    assert "Photo scene preset:" not in prompt
    assert "quiet natural scene with soft light" not in prompt
    assert f"Style direction: {style}." in prompt


@pytest.mark.parametrize("path_kind", ["controlled", "template", "enriched", "fallback"])
@pytest.mark.parametrize("style,anchors", PHOTO_IDENTITIES)
def test_photo_style_handoffs_preserve_existing_path_contracts(image_api, path_kind, style, anchors):
    plan = scene_planner.build_fallback_scene_plan(
        focus_title=None, selected_style=style, resolved_style=style, visual_mode="photo",
    )
    if path_kind == "controlled":
        built_prompt = build_controlled_scene_prompt(
            scene_plan=plan, selected_style=style, resolved_style=style, visual_mode="photo",
        )
        trace = "scene_planner_local"
    else:
        image_api.llm_prompt = (
            f"{STYLE_DESCRIPTIONS[style]}. {plan['setting']}. No text."
            if path_kind == "enriched" else "Ocean waves. No text."
        )
        built_prompt, trace = asyncio.run(yandex_gpt.build_enriched_image_prompt(
            style=style, resolved_style=style, sphere="inner_peace", subsphere=None,
            user_text=None, custom_style_description=None, affirmations=[],
            color_mood="warm natural tones", composition_hint=plan["composition"],
            use_llm=path_kind != "template", visual_mode="photo",
        ))
        assert trace == {"template": "template", "enriched": "llm", "fallback": "template_fallback"}[path_kind]
    path = asyncio.run(openai_image.generate_image(
        style=style, resolved_style_override=style, sphere="inner_peace", visual_mode="photo",
        prompt_override=built_prompt, image_prompt_trace=trace,
        color_mood="warm natural tones", composition_hint=plan["composition"],
    ))
    assert len(image_api.images) == 1
    prompt = image_api.images[0]["prompt"]
    meta = json.loads(Path(path).with_name(Path(path).stem + "_meta.json").read_text(encoding="utf-8"))
    assert_photo_contract(prompt, meta, style)
    assert meta["prompt_source"] == trace
    assert prompt.startswith(built_prompt.strip())
    assert len(image_api.texts) == (1 if path_kind in {"enriched", "fallback"} else 0)
    if path_kind == "controlled":
        assert f"Style direction: {style}." in prompt
        assert plan["setting"] in prompt
        assert meta["scene_type"] == plan["scene_type"]
        assert meta["photo_scene_preset"] is None
        assert "Photo scene preset:" not in prompt
    else:
        for anchor in anchors:
            assert anchor in prompt
        assert meta["photo_scene_preset"] in PHOTO_SCENE_PRESETS
        assert PHOTO_SCENE_PRESETS[meta["photo_scene_preset"]] in prompt
        assert prompt.count("Photo scene preset:") == 1
        if path_kind in {"template", "fallback"}:
            assert prompt == built_prompt.strip()
