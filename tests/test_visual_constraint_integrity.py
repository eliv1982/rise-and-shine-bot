"""FIX-03B-2B-1: provenance, deterministic resolution and offline final payloads."""

import asyncio
import base64
import datetime as dt
import json
import re
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from services import openai_image, scene_planner as planner, yandex_gpt
from services.coastal_intent import parse_coastal_text, user_coastal_intent, user_scene_prompt_parts
from services.ritual_config import resolve_style
from services.scene_prompt_builder import build_controlled_scene_prompt
from services.visual_constraints import (
    _fragments, forbidden_objects, positive_objects, suppress_soft_avoids, user_visual_constraints,
)


@pytest.mark.parametrize("text,positive,negative", [
    ("Show a mug. No windows", {"mug"}, {"window"}),
    ("No cups, tables and notebooks", set(), {"mug", "table", "notebook"}),
    ("Avoid windows, mugs; show a notebook", {"notebook"}, {"window", "mug"}),
    ("Покажи стол и блокнот. Без кружек и людей", {"table", "notebook"}, {"mug", "human"}),
    ("Без рук и ног", set(), {"hands", "body"}),
    ("No visible human body parts", set(), {"body"}),
    ("No people or visible body parts", set(), {"human", "body"}),
    ("I lost my notebook and use a table at work", set(), set()),
    ("I have no time for my notebook", set(), set()),
    ("A mug on a table", {"mug", "table"}, set()),
    ("tabletop, stable, windowsill, cupping, notebookish", set(), set()),
    ("Show a forest without people", set(), {"human"}),
    ("mug", {"mug"}, set()),
])
def test_bounded_authoritative_input_matching(text, positive, negative):
    assert user_visual_constraints(text) == (positive, negative)


@pytest.mark.parametrize("text", [
    "Show a mug. No cups", "No people; show hands", "Покажи кружку. Без чашек",
    "Include a notebook, avoid notebooks", "Show a window; no windows",
    "Show tables. No table", "Show a person; no human presence",
])
def test_explicit_conflict_is_unresolved(text):
    with pytest.raises(ValueError, match="Unresolved explicit visual conflict"):
        user_visual_constraints(text)


def test_custom_notes_are_authoritative_only_when_selected():
    assert user_visual_constraints("No mugs", style="nature", custom_style_description="Show a cup") == (set(), {"mug"})
    with pytest.raises(ValueError, match="explicit visual conflict"):
        user_visual_constraints("No mugs", style="custom", custom_style_description="Show a cup")
    with pytest.raises(ValueError, match="explicit visual conflict"):
        user_visual_constraints("No mugs", style="custom", custom_style_description="Editorial still life featuring a ceramic mug")
    assert user_visual_constraints("a geometric figure", style="custom", custom_style_description="a geometric figure")[0] == set()


@pytest.mark.parametrize("subject,ban", [
    ("ceramic mug", "cups"), ("coffee cups", "mug"), ("small tables", "table"),
    ("open notebook", "notebooks"), ("broad window", "windows"),
])
@pytest.mark.parametrize("origin", ["default", "planner", "memory"])
def test_required_scene_objects_override_only_automatic_avoids(subject, ban, origin):
    plan = {"scene_type": "test_scene", "setting": "calm room", "main_subject": subject}
    if origin == "planner":
        plan["avoid"] = [ban]
    memory = {"hard_avoid_today": [ban]} if origin == "memory" else None
    normalized = planner.normalize_scene_plan(plan, memory)
    assert not set(user_visual_constraints("Avoid " + ", ".join(normalized["avoid"]))[1]) & positive_objects(subject)
    assert subject == normalized["main_subject"]
    assert planner.normalize_scene_plan(normalized, memory) == normalized


def test_source_provenance_survives_repeated_normalization_and_hard_exclusions():
    plan = planner.normalize_scene_plan(
        {"scene_type": "forest_path", "avoid": ["lens flare"]},
        {"hard_avoid_today": ["no notebooks", "table"]},
    )
    plan = planner.reconcile_scene_constraints(plan, user_text="No windows. Show a notebook", selected_style="living_nature_photo")
    for _ in range(3):
        plan = planner.normalize_scene_plan(plan)
        sources = plan["constraint_sources"]
        assert sources["user_exclusions"] == ["window"]
        assert sources["user_requests"] == ["notebook"]
        assert "no notebooks" in sources["memory_avoid"]
        assert "no notebooks" not in sources["soft_avoid"]
        assert "lens flare" in sources["soft_avoid"]
        assert "no windows" in plan["avoid"]
        assert "no notebooks" not in plan["avoid"]

    mixed = planner.normalize_scene_plan(
        {"scene_type": "test_scene", "main_subject": "a mug"},
        {"hard_avoid_today": ["mug, fog and windows"]},
    )
    assert "fog" in mixed["avoid"]
    assert "fog" not in mixed["constraint_sources"]["soft_avoid"]
    assert planner.normalize_scene_plan(mixed) == mixed


def test_qualified_avoidance_and_nonconflicting_list_members_survive():
    assert suppress_soft_avoids(
        ["mugs and windows", "mug close-up", "notebook-centered productivity stock photo", "fog"], {"mug"},
    ) == ["windows", "mug close-up", "notebook-centered productivity stock photo", "fog"]
    assert not positive_objects("no mug, not table-centered; notebook without text") & {"mug", "table"}
    assert positive_objects(openai_image._ANATOMY_ANCHOR) == set()
    assert positive_objects("If a person appears, give them natural hands. Show a mug.") == {"mug"}
    assert suppress_soft_avoids(["mug, fog and windows", "mug close-up and notebooks"], {"mug", "notebook"}) == ["fog", "windows", "mug close-up"]


@pytest.mark.parametrize("field,value", [
    ("setting", "hands holding a leaf"), ("main_subject", "a person in the room"),
    ("composition", "visible arms in the foreground"), ("visual_motifs", ["background_guests"]),
    ("main_subject", "visible feet on a path"),
])
def test_explicit_none_never_emits_required_human_parts(field, value):
    with pytest.raises(ValueError, match="scene/exclusion conflict"):
        planner.build_scene_image_prompt({"scene_type": "forest_path", "human_presence": "none", field: value})


def test_hands_scene_has_consistent_fallback_presence():
    plan = planner.build_fallback_scene_plan(focus_title=None, visual_memory_context={"prefer_scene_types": ["hands_detail"]})
    assert plan["human_presence"] == "hands_only"
    assert "human" not in plan["avoid"]
    assert "hands interacting" in planner.build_scene_image_prompt(plan)


def test_explicit_people_request_overrides_generated_absence_default():
    plan = planner.reconcile_scene_constraints({"scene_type": "forest_path"}, user_text="Show hands")
    assert plan["human_presence"] == "hands_only"
    assert "human" not in plan["avoid"]
    assert "no hands" not in plan["avoid"]
    assert "No visible people" not in planner.build_scene_image_prompt(plan)


def test_hard_exclusion_chooses_existing_alternative_in_same_style():
    plan = planner.reconcile_scene_constraints(
        {"scene_type": "hands_detail", "human_presence": "hands_only"},
        user_text="No hands", selected_style="calm_lifestyle_photo", sphere="career",
    )
    assert plan["scene_type"] in planner.get_scene_candidates_for_style(selected_style="calm_lifestyle_photo")
    assert plan["scene_type"] != "hands_detail"
    assert not positive_objects(plan["setting"] + ". " + plan["main_subject"]) & {"hands"}
    assert "no hands" in plan["avoid"]


def test_no_people_cafe_without_compatible_preset_reports_unresolved():
    with pytest.raises(ValueError, match="within selected style"):
        build_controlled_scene_prompt(scene_plan={"scene_type": "street_cafe_terrace"}, selected_style="cafe_terrace_photo", user_text="No people")


def test_mandatory_style_ban_is_not_treated_as_a_soft_default():
    with pytest.raises(ValueError, match="living nature constraints"):
        build_controlled_scene_prompt(scene_plan={"scene_type": "office_morning_light"}, selected_style="living_nature_photo")


def test_local_template_cannot_bypass_mandatory_style_conflict(offline_api):
    with pytest.raises(ValueError, match="living nature constraints"):
        asyncio.run(yandex_gpt.build_enriched_image_prompt(
            style="living_nature_photo", sphere="career", subsphere=None, user_text="Show a mug",
            custom_style_description=None, affirmations=[], color_mood="natural daylight",
            composition_hint="open balanced frame", use_llm=False, visual_mode="photo",
        ))
    assert not offline_api.images and not offline_api.texts


def test_controlled_custom_positive_request_survives_default_avoid():
    prompt = build_controlled_scene_prompt(
        scene_plan={"scene_type": "forest_path"}, selected_style="custom",
        custom_style_description="Show a ceramic mug", user_text="calm mood",
    )
    assert "mug" not in re.search(r"Avoid: ([^.]+)", prompt).group(1).split(", ")
    assert "Show a ceramic mug" in prompt


def test_family_hints_reconcile_soft_bans_and_respect_hard_exclusions():
    prompt = build_controlled_scene_prompt(
        scene_plan={"scene_type": "office_morning_light", "human_presence": "none"},
        selected_style="sunny_morning_photo", user_text="No mugs",
        composition_hint="hands beside the window", focus_title="hands at rest",
        color_palette="hands in warm light",
    )
    assert "no mugs or cups" in prompt
    assert "coffee cup" not in prompt
    assert "hands beside" not in prompt and "hands at rest" not in prompt
    assert "hands in warm light" not in prompt
    assert "subtle human presence is optional" not in prompt
    prompt = build_controlled_scene_prompt(
        scene_plan={"scene_type": "office_morning_light"}, selected_style="sunny_morning_photo",
        focus_title="Avoid notebook",
    )
    assert "User exclusions: Avoid notebook" not in prompt
    assert "notebook planner" in prompt


@pytest.fixture
def offline_api(monkeypatch, tmp_path):
    capture = SimpleNamespace(images=[], texts=[])

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
                return Response({"data": [{"b64_json": base64.b64encode(b"offline image").decode()}]})
            assert url == "https://offline.invalid/v1/chat/completions"
            capture.texts.append(kwargs["json"])
            return Response({"choices": [{"message": {"content": "invalid JSON forces local fallback"}}]})

    monkeypatch.setattr(openai_image.aiohttp, "ClientSession", Session)
    monkeypatch.setattr(openai_image, "get_outputs_dir", lambda: str(tmp_path))
    monkeypatch.setattr(openai_image, "get_image_provider_config", lambda: SimpleNamespace(base_url="https://offline.invalid/v1", model="test-image", size="1024x1024", api_key="fake", timeout_seconds=30, provider="mock"))
    monkeypatch.setattr(yandex_gpt, "get_text_provider_config", lambda: SimpleNamespace(provider="openai", base_url="https://offline.invalid/v1", api_key="fake", model="test-text", timeout_seconds=30))
    return capture


@pytest.mark.parametrize("path_kind", ["direct", "template", "template_fallback", "controlled"])
@pytest.mark.parametrize("scene,style,scene_request,required", [
    ("office_morning_light", "sunny_morning_photo", "Show a mug", "mug"),
    ("street_cafe_terrace", "cafe_terrace_photo", "Show a table", "table"),
    ("office_morning_light", "sunny_morning_photo", "Show a notebook", "notebook"),
    ("quiet_cafe_window", "cafe_terrace_photo", "Show a window", "window"),
])
def test_deterministic_effective_payload_has_no_object_bans(offline_api, path_kind, scene, style, scene_request, required):
    prompt, trace = None, None
    if path_kind == "controlled":
        plan = planner.normalize_scene_plan({"scene_type": scene}, {"hard_avoid_today": [required]})
        prompt = build_controlled_scene_prompt(scene_plan=plan, user_text=scene_request, selected_style=style, visual_mode="photo")
        trace = "scene_planner_local"
    elif path_kind != "direct":
        prompt, trace = asyncio.run(yandex_gpt.build_enriched_image_prompt(
            style=style, sphere="career", subsphere=None, user_text=scene_request,
            custom_style_description=None, affirmations=[], color_mood="natural daylight",
            composition_hint="open balanced frame", use_llm=path_kind == "template_fallback", visual_mode="photo",
        ))
        assert trace == path_kind
    asyncio.run(openai_image.generate_image(
        style=style, sphere="career", user_text=scene_request, visual_mode="photo",
        prompt_override=prompt, image_prompt_trace=trace,
    ))
    final = offline_api.images[0]["prompt"]
    assert scene_request in final
    assert required in positive_objects(final)
    # Inspect complete object bans, keeping qualified anti-cliches legal.
    for avoid in re.findall(r"Avoid: ([^.]+)", final):
        assert required not in user_visual_constraints("Avoid " + avoid)[1]
    assert final.count("Scene type:") == (1 if path_kind == "controlled" else 0)
    assert final.count("Photo scene preset:") == (0 if path_kind == "controlled" else 1)
    if path_kind in {"template", "template_fallback"}:
        assert final == prompt.strip()
    assert len(offline_api.images) == 1
    assert len(offline_api.texts) == (1 if path_kind == "template_fallback" else 0)


_CP06_LIST_CASES = [
    ("No plants, mugs, and windows, and show a notebook", {"notebook"}, {"mug", "window"}),
    ("No mugs, plants, and windows", set(), {"mug", "window"}),
    ("Без растений, кружек, и окон, и покажи блокнот", {"notebook"}, {"mug", "window"}),
    ("No mugs, plants, vases, and windows, and include a notebook", {"notebook"}, {"mug", "window"}),
    ("Без кружек, растений, ваз, и окон, и покажите блокнот", {"notebook"}, {"mug", "window"}),
    ("No plants and mugs, vases and windows, and show a notebook", {"notebook"}, {"mug", "window"}),
    ("No mugs, plants and windows", set(), {"mug", "window"}),
    ("Without lanterns, pillows, and mugs; include a notebook", {"notebook"}, {"mug"}),
    ("No visible vases, mugs, and windows, and show a notebook", {"notebook"}, {"mug", "window"}),
    ("No mugs, ceramic vases, and windows, and show a notebook", {"notebook"}, {"mug", "window"}),
]


@pytest.mark.parametrize("text,required,excluded", _CP06_LIST_CASES)
@pytest.mark.parametrize("custom", [False, True])
def test_cp06_unknown_list_members_preserve_scope(text, required, excluded, custom):
    kwargs = {"user_text": text} if not custom else {
        "style": "custom", "custom_style_description": text,
    }
    assert user_visual_constraints(**kwargs) == (required, excluded)
    assert positive_objects(text) == required


@pytest.mark.parametrize("text,required,custom_required,excluded", [
    ("No plants, show a mug", {"mug"}, {"mug"}, set()),
    ("No plants; show a mug", {"mug"}, {"mug"}, set()),
    ("No plants. Show a mug", {"mug"}, {"mug"}, set()),
    ("No plants, a mug please", set(), {"mug"}, set()),
    ("No people, a mug please", set(), {"mug"}, {"human"}),
    ("No people, just me and a mug", set(), {"mug"}, {"human"}),
    ("Avoid people, and show a mug", {"mug"}, {"mug"}, {"human"}),
    ("No mugs, tables, and show a notebook", {"notebook"}, {"notebook"}, {"mug", "table"}),
    ("No mugs, tables, and windows", set(), set(), {"mug", "table", "window"}),
    ("I do not want to show a mug", set(), set(), {"mug"}),
    ("Never show people; show a window", {"window"}, {"window"}, {"human"}),
])
@pytest.mark.parametrize("custom", [False, True])
def test_cp06_required_negative_controls(text, required, custom_required, excluded, custom):
    kwargs = {"user_text": text} if not custom else {
        "style": "custom", "custom_style_description": text,
    }
    assert user_visual_constraints(**kwargs) == (custom_required if custom else required, excluded)


@pytest.mark.parametrize("text,required", [
    ("No plants, vases, and lanterns", set()),
    ("Без растений, ваз, и фонарей", set()),
    ("No time for my notebook, mugs", {"mug"}),
    ("No time for errands, mugs", {"mug"}),
])
def test_cp06_opaque_words_do_not_classify_unknown_prose(text, required):
    # Independent bare nouns retain their existing request semantics.
    assert user_visual_constraints(text) == (required, set())


@pytest.mark.parametrize("text,required,excluded", _CP06_LIST_CASES)
def test_cp06_coastal_prose_preserves_object_list_scope(text, required, excluded):
    positive, negative = user_scene_prompt_parts(text)
    assert positive_objects(positive) == required
    assert not re.search(r"\b(?:plants|vases|lanterns|pillows|растений|ваз)\b", positive, re.I)
    # Serialized exclusions must retain negative polarity across semicolons.
    assert not positive_objects(negative)
    assert user_visual_constraints(negative) == (set(), excluded)


@pytest.mark.parametrize("text,coast", [
    ("No people, ocean", "water"),
    ("No people, beach at sunset", "beach"),
    ("No plants, show rocky coast", "rocky"),
    ("No plants, include a lagoon", "lagoon"),
])
def test_cp06_shared_list_scope_preserves_accepted_coastal_grammar(text, coast):
    intent = user_coastal_intent(text)
    assert coast in intent.positive
    assert not intent.excluded
    assert intent.wants_coast


@pytest.mark.parametrize("text,required,excluded", _CP06_LIST_CASES[:5])
@pytest.mark.parametrize("custom", [False, True])
def test_cp06_provenance_normalization_and_caller_immutability(text, required, excluded, custom):
    raw = {"scene_type": "office_morning_light", "avoid": ["lens flare"]}
    memory = {"hard_avoid_today": ["no notebooks", "fog"]}
    raw_before, memory_before = deepcopy(raw), deepcopy(memory)
    plan = planner.normalize_scene_plan(raw, memory)
    plan_before = deepcopy(plan)
    style = "custom" if custom else "sunny_morning_photo"
    kwargs = dict(selected_style=style, resolved_style=resolve_style(style, "relationships", visual_mode="photo"),
                  sphere="relationships", user_text=None if custom else text,
                  custom_style_description=text if custom else None)
    if custom:
        assert kwargs["resolved_style"] == "custom"
    reconciled = planner.reconcile_scene_constraints(plan, **kwargs)
    assert reconciled["scene_type"] != "office_morning_light"
    for _ in range(3):
        sources = reconciled["constraint_sources"]
        assert sources["user_requests"] == sorted(required)
        assert sources["user_exclusions"] == sorted(excluded)
        assert sources["memory_avoid"] == ["no notebooks", "fog"]
        assert "lens flare" in sources["soft_avoid"]
        assert {"no mugs or cups", "no windows"} <= set(reconciled["avoid"])
        if required:
            assert "no notebooks" not in reconciled["avoid"]
        assert planner.normalize_scene_plan(reconciled, memory) == reconciled
        assert planner.reconcile_scene_constraints(reconciled, **kwargs) == reconciled
        reconciled = planner.normalize_scene_plan(reconciled)
    prompt = build_controlled_scene_prompt(scene_plan=plan, visual_mode="photo", **kwargs)
    assert build_controlled_scene_prompt(scene_plan=plan, visual_mode="photo", **kwargs) == prompt
    assert raw == raw_before and memory == memory_before and plan == plan_before


def _cp06_payload(offline_api, text, path_kind, custom):
    if custom:
        return _cp05_custom_payload(offline_api, text, path_kind)
    prompt, trace = None, None
    if path_kind == "controlled":
        prompt = build_controlled_scene_prompt(
            scene_plan={"scene_type": "office_morning_light"}, selected_style="sunny_morning_photo",
            visual_mode="photo", sphere="relationships", user_text=text,
        )
        trace = "scene_planner_local"
    elif path_kind != "direct":
        prompt, trace = asyncio.run(yandex_gpt.build_enriched_image_prompt(
            style="sunny_morning_photo", sphere="relationships", subsphere=None, user_text=text,
            custom_style_description=None, affirmations=[], color_mood="natural daylight",
            composition_hint="open balanced frame", use_llm=path_kind == "template_fallback", visual_mode="photo",
        ))
        assert trace == path_kind
    output = Path(asyncio.run(openai_image.generate_image(
        style="sunny_morning_photo", sphere="relationships", user_text=text, visual_mode="photo",
        prompt_override=prompt, image_prompt_trace=trace,
    )))
    final = offline_api.images[0]["prompt"]
    meta = json.loads(output.with_name(output.stem + "_meta.json").read_text(encoding="utf-8"))
    assert meta["final_prompt"] == meta["prompt"] == final
    assert meta["scene_type"] == meta["scene_preset"]
    assert meta["prompt_source"] == (trace or "template")
    assert final.count("Scene type:") == (1 if path_kind == "controlled" else 0)
    assert final.count("Photo scene preset:") == (0 if path_kind == "controlled" else 1)
    if path_kind == "controlled":
        assert meta["scene_type"] == re.match(r"Scene type: ([a-z_0-9]+)\.", final).group(1)
        assert meta["photo_scene_preset"] is None
    else:
        assert openai_image.PHOTO_SCENE_PRESETS[meta["scene_type"]] in final
    if path_kind in {"template", "template_fallback"}:
        assert final == prompt.strip()
    assert len(offline_api.images) == 1
    assert len(offline_api.texts) == (1 if path_kind == "template_fallback" else 0)
    return final


@pytest.mark.parametrize("text,required,excluded", _CP06_LIST_CASES[:5])
@pytest.mark.parametrize("custom", [False, True])
@pytest.mark.parametrize("path_kind", ["controlled", "direct", "template", "template_fallback"])
def test_cp06_final_provider_payload(offline_api, tmp_path, text, required, excluded, custom, path_kind):
    final = _cp06_payload(offline_api, text, path_kind, custom)
    assert not positive_objects(final.replace("Human presence: none.", "")) & excluded
    actual_required, actual_excluded = user_visual_constraints(final)
    assert required <= actual_required
    assert excluded <= actual_excluded
    for label in ("no mugs or cups", "no windows"):
        assert final.count(label) == 1
    if required:
        request = "покажите блокнот" if "покажите" in text else "покажи блокнот" if "покажи" in text else (
            "include a notebook" if "include" in text else "show a notebook")
        assert final.count(request) == 1
    # Inspect every positive field directly, not just with the repaired parser.
    for prose in re.findall(
        r'(?:User visual request: |The scene subtly reflects the idea: "|in the style: )([^.]*)', final,
    ):
        assert not re.search(r"\b(?:mugs?|cups?|windows?|кружек|окон)\b", prose, re.I)
        assert not re.search(r"\b(?:plants|vases|растений|ваз)\b", prose, re.I)
        assert not re.search(r"(?:^|; )\s*(?:and|or|и|или)\s*(?:;|$)", prose, re.I)
    assert "User exclusions:" in final
    (tmp_path / "cp06_effective_request.json").write_text(json.dumps({
        "path": path_kind, "custom": custom, "input": text,
        "required": sorted(required), "excluded": sorted(excluded),
        "image_request": offline_api.images[0], "text_requests": offline_api.texts,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.mark.parametrize("custom", [False, True])
@pytest.mark.parametrize("path_kind", ["controlled", "direct", "template", "template_fallback"])
@pytest.mark.parametrize("text", [
    "No plants, mugs, and windows, and show a window",
    "Без растений, кружек, и окон, и покажи окно",
    "Show a mug. No vases, mugs, plants, and windows",
])
def test_cp06_conflicts_stop_before_providers(offline_api, text, path_kind, custom):
    with pytest.raises(ValueError, match="Unresolved explicit visual conflict:"):
        _cp06_payload(offline_api, text, path_kind, custom)
    assert not offline_api.images and not offline_api.texts


@pytest.mark.parametrize("custom", [False, True])
@pytest.mark.parametrize("path_kind", ["controlled", "direct", "template", "template_fallback"])
@pytest.mark.parametrize("coast", ["Show rocky coast without beach", "Ocean view, no sandy beach", "Хочу океан и пальмы"])
def test_cp06_cross_scoper_retains_independent_coast_and_details(offline_api, coast, path_kind, custom):
    text = "Fine grain texture. No plants, mugs, and windows, and show a notebook. Soft blue palette. " + coast
    final = _cp06_payload(offline_api, text, path_kind, custom)
    assert "Fine grain texture" in final and "Soft blue palette" in final
    assert final.count("show a notebook") == 1
    intent = user_coastal_intent(text)
    actual = parse_coastal_text(final.replace("No shoreline foreground is required.", ""))
    assert actual.wants_coast and not actual.positive & intent.excluded
    assert intent.excluded <= actual.excluded
    assert not positive_objects(final.replace("Human presence: none.", "")) & {"mug", "window"}


def _cp05_custom_payload(offline_api, text, path_kind, *, user_text=None, sphere="relationships"):
    """Use real custom resolution/builders; only provider HTTP is replaced."""
    resolved = resolve_style("custom", sphere, visual_mode="photo")
    assert resolved == "custom"
    prompt, trace = None, None
    if path_kind == "controlled":
        prompt = build_controlled_scene_prompt(
            scene_plan={"scene_type": "office_morning_light"},
            selected_style="custom", resolved_style=resolved, visual_mode="photo",
            sphere=sphere, user_text=user_text, custom_style_description=text,
        )
        trace = "scene_planner_local"
    elif path_kind != "direct":
        prompt, trace = asyncio.run(yandex_gpt.build_enriched_image_prompt(
            style="custom", resolved_style=resolved, sphere=sphere, subsphere=None,
            user_text=user_text, custom_style_description=text, affirmations=[],
            color_mood="natural daylight", composition_hint="open balanced frame",
            use_llm=path_kind == "template_fallback", visual_mode="photo",
        ))
        assert trace == path_kind
    output = Path(asyncio.run(openai_image.generate_image(
        style="custom", resolved_style_override=resolved, sphere=sphere,
        user_text=user_text, custom_style_description=text, visual_mode="photo",
        prompt_override=prompt, image_prompt_trace=trace,
        color_mood="natural daylight", composition_hint="open balanced frame",
    )))
    final = offline_api.images[0]["prompt"]
    meta = json.loads(output.with_name(output.stem + "_meta.json").read_text(encoding="utf-8"))
    assert meta["resolved_style"] == "custom"
    assert meta["final_prompt"] == meta["prompt"] == final
    assert meta["scene_type"] == meta["scene_preset"]
    assert meta["prompt_source"] == (trace or "template")
    assert final.count("Scene type:") == (1 if path_kind == "controlled" else 0)
    assert final.count("Photo scene preset:") == (0 if path_kind == "controlled" else 1)
    if path_kind == "controlled":
        assert meta["scene_type"] == re.match(r"Scene type: ([a-z_0-9]+)\.", final).group(1)
        assert meta["photo_scene_preset"] is None
    else:
        assert openai_image.PHOTO_SCENE_PRESETS[meta["scene_type"]] in final
    if path_kind in {"template", "template_fallback"}:
        assert final == prompt.strip()
    assert len(offline_api.images) == 1
    assert len(offline_api.texts) == (1 if path_kind == "template_fallback" else 0)
    return final


@pytest.mark.parametrize("text,excluded,positive_request,style_detail", [
    ("No mugs, tables, and windows, and show a notebook", {"mug", "table", "window"}, "show a notebook", ""),
    ("Avoid people, show a mug", {"human"}, "show a mug", ""),
    ("No mugs, tables, and windows, and show a notebook, fine grain texture",
     {"mug", "table", "window"}, "show a notebook", "fine grain texture"),
    ("Fine grain texture. No mugs, tables, and windows, and show a notebook. Soft blue palette",
     {"mug", "table", "window"}, "show a notebook", "Soft blue palette"),
    ("Без кружек, столов, и окон, и покажи блокнот", {"mug", "table", "window"}, "покажи блокнот", ""),
])
@pytest.mark.parametrize("path_kind", ["controlled", "direct", "template", "template_fallback"])
def test_cp05_custom_final_payload_integrity(offline_api, text, excluded, positive_request, style_detail, path_kind):
    # Relationships has a compatible existing preset even before N-2 is fixed.
    # Neither custom style nor its real resolution is replaced with a photo style.
    final = _cp05_custom_payload(offline_api, text, path_kind)
    assert not positive_objects(final.replace("Human presence: none.", "")) & forbidden_objects(excluded)
    required, actual_excluded = user_visual_constraints(final)
    assert excluded <= actual_excluded
    assert ("mug" if "human" in excluded else "notebook") in required
    assert final.count(positive_request) == 1
    assert style_detail in final
    if "Fine grain texture" in text:
        assert "Fine grain texture" in final
    # Check the actual positive prose too, independently of object extraction.
    positive_prose = re.search(
        r"(?:User visual request: |Photo style direction: in the style: )([^.]*)", final,
    ).group(1)
    assert not re.search(r"(?:^|; )\s*(?:and|or|и|или)\s*(?:;|$)", positive_prose, re.I)
    if "table" in excluded:
        assert not re.search(r"\b(?:tables?|windows?|столов|окон)\b", positive_prose, re.I)


@pytest.mark.parametrize("path_kind", ["controlled", "direct", "template", "template_fallback"])
def test_cp05_custom_explicit_conflict_stops_before_all_providers(offline_api, path_kind):
    with pytest.raises(ValueError, match="Unresolved explicit visual conflict: mug"):
        _cp05_custom_payload(offline_api, "No mug, show a mug", path_kind)
    assert not offline_api.images and not offline_api.texts


@pytest.mark.parametrize("text", [
    "No mugs, tables, and windows, and show a notebook. Show rocky coast without beach",
    "No mugs, tables, and windows, and show a notebook. Ocean view, no sandy beach",
    "No mugs, tables, and windows, and show a notebook. Хочу океан и пальмы",
    "No mugs, tables, and windows, and show a notebook. Без моря",
])
@pytest.mark.parametrize("path_kind", ["controlled", "direct", "template", "template_fallback"])
def test_cp05_custom_coastal_intent_survives_object_filtering(offline_api, text, path_kind):
    intent = user_coastal_intent(None, style="custom", custom_style_description=text)
    final = _cp05_custom_payload(offline_api, text, path_kind)
    # Optional foreground composition is not a prohibition on the coast itself.
    actual = parse_coastal_text(final.replace("No shoreline foreground is required.", ""))
    assert actual.wants_coast == intent.wants_coast
    assert not actual.positive & intent.excluded
    assert intent.excluded <= actual.excluded
    assert not positive_objects(final.replace("Human presence: none.", "")) & {"mug", "table", "window"}
    assert "notebook" in positive_objects(final)
    assert final.count("show a notebook") == 1
    if intent.subtype == "rocky":
        assert "rocky" in actual.positive
    if "Хочу океан и пальмы" in text:
        assert "Хочу океан и пальмы" in final


@pytest.mark.parametrize("sphere", [None, "career"])
def test_cp05_custom_replacement_provenance_and_inputs_are_stable(monkeypatch, sphere):
    from services import scene_prompt_builder

    text = "No mugs, tables, and windows, and show a notebook"
    raw = {"scene_type": "office_morning_light", "avoid": ["lens flare"]}
    memory = {"hard_avoid_today": ["no notebooks"]}
    plan = planner.normalize_scene_plan(raw, memory)
    plan["constraint_sources"]["scene_hints"] = ["Work scene direction: coffee cup beside a window."]
    raw_before, memory_before, plan_before = deepcopy(raw), deepcopy(memory), deepcopy(plan)
    kwargs = dict(selected_style="custom", resolved_style=resolve_style("custom", sphere or "inner_peace", visual_mode="photo"),
                  custom_style_description=text, sphere=sphere)
    reconciled = planner.reconcile_scene_constraints(plan, **kwargs)
    assert reconciled["scene_type"] != "office_morning_light"
    for _ in range(3):
        sources = reconciled["constraint_sources"]
        assert sources["user_requests"] == ["notebook"]
        assert sources["user_exclusions"] == ["mug", "table", "window"]
        assert sources["memory_avoid"] == ["no notebooks"]
        assert sources["scene_hints"] == []
        assert "no notebooks" not in reconciled["avoid"]
        assert planner.reconcile_scene_constraints(reconciled, **kwargs) == reconciled
        assert planner.normalize_scene_plan(reconciled, memory) == reconciled

    observed = []

    def capture(candidate):
        normalized = planner.normalize_scene_plan(candidate)
        observed.append(normalized)
        return normalized

    monkeypatch.setattr(scene_prompt_builder, "normalize_scene_plan", capture)
    prompt = build_controlled_scene_prompt(scene_plan=plan, visual_mode="photo", **kwargs)
    rebuilt = observed[-1]
    assert rebuilt["scene_type"] == reconciled["scene_type"]
    assert rebuilt["constraint_sources"]["user_requests"] == ["notebook"]
    assert rebuilt["constraint_sources"]["user_exclusions"] == ["mug", "table", "window"]
    hints = rebuilt["constraint_sources"]["scene_hints"]
    assert not any("Work scene direction:" in hint for hint in hints)
    assert not positive_objects(". ".join(hints)) & {"mug", "table", "window"}
    assert not positive_objects(prompt.replace("Human presence: none.", "")) & {"mug", "table", "window"}
    assert prompt.count("show a notebook") == prompt.count("Scene type:") == 1
    assert build_controlled_scene_prompt(scene_plan=plan, visual_mode="photo", **kwargs) == prompt
    assert raw == raw_before and memory == memory_before and plan == plan_before


_CP04_NEGATIVE_LISTS = [
    ("Avoid mugs, tables, and windows", {"mug", "table", "window"}),
    ("No mugs, tables, and windows", {"mug", "table", "window"}),
    ("Избегайте кружек, и столов", {"mug", "table"}),
    ("Без людей, и окон", {"human", "window"}),
    ("No mugs, and tables", {"mug", "table"}),
    ("Avoid mugs, and windows", {"mug", "window"}),
    ("No mugs, tables, notebooks, and windows", {"mug", "table", "notebook", "window"}),
    ("Avoid mugs, tables, windows, and notebooks", {"mug", "table", "notebook", "window"}),
    ("Без кружек, столов, и окон", {"mug", "table", "window"}),
    ("Избегайте кружек, столов, окон, и блокнотов", {"mug", "table", "window", "notebook"}),
    ("No people, hands, and feet", {"human", "hands", "body"}),
    ("Без людей, рук, и ног", {"human", "hands", "body"}),
    ("No windows, or notebooks", {"window", "notebook"}),
    ("Без кружек, или столов", {"mug", "table"}),
    ("No mugs,\tAND   tables", {"mug", "table"}),
    ("No mugs, and tables or windows", {"mug", "table", "window"}),
]


@pytest.mark.parametrize("text,excluded", _CP04_NEGATIVE_LISTS)
@pytest.mark.parametrize("custom", [False, True])
def test_cp04_oxford_comma_excludes_every_list_member(text, excluded, custom):
    kwargs = {"user_text": text} if not custom else {
        "user_text": None, "style": "custom", "custom_style_description": text,
    }
    assert user_visual_constraints(**kwargs) == (set(), excluded)
    assert positive_objects(text) == set()
    assert all(negative and explicit for _, negative, explicit in _fragments(text))


@pytest.mark.parametrize("text,required,custom_required,excluded", [
    ("Avoid people, and show a mug", {"mug"}, {"mug"}, {"human"}),
    ("No mug, and show a table", {"table"}, {"table"}, {"mug"}),
    ("Avoid people, please show a mug", {"mug"}, {"mug"}, {"human"}),
    ("No people, a mug please", set(), {"mug"}, {"human"}),
    ("No people, just me and a mug", set(), {"mug"}, {"human"}),
    ("Avoid people, tables and windows", set(), set(), {"human", "table", "window"}),
    ("No cups, tables and notebooks", set(), set(), {"mug", "table", "notebook"}),
    ("No mugs please, and no windows either", set(), set(), {"mug", "window"}),
    ("Avoid people, show a mug", {"mug"}, {"mug"}, {"human"}),
    ("I do not want to show a mug", set(), set(), {"mug"}),
    ("Never show people; show a window", {"window"}, {"window"}, {"human"}),
    ("No mugs, tables, and windows, and show a notebook", {"notebook"}, {"notebook"}, {"mug", "table", "window"}),
    ("No mugs, and tables, please include a notebook", {"notebook"}, {"notebook"}, {"mug", "table"}),
    ("Без людей, и окон, и покажи стол", {"table"}, {"table"}, {"human", "window"}),
    ("Избегайте кружек, и столов, покажите окно", {"window"}, {"window"}, {"mug", "table"}),
    ("No people, and a mug please", set(), {"mug"}, {"human"}),
    ("No people, and just me and a mug", set(), {"mug"}, {"human"}),
])
@pytest.mark.parametrize("custom", [False, True])
def test_cp04_directive_and_ambiguity_boundaries(text, required, custom_required, excluded, custom):
    kwargs = {"user_text": text} if not custom else {
        "style": "custom", "custom_style_description": text,
    }
    assert user_visual_constraints(**kwargs) == (custom_required if custom else required, excluded)


@pytest.mark.parametrize("text,object_key", [
    ("Avoid mugs, tables, and windows, and show a window", "window"),
    ("No mugs, tables, and windows, and show a window", "window"),
    ("Избегайте кружек, и столов, покажи стол", "table"),
    ("Без людей, и окон, покажите окно", "window"),
    ("No mugs, tables, windows, and notebooks; include a notebook", "notebook"),
    ("Show a window. No mugs, tables, and windows", "window"),
])
@pytest.mark.parametrize("custom", [False, True])
def test_cp04_last_list_member_still_conflicts_with_explicit_request(text, object_key, custom):
    kwargs = {"user_text": text} if not custom else {
        "style": "custom", "custom_style_description": text,
    }
    with pytest.raises(ValueError, match="Unresolved explicit visual conflict: " + object_key):
        user_visual_constraints(**kwargs)


@pytest.mark.parametrize("text,excluded", _CP04_NEGATIVE_LISTS[:4])
@pytest.mark.parametrize("custom", [False, True])
@pytest.mark.parametrize("required", [set(), {"notebook"}])
def test_cp04_provenance_and_reconciliation_idempotency(text, excluded, custom, required):
    raw = {"scene_type": "office_morning_light", "avoid": ["lens flare"]}
    memory = {"hard_avoid_today": ["no notebooks", "fog"]}
    raw_before, memory_before = deepcopy(raw), deepcopy(memory)
    plan = planner.normalize_scene_plan(raw, memory)
    plan_before = deepcopy(plan)
    positive = "Show a notebook. " if required else ""
    kwargs = {"selected_style": "sunny_morning_photo", "user_text": positive + text}
    if custom:
        kwargs = {"selected_style": "custom", "resolved_style": "sunny_morning_photo",
                  "user_text": positive or None, "custom_style_description": text}
    reconciled = planner.reconcile_scene_constraints(plan, **kwargs)
    labels = {"mug": "no mugs or cups", "table": "no tables", "window": "no windows",
              "human": "no people or human presence"}
    for _ in range(3):
        sources = reconciled["constraint_sources"]
        assert sources["user_requests"] == sorted(required)
        assert sources["user_exclusions"] == sorted(excluded)
        assert sources["memory_avoid"] == ["no notebooks", "fog"]
        assert "lens flare" in sources["soft_avoid"]
        assert all(reconciled["avoid"].count(labels[key]) == 1 for key in excluded)
        if required:
            assert "no notebooks" not in reconciled["avoid"]
        assert planner.normalize_scene_plan(reconciled, memory) == reconciled
        assert planner.reconcile_scene_constraints(reconciled, **kwargs) == reconciled
        reconciled = planner.normalize_scene_plan(reconciled)
    assert raw == raw_before and memory == memory_before and plan == plan_before


@pytest.mark.parametrize("text,excluded", _CP04_NEGATIVE_LISTS[:4] + [
    ("No mugs, tables, notebooks, and windows", {"mug", "table", "notebook", "window"}),
    ("Избегайте кружек, столов, окон, и блокнотов", {"mug", "table", "window", "notebook"}),
])
@pytest.mark.parametrize("custom", [False, True])
@pytest.mark.parametrize("path_kind", ["controlled", "direct", "template", "template_fallback"])
def test_cp04_effective_payload_and_actual_scene(offline_api, text, excluded, custom, path_kind, tmp_path):
    style = "custom" if custom else "sunny_morning_photo"
    source = {"user_text": None if custom else text,
              "custom_style_description": text if custom else None}
    prompt, trace = None, None
    if path_kind == "controlled":
        prompt = build_controlled_scene_prompt(
            scene_plan={"scene_type": "office_morning_light"}, selected_style=style,
            resolved_style="sunny_morning_photo", visual_mode="photo", sphere="career",
            composition_hint="hands beside the window", **source,
        )
        trace = "scene_planner_local"
    elif path_kind != "direct":
        prompt, trace = asyncio.run(yandex_gpt.build_enriched_image_prompt(
            style=style, resolved_style="sunny_morning_photo", sphere="career", subsphere=None,
            affirmations=[], color_mood="natural daylight", composition_hint="hands beside the window",
            use_llm=path_kind == "template_fallback", visual_mode="photo", **source,
        ))
        assert trace == path_kind
    output = Path(asyncio.run(openai_image.generate_image(
        style=style, resolved_style_override="sunny_morning_photo", sphere="career",
        visual_mode="photo", prompt_override=prompt,
        image_prompt_trace=trace, photo_scene_preset_override="window_still_life" if path_kind == "direct" else None,
        image_hint="people with a coffee cup at a table beside the window", **source,
    )))
    assert len(offline_api.images) == 1
    assert len(offline_api.texts) == (1 if path_kind == "template_fallback" else 0)
    final = offline_api.images[0]["prompt"]
    labels = {"mug": "no mugs or cups", "table": "no tables", "notebook": "no notebooks",
              "window": "no windows", "human": "no people or human presence"}
    assert all(final.count(labels[key]) == 1 for key in excluded)
    assert not positive_objects(final.replace("Human presence: none.", "")) & forbidden_objects(excluded)
    assert excluded <= user_visual_constraints(final)[1]
    assert "User visual request:" not in final
    if "mug" in excluded:
        assert "coffee cup" not in final
    assert final.count("Scene type:") == (1 if path_kind == "controlled" else 0)
    assert final.count("Photo scene preset:") == (0 if path_kind == "controlled" else 1)
    if path_kind in {"template", "template_fallback"}:
        assert final == prompt.strip()
    meta = json.loads(output.with_name(output.stem + "_meta.json").read_text(encoding="utf-8"))
    assert meta["final_prompt"] == meta["prompt"] == final
    assert meta["scene_type"] == meta["scene_preset"]
    assert meta["prompt_source"] == (trace or "template")
    if path_kind == "controlled":
        scene = re.match(r"Scene type: ([a-z_0-9]+)\.", final).group(1)
        assert meta["scene_type"] == scene
        assert meta["photo_scene_preset"] is None
        assert planner.SCENE_PRESETS[scene]["setting"] in final
    else:
        scene = meta["photo_scene_preset"]
        assert meta["scene_type"] == scene
        assert openai_image.PHOTO_SCENE_PRESETS[scene] in final
        if path_kind == "direct" and "window" in excluded:
            assert scene != "window_still_life"
    (tmp_path / "cp04_effective_request.json").write_text(json.dumps({
        "path": path_kind, "custom": custom, "input": text, "required": [], "excluded": sorted(excluded),
        "image_request": offline_api.images[0], "text_requests": offline_api.texts, "metadata": meta,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.mark.parametrize("custom", [False, True])
@pytest.mark.parametrize("path_kind", ["controlled", "direct", "template", "template_fallback"])
def test_cp04_conflict_stops_before_providers(offline_api, custom, path_kind):
    text = "No mugs, tables, and windows, and show a window"
    style = "custom" if custom else "sunny_morning_photo"
    source = {"user_text": None if custom else text,
              "custom_style_description": text if custom else None}
    with pytest.raises(ValueError, match="Unresolved explicit visual conflict: window"):
        if path_kind == "controlled":
            build_controlled_scene_prompt(
                scene_plan={"scene_type": "office_morning_light"}, selected_style=style,
                resolved_style="sunny_morning_photo", **source,
            )
        elif path_kind == "direct":
            asyncio.run(openai_image.generate_image(style=style, sphere="career", **source))
        else:
            asyncio.run(yandex_gpt.build_enriched_image_prompt(
                style=style, resolved_style="sunny_morning_photo", sphere="career", subsphere=None,
                affirmations=[], color_mood="natural daylight", composition_hint="open frame",
                use_llm=path_kind == "template_fallback", visual_mode="photo", **source,
            ))
    assert not offline_api.images and not offline_api.texts


_CP03_REPRODUCTIONS = [
    ("Avoid people, show a mug", {"mug"}, {"human"}),
    ("Avoid mugs, show a table", {"table"}, {"mug"}),
    ("Exclude windows, show a notebook", {"notebook"}, {"window"}),
    ("Excluding people, include a window", {"window"}, {"human"}),
    ("Избегайте людей, show a mug", {"mug"}, {"human"}),
    ("Avoid people, please show a mug", {"mug"}, {"human"}),
]


@pytest.mark.parametrize("text,required,excluded", _CP03_REPRODUCTIONS)
@pytest.mark.parametrize("custom", [False, True])
def test_cp03_confirmed_directive_boundaries(text, required, excluded, custom):
    kwargs = {"user_text": text} if not custom else {
        "style": "custom", "custom_style_description": text,
    }
    assert user_visual_constraints(**kwargs) == (required, excluded)
    assert positive_objects(text) == required


def test_cp03_confirmed_same_object_conflict_retains_both_meanings():
    text = "Avoid people, show people"
    assert list(_fragments(text)) == [("people", True, True), ("people", False, True)]
    with pytest.raises(ValueError, match="Unresolved explicit visual conflict: human"):
        user_visual_constraints(text)


@pytest.mark.parametrize("negative_marker", [
    "Avoid", "Exclude", "Excluding", "Избегай", "Избегайте", "Исключи", "Исключите",
    "No", "Without", "Без",
])
@pytest.mark.parametrize("positive_marker", ["show", "include", "please show", "please include"])
@pytest.mark.parametrize("separator", [", ", "; ", ". ", " and "])
@pytest.mark.parametrize("negative_noun,positive_noun,excluded,required", [
    ("mugs", "a table", "mug", "table"),
    ("windows", "a notebook", "window", "notebook"),
    ("people", "a mug", "human", "mug"),
])
def test_cp03_metamorphic_directive_equivalence(
    negative_marker, positive_marker, separator, negative_noun, positive_noun, excluded, required,
):
    text = f"{negative_marker} {negative_noun}{separator}{positive_marker} {positive_noun}"
    assert user_visual_constraints(text) == ({required}, {excluded})
    assert positive_objects(text) == {required}


@pytest.mark.parametrize("separator", [", and ", " or ", " и ", " или ", " but ", "\n", "! ", "? "])
@pytest.mark.parametrize("positive_marker", ["show", "please include"])
def test_cp03_other_supported_boundaries(separator, positive_marker):
    text = f"Exclude mugs{separator}{positive_marker} a notebook"
    assert user_visual_constraints(text) == ({"notebook"}, {"mug"})


@pytest.mark.parametrize("text,required,excluded", [
    ("Избегайте людей, покажите кружку", {"mug"}, {"human"}),
    ("Исключи окна, изобрази блокнот", {"notebook"}, {"window"}),
    ("Исключите кружки и покажи стол", {"table"}, {"mug"}),
    ("Avoid mugs, I want a notebook", {"notebook"}, {"mug"}),
    ("Exclude windows, хочу блокнот", {"notebook"}, {"window"}),
    ("Show a notebook, avoid people, please include a window", {"notebook", "window"}, {"human"}),
    ("Avoid mugs, show a table, exclude windows, include a notebook", {"table", "notebook"}, {"mug", "window"}),
    ("Avoid people, tables and windows", set(), {"human", "table", "window"}),
    ("Exclude mugs, notebooks and tables", set(), {"mug", "notebook", "table"}),
    ("No cups, tables and notebooks", set(), {"mug", "table", "notebook"}),
    ("No mugs please, and no windows either", set(), {"mug", "window"}),
    ("Avoid people, tables and windows, please show a notebook", {"notebook"}, {"human", "table", "window"}),
    ("No people, a mug please", set(), {"human"}),
    ("No people, just me and a mug", set(), {"human"}),
])
def test_cp03_enumerations_and_mixed_directives(text, required, excluded):
    assert user_visual_constraints(text) == (required, excluded)


@pytest.mark.parametrize("predicate", [
    "I do not want to", "Do not ever", "I would rather not", "I do not want you to", "Never",
])
@pytest.mark.parametrize("verb", ["show", "include"])
@pytest.mark.parametrize("noun,excluded", [("a mug", "mug"), ("a table", "table"), ("a window", "window")])
def test_cp03_metamorphic_nested_verb_protection(predicate, verb, noun, excluded):
    text = f"{predicate} {verb} {noun}"
    assert user_visual_constraints(text) == (set(), {excluded})
    assert not positive_objects(text)
    # A preceding comma boundary must not leak past a fresh negative predicate.
    text = f"Avoid people, {text}, please include a notebook"
    assert user_visual_constraints(text) == ({"notebook"}, {"human", excluded})
    assert positive_objects(text) == {"notebook"}


@pytest.mark.parametrize("text", [
    "Avoid people, to show a mug", "Exclude windows, you to include a table",
    "Avoid people, discuss how to show a mug", "Avoid people please show a mug",
])
def test_cp03_unknown_links_do_not_become_independent_directives(text):
    required, _ = user_visual_constraints(text)
    assert not required
    assert not positive_objects(text)


@pytest.mark.parametrize("noun,object_key", [
    ("mugs", "mug"), ("tables", "table"), ("notebooks", "notebook"),
    ("windows", "window"), ("people", "human"), ("hands", "hands"), ("feet", "body"),
])
@pytest.mark.parametrize("separator", [", ", "; ", ". ", " and "])
@pytest.mark.parametrize("positive_marker", ["show", "please include"])
def test_cp03_metamorphic_conflict_preservation(noun, object_key, separator, positive_marker):
    text = f"Avoid {noun}{separator}{positive_marker} {noun}"
    with pytest.raises(ValueError, match="Unresolved explicit visual conflict: " + object_key):
        user_visual_constraints(text)


@pytest.mark.parametrize("text,required,excluded", _CP03_REPRODUCTIONS)
@pytest.mark.parametrize("custom", [False, True])
def test_cp03_provenance_idempotency_and_input_integrity(text, required, excluded, custom):
    raw = {"scene_type": "office_morning_light", "avoid": ["lens flare"]}
    memory = {"hard_avoid_today": ["no mugs", "no tables", "no notebooks", "no windows"]}
    raw_before, memory_before = deepcopy(raw), deepcopy(memory)
    plan = planner.normalize_scene_plan(raw, memory)
    plan_before = deepcopy(plan)
    kwargs = {"selected_style": "sunny_morning_photo", "user_text": text}
    if custom:
        kwargs = {"selected_style": "custom", "resolved_style": "sunny_morning_photo",
                  "custom_style_description": text}
    reconciled = planner.reconcile_scene_constraints(plan, **kwargs)
    for _ in range(3):
        sources = reconciled["constraint_sources"]
        assert sources["user_requests"] == sorted(required)
        assert sources["user_exclusions"] == sorted(excluded)
        assert sources["memory_avoid"] == memory["hard_avoid_today"]
        assert "lens flare" in sources["soft_avoid"]
        for key in required:
            assert "no " + key + "s" not in reconciled["avoid"]
        assert planner.normalize_scene_plan(reconciled, memory) == reconciled
        assert planner.reconcile_scene_constraints(reconciled, **kwargs) == reconciled
        reconciled = planner.normalize_scene_plan(reconciled)
    assert raw == raw_before and memory == memory_before and plan == plan_before


@pytest.mark.parametrize("path_kind", ["controlled", "direct", "template", "template_fallback"])
@pytest.mark.parametrize("text,required,excluded", _CP03_REPRODUCTIONS)
def test_cp03_production_payload_and_actual_scene(offline_api, text, required, excluded, path_kind, tmp_path):
    prompt, trace = None, None
    if path_kind == "controlled":
        plan = planner.normalize_scene_plan(
            {"scene_type": "office_morning_light"},
            {"hard_avoid_today": ["no mugs", "no tables", "no notebooks", "no windows"]},
        )
        prompt = build_controlled_scene_prompt(
            scene_plan=plan, selected_style="sunny_morning_photo", visual_mode="photo",
            sphere="career", user_text=text, composition_hint="hands beside the window",
        )
        trace = "scene_planner_local"
    elif path_kind != "direct":
        prompt, trace = asyncio.run(yandex_gpt.build_enriched_image_prompt(
            style="sunny_morning_photo", sphere="career", subsphere=None, user_text=text,
            custom_style_description=None, affirmations=[], color_mood="natural daylight",
            composition_hint="hands beside the window", use_llm=path_kind == "template_fallback",
            visual_mode="photo",
        ))
        assert trace == path_kind
    output = Path(asyncio.run(openai_image.generate_image(
        style="sunny_morning_photo", sphere="career", user_text=text, visual_mode="photo",
        prompt_override=prompt, image_prompt_trace=trace,
        photo_scene_preset_override="window_still_life" if path_kind == "direct" else None,
        image_hint="people with a coffee cup at a table beside the window",
    )))
    final = offline_api.images[0]["prompt"]
    # Literal clauses provide an oracle independent of the polarity parser.
    labels = {"mug": "no mugs or cups", "table": "no tables", "notebook": "no notebooks", "window": "no windows",
              "human": "no people or human presence"}
    for key in excluded:
        assert final.count(labels[key]) == 1
    for key in required:
        assert labels[key] not in final
    positive_directive = text.split(", ", 1)[1].removeprefix("please ")
    assert final.count(positive_directive) == 1
    actual_required, actual_excluded = user_visual_constraints(final)
    assert required <= actual_required
    assert excluded <= actual_excluded
    assert not required & actual_excluded
    assert not positive_objects(final.replace("Human presence: none.", "")) & forbidden_objects(excluded)
    assert final.count("Scene type:") == (1 if path_kind == "controlled" else 0)
    assert final.count("Photo scene preset:") == (0 if path_kind == "controlled" else 1)
    if path_kind in {"template", "template_fallback"}:
        assert final == prompt.strip()
    meta = json.loads(output.with_name(output.stem + "_meta.json").read_text(encoding="utf-8"))
    assert meta["final_prompt"] == meta["prompt"] == final
    assert meta["scene_type"] == meta["scene_preset"]
    assert meta["prompt_source"] == (trace or "template")
    if path_kind == "controlled":
        scene = re.match(r"Scene type: ([a-z_0-9]+)\.", final).group(1)
        assert meta["scene_type"] == scene
        assert meta["photo_scene_preset"] is None
        assert planner.SCENE_PRESETS[scene]["setting"] in final
    else:
        scene = meta["photo_scene_preset"]
        assert meta["scene_type"] == scene
        assert openai_image.PHOTO_SCENE_PRESETS[scene] in final
    assert len(offline_api.images) == 1
    assert len(offline_api.texts) == (1 if path_kind == "template_fallback" else 0)
    (tmp_path / "cp03_effective_request.json").write_text(json.dumps({
        "path": path_kind, "input": text, "required": sorted(required), "excluded": sorted(excluded),
        "image_request": offline_api.images[0], "text_requests": offline_api.texts, "metadata": meta,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.mark.parametrize("path_kind", ["controlled", "direct", "template", "template_fallback"])
def test_cp03_production_conflict_stops_before_providers(offline_api, path_kind):
    text = "Avoid people, show people"
    with pytest.raises(ValueError, match="Unresolved explicit visual conflict"):
        if path_kind == "controlled":
            build_controlled_scene_prompt(
                scene_plan={"scene_type": "office_morning_light"},
                selected_style="sunny_morning_photo", user_text=text,
            )
        elif path_kind == "direct":
            asyncio.run(openai_image.generate_image(
                style="sunny_morning_photo", sphere="career", user_text=text,
            ))
        else:
            asyncio.run(yandex_gpt.build_enriched_image_prompt(
                style="sunny_morning_photo", sphere="career", subsphere=None, user_text=text,
                custom_style_description=None, affirmations=[], color_mood="natural daylight",
                composition_hint="open frame", use_llm=path_kind == "template_fallback", visual_mode="photo",
            ))
    assert not offline_api.images and not offline_api.texts


@pytest.mark.parametrize("mode", ["photo", "illustration"])
@pytest.mark.parametrize("scene_request,forbidden", [
    ("No mugs", {"mug"}), ("No tables", {"table"}), ("No notebooks", {"notebook"}),
    ("No windows", {"window"}), ("No people", {"human", "hands", "body"}),
    ("No hands", {"hands"}),
])
def test_template_hard_exclusions_filter_generated_hints(offline_api, mode, scene_request, forbidden):
    asyncio.run(openai_image.generate_image(
        style="sunny_morning_photo" if mode == "photo" else "bright_nature_card",
        sphere="relationships", user_text=scene_request, visual_mode=mode,
        image_hint="hands by a table with a mug and notebook beside the window",
        composition_hint="hands by the window",
    ))
    final = offline_api.images[0]["prompt"]
    assert "User exclusions:" in final
    assert not positive_objects(final) & forbidden


@pytest.mark.parametrize("trace", [None, "template", "scene_planner_local", "llm"])
def test_explicit_conflicts_stop_before_image_provider(offline_api, trace):
    with pytest.raises(ValueError, match="explicit visual conflict"):
        asyncio.run(openai_image.generate_image(
            style="sunny_morning_photo", sphere="career", user_text="Show a mug. No cups",
            prompt_override="A cup on a table. No text." if trace else None, image_prompt_trace=trace,
        ))
    assert not offline_api.images and not offline_api.texts


def test_direct_template_records_actual_compatible_alternative(offline_api):
    output = Path(asyncio.run(openai_image.generate_image(
        style="calm_lifestyle_photo", sphere="career", user_text="No hands",
        visual_mode="photo", photo_scene_preset_override="hands_detail",
    )))
    meta = json.loads(output.with_name(output.stem + "_meta.json").read_text(encoding="utf-8"))
    assert meta["photo_scene_preset"] != "hands_detail"
    assert openai_image.PHOTO_SCENE_PRESETS[meta["photo_scene_preset"]] in meta["final_prompt"]
    assert not positive_objects(meta["final_prompt"]) & {"hands"}


def test_profile_text_avoids_do_not_enter_visual_constraints():
    plan = planner.normalize_scene_plan({"scene_type": "hands_detail", "avoid_topics": "people", "avoid_words": "hands"})
    assert plan["constraint_sources"]["user_exclusions"] == []
    assert "hands interacting" in planner.build_scene_image_prompt(plan)


@pytest.mark.parametrize("path_kind", ["manual", "scheduled"])
def test_orchestration_records_the_reconciled_controlled_scene(initialized_db, monkeypatch, offline_api, path_kind):
    import database as db
    import scheduler
    from handlers import generation
    from test_coastal_intent_integrity import Message, State, install_orchestration_stubs

    module = generation if path_kind == "manual" else scheduler
    install_orchestration_stubs(monkeypatch, module, "controlled", "hands_detail")
    records = []

    async def shadow(**kwargs):
        return {"scene_plan": {"scene_type": "hands_detail", "human_presence": "none"}}

    async def record(**kwargs):
        records.append(kwargs)

    monkeypatch.setattr(module, "build_scene_plan_shadow_best_effort", shadow)
    monkeypatch.setattr(module, "record_generation_history_best_effort", record)

    async def run():
        await db.create_or_update_user(1, "offline", name="User", language="en")
        if path_kind == "manual":
            monkeypatch.setattr(generation, "_generation_preflight_error", lambda *_: None)
            message = Message()
            state = State(sphere="career", style="calm_lifestyle_photo", visual_mode="photo")
            await generation._run_generation(message, state, theme_text="calm mood")
            assert len(message.photos) == 1, message.answers
        else:
            await db.create_subscription(
                1, "career", None, "calm_lifestyle_photo", "en", 8, 0,
                subscription_mode="sphere_focus", subscription_sphere="career",
                subscription_style_mode="calm_lifestyle_photo", visual_mode="photo", allowed_visual_modes=["photo"],
            )

            class Bot:
                async def send_photo(self, **kwargs):
                    return SimpleNamespace(photo=[])

            await scheduler.send_daily_affirmations(Bot(), now=dt.datetime(2030, 3, 1, 8, tzinfo=scheduler.MOSCOW))
        assert len(records) == 1

    asyncio.run(run())
    actual_scene = records[0]["scene_type"]
    assert actual_scene != "hands_detail"
    assert actual_scene in planner.get_scene_candidates_for_style(selected_style="calm_lifestyle_photo")
    assert records[0]["visual_motifs"]["scene_prompt_controlled"]["used_scene_type"] == actual_scene
    final = offline_api.images[0]["prompt"]
    assert final.startswith("Scene type: " + actual_scene + ".")
    assert "Human presence: none." in final
    assert not positive_objects(final.replace("Human presence: none.", "")) & {"human", "hands", "body"}


@pytest.mark.parametrize("separator", [" {join} ", ", {join} ", ", ", "; ", ". ", "\n", ": "])
@pytest.mark.parametrize("first,second,join,excluded", [
    ("No mug", "no table", "and", {"mug", "table"}),
    ("No people", "no windows", "or", {"human", "window"}),
    ("Avoid people", "avoid windows", "and", {"human", "window"}),
    ("Без людей", "без окон", "и", {"human", "window"}),
    ("Избегайте кружек", "исключите столы", "или", {"mug", "table"}),
    ("Не хочу видеть людей", "не хочу видеть окон", "и", {"human", "window"}),
])
def test_cp01_repeated_exclusions_keep_every_object(first, second, join, excluded, separator):
    text = first + separator.format(join=join) + second
    assert user_visual_constraints(text) == (set(), excluded)
    assert not positive_objects(text)


@pytest.mark.parametrize("text,excluded", [
    ("I do not want a mug", {"mug"}),
    ("I don't want a cup", {"mug"}),
    ("I don’t want a cup", {"mug"}),
    ("No people whatsoever", {"human"}),
    ("No mugs please, and no windows either", {"mug", "window"}),
    ("I'd rather not have a window", {"window"}),
    ("I’d rather not have a window", {"window"}),
    ("I would rather not have a window", {"window"}),
    ("Не хочу видеть людей", {"human"}),
    ("I do not want a mug and I do not want a window", {"mug", "window"}),
    ("No mugs and no tables and no windows", {"mug", "table", "window"}),
])
def test_cp01_bounded_exclusion_formulations(text, excluded):
    assert user_visual_constraints(text) == (set(), excluded)


@pytest.mark.parametrize("text", [
    "I read about people and windows",
    "I do not want to discuss a mug",
    "I do not want a mug removed",
    "No people whatsoever attended the meeting",
    "No mugs please the window designer",
    "I'd rather not have a window debate",
    "Не хочу видеть людей в отчете",
    "I have no time for my notebook and no reason to discuss windows",
    "No mugshot and no windowsill",
    "I mentioned the words mug and table",
])
def test_cp01_incidental_object_mentions_are_not_exclusions(text):
    assert user_visual_constraints(text) == (set(), set())


@pytest.mark.parametrize("text,positive,negative", [
    ("No mug and show a table", {"table"}, {"mug"}),
    ("Show a mug and no table", {"mug"}, {"table"}),
    ("No people whatsoever, and include a notebook", {"notebook"}, {"human"}),
    ("No mugs please, and show a window", {"window"}, {"mug"}),
    ("Без людей и покажи стол", {"table"}, {"human"}),
    ("Покажи стол и без окон", {"table"}, {"window"}),
    ("Не хочу видеть людей, но хочу окно", {"window"}, {"human"}),
    ("I'd rather not have a window; show a cup", {"mug"}, {"window"}),
])
def test_cp01_positive_directives_end_exclusions(text, positive, negative):
    assert user_visual_constraints(text) == (positive, negative)


@pytest.mark.parametrize("text", [
    "No mug and no table. Show a cup",
    "No people and no windows. Include hands",
    "Без людей и без окон. Покажи руки",
    "Avoid people and avoid windows. Show a person",
    "I do not want a mug. Show a cup",
    "No people whatsoever. Include a face",
    "No mugs please, and no windows either. Show a window",
    "I'd rather not have a window. Show windows",
    "Не хочу видеть людей. Покажи человека",
])
def test_cp01_conflicts_include_first_excluded_object(text):
    with pytest.raises(ValueError, match="Unresolved explicit visual conflict"):
        user_visual_constraints(text)


@pytest.mark.parametrize("text,excluded", [
    ("No mug and no table", {"mug", "table"}),
    ("No people and no windows", {"human", "window"}),
    ("Без людей и без окон", {"human", "window"}),
    ("Avoid people and avoid windows", {"human", "window"}),
    ("I do not want a mug", {"mug"}),
    ("No people whatsoever", {"human"}),
    ("No mugs please, and no windows either", {"mug", "window"}),
    ("I'd rather not have a window", {"window"}),
    ("Не хочу видеть людей", {"human"}),
])
@pytest.mark.parametrize("path_kind", ["direct", "template", "template_fallback", "controlled"])
def test_cp01_final_payload_preserves_explicit_exclusions(offline_api, text, excluded, path_kind):
    prompt, trace = None, None
    if path_kind == "controlled":
        prompt = build_controlled_scene_prompt(
            scene_plan={"scene_type": "office_morning_light"},
            selected_style="sunny_morning_photo", visual_mode="photo", sphere="career",
            user_text=text, composition_hint="hands beside the window",
        )
        trace = "scene_planner_local"
    elif path_kind != "direct":
        prompt, trace = asyncio.run(yandex_gpt.build_enriched_image_prompt(
            style="sunny_morning_photo", sphere="career", subsphere=None, user_text=text,
            custom_style_description=None, affirmations=[], color_mood="natural daylight",
            composition_hint="hands beside the window", use_llm=path_kind == "template_fallback",
            visual_mode="photo",
        ))
        assert trace == path_kind
    asyncio.run(openai_image.generate_image(
        style="sunny_morning_photo", sphere="career", user_text=text, visual_mode="photo",
        prompt_override=prompt, image_prompt_trace=trace,
        image_hint="people with a coffee cup at a table beside the window",
    ))
    final = offline_api.images[0]["prompt"]
    assert not positive_objects(final.replace("Human presence: none.", "")) & forbidden_objects(excluded)
    assert excluded <= user_visual_constraints(final)[1]
    if "mug" in excluded:
        assert "coffee cup" not in final
    assert final.count("Scene type:") == (1 if path_kind == "controlled" else 0)
    assert final.count("Photo scene preset:") == (0 if path_kind == "controlled" else 1)
    if path_kind in {"template", "template_fallback"}:
        assert final == prompt.strip()
    assert len(offline_api.images) == 1
    assert len(offline_api.texts) == (1 if path_kind == "template_fallback" else 0)


@pytest.mark.parametrize("trace", [None, "template", "scene_planner_local", "llm"])
def test_cp01_repeated_exclusion_conflict_stops_before_image_provider(offline_api, trace):
    with pytest.raises(ValueError, match="explicit visual conflict"):
        asyncio.run(openai_image.generate_image(
            style="sunny_morning_photo", sphere="career",
            user_text="Show a cup. No mug and no table",
            prompt_override="A coffee cup. No text." if trace else None, image_prompt_trace=trace,
        ))
    assert not offline_api.images and not offline_api.texts


@pytest.mark.parametrize("custom", [False, True])
def test_cp01_exclusion_provenance_and_normalization_are_stable(custom):
    raw = {"scene_type": "office_morning_light", "avoid": ["lens flare"]}
    memory = {"hard_avoid_today": ["no notebooks", "window"]}
    raw_before, memory_before = deepcopy(raw), deepcopy(memory)
    plan = planner.normalize_scene_plan(raw, memory)
    plan_before = deepcopy(plan)
    text = "Show a notebook. No mug and no table"
    kwargs = {"selected_style": "sunny_morning_photo", "user_text": text}
    if custom:
        kwargs.update(selected_style="custom", resolved_style="sunny_morning_photo",
                      user_text="Show a notebook", custom_style_description="No mug and no table")
    reconciled = planner.reconcile_scene_constraints(plan, **kwargs)
    for _ in range(3):
        sources = reconciled["constraint_sources"]
        assert sources["user_requests"] == ["notebook"]
        assert sources["user_exclusions"] == ["mug", "table"]
        assert "no notebooks" in sources["memory_avoid"]
        assert "lens flare" in sources["soft_avoid"]
        assert "no notebooks" not in reconciled["avoid"]
        assert {"no mugs or cups", "no tables"} <= set(reconciled["avoid"])
        assert planner.normalize_scene_plan(reconciled, memory) == reconciled
        assert planner.reconcile_scene_constraints(reconciled, **kwargs) == reconciled
        reconciled = planner.normalize_scene_plan(reconciled)
    assert raw == raw_before and memory == memory_before and plan == plan_before


def test_cp01_scene_replacement_invalidates_old_hints_and_rebuilds_selected_hints(monkeypatch):
    plan = planner.normalize_scene_plan({
        "scene_type": "office_morning_light",
        "constraint_sources": {
            "scene_hints": ["Work scene direction: coffee cup beside a window."],
            "user_requests": ["notebook"], "user_exclusions": ["mug", "window"],
            "memory_avoid": ["no notebooks", "lens flare"],
        },
    })
    before = deepcopy(plan)
    reconciled = planner.reconcile_scene_constraints(plan, selected_style="sunny_morning_photo")
    assert reconciled["scene_type"] != "office_morning_light"
    sources = reconciled["constraint_sources"]
    assert sources["scene_hints"] == []
    assert sources["user_requests"] == ["notebook"]
    assert sources["user_exclusions"] == ["mug", "window"]
    assert sources["memory_avoid"] == ["no notebooks", "lens flare"]
    assert "no notebooks" not in reconciled["avoid"]
    assert "window" in reconciled["avoid"]  # Old hint must no longer suppress this soft ban.
    assert planner.normalize_scene_plan(reconciled) == reconciled
    assert plan == before

    # Observe the real builder's final normalization, after it rebuilds family hints.
    from services import scene_prompt_builder
    normalized_plans = []

    def capture_normalization(candidate):
        normalized = planner.normalize_scene_plan(candidate)
        normalized_plans.append(normalized)
        return normalized

    monkeypatch.setattr(scene_prompt_builder, "normalize_scene_plan", capture_normalization)
    prompt = scene_prompt_builder.build_controlled_scene_prompt(
        scene_plan=plan, selected_style="sunny_morning_photo", composition_hint="open balanced frame",
    )
    rebuilt = normalized_plans[-1]
    hints = rebuilt["constraint_sources"]["scene_hints"]
    assert "Composition preference: open balanced frame." in hints
    assert not any("Work scene direction:" in hint for hint in hints)
    assert not positive_objects(". ".join(hints)) & {"mug", "window"}
    assert not positive_objects(prompt.replace("Human presence: none.", "")) & {"mug", "window"}
    assert plan == before


_CP02_NEGATIVE_CASES = [
    ("not show a mug", {"mug"}),
    ("I do not want to show a mug", {"mug"}),
    ("Do not ever include a table", {"table"}),
    ("I would rather not show a window", {"window"}),
    ("I do not want you to show a table", {"table"}),
    ("Never show people", {"human"}),
]


@pytest.mark.parametrize("text,excluded", _CP02_NEGATIVE_CASES + [
    ("not include a cup", {"mug"}),
    ("I don't want to include a notebook", {"notebook"}),
    ("I don’t want you to show a window", {"window"}),
    ("Do not ever show a table", {"table"}),
    ("I'd rather not show a cup", {"mug"}),
    ("Never include visible human body parts", {"body"}),
])
@pytest.mark.parametrize("custom", [False, True])
def test_cp02_nested_visual_verbs_preserve_negative_polarity(text, excluded, custom):
    kwargs = {"user_text": text}
    if custom:
        kwargs = {"style": "custom", "custom_style_description": text}
    assert user_visual_constraints(**kwargs) == (set(), excluded)
    assert not positive_objects(text)


@pytest.mark.parametrize("text,required,excluded", [
    ("No mug and show a table", {"table"}, {"mug"}),
    ("No people, show a mug", {"mug"}, {"human"}),
    ("Never show people; show a window", {"window"}, {"human"}),
    ("Do not show a mug. Show a notebook", {"notebook"}, {"mug"}),
    ("No mug or include a table", {"table"}, {"mug"}),
    ("Never show people\nInclude a notebook", {"notebook"}, {"human"}),
    ("not show a mug! Show a window", {"window"}, {"mug"}),
    ("I would rather not show a window? Include a notebook", {"notebook"}, {"window"}),
    ("Do not ever include a table but show a notebook", {"notebook"}, {"table"}),
    ("Без людей и покажи стол", {"table"}, {"human"}),
    ("Не хочу видеть людей, но хочу окно", {"window"}, {"human"}),
    ("Include a mug; I do not want you to show a window", {"mug"}, {"window"}),
    ("Show a notebook and never show people", {"notebook"}, {"human"}),
    ("I do not want to show a mug, include a window", {"window"}, {"mug"}),
    ("Do not show a mug and show a table", {"table"}, {"mug"}),
    ("I do not want you to show a table. Include a notebook", {"notebook"}, {"table"}),
    ("No mug I want a table", {"table"}, {"mug"}),
    ("Без кружек хочу стол", {"table"}, {"mug"}),
])
def test_cp02_independent_directives_reset_polarity(text, required, excluded):
    assert user_visual_constraints(text) == (required, excluded)
    assert required <= positive_objects(text)
    assert not positive_objects(text) & forbidden_objects(excluded)


@pytest.mark.parametrize("text,required,excluded", [
    ("I read about people and windows", set(), set()),
    ("I do not want to discuss a mug", set(), set()),
    ("I do not want to discuss how to show a mug", set(), set()),
    ("I do not want a mug removed", set(), set()),
    ("Never discuss people at a table", set(), set()),
    ("Never show people in my report", set(), set()),
    ("I mentioned the words mug and table", set(), set()),
    ("notebookish, windowless, stable, mugshot", set(), set()),
    ("No people, a mug please", set(), {"human"}),
    ("No people, just me and a mug", set(), {"human"}),
    ("No people, a mug", {"mug"}, {"human"}),
    ("No people, the table", {"table"}, {"human"}),
    ("No cups, tables and notebooks", set(), {"mug", "table", "notebook"}),
    ("No mugs please, and no windows either", set(), {"mug", "window"}),
    ("Без людей, столы и окна", set(), {"human", "table", "window"}),
])
def test_cp02_incidental_mentions_and_comma_continuation(text, required, excluded):
    assert user_visual_constraints(text) == (required, excluded)


@pytest.mark.parametrize("text", [
    "I do not want to show a mug. Show a cup",
    "Never show people; include hands",
    "Do not ever include a table and show a table",
    "I would rather not show a window, show windows",
    "I do not want you to show a table. Include tables",
    "Show a person. Never show people",
])
def test_cp02_explicit_contradictions_remain_unresolved(text):
    with pytest.raises(ValueError, match="Unresolved explicit visual conflict"):
        user_visual_constraints(text)


@pytest.mark.parametrize("text", [
    "I do not want to show a mug. Show a cup",
    "Never show people; include hands",
])
@pytest.mark.parametrize("trace", [None, "template", "scene_planner_local", "llm"])
def test_cp02_contradictions_stop_before_providers(offline_api, text, trace):
    with pytest.raises(ValueError, match="Unresolved explicit visual conflict"):
        asyncio.run(openai_image.generate_image(
            style="sunny_morning_photo", sphere="career", user_text=text,
            prompt_override="A mug on a table." if trace else None, image_prompt_trace=trace,
        ))
    assert not offline_api.images and not offline_api.texts


@pytest.mark.parametrize("text,excluded", _CP02_NEGATIVE_CASES)
@pytest.mark.parametrize("custom", [False, True])
def test_cp02_negative_provenance_is_idempotent_without_input_mutation(text, excluded, custom):
    raw = {"scene_type": "office_morning_light", "avoid": ["lens flare"]}
    memory = {"hard_avoid_today": ["no notebooks"]}
    raw_before, memory_before = deepcopy(raw), deepcopy(memory)
    plan = planner.normalize_scene_plan(raw, memory)
    plan_before = deepcopy(plan)
    kwargs = {"selected_style": "sunny_morning_photo", "user_text": text + ". Show a notebook"}
    if custom:
        kwargs.update(selected_style="custom", resolved_style="sunny_morning_photo",
                      user_text="Show a notebook", custom_style_description=text)
    reconciled = planner.reconcile_scene_constraints(plan, **kwargs)
    for _ in range(3):
        sources = reconciled["constraint_sources"]
        assert sources["user_exclusions"] == sorted(excluded)
        assert sources["user_requests"] == ["notebook"]
        assert "no notebooks" in sources["memory_avoid"]
        assert "no notebooks" not in reconciled["avoid"]
        assert "lens flare" in sources["soft_avoid"]
        if "human" in excluded:
            assert reconciled["human_presence"] == "none"
        assert planner.normalize_scene_plan(reconciled, memory) == reconciled
        assert planner.reconcile_scene_constraints(reconciled, **kwargs) == reconciled
        reconciled = planner.normalize_scene_plan(reconciled)
    assert raw == raw_before and memory == memory_before and plan == plan_before


@pytest.mark.parametrize("text,excluded,required", [
    *((text, excluded, set()) for text, excluded in _CP02_NEGATIVE_CASES),
    ("No mug and show a table", {"mug"}, {"table"}),
    ("No people, show a mug", {"human"}, {"mug"}),
    ("Never show people; show a window", {"human"}, {"window"}),
    ("Do not show a mug. Show a notebook", {"mug"}, {"notebook"}),
    ("I do not want you to show a table. Include a notebook", {"table"}, {"notebook"}),
    ("I would rather not show a window, include a mug", {"window"}, {"mug"}),
])
@pytest.mark.parametrize("path_kind", ["direct", "template", "template_fallback", "controlled"])
def test_cp02_effective_payload_and_actual_scene_metadata(offline_api, text, excluded, required, path_kind):
    prompt, trace = None, None
    if path_kind == "controlled":
        prompt = build_controlled_scene_prompt(
            scene_plan={"scene_type": "office_morning_light"},
            selected_style="sunny_morning_photo", visual_mode="photo", sphere="career",
            user_text=text, composition_hint="hands beside the window",
        )
        trace = "scene_planner_local"
    elif path_kind != "direct":
        prompt, trace = asyncio.run(yandex_gpt.build_enriched_image_prompt(
            style="sunny_morning_photo", sphere="career", subsphere=None, user_text=text,
            custom_style_description=None, affirmations=[], color_mood="natural daylight",
            composition_hint="hands beside the window", use_llm=path_kind == "template_fallback",
            visual_mode="photo",
        ))
        assert trace == path_kind
    output = Path(asyncio.run(openai_image.generate_image(
        style="sunny_morning_photo", sphere="career", user_text=text, visual_mode="photo",
        prompt_override=prompt, image_prompt_trace=trace,
        photo_scene_preset_override="window_still_life" if path_kind == "direct" else None,
        image_hint="people with a coffee cup at a table beside the window",
    )))
    final = offline_api.images[0]["prompt"]
    assert not positive_objects(final.replace("Human presence: none.", "")) & forbidden_objects(excluded)
    actual_required, actual_excluded = user_visual_constraints(final)
    assert required <= actual_required
    assert excluded <= actual_excluded
    labels = {"mug": "no mugs or cups", "table": "no tables", "window": "no windows",
              "human": "no people or human presence"}
    assert all(labels[key] in final for key in excluded)
    if "mug" in excluded:
        assert "coffee cup" not in final
    assert final.count("Scene type:") == (1 if path_kind == "controlled" else 0)
    assert final.count("Photo scene preset:") == (0 if path_kind == "controlled" else 1)
    if path_kind in {"template", "template_fallback"}:
        assert final == prompt.strip()
    meta = json.loads(output.with_name(output.stem + "_meta.json").read_text(encoding="utf-8"))
    assert meta["final_prompt"] == meta["prompt"] == final
    assert meta["scene_type"] == meta["scene_preset"]
    assert meta["prompt_source"] == (trace or "template")
    if path_kind == "controlled":
        actual_scene = re.match(r"Scene type: ([a-z_0-9]+)\.", final).group(1)
        assert meta["scene_type"] == actual_scene
        assert meta["photo_scene_preset"] is None
        assert planner.SCENE_PRESETS[actual_scene]["setting"] in final
    else:
        assert meta["scene_type"] == meta["photo_scene_preset"]
        assert openai_image.PHOTO_SCENE_PRESETS[meta["scene_type"]] in final
        if path_kind == "direct" and "window" in excluded:
            assert meta["scene_type"] != "window_still_life"
    assert len(offline_api.images) == 1
    assert len(offline_api.texts) == (1 if path_kind == "template_fallback" else 0)
