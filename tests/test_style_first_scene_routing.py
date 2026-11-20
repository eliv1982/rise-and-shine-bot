"""FIX-03B-2A: style-owned routing, rotation and effective offline image requests."""

import asyncio
import base64
import datetime as dt
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from services import openai_image, ritual_config as config, scene_planner, yandex_gpt
from services.scene_prompt_builder import build_controlled_scene_prompt


SPHERES = config.MAIN_SPHERES + config.LEGACY_SPHERES
COMPATIBLE = {
    "sunny_morning_photo": {"outdoor_path", "restful_daily_scene", "city_veranda_morning", "window_still_life"},
    "living_nature_photo": {"outdoor_path", "riverside", "mountain_view"},
    "urban_city_photo": {"city_veranda_morning", "courtyard_cafe", "quiet_city_morning", "city_park", "bridge_walkway"},
    "cafe_terrace_photo": {"street_cafe_terrace", "city_veranda_morning", "courtyard_cafe", "bookstore_cafe"},
    "rural_calm_photo": {"village_veranda", "cottage_garden", "orchard_morning", "country_road"},
    "sea_coast_photo": {"ocean_sunrise", "seaside_sunset", "quiet_beach_morning", "rocky_coast", "dunes_and_seabirds", "coastal_path"},
    "cozy_home_photo": {"warm_living_room", "restful_daily_scene", "botanical_corner"},
    "book_nook_photo": {"bookshop_aisle", "reading_chair"},
    "calm_lifestyle_photo": {"calm_workspace", "relationship_table_scene", "hands_detail"},
}
FAMILIES = {
    "sunny_morning_photo": "photo_general", "living_nature_photo": "living_nature",
    "urban_city_photo": "urban", "cafe_terrace_photo": "cafe_terrace",
    "rural_calm_photo": "rural_calm", "sea_coast_photo": "coastal",
    "cozy_home_photo": "cozy_home", "book_nook_photo": "book_nook",
    "calm_lifestyle_photo": "calm_lifestyle",
}
ALIASES = [(alias, style) for alias, style in config.PHOTO_STYLE_ALIASES.items() if style in COMPATIBLE]


def expected_family(style, sphere):
    if style == "sunny_morning_photo" and sphere in {"career", "money"}:
        return "professional_calm"
    return FAMILIES[style]


@pytest.mark.parametrize("style", config.PHOTO_STYLE_KEYS)
@pytest.mark.parametrize("sphere", SPHERES)
def test_photo_routing_matrix_preserves_style_before_sphere_and_focus(style, sphere):
    candidates = config.get_photo_scene_presets(sphere, style)
    assert candidates and set(candidates) <= COMPATIBLE[style]
    overlap = [scene for scene in config.PHOTO_SCENE_ROUTING[sphere] if scene in COMPATIBLE[style]]
    if overlap and style != "sea_coast_photo":
        assert candidates == overlap
    else:
        assert set(candidates) == COMPATIBLE[style]
    for focus in config.get_focuses(sphere):
        for day_offset in range(7):
            kwargs = dict(user_id=42, day=dt.date(2030, 1, 7) + dt.timedelta(days=day_offset), focus_key=focus["key"])
            selected = config.resolve_photo_scene_preset(sphere, style, **kwargs)
            assert selected in candidates
            assert selected == config.resolve_photo_scene_preset(sphere, style, **kwargs)
        assert config.resolve_photo_scene_preset(sphere, style, focus_key=focus["key"]) in candidates


@pytest.mark.parametrize("style,sphere,excluded", [
    ("cafe_terrace_photo", "inner_peace", "window_still_life"),
    ("cafe_terrace_photo", "money", "window_still_life"),
    ("rural_calm_photo", "career", "botanical_corner"),
    ("urban_city_photo", "inner_peace", "outdoor_path"),
])
def test_confirmed_defects_cannot_return_incompatible_sphere_scene(style, sphere, excluded):
    assert excluded not in config.get_photo_scene_presets(sphere, style)
    assert config.resolve_photo_scene_preset(sphere, style) in COMPATIBLE[style]


@pytest.mark.parametrize("alias,style", ALIASES)
@pytest.mark.parametrize("sphere", SPHERES)
def test_legacy_aliases_share_canonical_photo_and_controlled_routing(alias, style, sphere):
    assert config.get_photo_scene_presets(sphere, alias) == config.get_photo_scene_presets(sphere, style)
    kwargs = dict(user_id=55, day=dt.date(2030, 4, 5), focus_key="steady_focus")
    assert config.resolve_photo_scene_preset(sphere, alias, **kwargs) == config.resolve_photo_scene_preset(sphere, style, **kwargs)
    assert scene_planner.resolve_scene_style_family(selected_style=alias, sphere=sphere) == expected_family(style, sphere)
    assert scene_planner.get_scene_candidates_for_style(selected_style=alias, sphere=sphere) == scene_planner.get_scene_candidates_for_style(selected_style=style, sphere=sphere)


@pytest.mark.parametrize("sphere", SPHERES)
@pytest.mark.parametrize("style", [None, "auto", "random_suitable", "unknown_style"])
def test_unresolved_auto_selector_retains_existing_sphere_contract(style, sphere):
    assert config.get_photo_scene_presets(sphere, style) == config.PHOTO_SCENE_ROUTING[sphere]


@pytest.mark.parametrize("sphere", SPHERES)
def test_resolved_auto_style_obeys_its_compatible_environment(sphere):
    for day_offset in range(14):
        day = dt.date(2030, 1, 7) + dt.timedelta(days=day_offset)
        style = config.resolve_style("auto", sphere, user_id=42, day=day, visual_mode="photo")
        assert style in config.PHOTO_STYLE_KEYS
        assert config.resolve_photo_scene_preset(sphere, style, user_id=42, day=day) in COMPATIBLE[style]
        assert scene_planner.resolve_scene_style_family(selected_style="auto", resolved_style=style, sphere=sphere) == expected_family(style, sphere)


@pytest.mark.parametrize("style", config.PHOTO_STYLE_KEYS)
def test_photo_variation_recent_scene_and_archetype_filters_and_exhaustion(style):
    # Preferred sphere scenes rotate first, then other compatible style scenes.
    for sphere in SPHERES:
        pool = config.get_photo_scene_presets(sphere, style)
        for scene in pool:
            assert scene in config.PHOTO_SCENE_PRESETS
            assert config.resolve_photo_scene_preset(sphere, style, recent_scene_presets=[other for other in pool if other != scene]) == scene
        all_archetypes = list({config.get_visual_archetype(style, scene) for scene in pool})
        assert config.resolve_photo_scene_preset(sphere, style, recent_scene_presets=list(COMPATIBLE[style]) + ["forest_path"], recent_archetypes=all_archetypes) in pool
        first_archetype = config.get_visual_archetype(style, pool[0])
        alternatives = [scene for scene in pool if config.get_visual_archetype(style, scene) != first_archetype]
        if alternatives:
            assert config.resolve_photo_scene_preset(sphere, style, recent_archetypes=[first_archetype]) in alternatives
        remaining = COMPATIBLE[style] - set(pool)
        if remaining:
            assert config.resolve_photo_scene_preset(sphere, style, recent_scene_presets=pool) in remaining
    reachable = {config.resolve_photo_scene_preset(sphere, style, recent_scene_presets=[other for other in COMPATIBLE[style] if other != scene]) for sphere in SPHERES for scene in COMPATIBLE[style]}
    assert reachable == COMPATIBLE[style]
    assert len(reachable) >= 2


@pytest.mark.parametrize("style", config.PHOTO_STYLE_KEYS)
@pytest.mark.parametrize("sphere", SPHERES)
def test_controlled_style_family_precedes_sphere_and_preserves_pool_on_exhaustion(style, sphere):
    assert scene_planner.resolve_scene_style_family(selected_style=style, sphere=sphere) == expected_family(style, sphere)
    assert scene_planner.resolve_scene_style_family(selected_style=style.upper(), sphere=sphere) == expected_family(style, sphere)
    pool = scene_planner.get_scene_candidates_for_style(selected_style=style, visual_mode="photo", sphere=sphere)
    assert len(pool) >= 2
    for scene in pool:
        assert scene in scene_planner.SCENE_PRESETS
    baseline = scene_planner.get_scene_candidates_for_style(selected_style=style, visual_mode="photo")
    if style == "sunny_morning_photo" and sphere in {"career", "money"}:
        assert pool == ["quiet_city_morning", "calm_cafe_corner", "bookstore_cafe", "city_park_before_work", "courtyard_morning", "office_morning_light", "coworking_quiet_corner", "bridge_walkway", "street_after_rain", "tram_stop_morning", "library_corner"]
    else:
        assert pool == baseline
    memory = {"recent_scene_types": pool, "recent_scene_families": [scene_planner.normalize_scene_family(scene) for scene in pool], "overused_scene_families": [scene_planner.normalize_scene_family(scene) for scene in pool], "prefer_scene_types": ["forest_path", "library_corner"]}
    plan = scene_planner.build_fallback_scene_plan(focus_title="steady focus", selected_style=style, sphere=sphere, visual_memory_context=memory)
    assert plan["scene_type"] in pool
    assert plan["mood"] == "calm, grounded atmosphere for: steady focus"


@pytest.mark.parametrize("style", config.PHOTO_STYLE_KEYS)
def test_controlled_variation_and_recent_family_filter_are_preserved(style):
    pool = scene_planner.get_scene_candidates_for_style(selected_style=style)
    for scene in pool:
        plan = scene_planner.build_fallback_scene_plan(focus_title=None, selected_style=style, visual_memory_context={"recent_scene_types": [other for other in pool if other != scene]})
        assert plan["scene_type"] == scene
    family = scene_planner.normalize_scene_family(pool[0])
    alternatives = [scene for scene in pool if scene_planner.normalize_scene_family(scene) != family]
    if alternatives:
        plan = scene_planner.build_fallback_scene_plan(focus_title=None, selected_style=style, visual_memory_context={"recent_scene_families": [family], "overused_scene_families": [family]})
        assert plan["scene_type"] in alternatives


def test_candidate_semantics_and_controlled_compatibility_boundaries():
    assert set(COMPATIBLE) == set(config.PHOTO_STYLE_KEYS)
    assert "city buildings" in config.PHOTO_SCENE_PRESETS["city_park"]
    assert "bookstore_cafe" in COMPATIBLE["cafe_terrace_photo"]
    assert "bookshop_aisle" not in COMPATIBLE["cafe_terrace_photo"]
    assert "botanical_corner" not in COMPATIBLE["living_nature_photo"]
    urban = scene_planner.get_scene_candidates_for_style(selected_style="urban_city_photo")
    assert "city_park" in urban and "autumn_park" not in urban and "library_corner" not in urban
    lifestyle = scene_planner.get_scene_candidates_for_style(selected_style="calm_lifestyle_photo")
    assert {"hands_detail", "balcony_garden", "calm_cafe_corner"} <= set(lifestyle)
    assert not {"library_corner", "reading_corner", "bookstore_cafe"} & set(lifestyle)
    # Coherent controlled pools retain their full existing variety.
    assert len(scene_planner.get_scene_candidates_for_style(selected_style="living_nature_photo")) == 12
    assert len(scene_planner.get_scene_candidates_for_style(selected_style="rural_calm_photo")) == 9
    assert len(scene_planner.get_scene_candidates_for_style(selected_style="cafe_terrace_photo")) == 7


@pytest.fixture
def offline_api(monkeypatch, tmp_path):
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
            if url == "https://offline.invalid/v1/images/generations":
                capture.images.append(kwargs["json"])
                return Response({"data": [{"b64_json": base64.b64encode(b"mock image").decode()}]})
            assert url == "https://offline.invalid/v1/chat/completions", url
            capture.texts.append(kwargs["json"])
            return Response({"choices": [{"message": {"content": json.dumps({"prompt": capture.llm_prompt})}}]})

    monkeypatch.setattr(openai_image.aiohttp, "ClientSession", Session)
    monkeypatch.setattr(openai_image, "get_outputs_dir", lambda: str(tmp_path))
    monkeypatch.setattr(openai_image, "get_image_provider_config", lambda: SimpleNamespace(base_url="https://offline.invalid/v1", model="unchanged-test-image-model", size="1024x1024", api_key="fake", timeout_seconds=30, provider="mock"))
    monkeypatch.setattr(yandex_gpt, "get_text_provider_config", lambda: SimpleNamespace(provider="openai", base_url="https://offline.invalid/v1", api_key="fake", model="unchanged-test-text-model", timeout_seconds=30))
    return capture


@pytest.mark.parametrize("path_kind", ["template", "template_fallback", "controlled", "llm"])
@pytest.mark.parametrize("style", config.PHOTO_STYLE_KEYS)
@pytest.mark.parametrize("sphere", SPHERES)
def test_effective_final_image_payload_matrix(offline_api, tmp_path, path_kind, style, sphere):
    plan = scene_planner.build_fallback_scene_plan(focus_title="steady focus", selected_style=style, resolved_style=style, visual_mode="photo", sphere=sphere)
    if path_kind == "controlled":
        built = build_controlled_scene_prompt(scene_plan=plan, selected_style=style, resolved_style=style, sphere=sphere, visual_mode="photo")
        trace = "scene_planner_local"
    else:
        offline_api.llm_prompt = f"{config.STYLE_DESCRIPTIONS[style]}. {plan['setting']}. No text." if path_kind == "llm" else ""
        built, trace = asyncio.run(yandex_gpt.build_enriched_image_prompt(style=style, resolved_style=style, sphere=sphere, subsphere=None, user_text=None, custom_style_description=None, affirmations=[], color_mood="warm natural tones", composition_hint="open balanced frame", use_llm=path_kind != "template", visual_mode="photo"))
        assert trace == path_kind
    output = Path(asyncio.run(openai_image.generate_image(style=style, resolved_style_override=style, sphere=sphere, visual_mode="photo", prompt_override=built, image_prompt_trace=trace, color_mood="warm natural tones", composition_hint="open balanced frame")))
    assert len(offline_api.images) == 1
    assert len(offline_api.texts) == (1 if path_kind in {"llm", "template_fallback"} else 0)
    payload = offline_api.images[0]
    prompt = payload["prompt"]
    meta = json.loads(output.with_name(output.stem + "_meta.json").read_text(encoding="utf-8"))
    assert payload["model"] == "unchanged-test-image-model"
    assert payload["n"] == 1 and payload["size"] == "1024x1024"
    assert meta["final_prompt"] == prompt and meta["prompt_source"] == trace
    assert meta["resolved_style"] == style and meta["visual_mode"] == "photo"
    assert "no text" in prompt.lower()
    assert "decorative symbolic card" not in prompt.lower()
    if path_kind == "controlled":
        assert meta["photo_scene_preset"] is None
        assert meta["scene_type"] == plan["scene_type"]
        assert plan["setting"] in prompt
        assert "Photo scene preset:" not in prompt
    else:
        scene = meta["photo_scene_preset"]
        assert scene in COMPATIBLE[style]
        assert config.PHOTO_SCENE_PRESETS[scene] in prompt
        assert prompt.count("Photo scene preset:") == 1
        if path_kind in {"template", "template_fallback"}:
            assert prompt == built.strip()
    # The old secondary sphere defaults must not undo compatible scene routing.
    assert "Prefer a bright organized desk" not in prompt
    assert "realistic editorial photo of a bright workspace" not in prompt
    assert "prefer light workspace" not in prompt
    if sphere == "money":
        assert "payment cards" in prompt
    (tmp_path / "effective_request.json").write_text(json.dumps({"path": path_kind, "style": style, "sphere": sphere, "text_requests": offline_api.texts, "image_request": payload, "metadata": meta}, indent=2), encoding="utf-8")
