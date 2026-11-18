"""Profile -> handler -> real prompt builder -> mocked HTTP transport regressions.

SQLite and output paths are isolated by conftest; Telegram and image generation
are fakes. The text generator itself runs, including final request serialization.
"""
import asyncio
import copy
import json
from types import SimpleNamespace

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

import database as db
from config import TextProviderConfig
from handlers import generation, start
from services import yandex_gpt as provider
from services.text_prompt_builder import PROFILE_GUIDANCE_MAX_CHARS, build_profile_text_guidance
from services.ritual_config import get_focus_for_date
from states import GenerationState, ProfileEditState


USER_ID = 72002


class Message:
    def __init__(self, user_id=USER_ID):
        self.from_user = SimpleNamespace(id=user_id)
        self.answers = []
        self.photos = []
        self.voices = []
        self.fail_delivery = False
        self.edits = []

    async def answer(self, text, **kwargs):
        self.answers.append(text)

    async def edit_reply_markup(self, **kwargs):
        pass

    async def edit_text(self, text, **kwargs):
        self.edits.append(text)

    async def answer_photo(self, **kwargs):
        if self.fail_delivery:
            raise RuntimeError("synthetic Telegram failure")
        self.photos.append(kwargs)
        return SimpleNamespace(photo=[SimpleNamespace(file_id="test-photo")])

    async def answer_voice(self, **kwargs):
        self.voices.append(kwargs)


class Callback:
    def __init__(self, data):
        self.data = data
        self.from_user = SimpleNamespace(id=USER_ID)
        # In an actual callback, the attached message was sent by the bot.
        self.message = Message(user_id=990002)

    async def answer(self, text=None):
        pass


@pytest.fixture
def flow(monkeypatch, initialized_db):
    settings = SimpleNamespace(
        disable_daily_generation_limit=False, generation_daily_limit=20,
        llm_image_prompt_enabled=False, show_image_debug=False,
        image_model="test-image", image_size="1024x1024",
        text_planner_shadow_enabled=False, text_planner_controlled_enabled=False,
        text_memory_context_enabled=False, text_reviewer_shadow_enabled=True,
        orchestrator_shadow_enabled=True, scene_planner_shadow_enabled=False,
        scene_planner_image_prompt_enabled=False,
    )
    state = FSMContext(storage=MemoryStorage(), key=StorageKey(bot_id=990002, chat_id=USER_ID, user_id=USER_ID))
    harness = SimpleNamespace(
        settings=settings, state=state, requests=[], image_calls=[], history=[],
        transport_error=None, image_error=None, planner_calls=[], response_content=None,
    )

    class Response:
        status = 200

        async def __aenter__(self):
            if harness.transport_error:
                raise harness.transport_error
            return self

        async def __aexit__(self, *_):
            return False

        async def json(self):
            english = "Write in English." in harness.requests[-1]["messages"][0]["content"]
            payload = {
                "focus": "steady focus" if english else "спокойный фокус",
                "affirmations": ["I protect my energy", "My experience matters", "I can choose calmly", "I notice my support"] if english else [
                    "Сегодня я берегу силы", "Мой опыт имеет значение",
                    "Мне доступен спокойный выбор", "Я замечаю свою опору",
                ],
            }
            return {"choices": [{"message": {"content": harness.response_content if harness.response_content is not None else json.dumps(payload)}, "finish_reason": "stop"}]}

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        def post(self, url, **kwargs):
            harness.requests.append(copy.deepcopy(kwargs["json"]))
            assert url == "https://text.invalid/v1/chat/completions"
            return Response()

    async def image_prompt(**kwargs):
        return "test image prompt", "template"

    async def image(**kwargs):
        harness.image_calls.append(kwargs)
        if harness.image_error:
            raise harness.image_error
        return "fake_image.png"

    async def history(**kwargs):
        harness.history.append(kwargs)

    real_guidance = generation.build_text_generation_guidance

    def guidance(**kwargs):
        result = real_guidance(**kwargs)
        harness.planner_calls.append((kwargs, result))
        return result

    monkeypatch.setattr(generation, "get_settings", lambda: settings)
    monkeypatch.setattr(provider, "get_text_provider_config", lambda: TextProviderConfig(
        provider="openai", base_url="https://text.invalid/v1", api_key="synthetic-key",
        model="gpt-6-luna", timeout_seconds=5,
    ))
    monkeypatch.setattr(provider.aiohttp, "ClientSession", Session)
    monkeypatch.setattr(generation, "build_text_generation_guidance", guidance)
    monkeypatch.setattr(generation, "build_enriched_image_prompt", image_prompt)
    monkeypatch.setattr(generation, "generate_image", image)
    monkeypatch.setattr(generation, "update_image_meta", lambda **kwargs: {
        "scene_preset": "test-scene", "visual_archetype": "test-archetype",
    })
    monkeypatch.setattr(generation, "record_generation_history_best_effort", history)
    monkeypatch.setattr(generation, "log_generation_ok", lambda *args: None)
    monkeypatch.setattr(generation, "log_generation_fail", lambda *args: None)
    return harness


async def save_preferences(preferences, language="ru"):
    await db.create_or_update_user(USER_ID, "test-user", name="Test", gender="female", language=language)
    await db.update_user_profile_preferences(USER_ID, preferences)


def user_prompt(flow, index=-1):
    return flow.requests[index]["messages"][1]["content"]


def preferences(language, *, long=False):
    focus = "спокойный фокус" if language == "ru" else "steady focus"
    if long:
        # Varied, valid prose: the existing gibberish guard rejects repeated
        # filler before prompt construction, so that would not test budgeting.
        focus += (
            ". Хочу внимательнее относиться к своим силам, замечать усталость, выбирать посильные задачи, "
            "сохранять любопытство. Сейчас особенно важны отдых после насыщенного рабочего дня, прогулки, "
            "уютный дом, творчество, встречи с близкими людьми, честный разговор о границах. "
            "Мне помогает планировать неделю с запасом времени, оставлять свободные вечера для чтения, "
            "музыки, рисования, приготовления еды. Постепенно учусь просить поддержку, принимать несовершенство, "
            "отказываться от лишних обязательств без чувства вины. Желаю вернуть ощущение собственного ритма, "
            "внутреннюю уверенность, доверие решениям, интерес новым идеям. Пусть внимание возвращается "
            "к простым наблюдаемым вещам: свету за окном, тёплой чашке, удобному креслу, свежему воздуху. "
            "Полезно записывать мысли, пробовать небольшие изменения, понимать желания, беречь отношения, "
            "находить удовольствие в повседневности, праздновать достигнутое, давать себе пространство для выбора."
            if language == "ru" else
            ". I want to notice my energy, respect fatigue, choose manageable tasks and remain curious. "
            "Rest after busy working days, walks outside, a comfortable home, creativity and honest conversations "
            "with close friends matter especially now. Planning each week with room for surprises helps me leave "
            "evenings free for reading, music, drawing, cooking and reflection. Gradually I learn to ask for support, "
            "accept imperfect results and decline extra commitments without guilt. My intention is to recover a "
            "personal rhythm, inner confidence, trust in decisions and interest in unfamiliar ideas. Attention can "
            "return to ordinary observable details: sunlight through windows, a warm cup, comfortable chairs, fresh "
            "air, quiet gardens, familiar streets. Writing thoughts down, trying small changes, understanding wishes, "
            "protecting relationships, finding everyday pleasure, celebrating progress and allowing space for choice "
            "all feel helpful. There is permission to pause, listen carefully, appreciate effort, explore possibilities, "
            "remember strengths, practice patience, enjoy simple moments and move forward at a sustainable pace."
        )
    return {
        "tone_preference": "calm_no_pathos",
        "support_style": "grounding",
        "text_length_preference": "short",
        "current_focus": focus,
        "life_areas": ["отдых", "творчество"] if language == "ru" else ["rest", "creativity"],
        "avoid_topics": ["болезни", "конфликты"] if language == "ru" else ["illness", "conflicts"],
        "avoid_words": ["срочно", "должен"] if language == "ru" else ["urgently", "must"],
    }


@pytest.mark.parametrize("language", ["ru", "en"])
@pytest.mark.parametrize("long", [False, True], ids=["short", "long"])
@pytest.mark.parametrize("planner,memory", [(False, False), (True, False), (True, True)])
def test_profile_constraints_reach_final_provider_payload(flow, monkeypatch, language, long, planner, memory):
    prefs = preferences(language, long=long)
    flow.settings.text_planner_controlled_enabled = planner
    flow.settings.text_memory_context_enabled = memory
    memory_calls = []

    async def get_memory(uid, limit):
        memory_calls.append((uid, limit))
        return {
            "recent_focus_titles": ["previous focus " * 80],
            "avoid_affirmation_openings": ["I allow", "Я позволяю"],
            "avoid_soft_actions": ["name three things " * 80],
            "avoid_phrases": ["memory tail " * 100],
        }

    monkeypatch.setattr(generation, "get_text_memory_context", get_memory)

    async def run():
        await save_preferences(prefs, language)
        await generation.cb_generate_from_profile(Callback("profile_generate:yes"), flow.state)
        assert len(flow.requests) == 1
        prompt = user_prompt(flow)
        profile = build_profile_text_guidance(preferences=prefs, language=language)
        assert len(profile) <= PROFILE_GUIDANCE_MAX_CHARS
        assert profile in prompt  # the entire budgeted Profile block, no downstream clipping
        assert prompt.count("Profile preference guidance:") == 1
        assert f"avoid_topics: {', '.join(prefs['avoid_topics'])}" in prompt
        assert f"avoid_words: {', '.join(prefs['avoid_words'])}" in prompt
        assert "Do not center the text on avoid_topics or use avoid_words verbatim." in prompt
        assert "preferred_tone: calm_no_pathos" in prompt
        assert "preferred_support_style: grounding" in prompt
        assert "preferred_text_length: short" in prompt
        assert "life_areas: " + ", ".join(prefs["life_areas"]) in prompt
        assert "спокойный фокус" in prompt if language == "ru" else "steady focus" in prompt
        assert len(prompt) + len(flow.requests[0]["messages"][0]["content"]) <= provider._PROFILE_PROMPT_MAX_CHARS
        assert ("Text planner guidance:" in prompt) is planner
        source = flow.planner_calls[0][1]
        if planner:
            assert provider._clip_user_text(source, 1500) in prompt  # same planner budget as ordinary generation
            assert "Profile exclusions and tone/support/length preferences override planner suggestions." in prompt
        assert memory_calls == ([(USER_ID, 10)] if memory else [])
        if memory:
            assert "Text memory / anti-repeat guidance:" in source
            assert "I allow, Я позволяю" in source
        if language == "ru":
            assert "Язык: русский" in prompt
            assert "женском роде" in prompt
            assert "тёплое неформальное обращение на «ты»" in prompt
        else:
            assert "Language: English." in prompt
            assert "Язык: русский" not in prompt
        assert flow.history[0]["request_type"] == "profile_preferences"
        assert (await flow.state.get_data())["last_generation"]["use_profile_preferences"] is True

    asyncio.run(run())


@pytest.mark.parametrize("language", ["ru", "en"])
@pytest.mark.parametrize("change", ["unchanged", "updated", "removed"])
def test_profile_more_reloads_current_preferences_without_storing_them(flow, language, change):
    initial = preferences(language)

    async def run():
        await save_preferences(initial, language)
        await generation._start_profile_generation(Message(), flow.state, user_id=USER_ID)
        first_data = await flow.state.get_data()
        assert first_data["last_generation"]["use_profile_preferences"] is True
        assert first_data["last_generation"]["theme_text"] is None
        assert initial["current_focus"].strip() not in json.dumps(first_data, ensure_ascii=False)
        assert "avoid_words" not in json.dumps(first_data)
        old_sphere = first_data["last_generation"]["sphere"]
        # Exercise preservation of all repeat parameters and history as well.
        first_data["last_generation"].update(
            subsphere="friends", style="custom", visual_mode="photo",
            custom_style_description="warm table scene",
        )
        await flow.state.update_data(last_generation=first_data["last_generation"])
        current = initial
        if change == "updated":
            current = {
                "current_focus": "Новый замысел" if language == "ru" else "A new direction",
                "tone_preference": "quiet_encouraging",
                "avoid_topics": ["новая тема" if language == "ru" else "new topic"],
                "avoid_words": ["поспеши" if language == "ru" else "hurry"],
            }
        elif change == "removed":
            current = {}
        await db.update_user_profile_preferences(USER_ID, current)
        await generation.again_affirmation(Callback("again:yes"), flow.state)
        assert len(flow.requests) == 2
        second = user_prompt(flow)
        if current:
            assert build_profile_text_guidance(preferences=current, language=language) in second
        else:
            assert "Profile preference guidance:" not in second
        if change != "unchanged":
            assert initial["current_focus"].strip() not in second
            assert "avoid_words: " + ", ".join(initial["avoid_words"]) not in second
        data = await flow.state.get_data()
        last = data["last_generation"]
        assert last["use_profile_preferences"] is True  # origin survives even when preferences were removed
        assert last["sphere"] == old_sphere
        assert last["subsphere"] == "friends"
        assert last["style"] == "custom"
        assert last["visual_mode"] == "photo"
        assert last["custom_style_description"] == "warm table scene"
        assert last["theme_text"] is None
        assert len(data["recent_generation_history"]) == 2
        assert flow.image_calls[1]["recent_scene_presets"] == ["test-scene"]
        assert flow.image_calls[1]["recent_archetypes"] == ["test-archetype"]
        assert len(flow.history) == 2
        assert all(item["request_type"] == "profile_preferences" for item in flow.history)
        assert all(item["visual_motifs"]["profile_text_guidance"]["profile_used"] for item in flow.history)
        if current:
            assert current["current_focus"] not in json.dumps(data, ensure_ascii=False)

    asyncio.run(run())


@pytest.mark.parametrize("new_flow", ["command", "result_button", "inline_command"])
def test_new_flow_and_ordinary_more_do_not_apply_profile(flow, monkeypatch, new_flow):
    async def unexpected_preferences(_uid):
        pytest.fail("ordinary generation must not fetch Profile Preferences")

    async def run():
        await save_preferences(preferences("en"), "en")
        await generation._start_profile_generation(Message(), flow.state, user_id=USER_ID)
        monkeypatch.setattr(generation, "get_user_profile_preferences", unexpected_preferences)
        if new_flow == "command":
            await generation.cmd_new(Message(), flow.state)
        elif new_flow == "result_button":
            await generation.new_request_from_result(Callback("new:yes"), flow.state)
        else:
            await generation.cb_new_affirmation(Callback("cmd:new"), flow.state)
        assert (await flow.state.get_data()).get("use_profile_preferences") is None
        await flow.state.update_data(sphere="relationships", subsphere="partner", style="nature", visual_mode="illustration")
        await generation._run_generation(Message(), flow.state, theme_text="An ordinary theme")
        await generation.again_affirmation(Callback("again:yes"), flow.state)
        assert len(flow.requests) == 3
        for index in (1, 2):
            assert "Profile preference guidance:" not in user_prompt(flow, index)
            assert "An ordinary theme" in user_prompt(flow, index)
        assert (await flow.state.get_data())["last_generation"]["use_profile_preferences"] is False

    asyncio.run(run())


@pytest.mark.parametrize("failure", ["text", "image", "delivery", "task_cancel"])
def test_failed_profile_more_keeps_last_success_and_profile_retry(flow, failure):
    async def run():
        await save_preferences(preferences("en"), "en")
        await generation._start_profile_generation(Message(), flow.state, user_id=USER_ID)
        last_success = copy.deepcopy((await flow.state.get_data())["last_generation"])
        callback = Callback("again:yes")
        if failure == "text":
            flow.transport_error = RuntimeError("synthetic provider failure")
        elif failure == "task_cancel":
            flow.transport_error = asyncio.CancelledError()
        elif failure == "image":
            flow.image_error = RuntimeError("synthetic image failure")
        else:
            callback.message.fail_delivery = True
        if failure in ("delivery", "task_cancel"):
            expected = asyncio.CancelledError if failure == "task_cancel" else RuntimeError
            with pytest.raises(expected):
                await generation.again_affirmation(callback, flow.state)
        else:
            await generation.again_affirmation(callback, flow.state)
            assert await flow.state.get_state() == GenerationState.choosing_style.state
        data = await flow.state.get_data()
        assert data["last_generation"] == last_success
        assert data["use_profile_preferences"] is True
        assert len(data["recent_generation_history"]) == 1
        assert len(flow.history) == 1
        assert await db.get_generation_usage_today(USER_ID) == 1  # failed reservation released
        flow.transport_error = flow.image_error = None
        await db.update_user_profile_preferences(USER_ID, {"current_focus": "Fresh retry context", "avoid_words": ["rush"]})
        await generation._run_generation(Message(), flow.state, theme_text="stale previous theme")
        assert "Fresh retry context" in user_prompt(flow)
        assert "avoid_words: rush" in user_prompt(flow)
        assert "stale previous theme" not in user_prompt(flow)
        assert len(flow.history) == 2
        assert await db.get_generation_usage_today(USER_ID) == 2

    asyncio.run(run())


def test_cancel_after_profile_failure_clears_origin_and_previous_more_context(flow):
    async def run():
        await save_preferences(preferences("ru"))
        await generation._start_profile_generation(Message(), flow.state, user_id=USER_ID)
        flow.transport_error = RuntimeError("synthetic failure")
        await generation.again_affirmation(Callback("again:yes"), flow.state)
        await start.cmd_cancel(Message(), flow.state)
        assert await flow.state.get_data() == {}
        assert await flow.state.get_state() is None
        await generation.again_affirmation(Callback("again:yes"), flow.state)
        assert len(flow.requests) == 2  # no extra request from stale More
        flow.transport_error = None
        await generation.cmd_new(Message(), flow.state)
        await flow.state.update_data(sphere="inner_peace", style="nature")
        await generation._run_generation(Message(), flow.state, theme_text="Обычный настрой")
        assert "Profile preference guidance:" not in user_prompt(flow)

    asyncio.run(run())


@pytest.mark.parametrize("language", ["ru", "en"])
def test_oversize_exclusions_are_reported_without_sending_partial_provider_request(flow, language):
    async def run():
        await save_preferences({"avoid_topics": ["topic " * 1000], "avoid_words": ["important-tail"]}, language)
        message = Message()
        await generation._start_profile_generation(message, flow.state, user_id=USER_ID)
        assert flow.requests == []
        assert flow.image_calls == []
        assert "Сократи" in message.answers[-1] if language == "ru" else "Shorten" in message.answers[-1]
        data = await flow.state.get_data()
        assert data["use_profile_preferences"] is True
        assert "last_generation" not in data
        assert await db.get_generation_usage_today(USER_ID) == 0
        await db.update_user_profile_preferences(USER_ID, {"avoid_words": ["important-tail"]})
        await generation._run_generation(message, flow.state, theme_text=None)
        assert "avoid_words: important-tail" in user_prompt(flow)

    asyncio.run(run())


@pytest.mark.parametrize("malformed", [None, [], 7, "bad preferences", {
    "current_focus": {"bad": "focus"}, "life_areas": 42,
    "tone_preference": False, "support_style": ["wrong type"],
    "avoid_topics": {"bad": "topic"}, "avoid_words": [None, 5, {}, " must ", "MUST"],
}])
def test_malformed_profile_input_cannot_crash_generation(flow, monkeypatch, malformed):
    async def get_preferences(_uid):
        return malformed

    monkeypatch.setattr(generation, "get_user_profile_preferences", get_preferences)

    async def run():
        await save_preferences({}, "en")
        await generation._start_profile_generation(Message(), flow.state, user_id=USER_ID)
        assert len(flow.requests) == 1
        assert len(flow.history) == 1
        assert "{'bad':" not in user_prompt(flow)
        if isinstance(malformed, dict):
            assert "avoid_words: must" in user_prompt(flow)
            assert "MUST" not in user_prompt(flow)

    asyncio.run(run())


@pytest.mark.parametrize("language", ["ru", "en"])
def test_provider_preserves_both_large_exclusion_lists_intact_before_optional_context(flow, language):
    topics = [f"запретная тема {i}" if language == "ru" else f"avoided topic {i}" for i in range(25)]
    words = [f"слово{i}" if language == "ru" else f"word{i}" for i in range(25)]
    prefs = {
        "avoid_topics": topics, "avoid_words": words,
        "current_focus": "focus " * 3000, "life_areas": ["area " * 300],
        "tone_preference": "tone " * 1000, "support_style": "support " * 1000,
        "text_length_preference": "short " * 1000,
    }

    asyncio.run(provider.generate_affirmations(
        sphere="money", language=language, gender="female", profile_preferences=prefs,
        user_text="theme " * 3000, focus="focus " * 3000, micro_theme="step " * 3000,
        sphere_label="label " * 3000, gender_hint="female " * 3000,
        text_plan_guidance="planner context " * 3000,
    ))
    prompt = user_prompt(flow)
    assert "avoid_topics: " + ", ".join(topics) in prompt
    assert "avoid_words: " + ", ".join(words) in prompt
    assert build_profile_text_guidance(preferences=prefs, language=language) in prompt
    assert sum(len(message["content"]) for message in flow.requests[0]["messages"]) <= provider._PROFILE_PROMPT_MAX_CHARS


@pytest.mark.parametrize("target,source,localized", [
    ("en", "Хочу спокойно обсуждать оплату своей работы", "Discussing fair pay for my work calmly"),
    ("ru", "I want to enjoy quiet evenings without checking work messages", "Спокойные вечера без проверки рабочих сообщений"),
])
@pytest.mark.parametrize("origin", ["profile", "ordinary"])
def test_cross_language_final_card_preserves_meaning_source_and_deterministic_step(flow, target, source, localized, origin):
    phrases = ["I value my own pace", "My time matters", "I can choose a pause", "My needs deserve attention"] if target == "en" else [
        "Я берегу свой ритм", "Моё время имеет значение", "Мне доступна спокойная пауза", "Я замечаю свои потребности",
    ]
    flow.response_content = json.dumps({"focus": localized, "affirmations": phrases})

    async def run():
        prefs = {"current_focus": source, "tone_preference": "calm_no_pathos", "avoid_words": ["rush"]}
        await save_preferences(prefs, target)
        before = await db._fetchone("SELECT profile_preferences_json FROM users WHERE user_id = ?", (USER_ID,))
        message = Message()
        if origin == "profile":
            await generation._start_profile_generation(message, flow.state, user_id=USER_ID)
        else:
            await flow.state.update_data(sphere="career", style="auto", visual_mode="illustration")
            await generation._run_generation(message, flow.state, theme_text=source)
        assert len(message.photos) == 1
        caption = message.photos[0]["caption"]
        assert ("Focus of the day: " if target == "en" else "Фокус дня: ") + localized in caption
        assert source not in caption
        assert ("your daily focus" if target == "en" else "твой настрой на сегодня") in caption
        assert ("Gentle step of the day:" if target == "en" else "Мягкий шаг дня:") in caption
        assert all(f"• {phrase}" in caption for phrase in phrases)
        last = (await flow.state.get_data())["last_generation"]
        focus = get_focus_for_date(USER_ID, last["sphere"], generation.dt.datetime.now().date())
        assert focus[f"micro_step_{target}"] in caption
        assert flow.history[-1]["focus_title"] == localized
        assert len(flow.requests) == 1
        assert source in user_prompt(flow)
        assert "Language: English." in user_prompt(flow) if target == "en" else "Язык: русский." in user_prompt(flow)
        assert flow.image_calls[0]["user_text"] == source  # image input is unchanged
        after = await db._fetchone("SELECT profile_preferences_json FROM users WHERE user_id = ?", (USER_ID,))
        assert before[0] == after[0]
        assert (await db.get_user_profile_preferences(USER_ID))["current_focus"] == source

    asyncio.run(run())


@pytest.mark.parametrize("initial,target", [("ru", "en"), ("en", "ru")])
@pytest.mark.parametrize("switch", ["profile", "global"])
def test_profile_more_after_language_change_keeps_origin_and_reloads_preferences(flow, initial, target, switch):
    async def run():
        original = {"current_focus": "Поддерживать связь с друзьями" if initial == "ru" else "Keeping in touch with friends", "avoid_words": ["rush"]}
        await save_preferences(original, initial)
        await generation._start_profile_generation(Message(), flow.state, user_id=USER_ID)
        last = copy.deepcopy((await flow.state.get_data())["last_generation"])
        await start.profile_callback(Callback("profile:open"), flow.state)
        if switch == "profile":
            await start.profile_edit_language(Callback("profile_edit:language"), flow.state)
            await start.profile_set_language(Callback(f"profile_lang:{target}"), flow.state)
        else:
            await start.cmd_language_callback(Callback(f"ui_lang:{target}"), flow.state)
        assert (await flow.state.get_data())["last_generation"] == last
        assert await flow.state.get_state() is None
        assert await db.get_user_profile_preferences(USER_ID) == original
        updated = {"current_focus": "Находить время для важных разговоров" if initial == "ru" else "Making time for meaningful conversations", "avoid_words": ["rush"]}
        await db.update_user_profile_preferences(USER_ID, updated)
        localized = "Making time for meaningful conversations" if target == "en" else "Находить время для важных разговоров"
        phrases = ["My conversations matter"] * 4 if target == "en" else ["Мои разговоры имеют значение"] * 4
        flow.response_content = json.dumps({"focus": localized, "affirmations": phrases})
        callback = Callback("again:yes")
        await generation.again_affirmation(callback, flow.state)
        assert len(flow.requests) == 2
        assert updated["current_focus"] in user_prompt(flow)
        assert original["current_focus"] not in user_prompt(flow)
        caption = callback.message.photos[0]["caption"]
        assert ("Focus of the day: " if target == "en" else "Фокус дня: ") + localized in caption
        assert "Language: English." in user_prompt(flow) if target == "en" else "Язык: русский." in user_prompt(flow)
        assert (await flow.state.get_data())["last_generation"]["use_profile_preferences"] is True
        assert await db.get_user_profile_preferences(USER_ID) == updated

    asyncio.run(run())


@pytest.mark.parametrize("target,source", [("en", "Бережно отдыхать"), ("ru", "Rest gently")])
@pytest.mark.parametrize("response", ["broken JSON", "wrong_focus_language", "wrong_affirmation_language", "extra_step"])
def test_generated_card_validation_and_extra_keys_keep_preferences(flow, target, source, response):
    focus = "Rest gently" if target == "en" else "Бережно отдыхать"
    phrases = ["My rest matters"] * 4 if target == "en" else ["Мой отдых важен"] * 4
    payload = {"focus": focus, "affirmations": phrases}
    if response == "wrong_focus_language":
        payload["focus"] = source
    elif response == "wrong_affirmation_language":
        payload["affirmations"][0] = source
    elif response == "extra_step":
        payload["gentle_step"] = "not allowed"
    flow.response_content = "broken JSON" if response == "broken JSON" else json.dumps(payload)

    async def run():
        await save_preferences({"current_focus": source}, target)
        message = Message()
        await generation._start_profile_generation(message, flow.state, user_id=USER_ID)
        assert len(flow.requests) == 1
        if response == "extra_step":
            assert len(message.photos) == len(flow.image_calls) == len(flow.history) == 1
            caption = message.photos[0]["caption"]
            assert "not allowed" not in caption
            last = (await flow.state.get_data())["last_generation"]
            focus_data = get_focus_for_date(USER_ID, last["sphere"], generation.dt.datetime.now().date())
            assert focus_data[f"micro_step_{target}"] in caption
            assert last["language"] == target
            assert await db.get_generation_usage_today(USER_ID) == 1
            assert (await db.get_user_profile_preferences(USER_ID))["current_focus"] == source
            return
        assert not message.photos and not flow.image_calls and not flow.history
        assert source not in "\n".join(message.answers)
        assert "Could not create" in message.answers[-1] if target == "en" else "Не удалось собрать" in message.answers[-1]
        assert (await db.get_user_profile_preferences(USER_ID))["current_focus"] == source
        assert await db.get_generation_usage_today(USER_ID) == 0

    asyncio.run(run())


@pytest.mark.parametrize("initial,target", [("ru", "en"), ("en", "ru")])
@pytest.mark.parametrize("phase", ["text", "image", "text_error", "image_error"])
def test_language_switch_during_provider_call_discards_old_card_and_preserves_new_flow(flow, monkeypatch, initial, target, phase):
    async def run():
        prefs = {"current_focus": "Бережный отдых" if initial == "ru" else "Gentle rest"}
        await save_preferences(prefs, initial)
        await generation._start_profile_generation(Message(), flow.state, user_id=USER_ID)
        last_success = copy.deepcopy((await flow.state.get_data())["last_generation"])
        name = "generate_card_text" if phase.startswith("text") else "generate_image"
        original_call = getattr(generation, name)
        if phase == "text_error":
            flow.transport_error = RuntimeError("synthetic provider failure")
        elif phase == "image_error":
            flow.image_error = RuntimeError("synthetic image failure")

        async def switch_while_awaiting_provider(**kwargs):
            try:
                return await original_call(**kwargs)
            finally:
                await start.cmd_language_callback(Callback(f"ui_lang:{target}"), flow.state)
                # A subsequent user action must not be overwritten by the old run.
                await flow.state.set_state(ProfileEditState.editing_current_focus)
                await flow.state.update_data(pending_value="new flow draft")

        monkeypatch.setattr(generation, name, switch_while_awaiting_provider)
        callback = Callback("again:yes")
        await generation.again_affirmation(callback, flow.state)
        assert callback.message.photos == []
        assert "language changed" in callback.message.answers[-1] if target == "en" else "Язык изменился" in callback.message.answers[-1]
        assert await flow.state.get_state() == ProfileEditState.editing_current_focus.state
        data = await flow.state.get_data()
        assert data["pending_value"] == "new flow draft"
        assert data["last_generation"] == last_success
        assert len(flow.history) == len(data["recent_generation_history"]) == 1
        assert await db.get_generation_usage_today(USER_ID) == 1
        assert await db.get_user_profile_preferences(USER_ID) == prefs
        assert len(flow.requests) == 2  # one call per attempt, no automatic retry
        assert len(flow.image_calls) == (2 if phase.startswith("image") else 1)

    asyncio.run(run())


@pytest.mark.parametrize("card_language,ui", [("ru", "en"), ("en", "ru")])
@pytest.mark.parametrize("switch", ["command", "profile"])
def test_interactive_tts_uses_completed_card_language_after_interface_switch(flow, monkeypatch, card_language, ui, switch):
    calls = []

    async def synthesize(affirmations, **kwargs):
        calls.append((affirmations, kwargs))
        return "mocked_audio.ogg"

    monkeypatch.setattr(generation, "synthesize_affirmations_with_pauses", synthesize)

    async def run():
        prefs = {"current_focus": "Спокойный рост" if card_language == "ru" else "Gentle growth"}
        await save_preferences(prefs, card_language)
        await generation._start_profile_generation(Message(), flow.state, user_id=USER_ID)
        last = copy.deepcopy((await flow.state.get_data())["last_generation"])
        assert last["language"] == card_language
        handler = start.cmd_language_callback if switch == "command" else start.profile_set_language
        prefix = "ui_lang" if switch == "command" else "profile_lang"
        await handler(Callback(f"{prefix}:{ui}"), flow.state)
        callback = Callback("tts:yes")
        await generation.tts_affirmations(callback, flow.state)
        assert (await db.get_user(USER_ID))["language"] == ui
        assert (await flow.state.get_data())["last_generation"] == last
        assert len(flow.requests) == 1
        assert await db.get_user_profile_preferences(USER_ID) == prefs
        assert len(calls) == len(callback.message.voices) == (1 if card_language == "ru" else 0)
        if calls:
            assert calls[0][0] == last["affirmations"]
        else:
            assert "audio" in callback.message.answers[-1] or "озвучка" in callback.message.answers[-1].lower()

    asyncio.run(run())


@pytest.mark.parametrize("ui", ["ru", "en"])
def test_legacy_card_without_language_does_not_guess_audio_language_from_ui(flow, monkeypatch, ui):
    async def forbidden(*args, **kwargs):
        raise AssertionError("Unknown card language must not cause a paid TTS request")

    monkeypatch.setattr(generation, "synthesize_affirmations_with_pauses", forbidden)

    async def run():
        await save_preferences({}, ui)
        await flow.state.update_data(last_generation={"affirmations": ["Legacy text"] * 4})
        callback = Callback("tts:yes")
        await generation.tts_affirmations(callback, flow.state)
        assert not callback.message.voices and not flow.requests
        assert "Create a new" in callback.message.answers[-1] if ui == "en" else "Создай новый" in callback.message.answers[-1]

    asyncio.run(run())
