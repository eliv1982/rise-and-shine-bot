"""FIX-03A R1: real handlers/builders/history, providers mocked only at HTTP."""

import asyncio
import base64
import datetime as dt
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

import database as db
import scheduler
from config import TextProviderConfig
from handlers import generation, subscribe
from handlers.generation_messages import scene_style_conflict_text
from services import openai_image, yandex_gpt
from services.coastal_intent import coastal_request_text, parse_coastal_text
from services.ritual_config import PHOTO_SCENE_PRESETS, SYMBOLIC_STYLE_KEYS, get_visual_archetype
from services.generation_history import build_visual_motifs, record_generation_history_best_effort
from services.scene_planner import apply_coastal_scene_intent, normalize_scene_plan
from services.scene_prompt_builder import build_controlled_scene_prompt
from services.visual_memory import build_visual_memory_context, get_visual_memory_context
from states import GenerationState


SCOPES = [
    ("No text, ocean sunrise", {"water"}, set()),
    ("No people, beach at sunset", {"beach"}, set()),
    ("без людей, море", {"water"}, set()),
    ("Avoid crowds and show a tropical beach", {"beach"}, set()),
    ("No beach and no ocean", set(), {"beach", "water"}),
    ("Avoid beaches and rocky shores", set(), {"beach", "rocky"}),
    ("No people, no beach, show mountains", set(), {"beach"}),
    ("No text, tropical beach with palms", {"beach"}, set()),
    ("Без людей, без пляжа, скалистый берег", {"rocky"}, {"beach"}),
    ("Avoid beach, ocean and coastline", set(), {"beach", "water", "coast"}),
    ("Avoid beach and ocean, but show rocky coast", {"rocky"}, {"beach", "water"}),
    ("Без пляжа и океана", set(), {"beach", "water"}),
    ("Не хочу пляж и скалистый берег", set(), {"beach", "rocky"}),
    ("Избегай толпы и покажи океан", {"water"}, set()),
    ("No ocean, show a tropical beach", {"beach"}, {"water"}),
    ("No beach, show beach and ocean", {"beach", "water"}, {"beach"}),
    ("Do not include ocean", set(), {"water"}),
    ("Don't show a beach", set(), {"beach"}),
    ("Не показывайте море", set(), {"water"}),
    ("Избегайте пляжей и скалистых берегов", set(), {"beach", "rocky"}),
]


@pytest.mark.parametrize("text,positive,excluded", SCOPES)
def test_f1_negation_scope_and_coordinated_exclusions(text, positive, excluded):
    intent = parse_coastal_text(text)
    assert intent.positive == positive
    assert intent.excluded == excluded
    assert intent.wants_coast == bool(positive - excluded and not excluded & {"water", "coast"})


@pytest.mark.parametrize("text", [
    "береги себя", "Береги себя", "берегите себя", "Берегите себя", "берегу себя",
    "берегись", "research", "seasonal", "seated", "oceanic", "seashorelineage",
])
def test_f2_verbs_and_word_boundaries(text):
    assert not parse_coastal_text(text).positive


@pytest.mark.parametrize("text,kind", [
    ("берег", "coast"), ("у берега", "coast"), ("на берегах", "coast"),
    ("берегом", "coast"), ("берега", "coast"), ("берегов", "coast"),
    ("скалистый берег", "rocky"), ("скалистого берега", "rocky"),
    ("скалистым берегом", "rocky"), ("скалистые берега", "rocky"),
    ("на берегу", "coast"), ("к берегу", "coast"), ("на скалистом берегу", "rocky"),
])
def test_f2_shoreline_nouns(text, kind):
    assert parse_coastal_text(text).positive == {kind}


class Message:
    def __init__(self, user_id=1, fail_delivery=False):
        self.from_user = SimpleNamespace(id=user_id)
        self.answers, self.photos, self.markups = [], [], []
        self.fail_delivery = fail_delivery

    async def answer(self, text, **kwargs):
        self.answers.append(text)
        self.markups.append(kwargs.get("reply_markup"))

    async def answer_photo(self, **kwargs):
        if self.fail_delivery:
            raise RuntimeError("offline delivery failed")
        self.photos.append(kwargs)
        return SimpleNamespace(photo=[SimpleNamespace(file_id="offline-file")])

    async def edit_text(self, text, **kwargs):
        self.answers.append(text)

    async def edit_reply_markup(self, **kwargs):
        pass


class Callback:
    def __init__(self, message=None, data="again:yes"):
        self.from_user = SimpleNamespace(id=1)
        self.message = message or Message(user_id=9000)
        self.data = data

    async def answer(self, *args, **kwargs):
        pass


def state(**data):
    value = FSMContext(storage=MemoryStorage(), key=StorageKey(bot_id=9000, chat_id=1, user_id=1))
    asyncio.run(value.update_data(**data))
    return value


@pytest.fixture
def offline(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        disable_daily_generation_limit=False, generation_daily_limit=20,
        scene_planner_image_prompt_enabled=False, scene_planner_shadow_enabled=True,
        llm_image_prompt_enabled=False, show_image_debug=False,
        text_planner_shadow_enabled=False, text_planner_controlled_enabled=False,
        text_memory_context_enabled=False, text_reviewer_shadow_enabled=False,
        orchestrator_shadow_enabled=False,
    )
    harness = SimpleNamespace(
        settings=settings, images=[], texts=[], llm_prompt="An ocean view with calm waves. No text.",
        output=tmp_path / "images", cancel_text=False,
    )
    text_config = TextProviderConfig(
        provider="openai", base_url="https://offline.invalid/v1", api_key="fake",
        model="gpt-6-luna", timeout_seconds=5,
    )

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
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        def post(self, url, **kwargs):
            payload = kwargs["json"]
            if url == "https://offline.invalid/v1/images/generations":
                harness.images.append(payload)
                return Response({"data": [{"b64_json": base64.b64encode(b"offline png").decode()}]})
            assert url == "https://offline.invalid/v1/chat/completions", url
            harness.texts.append(payload)
            if harness.cancel_text:
                raise asyncio.CancelledError()
            if "You write ONE English prompt" in payload["messages"][1]["content"]:
                content = {"prompt": harness.llm_prompt}
            else:
                english = "Write in English." in payload["messages"][0]["content"]
                content = {
                    "focus": "Clear focus" if english else "Спокойный фокус",
                    "affirmations": ["I trust my pace", "My experience matters", "I can choose calmly", "I notice my support"] if english else [
                        "Я доверяю своему темпу", "Мой опыт имеет значение", "Мне доступен спокойный выбор", "Я замечаю свою опору",
                    ],
                }
            return Response({"choices": [{"message": {"content": json.dumps(content)}, "finish_reason": "stop"}]})

    monkeypatch.setattr(openai_image.aiohttp, "ClientSession", Session)
    monkeypatch.setattr(openai_image, "get_outputs_dir", lambda: str(harness.output))
    monkeypatch.setattr(openai_image, "get_image_provider_config", lambda: SimpleNamespace(
        base_url="https://offline.invalid/v1", api_key="fake", model="unchanged-offline-model",
        provider="mock", size="1024x1024", timeout_seconds=30,
    ))
    monkeypatch.setattr(yandex_gpt, "get_text_provider_config", lambda: text_config)
    monkeypatch.setattr(generation, "get_settings", lambda: settings)
    monkeypatch.setattr(scheduler, "get_settings", lambda: settings)
    monkeypatch.setattr(scheduler, "last_subscription_affirmations", {})
    monkeypatch.setattr(subscribe, "last_subscription_affirmations", scheduler.last_subscription_affirmations)
    return harness


def configure_path(offline, path):
    offline.settings.scene_planner_image_prompt_enabled = path == "controlled"
    offline.settings.llm_image_prompt_enabled = path == "enriched"


async def image_payload(offline, path, text, *, style="auto", sphere="career", notes=None, scene="forest_path", visual_mode="photo", color_mood="gold and blue"):
    resolved = ("sea_coast_photo" if visual_mode == "photo" else "bright_nature_card") if style == "auto" else style
    prompt, trace = None, "template"
    if path == "controlled":
        prompt = build_controlled_scene_prompt(
            scene_plan={"scene_type": scene}, user_text=text, selected_style=style,
            resolved_style=resolved, visual_mode=visual_mode, custom_style_description=notes,
            color_palette=color_mood,
            composition_hint="wide-angle interior with daylight pouring in from one side",
        )
        trace = "scene_planner_local"
    elif path == "enriched":
        prompt, trace = await yandex_gpt.build_enriched_image_prompt(
            style=style, resolved_style=resolved, sphere=sphere, subsphere=None,
            user_text=text, custom_style_description=notes, affirmations=[],
            color_mood=color_mood, composition_hint="wide-angle interior", use_llm=True,
            visual_mode=visual_mode,
        )
    image_path = await openai_image.generate_image(
        style=style, resolved_style_override=resolved, sphere=sphere, user_text=text,
        custom_style_description=notes, visual_mode=visual_mode, prompt_override=prompt,
        image_prompt_trace=trace, color_mood=color_mood, composition_hint="wide-angle interior",
    )
    return offline.images[-1]["prompt"], json.loads(Path(image_path.replace(".png", "_meta.json")).read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", ["controlled", "template", "enriched"])
@pytest.mark.parametrize("text,positive,excluded", SCOPES)
def test_f1_f5_actual_payload_scope_and_exclusion_clauses(offline, path, text, positive, excluded):
    offline.llm_prompt = "Ocean sunrise. No text." if "water" in positive else "Tropical beach with palms. No text."
    prompt, meta = asyncio.run(image_payload(offline, path, text))
    intent = parse_coastal_text(text)
    if excluded:
        assert intent.exclusion_clause() in prompt
    if intent.wants_coast:
        assert coastal_request_text(text) in prompt
        assert "wide-angle interior" not in prompt
    else:
        assert "Coastal realism is mandatory" not in prompt
    for directive in ["Explicit coastal scene request: ", "Requested beach scene: ", "Requested lagoon scene: "]:
        if directive in prompt:
            # Positive directives contain no negative marker from the original expression.
            fragment = prompt.split(directive, 1)[1].split(".", 1)[0]
            assert not parse_coastal_text(fragment).excluded
    assert meta["final_prompt"] == prompt
    assert offline.images[-1]["model"] == "unchanged-offline-model"


@pytest.mark.parametrize("path", ["controlled", "template", "enriched"])
@pytest.mark.parametrize("text,excluded", [
    ("Avoid beach, show rocky coast", "beach"), ("Море без пляжа", "beach"),
    ("Ocean view, no sandy beach", "sandy"), ("Ocean view, no rocky coast", "rocky"),
])
def test_f4_f5_no_invented_positive_scene(offline, path, text, excluded):
    offline.llm_prompt = "A real ocean view. No text." if excluded == "rocky" else "A rocky coast and ocean. No text."
    prompt, _ = asyncio.run(image_payload(offline, path, text))
    assert parse_coastal_text(text).exclusion_clause() in prompt
    assert f"Explicit coastal scene request: {text}" not in prompt
    if excluded == "rocky":
        # Ignore scoped negatives when checking what the API is told to draw.
        assert not parse_coastal_text(prompt).positive & {"beach", "sandy", "rocky"}
        assert "quiet_beach_morning" not in prompt
        assert "clean beach foreground" not in prompt
    if excluded in {"beach", "sandy"}:
        assert not parse_coastal_text(prompt).positive & {"beach", "sandy"}


@pytest.mark.parametrize("scene,archetype", [("forest_path", "forest_path"), ("office_morning_light", "workspace_desk")])
def test_f3_controlled_noncoastal_scene_with_automatic_coastal_style(offline, initialized_db, scene, archetype):
    prompt, meta = asyncio.run(image_payload(offline, "controlled", "Calm confidence", scene=scene))
    assert meta["scene_type"] == meta["scene_preset"] == scene
    assert meta["photo_scene_preset"] is None
    assert meta["visual_archetype"] == archetype
    assert "Photo scene preset:" not in prompt
    assert "Coastal realism is mandatory" not in prompt
    assert not parse_coastal_text(prompt.split("Avoid:", 1)[0]).positive

    async def run():
        await db.create_or_update_user(1, "offline", language="en")
        motifs = build_visual_motifs(image_meta=meta)
        motifs["scene_plan_shadow"] = {"scene_plan": {"scene_type": "coastal_morning"}}
        await record_generation_history_best_effort(
            telegram_user_id=1, request_type="manual", image_prompt=prompt,
            scene_type=meta["scene_type"], visual_motifs=motifs,
        )
        visual = (await db.get_recent_visual_history(1))[0]
        assert visual["scene_type"] == visual["visual_motifs"]["scene_type"] == scene
        assert (await get_visual_memory_context(1))["recent_scene_types"] == [scene]
        assert (await db.get_recent_generation_history(1))[0]["image_prompt"] == prompt

    asyncio.run(run())


@pytest.mark.parametrize("record,expected", [
    ({"scene_type": "outdoor_path"}, ["outdoor_path"]),
    ({"visual_motifs": {"scene_type": "calm_workspace"}}, ["calm_workspace"]),
    ({"visual_motifs": {"scene_prompt_controlled": {"used_scene_type": "forest_path"}}}, ["forest_path"]),
    ({"visual_motifs": {"scene_plan_shadow": {"scene_plan": {"scene_type": "riverside"}}}}, ["riverside"]),
    ({"visual_motifs": "historic non-dict"}, []),
])
def test_f3_legacy_history_remains_readable(record, expected):
    assert build_visual_memory_context([], [record])["recent_scene_types"] == expected


@pytest.mark.parametrize("path", ["controlled", "template", "enriched"])
@pytest.mark.parametrize("sphere", ["career", "money"])
@pytest.mark.parametrize("style", ["auto", "living_nature_photo", "sunny_morning_photo", "sea_coast_photo"])
def test_f6_sphere_cannot_override_compatible_explicit_coast(offline, path, sphere, style):
    prompt, meta = asyncio.run(image_payload(offline, path, "Ocean view", style=style, sphere=sphere))
    assert "Ocean view" in prompt
    assert "prefer light workspace" not in prompt
    assert "Prefer a bright organized desk" not in prompt
    assert "wide-angle interior" not in prompt
    if style != "auto":
        assert meta["selected_style"] == style


@pytest.mark.parametrize("visual_mode", ["photo", "illustration"])
@pytest.mark.parametrize("sphere", ["career", "money"])
def test_f6_enrichment_cannot_turn_an_explicit_coast_into_an_interior(offline, visual_mode, sphere):
    offline.llm_prompt = "An ocean view from a desk inside a bright room. No text."

    async def run():
        prompt, trace = await yandex_gpt.build_enriched_image_prompt(
            style="auto", resolved_style="cozy_home_photo" if visual_mode == "photo" else "quiet_interior",
            sphere=sphere, subsphere=None, user_text="Ocean view", custom_style_description=None,
            affirmations=[], color_mood="gold and blue", composition_hint="wide-angle interior",
            use_llm=True, visual_mode=visual_mode,
        )
        assert trace == "template_fallback"
        await openai_image.generate_image(
            style="auto", sphere=sphere, user_text="Ocean view", visual_mode=visual_mode,
            prompt_override=prompt, image_prompt_trace=trace,
        )

    asyncio.run(run())
    assert len(offline.texts) == len(offline.images) == 1
    final = offline.images[0]["prompt"]
    assert "Ocean view" in final
    assert "a desk inside" not in final
    assert "wide-angle interior" not in final
    assert "Prefer a bright organized desk" not in final
    assert "prefer light workspace" not in final


@pytest.mark.parametrize("language", ["ru", "en"])
def test_f10_existing_style_reselection_recovers_without_spending_on_conflict(offline, initialized_db, language):
    flow = state(sphere="career", style="sea_coast_photo", visual_mode="photo")
    message = Message(user_id=9000)

    async def run():
        await db.create_or_update_user(1, "offline", language=language)
        await generation._start_generation_after_preflight(message, flow, "No ocean", language, user_telegram_id=1)
        assert not offline.texts and not offline.images
        assert (await flow.get_data())["theme_text"] == "No ocean"
        await generation.choose_style(Callback(message, "style:living_nature_photo"), flow)
        assert len(message.photos) == 1, message.answers
        assert len(offline.texts) == len(offline.images) == 1
        assert "Scene exclusions: no ocean or sea." in offline.images[0]["prompt"]
        assert await db.get_generation_usage_today(1) == 1

    asyncio.run(run())


@pytest.mark.parametrize("scene,setting", [
    ("coastal_morning", "tropical palm beach"), ("coastal_morning", "turquoise lagoon"),
    ("dune_grass", "coastal dune grass and sandy natural textures"),
    ("rocky_shore", "rocky coast with wet stones"), ("sea_horizon", "open ocean"),
])
def test_f7_coastal_families_have_no_generic_beach_ban(scene, setting):
    plan = normalize_scene_plan({"scene_type": scene, "setting": setting}, visual_memory_context={"hard_avoid_today": ["beach"]})
    assert "beach" not in plan["avoid"]
    assert plan["scene_type"] == scene
    assert plan["setting"] == setting


@pytest.mark.parametrize("style,text,notes,expected", [
    ("auto", None, "Ocean view", False), ("living_nature_photo", None, "Tropical beach", False),
    ("custom", None, "Ocean view", True), ("custom", "No ocean", "Ocean view", False),
    ("custom", "Ocean view", "No ocean", False), ("auto", "No people, ocean sunrise", None, True),
])
def test_f8_handler_diagnostics_use_applicable_context(offline, initialized_db, style, text, notes, expected):
    flow = state(sphere="career", style=style, visual_mode="photo", custom_style_description=notes)

    async def run():
        await db.create_or_update_user(1, "offline", language="en")
        message = Message()
        await generation._run_generation(message, flow, theme_text=text)
        assert len(message.photos) == 1, message.answers

    asyncio.run(run())
    meta = json.loads(next(offline.output.glob("*_meta.json")).read_text(encoding="utf-8"))
    assert meta["coastal_hint_detected"] is expected
    if style != "custom" and notes:
        assert notes not in meta["final_prompt"]


@pytest.mark.parametrize("entry", ["preflight", "direct", "more"])
@pytest.mark.parametrize("language", ["ru", "en"])
@pytest.mark.parametrize("style,text", [
    ("sea_coast_photo", "No ocean"), ("bright_ocean_coast_photo", "Без моря"),
    ("cozy_home_photo", "Ocean view"), ("book_nook_photo", "Tropical beach"),
    ("quiet_interior", "Ocean view"),
])
def test_f6_f10_handler_conflicts_before_paid_generation(offline, initialized_db, entry, language, style, text):
    flow = state(sphere="career", style=style, visual_mode="photo", theme_text=text)
    message = Message()

    async def run():
        await db.create_or_update_user(1, "offline", language=language)
        if entry == "preflight":
            await generation._start_generation_after_preflight(message, flow, text, language)
        elif entry == "direct":
            await generation._run_generation(message, flow, theme_text=text)
        else:
            await flow.update_data(last_generation={"sphere": "career", "style": style, "visual_mode": "photo", "theme_text": text})
            await generation.again_affirmation(Callback(message), flow)
        assert scene_style_conflict_text(language) in message.answers
        assert await flow.get_state() == GenerationState.choosing_style.state
        assert await db.get_generation_usage_today(1) == 0
        assert not await db.get_recent_generation_history(1)
        assert not offline.texts and not offline.images
        assert not message.photos
        buttons = message.markups[-1].inline_keyboard
        assert any(button.callback_data == "nav:main_menu" for row in buttons for button in row)
        await generation.nav_to_main_menu(Callback(message, "nav:main_menu"), flow)
        assert await flow.get_data() == {}

    asyncio.run(run())


@pytest.mark.parametrize("path", ["controlled", "template", "enriched"])
@pytest.mark.parametrize("text", [
    "No text, ocean sunrise", "No people, beach at sunset", "без людей, море",
    "Avoid crowds and show a tropical beach",
])
def test_f9_manual_and_more_real_handler_payloads(offline, initialized_db, path, text):
    configure_path(offline, path)
    offline.llm_prompt = "A tropical beach with palms and ocean. No text." if "beach" in text else "Ocean sunrise. No text."
    flow = state(sphere="career", style="auto", visual_mode="photo")
    message = Message()

    async def run():
        await db.create_or_update_user(1, "offline", language="en")
        await generation._run_generation(message, flow, theme_text=text)
        await generation.again_affirmation(Callback(message), flow)
        assert len(message.photos) == 2, message.answers
        assert await db.get_generation_usage_today(1) == 2
        records = await db.get_recent_generation_history(1)
        assert {r["image_prompt"] for r in records} == {p["prompt"] for p in offline.images}
        if path == "controlled":
            visuals = await db.get_recent_visual_history(1)
            recent = (await flow.get_data())["recent_generation_history"]
            assert all(v["scene_type"] for v in visuals)
            assert recent[-1]["scene_preset"] == visuals[0]["scene_type"]
            assert all(v["visual_motifs"]["scene_prompt_controlled"]["photo_scene_preset_override"] is None for v in visuals)

    asyncio.run(run())
    assert len(offline.images) == 2
    for payload in offline.images:
        assert coastal_request_text(text) in payload["prompt"]


@pytest.mark.parametrize("path", ["controlled", "template", "enriched"])
def test_f9_profile_and_more_use_current_preferences_keep_illustration(offline, initialized_db, path):
    configure_path(offline, path)
    offline.llm_prompt = "An ocean sunrise with calm waves. No text."
    flow = state()
    message = Message()

    async def run():
        await db.create_or_update_user(1, "offline", language="en")
        await db.update_user_profile_preferences(1, {"current_focus": "No people, ocean sunrise", "avoid_topics": ["beach"]})
        await generation._start_profile_generation(message, flow, user_id=1)
        assert len(message.photos) == 1, message.answers
        await db.update_user_profile_preferences(1, {"current_focus": "Tropical beach with palms", "avoid_topics": ["beach"]})
        offline.llm_prompt = "Tropical beach with palms and ocean. No text."
        await generation.again_affirmation(Callback(message), flow)
        assert len(message.photos) == 2, message.answers
        last = (await flow.get_data())["last_generation"]
        assert last["visual_mode"] == "illustration" and last["theme_text"] is None

    asyncio.run(run())
    assert "ocean sunrise" in offline.images[0]["prompt"]
    assert "Tropical beach with palms" in offline.images[1]["prompt"]
    assert "Scene exclusions: no beach" not in offline.images[1]["prompt"]
    metas = [json.loads(p.read_text(encoding="utf-8")) for p in offline.output.glob("*_meta.json")]
    assert all(m["visual_mode"] == "illustration" for m in metas)


@pytest.mark.parametrize("path", ["controlled", "template", "enriched"])
@pytest.mark.parametrize("style", ["living_nature_photo", "sea_coast_photo"])
def test_f9_scheduled_then_subscription_more_payloads_history_and_language(offline, initialized_db, path, style):
    configure_path(offline, path)
    offline.llm_prompt = "Ocean view. No text." if style == "sea_coast_photo" else "A real forest path with trees. No text."
    flow = state()
    message = Message(user_id=9000)

    class Bot:
        sent = []

        async def send_photo(self, **kwargs):
            self.sent.append(kwargs)
            return SimpleNamespace(photo=[SimpleNamespace(file_id="scheduled-file")])

    async def run():
        await db.create_or_update_user(1, "offline", language="ru")
        await db.create_subscription(
            1, "career", None, style, "en", 8, 0, subscription_mode="sphere_focus",
            subscription_sphere="career", subscription_style_mode=style,
            visual_mode="photo", allowed_visual_modes=["photo"],
        )
        bot = Bot()
        await scheduler.send_daily_affirmations(bot, now=dt.datetime(2030, 3, 1, 8, 0, tzinfo=scheduler.MOSCOW))
        assert len(bot.sent) == 1
        assert "your daily focus" in bot.sent[0]["caption"].lower()
        await subscribe.subscription_more(Callback(message, "sub_more:yes"), flow)
        assert len(message.photos) == 1, message.answers
        assert "твой настрой" in message.photos[0]["caption"].lower()
        assert (await db.get_subscription_deliveries(["2030-03-01"]))[0]["status"] == "sent"
        visuals = await db.get_recent_visual_history(1)
        assert len(visuals) == 2
        if path == "controlled":
            assert all(v["scene_type"] for v in visuals)
            for v in visuals:
                assert v["scene_type"] == v["visual_motifs"]["scene_prompt_controlled"]["used_scene_type"]
        records = await db.get_recent_generation_history(1)
        assert {r["image_prompt"] for r in records} == {p["prompt"] for p in offline.images}

    asyncio.run(run())
    assert len(offline.images) == 2
    for payload in offline.images:
        if style == "living_nature_photo":
            assert "Coastal realism is mandatory" not in payload["prompt"]
        if path == "controlled":
            assert "Photo scene preset:" not in payload["prompt"]


@pytest.mark.parametrize("failure", ["cancel", "delivery"])
def test_f10_existing_reservation_cleanup_with_real_transport_boundary(offline, initialized_db, failure):
    flow = state(sphere="career", style="auto", visual_mode="photo")
    offline.cancel_text = failure == "cancel"
    message = Message(fail_delivery=failure == "delivery")

    async def run():
        await db.create_or_update_user(1, "offline", language="en")
        with pytest.raises(asyncio.CancelledError if failure == "cancel" else RuntimeError):
            await generation._run_generation(message, flow, theme_text="No text, ocean sunrise")
        assert await db.get_generation_usage_today(1) == 0
        assert not await db.get_recent_generation_history(1)

    asyncio.run(run())


# Final remediation R2: assertions always inspect the serialized image request.
@pytest.mark.parametrize("text", ["Ocean view", "Ocean view, no sandy beach", "Tropical beach with palms", "Turquoise lagoon"])
def test_r2_n1_double_application_has_one_final_directive(offline, text):
    first = apply_coastal_scene_intent({"scene_type": "forest_path"}, user_text=text, selected_style="auto")
    second = apply_coastal_scene_intent(first, user_text=text, selected_style="auto")
    assert second == first
    prompt = build_controlled_scene_prompt(
        scene_plan=second, user_text=text, selected_style="auto", visual_mode="photo",
    )
    path = asyncio.run(openai_image.generate_image(
        style="auto", sphere="career", user_text=text, visual_mode="photo",
        prompt_override=prompt, image_prompt_trace="scene_planner_local",
    ))
    final = offline.images[-1]["prompt"]
    directive = "Explicit coastal scene request: " + coastal_request_text(text)
    assert final.count(directive) == 1
    meta = json.loads(Path(path.replace(".png", "_meta.json")).read_text(encoding="utf-8"))
    assert meta["scene_type"] == first["scene_type"]
    assert meta["final_prompt"] == final
    assert meta["photo_scene_preset"] is None


def test_r2_n1_handler_manual_more_preserves_actual_history(offline, initialized_db, record_property):
    configure_path(offline, "controlled")
    flow = state(sphere="career", style="auto", visual_mode="photo")
    message = Message()

    async def run():
        await db.create_or_update_user(1, "offline", language="en")
        await generation._run_generation(message, flow, theme_text="Ocean view")
        await generation.again_affirmation(Callback(message), flow)
        assert len(message.photos) == len(offline.images) == 2
        records = await db.get_recent_generation_history(1)
        visuals = await db.get_recent_visual_history(1)
        assert {r["image_prompt"] for r in records} == {p["prompt"] for p in offline.images}
        assert all(v["scene_type"] == v["visual_motifs"]["scene_prompt_controlled"]["used_scene_type"] for v in visuals)
        assert (await get_visual_memory_context(1))["recent_scene_types"] == list(dict.fromkeys(v["scene_type"] for v in visuals))

    asyncio.run(run())
    for payload in offline.images:
        assert payload["prompt"].count("Explicit coastal scene request: Ocean view") == 1
    record_property("final_payload", json.dumps(offline.images[-1]))


COMPATIBLE_COASTAL_STYLES = [
    ("urban_city_photo", "Urban waterfront with an ocean view", "urban waterfront"),
    ("cafe_terrace_photo", "Seaside cafe overlooking the ocean", "seaside cafe terrace"),
    ("rural_calm_photo", "Coastal village with a sea view", "coastal village"),
    ("calm_lifestyle_photo", "Ocean view", "coastal lifestyle"),
    ("cafe_terrace_photo", "Cafe terrace on a tropical palm beach with an ocean view", "seaside cafe terrace"),
    ("urban_city_photo", "Tropical palm beach beside an urban waterfront", "urban waterfront"),
    ("rural_calm_photo", "Coastal village beside a tropical beach with palms", "coastal village"),
    ("calm_lifestyle_photo", "Tropical beach with palms", "coastal lifestyle"),
    ("urban_city_photo", "Turquoise lagoon", "urban waterfront"),
    ("cafe_terrace_photo", "Turquoise lagoon", "seaside cafe terrace"),
    ("rural_calm_photo", "Turquoise lagoon", "coastal village"),
    ("calm_lifestyle_photo", "Turquoise lagoon", "coastal lifestyle"),
]


@pytest.mark.parametrize("path", ["controlled", "template", "enriched"])
@pytest.mark.parametrize("style,text,direction", COMPATIBLE_COASTAL_STYLES)
def test_r2_n2_compatible_final_payload(offline, path, style, text, direction, record_property):
    offline.llm_prompt = text + ". No text."
    assert generation._generation_preflight_error({"sphere": "career", "style": style, "visual_mode": "photo"}, text, "en") is None
    prompt, meta = asyncio.run(image_payload(offline, path, text, style=style))
    low = prompt.lower()
    assert direction in low
    assert text in prompt
    assert meta["selected_style"] == style
    assert meta["photo_scene_preset"] is None
    for conflicting in ("quiet street, courtyard", "realistic rural morning", "simple morning ritual", "no tables", "no chairs", "no built structures", "only natural shoreline elements"):
        assert conflicting not in low
    if style == "cafe_terrace_photo":
        assert "table" not in low.split("avoid:", 1)[-1].split(".", 1)[0].split(", ")
    if "lagoon" in text.lower():
        assert "requested lagoon or bay" in low or "lagoon or bay view" in low
        assert "open horizon over water" not in low
        assert "overlooking the ocean" not in low
        assert "overlooking the sea" not in low
    record_property("final_payload", json.dumps(offline.images[-1]))


@pytest.mark.parametrize("path", ["controlled", "template", "enriched"])
@pytest.mark.parametrize("style", ["urban_city_photo", "cafe_terrace_photo", "rural_calm_photo"])
def test_r2_n2_incompatible_final_payload_is_never_sent(offline, path, style):
    with pytest.raises(ValueError, match="conflicts"):
        asyncio.run(image_payload(offline, path, "Tropical beach with palms", style=style))
    assert not offline.images and not offline.texts


@pytest.mark.parametrize("entry", ["preflight", "direct", "more"])
@pytest.mark.parametrize("style", ["urban_city_photo", "cafe_terrace_photo", "rural_calm_photo"])
@pytest.mark.parametrize("text", ["Tropical beach with palms", "Тропический пляж с пальмами"])
def test_r2_n2_dedicated_beach_conflict_before_paid_calls(offline, initialized_db, entry, style, text):
    flow = state(sphere="career", style=style, visual_mode="photo", theme_text=text)
    message = Message()

    async def run():
        await db.create_or_update_user(1, "offline", language="en")
        if entry == "preflight":
            await generation._start_generation_after_preflight(message, flow, text, "en")
        elif entry == "direct":
            await generation._run_generation(message, flow, theme_text=text)
        else:
            await flow.update_data(last_generation={"sphere": "career", "style": style, "visual_mode": "photo", "theme_text": text})
            await generation.again_affirmation(Callback(message), flow)
        assert scene_style_conflict_text("en") in message.answers
        assert await flow.get_state() == GenerationState.choosing_style.state
        assert (await flow.get_data())["theme_text"] == text
        assert await db.get_generation_usage_today(1) == 0
        assert not await db.get_recent_generation_history(1)
        assert not offline.images and not offline.texts

    asyncio.run(run())


@pytest.mark.parametrize("path", ["controlled", "template", "enriched"])
@pytest.mark.parametrize("visual_mode", ["photo", "illustration"])
@pytest.mark.parametrize("text,wanted,opposite", [
    ("No text, ocean sunrise", "sunrise", ("sunset", "evening")),
    ("No people, beach at sunset", "sunset", ("sunrise", "morning", "dawn")),
    ("Без людей, море на рассвете", "sunrise", ("sunset", "evening")),
    ("Без текста, пляж на закате", "sunset", ("sunrise", "morning", "dawn")),
    ("No people, lagoon at sunset", "sunset", ("sunrise", "morning", "dawn")),
])
def test_r2_n4_final_payload_has_no_conflicting_time(offline, monkeypatch, path, visual_mode, text, wanted, opposite, record_property):
    # Force both an opposite automatic preset and a conflicting enriched reply.
    preset = "vivid_seaside_sunset" if wanted == "sunrise" else "sunny_beach_morning"
    monkeypatch.setattr(openai_image, "resolve_photo_scene_preset", lambda *args, **kwargs: preset)
    offline.llm_prompt = "An ocean coast and beach at " + opposite[0] + ". No text."
    prompt, meta = asyncio.run(image_payload(
        offline, path, text, visual_mode=visual_mode, scene="coastal_morning",
        color_mood="warm sunrise gold, morning blue" if wanted == "sunset" else "warm sunset gold, evening blue",
    ))
    assert wanted in prompt.lower()
    # The illustration contract has an existing negative silhouette-at-sunset
    # example; inspect positive instructions separately from that safety list.
    positive = prompt.split("Avoid:", 1)[0].lower()
    assert all(word not in positive for word in opposite)
    assert meta["final_prompt"] == prompt
    if "lagoon" in text:
        assert "open sea horizon" not in prompt.lower()
        assert "open horizon over water" not in prompt.lower()
    if path == "enriched":
        assert len(offline.texts) == 1
        assert meta["prompt_source"] == "template_fallback"
    record_property("final_payload", json.dumps(offline.images[-1]))


@pytest.mark.parametrize("path", ["controlled", "template", "enriched"])
def test_r2_n4_selected_custom_notes_time_is_authoritative(offline, path):
    offline.llm_prompt = "A beach and ocean at sunrise. No text."
    prompt, _ = asyncio.run(image_payload(
        offline, path, None, style="custom", notes="No people, beach at sunset", scene="coastal_morning",
        color_mood="warm sunrise gold, morning blue",
    ))
    assert "sunset" in prompt
    assert not any(word in prompt.lower() for word in ("sunrise", "morning", "dawn"))


@pytest.mark.parametrize("visual_mode", ["photo", "illustration"])
@pytest.mark.parametrize("path", ["controlled", "template", "enriched"])
@pytest.mark.parametrize("notes,exclusion", [("Avoid beach", "no beach"), ("Without ocean", "no ocean or sea"), ("No people", "No people")])
def test_r2_n5_exclusion_only_custom_style_has_valid_phrase(offline, path, visual_mode, notes, exclusion, record_property):
    offline.llm_prompt = "A calm forest path. No text."
    prompt, _ = asyncio.run(image_payload(offline, path, "Quiet confidence", style="custom", notes=notes, visual_mode=visual_mode))
    assert "in the style: ." not in prompt
    assert "in the style:" not in prompt
    assert exclusion in prompt
    if path == "template":
        assert "a balanced, natural visual treatment" in prompt
    record_property("final_payload", json.dumps(offline.images[-1]))


@pytest.mark.parametrize("path", ["controlled", "template", "enriched"])
@pytest.mark.parametrize("style", ["auto", "sea_coast_photo", "bright_ocean_coast_photo"])
def test_r2_n4_coastal_selection_keeps_theme_lighting(offline, path, style):
    offline.llm_prompt = "Ocean sunrise. No text."
    prompt, _ = asyncio.run(image_payload(
        offline, path, "At sunset", style=style, scene="coastal_morning", color_mood="morning blue, dawn gold",
    ))
    assert "sunset" in prompt.lower()
    assert not any(word in prompt.lower() for word in ("morning", "sunrise", "dawn"))


@pytest.mark.parametrize("entry", ["preflight", "direct", "more"])
@pytest.mark.parametrize("style", SYMBOLIC_STYLE_KEYS)
def test_r2_n6_all_symbolic_styles_accept_ocean_context(offline, initialized_db, entry, style, record_property):
    # Even with both alternate builders enabled, symbolic mode owns its prompt.
    offline.settings.scene_planner_image_prompt_enabled = True
    offline.settings.llm_image_prompt_enabled = True
    flow = state(sphere="career", style=style, visual_mode="symbolic", theme_text="Ocean view")
    message = Message()

    async def run():
        await db.create_or_update_user(1, "offline", language="en")
        if entry == "preflight":
            await generation._start_generation_after_preflight(message, flow, "Ocean view", "en")
        elif entry == "direct":
            await generation._run_generation(message, flow, theme_text="Ocean view")
        else:
            await flow.update_data(last_generation={"sphere": "career", "style": style, "visual_mode": "symbolic", "theme_text": "Ocean view"})
            await generation.again_affirmation(Callback(message), flow)
        assert len(message.photos) == len(offline.images) == 1, message.answers
        assert await db.get_generation_usage_today(1) == 1

    asyncio.run(run())
    prompt = offline.images[0]["prompt"]
    assert "one centered visible symbol" in prompt if style == "daily_symbol" else "one centered visible mandala" in prompt
    assert "use it only as abstract emotional meaning" in prompt
    assert "Explicit coastal scene request:" not in prompt
    assert "Coastal realism is mandatory" not in prompt
    assert "Photo scene preset:" not in prompt
    meta = json.loads(next(offline.output.glob("*_meta.json")).read_text(encoding="utf-8"))
    assert meta["prompt_branch"] == "symbolic"
    assert meta["prompt_source"] == "symbolic_prompt_builder"
    record_property("final_payload", json.dumps(offline.images[-1]))


@pytest.mark.parametrize("visual_mode", ["photo", "illustration"])
@pytest.mark.parametrize("style", SYMBOLIC_STYLE_KEYS + ["quiet_interior"])
def test_r2_n6_photographic_and_illustrated_conflicts_still_preflight(offline, initialized_db, visual_mode, style):
    flow = state(sphere="career", style=style, visual_mode=visual_mode)
    message = Message()

    async def run():
        await db.create_or_update_user(1, "offline", language="en")
        await generation._run_generation(message, flow, theme_text="Ocean view")
        assert scene_style_conflict_text("en") in message.answers
        assert await flow.get_state() == GenerationState.choosing_style.state
        assert not offline.images and not offline.texts
        assert await db.get_generation_usage_today(1) == 0

    asyncio.run(run())


# R3 exercises the real assembled-template handoff, including More and scheduler.
R3_INPUTS = [
    "Ocean view", "Ocean sunrise", "Beach at sunset",
    "Avoid beach, show rocky coast", "Море без пляжа", "Tropical beach with palms",
]


@pytest.fixture
def final_boundary_handoffs(offline, monkeypatch):
    calls = []

    async def generate(**kwargs):
        path = await openai_image.generate_image(**kwargs)
        calls.append({**kwargs, "image_path": path})
        return path

    monkeypatch.setattr(generation, "generate_image", generate)
    monkeypatch.setattr(scheduler, "generate_image", generate)

    def stable_choice(values):
        if values is openai_image._COLOR_MOODS:
            return "clear natural light, blue and gold"
        if values is openai_image._COMPOSITION_HINTS:
            return "open airy composition with visible depth"
        return values[0]

    monkeypatch.setattr(openai_image.random, "choice", stable_choice)
    return calls


def configure_final_boundary(offline, path, text):
    configure_path(offline, "enriched" if path in {"fallback", "llm"} else path)
    offline.llm_prompt = "" if path == "fallback" else {
        "Ocean view": "A real ocean view with waves and clear natural light. No text.",
        "Ocean sunrise": "A real ocean sunrise with waves. No text.",
        "Beach at sunset": "A real beach at sunset with waves. No text.",
        "Avoid beach, show rocky coast": "A real rocky coast with waves. No text.",
        "Море без пляжа": "A real ocean view with waves, no beach. No text.",
        "Tropical beach with palms": "A real tropical beach with palms and ocean waves. No text.",
    }.get(text, "A real forest path with trees. No text.")


def assert_final_boundary(offline, call, payload, path, text=None):
    prompt = payload["prompt"]
    trace = {"fallback": "template_fallback", "controlled": "scene_planner_local", "llm": "llm"}.get(path, "template")
    assert call["prompt_override"]  # Never the direct prompt_override=None shortcut.
    assert call["image_prompt_trace"] == trace
    meta = json.loads(Path(call["image_path"].replace(".png", "_meta.json")).read_text(encoding="utf-8"))
    assert meta["prompt_source"] == trace
    assert meta["prompt"] == meta["final_prompt"] == prompt
    assert meta["prompt_branch"] == meta["visual_mode"] == "photo"
    assert "No text" in prompt or "no text" in prompt
    assert openai_image._build_photo_negative_prompt() in prompt
    assert prompt.count("Photo negative prompt:") == 1
    assert prompt.count("Photo scene preset:") <= 1
    assert prompt.count("Time of day and lighting:") <= 1
    if path in {"template", "fallback"}:
        # Full payload equality also protects every existing local safeguard,
        # style/mode constraint and user exclusion from a second assembly pass.
        assert prompt == call["prompt_override"].strip()
        assert "PHOTO BRANCH ONLY" in prompt
        assert openai_image._ANATOMY_ANCHOR in prompt
        preset = next((key for key, block in PHOTO_SCENE_PRESETS.items() if block in prompt), None)
        assert meta["photo_scene_preset"] == meta["scene_preset"] == meta["scene_type"] == preset
        assert meta["visual_archetype"] == get_visual_archetype(style=meta["resolved_style"], scene_preset=preset)
    else:
        assert prompt.startswith(call["prompt_override"])
        assert "Strict photo branch:" in prompt
    if path == "controlled":
        assert "Photo scene preset:" not in prompt
        assert meta["photo_scene_preset"] is None
        assert prompt.startswith("Scene type: " + meta["scene_type"] + ".")
    if text or meta["resolved_style"] == "sea_coast_photo":
        positive = prompt.split("Photo negative prompt:", 1)[0].split("Avoid:", 1)[0].lower()
        morning = re.search(r"\b(?:sunrise|morning|dawn)\b", positive)
        evening = re.search(r"\b(?:sunset|evening)\b", positive)
        assert not (morning and evening), positive
    if text:
        intent = parse_coastal_text(text)
        assert prompt.count("Explicit coastal scene request:") == 1
        assert coastal_request_text(text) in prompt
        if intent.excluded:
            assert intent.exclusion_clause() in prompt
        if "без пляжа" in text or "Avoid beach" in text:
            assert "Scene exclusions: no beach." in prompt
            assert "Photo scene preset: quiet_beach_morning." not in prompt
        if text == "Ocean sunrise":
            assert morning and not evening
        if text == "Beach at sunset":
            assert evening and not morning
    return meta


@pytest.mark.parametrize("path", ["template", "fallback", "controlled", "llm"])
@pytest.mark.parametrize("text", R3_INPUTS)
def test_r3_manual_and_more_final_boundary(offline, initialized_db, final_boundary_handoffs, path, text, record_property):
    configure_final_boundary(offline, path, text)
    flow = state(sphere="career", style="auto", visual_mode="photo")
    message = Message()

    async def run():
        await db.create_or_update_user(1, "offline", language="en")
        await generation._run_generation(message, flow, theme_text=text)
        await generation.again_affirmation(Callback(message), flow)
        assert len(message.photos) == len(offline.images) == len(final_boundary_handoffs) == 2, message.answers
        metas = [assert_final_boundary(offline, call, payload, path, text)
                 for call, payload in zip(final_boundary_handoffs, offline.images)]
        records = await db.get_recent_generation_history(1)
        visuals = await db.get_recent_visual_history(1)
        assert len(records) == len(visuals) == 2
        assert [r["image_prompt"] for r in records] == [p["prompt"] for p in reversed(offline.images)]
        assert [v["scene_type"] for v in visuals] == [m["scene_type"] for m in reversed(metas)]
        recent = (await flow.get_data())["recent_generation_history"]
        assert [r["scene_preset"] for r in recent] == [m["scene_preset"] for m in metas]
        assert await db.get_generation_usage_today(1) == 2

    asyncio.run(run())
    record_property("image_handoffs", json.dumps(final_boundary_handoffs, ensure_ascii=False))
    record_property("final_payloads", json.dumps(offline.images, ensure_ascii=False))


@pytest.mark.parametrize("path", ["template", "fallback", "controlled", "llm"])
@pytest.mark.parametrize("style", ["sea_coast_photo", "living_nature_photo"])
def test_r3_scheduled_final_boundary(offline, initialized_db, final_boundary_handoffs, path, style, record_property):
    configure_final_boundary(offline, path, "Ocean view" if style == "sea_coast_photo" else None)

    class Bot:
        def __init__(self):
            self.sent = []

        async def send_photo(self, **kwargs):
            self.sent.append(kwargs)
            return SimpleNamespace(photo=[SimpleNamespace(file_id="scheduled-r3-file")])

    async def run():
        await db.create_or_update_user(1, "offline", language="ru")
        await db.create_subscription(
            1, "career", None, style, "en", 8, 0, subscription_mode="sphere_focus",
            subscription_sphere="career", subscription_style_mode=style,
            visual_mode="photo", allowed_visual_modes=["photo"],
        )
        bot = Bot()
        await scheduler.send_daily_affirmations(bot, now=dt.datetime(2030, 3, 1, 8, 0, tzinfo=scheduler.MOSCOW))
        assert len(bot.sent) == len(offline.images) == len(final_boundary_handoffs) == 1
        call = final_boundary_handoffs[0]
        assert call["user_text"] is None  # Scheduled content has no manual user theme.
        meta = assert_final_boundary(offline, call, offline.images[0], path)
        assert "your daily focus" in bot.sent[0]["caption"].lower()
        assert (await db.get_subscription_deliveries(["2030-03-01"]))[0]["status"] == "sent"
        records = await db.get_recent_generation_history(1)
        visuals = await db.get_recent_visual_history(1)
        assert len(records) == len(visuals) == 1
        assert records[0]["image_prompt"] == offline.images[0]["prompt"]
        assert visuals[0]["scene_type"] == meta["scene_type"]
        if style == "living_nature_photo":
            assert "Coastal realism is mandatory" not in offline.images[0]["prompt"]

    asyncio.run(run())
    record_property("image_handoffs", json.dumps(final_boundary_handoffs, ensure_ascii=False))
    record_property("final_payloads", json.dumps(offline.images, ensure_ascii=False))


@pytest.mark.parametrize("trace", [None, "override", "llm"])
def test_r3_raw_override_still_receives_photo_enforcement(offline, trace):
    raw = "A real ocean sunrise with waves."
    path = asyncio.run(openai_image.generate_image(
        style="sea_coast_photo", sphere="career", visual_mode="photo",
        user_text="Ocean sunrise", prompt_override=raw, image_prompt_trace=trace,
    ))
    prompt = offline.images[0]["prompt"]
    assert prompt.startswith(raw)
    assert "No text, no words on the image." in prompt
    assert "Strict photo branch:" in prompt
    assert openai_image._build_photo_negative_prompt() in prompt
    assert prompt.count("Explicit coastal scene request:") == 1
    assert prompt.count("Photo scene preset:") == 1
    assert prompt.count("Time of day and lighting:") == 1
    meta = json.loads(Path(path.replace(".png", "_meta.json")).read_text(encoding="utf-8"))
    assert meta["prompt_source"] == (trace or "override")
    assert meta["final_prompt"] == prompt


@pytest.mark.parametrize("trace", ["template", "template_fallback"])
def test_r3_symbolic_mode_still_owns_prompt(offline, trace):
    path = asyncio.run(openai_image.generate_image(
        style="mandala_harmony", sphere="career", visual_mode="symbolic",
        user_text="Ocean view", prompt_override="A real ocean photograph.", image_prompt_trace=trace,
    ))
    prompt = offline.images[0]["prompt"]
    assert "one centered visible mandala" in prompt
    assert "A real ocean photograph." not in prompt
    assert "Photo scene preset:" not in prompt
    meta = json.loads(Path(path.replace(".png", "_meta.json")).read_text(encoding="utf-8"))
    assert meta["prompt_source"] == "symbolic_prompt_builder"
    assert meta["visual_mode"] == "symbolic"


@pytest.mark.parametrize("path", ["template", "fallback"])
def test_r3_custom_exclusions_survive_assembled_handler_handoff(
    offline, initialized_db, final_boundary_handoffs, path,
):
    configure_final_boundary(offline, path, "Ocean view")
    notes = "Natural photography, no people, avoid beach"
    flow = state(sphere="career", style="custom", visual_mode="photo", custom_style_description=notes)
    message = Message()

    async def run():
        await db.create_or_update_user(1, "offline", language="en")
        await generation._run_generation(message, flow, theme_text="Ocean view")
        assert len(message.photos) == len(final_boundary_handoffs) == 1, message.answers
        assert_final_boundary(offline, final_boundary_handoffs[0], offline.images[0], path, "Ocean view")

    asyncio.run(run())
    prompt = offline.images[0]["prompt"]
    assert "Scene exclusions: no beach." in prompt
    assert "no people" in prompt
    assert "Natural photography" in prompt
    assert prompt.count("User exclusions:") == 1
