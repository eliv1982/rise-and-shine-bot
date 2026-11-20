"""FIX-03A: deterministic user intent and effective mocked image API payloads."""

import asyncio
import base64
import datetime as dt
import json
from types import SimpleNamespace

import pytest

from services import openai_image, yandex_gpt
from services.coastal_intent import parse_coastal_text, user_coastal_intent
from services.ritual_config import has_coastal_intent
from services.scene_planner import apply_coastal_scene_intent, normalize_scene_plan, resolve_scene_style_family
from services.scene_prompt_builder import build_controlled_scene_prompt


@pytest.mark.parametrize("text", [
    "Avoid beach", "No ocean", "Without coastline", "Без моря", "Не хочу пляж",
    "Without ocean", "Avoid beach, ocean and coastline", "Avoid: beach, ocean",
    "Do not show ocean", "Не показывай море",
])
def test_negative_only(text):
    assert not has_coastal_intent(text)
    assert parse_coastal_text(text).excluded


@pytest.mark.parametrize("text", [
    "Ocean sunrise", "Tropical beach with palm trees", "Rocky coastline",
    "Море на рассвете", "Хочу океан и пальмы", "Philippine-style tropical island beach",
    "Turquoise lagoon", "Ocean view", "Хочу спокойное побережье моря",
])
def test_positive(text):
    assert has_coastal_intent(text)


@pytest.mark.parametrize("text,excluded", [
    ("Avoid beach, show rocky coast", "beach"),
    ("Море без пляжа", "beach"),
    ("Ocean view, no sandy beach", "sandy"),
])
def test_mixed(text, excluded):
    intent = parse_coastal_text(text)
    assert intent.wants_coast
    assert intent.subtype == ("rocky" if text.startswith("Avoid") else "water")
    assert intent.excluded == {excluded}


@pytest.mark.parametrize("text", ["research", "seasonal", "seated", "берегу себя"])
def test_incidental_substrings(text):
    assert not has_coastal_intent(text)
    assert not parse_coastal_text(text).positive
    assert resolve_scene_style_family(selected_style=text) != "coastal"


def test_custom_notes_are_scoped_to_selected_custom_style():
    assert not user_coastal_intent(None, style="auto", custom_style_description="Ocean view").wants_coast
    assert user_coastal_intent(None, style="custom", custom_style_description="Ocean view").wants_coast
    assert not user_coastal_intent(None, style="custom", custom_style_description="No ocean").wants_coast
    assert not user_coastal_intent("No ocean", style="custom", custom_style_description="Ocean view").wants_coast


@pytest.fixture
def image_api(monkeypatch, tmp_path):
    """Run real prompt builders and generate_image; replace only HTTP/providers."""
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
            if url == "https://offline.test/images/generations":
                capture.images.append(kwargs["json"])
                return Response({"data": [{"b64_json": base64.b64encode(b"mock png").decode()}]})
            assert url == "https://offline.test/text", f"Unexpected HTTP target: {url}"
            capture.texts.append(kwargs["json"])
            return Response({"result": json.dumps({"prompt": capture.llm_prompt})})

    monkeypatch.setattr(openai_image.aiohttp, "ClientSession", Session)
    monkeypatch.setattr(openai_image, "get_outputs_dir", lambda: str(tmp_path))
    monkeypatch.setattr(openai_image, "get_image_provider_config", lambda: SimpleNamespace(
        base_url="https://offline.test", model="unchanged-test-image-model", size="1024x1024",
        api_key="fake", timeout_seconds=30, provider="mock",
    ))
    monkeypatch.setattr(yandex_gpt, "get_text_provider_config", lambda: SimpleNamespace(timeout_seconds=90, provider="mock"))
    monkeypatch.setattr(yandex_gpt, "_build_text_provider_request", lambda _cfg, **kwargs: (
        "https://offline.test/text", {}, kwargs,
    ))
    monkeypatch.setattr(yandex_gpt, "_parse_text_provider_response", lambda _cfg, data: data["result"])
    return capture


SCENES = [
    pytest.param("forest_path", "living_nature_photo", "Forest path",
                 "A real forest path among trees. Avoid beach. No text.", False, id="forest-default-avoid"),
    pytest.param("office_morning_light", "light_interior_photo", "Workspace, no ocean",
                 "A real workspace in morning light. No ocean. No text.", False, id="workspace-negative"),
    pytest.param("sea_horizon", "auto", "Tropical beach with palm trees",
                 "A real tropical beach with palm trees and turquoise ocean. No text.", True, id="tropical-beach"),
    pytest.param("dune_grass", "auto", "Avoid beach, show rocky coast",
                 "A real rocky coast with waves. No beach. No text.", True, id="rocky-excluding-beach"),
    pytest.param("sea_horizon", "auto", "Море без пляжа",
                 "A real rocky coast with open ocean. No beach. No text.", True, id="ru-mixed"),
    pytest.param("sea_horizon", "auto", "Ocean view, no sandy beach",
                 "A real rocky coast and ocean view. No sandy beach. No text.", True, id="sandy-subtype"),
    pytest.param("sea_horizon", "auto", "Philippine-style tropical island beach with palms",
                 "A real tropical island beach with palms and turquoise ocean. No text.", True, id="island-beach"),
    pytest.param("sea_horizon", "auto", "Turquoise lagoon",
                 "A real turquoise lagoon with limestone cliffs. No text.", True, id="lagoon"),
]


@pytest.mark.parametrize("path", ["controlled", "template", "enriched"])
@pytest.mark.parametrize("scene,style,scene_request,llm_scene,coastal", SCENES)
def test_effective_final_image_api_prompt(image_api, path, scene, style, scene_request, llm_scene, coastal):
    image_api.llm_prompt = llm_scene
    resolved_style = "sea_coast_photo" if coastal else style

    async def run():
        if path == "controlled":
            prompt = build_controlled_scene_prompt(
                scene_plan={"scene_type": scene}, user_text=scene_request,
                visual_mode="photo", selected_style=style, resolved_style=resolved_style,
            )
            trace = "scene_planner_local"
        elif path == "enriched":
            prompt, trace = await yandex_gpt.build_enriched_image_prompt(
                style=style, resolved_style=resolved_style, sphere="career", subsphere=None,
                user_text=scene_request, custom_style_description=None, affirmations=[],
                color_mood="green and gold", composition_hint="open composition",
                use_llm=True, visual_mode="photo",
            )
            assert trace == "llm"
        else:
            prompt, trace = None, "template"
        await openai_image.generate_image(
            style=style, resolved_style_override=resolved_style, sphere="career",
            user_text=scene_request, visual_mode="photo", prompt_override=prompt,
            image_prompt_trace=trace, color_mood="green and gold", composition_hint="open composition",
            # A generated hint cannot override the concrete non-coastal choice.
            image_hint="ocean coast with sand" if not coastal else None,
        )

    asyncio.run(run())
    assert len(image_api.images) == 1
    prompt = image_api.images[0]["prompt"].lower()
    assert image_api.images[0]["model"] == "unchanged-test-image-model"
    assert "strict photo branch" in prompt or "photo branch only" in prompt
    if not coastal:
        assert "coastal realism is mandatory" not in prompt
        assert "open ocean or open sea coast" not in prompt
        assert "ocean coast with sand" not in prompt
        assert "photo scene preset: ocean" not in prompt
        if path == "controlled":
            assert f"scene type: {scene}" in prompt
        else:
            assert "forest path" in prompt if scene == "forest_path" else "workspace" in prompt
    elif "beach" in scene_request.lower() and not scene_request.lower().startswith("avoid") and "no sandy" not in scene_request.lower():
        assert "beach" in prompt and "palm" in prompt
        assert "avoid: mug, notebook, table, window, beach" not in prompt
        assert "scene exclusions: no beach" not in prompt
    elif parse_coastal_text(scene_request).excluded:
        if parse_coastal_text(scene_request).subtype == "rocky":
            assert "rocky" in prompt
        assert "no sandy beach" in prompt or "no beach" in prompt
        assert "clean beach foreground" not in prompt
        assert "broad sand beach" not in prompt
        assert "photo scene preset: quiet_beach" not in prompt
    else:
        assert "lagoon" in prompt
        assert "open ocean or open sea coast" not in prompt
        assert "open horizon over water" not in prompt
        assert "visible horizon over water" not in prompt


@pytest.mark.parametrize("scene_request,style,llm_scene", [
    ("Avoid beach", "living_nature_photo", "A sunny beach with palm trees."),
    ("Workspace, no ocean", "light_interior_photo", "Ocean sunrise over water."),
    ("Tropical beach with palm trees", "auto", "A forest path with trees."),
    ("Avoid beach, show rocky coast", "auto", "A sandy beach with waves."),
    ("Ocean view, no sandy beach", "auto", "A sandy beach with ocean view."),
    ("Turquoise lagoon", "auto", "A wide open ocean horizon."),
])
def test_enrichment_rejects_coastal_intent_drift_at_final_api(image_api, scene_request, style, llm_scene):
    image_api.llm_prompt = llm_scene

    async def run():
        prompt, trace = await yandex_gpt.build_enriched_image_prompt(
            style=style, sphere="career", subsphere=None, user_text=scene_request,
            custom_style_description=None, affirmations=[], color_mood="gold",
            composition_hint="wide", use_llm=True, visual_mode="photo",
        )
        assert trace == "template_fallback"
        await openai_image.generate_image(
            style=style, sphere="career", user_text=scene_request, visual_mode="photo",
            prompt_override=prompt, image_prompt_trace=trace,
        )

    asyncio.run(run())
    prompt = image_api.images[0]["prompt"].lower()
    assert llm_scene.lower() not in prompt
    intent = parse_coastal_text(scene_request)
    assert ("coastal realism is mandatory" in prompt) == intent.wants_coast
    if intent.excluded & {"beach", "sandy"} and intent.wants_coast:
        assert "clean beach foreground" not in prompt
        if intent.subtype == "rocky":
            assert "rocky" in prompt
    assert len(image_api.texts) == len(image_api.images) == 1


def test_selected_beach_drops_generic_avoid_but_explicit_exclusion_wins():
    beach = normalize_scene_plan({
        "scene_type": "coastal_morning", "setting": "tropical beach with palms",
        "main_subject": "beach and turquoise ocean", "avoid": ["beach"],
    })
    assert "beach" not in beach["avoid"]
    rocky = apply_coastal_scene_intent(beach, user_text="Avoid beach, show rocky coast")
    assert rocky["scene_type"] == "rocky_shore"
    assert "Scene exclusions: no beach." in rocky["avoid"]


def test_explicit_style_and_family_exclusion_reports_conflict_without_api(image_api):
    with pytest.raises(ValueError, match="conflicts with the explicit coastal exclusion"):
        asyncio.run(openai_image.generate_image(
            style="sea_coast_photo", sphere="career", user_text="No ocean", visual_mode="photo",
        ))
    assert not image_api.images


@pytest.mark.parametrize("scene_request", [
    "Avoid beach", "No ocean", "Without coastline", "Без моря", "Не хочу пляж",
    "research", "seasonal", "seated", "берегу себя",
])
def test_negative_and_incidental_text_at_final_api(image_api, scene_request):
    asyncio.run(openai_image.generate_image(
        style="auto", sphere="career", user_text=scene_request, visual_mode="photo",
        resolved_style_override="light_interior_photo",
    ))
    prompt = image_api.images[0]["prompt"].lower()
    assert "coastal realism is mandatory" not in prompt
    assert "real coastal travel/editorial photo scene" not in prompt
    assert "workspace" in prompt


@pytest.mark.parametrize("scene_request", ["Avoid beach", "No ocean", "Без моря"])
def test_negative_only_does_not_promote_automatic_coastal_default(image_api, scene_request):
    asyncio.run(openai_image.generate_image(
        style="auto", sphere="inner_peace", user_text=scene_request, visual_mode="photo",
        resolved_style_override="sea_coast_photo",
    ))
    assert "coastal realism is mandatory" not in image_api.images[0]["prompt"].lower()


@pytest.mark.parametrize("scene_request", [
    "Ocean sunrise", "Tropical beach with palm trees", "Rocky coastline",
    "Море на рассвете", "Хочу океан и пальмы", "Philippine-style tropical island scenery",
])
def test_positive_requests_reach_final_api(image_api, scene_request):
    asyncio.run(openai_image.generate_image(
        style="auto", sphere="career", user_text=scene_request, visual_mode="photo",
        resolved_style_override="light_interior_photo",
    ))
    prompt = image_api.images[0]["prompt"]
    assert scene_request in prompt
    assert "Coastal realism is mandatory" in prompt


def test_generated_override_hint_and_inactive_notes_do_not_supply_user_intent(image_api):
    asyncio.run(openai_image.generate_image(
        style="auto", sphere="career", visual_mode="photo",
        resolved_style_override="light_interior_photo",
        prompt_override="A real workspace. Avoid beach, ocean and coastline.",
        image_hint="Ocean sunrise", custom_style_description="Tropical beach",
    ))
    prompt = image_api.images[0]["prompt"]
    assert "Coastal realism is mandatory" not in prompt
    assert "open ocean or open sea coast" not in prompt
    assert "workspace" in prompt


def test_selected_custom_coastal_details_survive_unrelated_emotional_theme(image_api):
    prompt = build_controlled_scene_prompt(
        scene_plan={"scene_type": "forest_path"}, selected_style="custom",
        user_text="Calm confidence", custom_style_description="Tropical beach with palms",
    )
    assert "Tropical beach with palms" in prompt
    asyncio.run(openai_image.generate_image(
        style="custom", sphere="career", visual_mode="photo", user_text="Calm confidence",
        custom_style_description="Tropical beach with palms", prompt_override=prompt,
        image_prompt_trace="scene_planner_local",
    ))
    assert "Tropical beach with palms" in image_api.images[0]["prompt"]


@pytest.mark.parametrize("scene_request", [
    "Ocean view, no rocky coast", "Ocean view, no beach and rocky coast",
])
@pytest.mark.parametrize("path", ["controlled", "template"])
def test_rocky_exclusion_is_not_reintroduced_by_subtype_fallback(image_api, scene_request, path):
    prompt = build_controlled_scene_prompt(
        scene_plan={"scene_type": "rocky_shore"}, selected_style="auto", user_text=scene_request,
    ) if path == "controlled" else None
    asyncio.run(openai_image.generate_image(
        style="auto", sphere="career", visual_mode="photo", user_text=scene_request,
        prompt_override=prompt, image_prompt_trace="scene_planner_local" if prompt else "template",
    ))
    final = image_api.images[0]["prompt"].lower()
    assert "no rocky coast" in final
    assert "photo scene preset: rocky_coast" not in final
    assert "rocky foreground" not in final
    if "no beach" in scene_request:
        assert "photo scene preset: quiet_beach" not in final
        assert "clean beach foreground" not in final


class State:
    def __init__(self, **data):
        self.data = data

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def set_state(self, state):
        self.state = state

    async def clear(self):
        self.data = {}
        self.state = None


class Message:
    def __init__(self):
        self.from_user = SimpleNamespace(id=1)
        self.photos = []
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append(text)

    async def answer_photo(self, photo, **kwargs):
        self.photos.append(kwargs)

    async def edit_reply_markup(self, **kwargs):
        pass


def install_orchestration_stubs(monkeypatch, module, path, scene):
    settings = SimpleNamespace(
        disable_daily_generation_limit=True, generation_daily_limit=0,
        llm_image_prompt_enabled=path == "enriched", show_image_debug=False,
        scene_planner_image_prompt_enabled=path == "controlled",
    )

    async def no_shadow(**kwargs):
        return None

    async def scene_shadow(**kwargs):
        return {"scene_plan": {"scene_type": scene}}

    async def card(**kwargs):
        return yandex_gpt.GeneratedCardText(kwargs.get("focus") or "Clear focus", [
            "I trust my pace", "I can choose calmly", "My experience supports me", "My judgment matters",
        ])

    monkeypatch.setattr(module, "get_settings", lambda: settings)
    monkeypatch.setattr(module, "generate_card_text", card)
    monkeypatch.setattr(module, "build_text_plan_shadow_best_effort", no_shadow)
    monkeypatch.setattr(module, "build_scene_plan_shadow_best_effort", scene_shadow)
    monkeypatch.setattr(module, "build_text_reviewer_shadow_best_effort", lambda **kwargs: None)
    monkeypatch.setattr(module, "is_text_planner_controlled_enabled", lambda *_: False)


@pytest.mark.parametrize("path", ["controlled", "template", "enriched"])
@pytest.mark.parametrize("scene_request,style,scene,coastal", [
    ("Forest path. Avoid beach", "living_nature_photo", "forest_path", False),
    ("Tropical beach with palm trees", "auto", "sea_horizon", True),
    ("Avoid beach, show rocky coast", "auto", "dune_grass", True),
])
def test_manual_and_more_effective_api_payloads(initialized_db, monkeypatch, image_api, path, scene_request, style, scene, coastal):
    import database as db
    from handlers import generation

    install_orchestration_stubs(monkeypatch, generation, path, scene)
    monkeypatch.setattr(generation, "_generation_preflight_error", lambda *_: None)
    image_api.llm_prompt = (
        "A tropical beach with palm trees and ocean. No text." if "Tropical" in scene_request else
        "A rocky coast with ocean waves. No beach. No text." if coastal else
        "A real forest path among trees. Avoid beach. No text."
    )
    state = State(sphere="career", style=style, visual_mode="photo")
    message = Message()

    class Callback:
        from_user = SimpleNamespace(id=1)

        async def answer(self):
            pass

    callback = Callback()
    callback.message = message

    async def run():
        await db.create_or_update_user(1, "offline", name="User", language="en")
        await generation._run_generation(message, state, theme_text=scene_request)
        assert len(message.photos) == 1, message.answers
        await generation.again_affirmation(callback, state)
        assert len(message.photos) == 2, message.answers
        assert state.data["last_generation"]["theme_text"] == scene_request

    asyncio.run(run())
    assert len(image_api.images) == 2
    for payload in image_api.images:
        prompt = payload["prompt"].lower()
        if not coastal:
            assert "forest path" in prompt
            assert "coastal realism is mandatory" not in prompt
        elif "Tropical" in scene_request:
            assert "beach" in prompt and "palm" in prompt
            assert "scene exclusions: no beach" not in prompt
        else:
            assert "rocky" in prompt and "no beach" in prompt
            assert "clean beach foreground" not in prompt


@pytest.mark.parametrize("path", ["controlled", "template", "enriched"])
@pytest.mark.parametrize("style,scene,coastal", [
    ("living_nature_photo", "forest_path", False),
    ("light_interior_photo", "office_morning_light", False),
    ("sea_coast_photo", "coastal_morning", True),
])
def test_scheduled_effective_api_payload(initialized_db, monkeypatch, image_api, path, style, scene, coastal):
    import database as db
    import scheduler

    install_orchestration_stubs(monkeypatch, scheduler, path, scene)
    image_api.llm_prompt = (
        "A real ocean coast with waves. No text." if coastal else
        "A real forest path among trees. Avoid beach. No text." if scene == "forest_path" else
        "A real workspace with morning light. No ocean. No text."
    )

    class Bot:
        sent = []

        async def send_photo(self, **kwargs):
            self.sent.append(kwargs)
            return SimpleNamespace(photo=[])

    async def run():
        await db.create_or_update_user(1, "offline", name="User", language="ru")
        await db.create_subscription(
            1, "career", None, style, "en", 8, 0, subscription_mode="sphere_focus",
            subscription_sphere="career", subscription_style_mode=style,
            visual_mode="photo", allowed_visual_modes=["photo"],
        )
        bot = Bot()
        await scheduler.send_daily_affirmations(bot, now=dt.datetime(2030, 3, 1, 8, 0, tzinfo=scheduler.MOSCOW))
        assert len(bot.sent) == 1
        assert (await db.get_subscription_deliveries(["2030-03-01"]))[0]["status"] == "sent"

    asyncio.run(run())
    assert len(image_api.images) == 1
    prompt = image_api.images[0]["prompt"].lower()
    assert ("coastal realism is mandatory" in prompt) == (coastal and path != "controlled")
    if not coastal:
        assert "open ocean or open sea coast" not in prompt
        assert "photo scene preset: quiet_beach" not in prompt
