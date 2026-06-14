import asyncio
from types import SimpleNamespace

from handlers import generation
from services.generation_context import build_generation_context_snapshot


class _FakeState:
    def __init__(self, data=None):
        self.data = dict(data or {})
        self.state = None
        self.cleared = False

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def set_state(self, state):
        self.state = state

    async def clear(self):
        self.data = {}
        self.state = None
        self.cleared = True


class _FakeMessage:
    def __init__(self, user_id=123, *, fail_edit_text=False, fail_edit_reply_markup=False):
        self.from_user = SimpleNamespace(id=user_id)
        self.answers = []
        self.photos = []
        self.edits = []
        self.reply_markup_clears = []
        self.fail_edit_text = fail_edit_text
        self.fail_edit_reply_markup = fail_edit_reply_markup

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))

    async def answer_photo(self, photo, caption=None, reply_markup=None):
        self.photos.append((photo, caption, reply_markup))

    async def edit_text(self, text, reply_markup=None):
        if self.fail_edit_text:
            raise RuntimeError("edit_text failed")
        self.edits.append((text, reply_markup))

    async def edit_reply_markup(self, reply_markup=None):
        if self.fail_edit_reply_markup:
            raise RuntimeError("edit_reply_markup failed")
        self.reply_markup_clears.append(reply_markup)


class _FakeCallback:
    def __init__(self, user_id=123, *, fail_edit_text=False, fail_edit_reply_markup=False):
        self.from_user = SimpleNamespace(id=user_id)
        self.message = _FakeMessage(
            user_id=user_id,
            fail_edit_text=fail_edit_text,
            fail_edit_reply_markup=fail_edit_reply_markup,
        )
        self.answered = False

    async def answer(self):
        self.answered = True


def test_generation_context_uses_explicit_theme_and_preserves_separate_style_notes():
    snapshot = build_generation_context_snapshot(
        {
            "sphere": "relationships",
            "subsphere": "partner",
            "theme_text": "stale theme from fsm",
            "style": "custom",
            "custom_style_description": "soft coastal editorial photo",
            "visual_mode": "photo",
        },
        theme_text="explicit theme",
    )

    assert snapshot.theme_text == "explicit theme"
    assert snapshot.custom_style_description == "soft coastal editorial photo"
    assert snapshot.subsphere == "partner"


def test_generation_context_preserves_current_fallbacks_for_missing_values():
    snapshot = build_generation_context_snapshot({}, theme_text=None)

    assert snapshot.sphere is None
    assert snapshot.subsphere is None
    assert snapshot.style == "nature"
    assert snapshot.visual_mode == "illustration"
    assert snapshot.custom_style_description is None
    assert snapshot.last_stt_meta is None
    assert snapshot.recent_generation_history == []


def test_generation_context_copies_recent_generation_history():
    history = [{"selected_style": "sea_coast_photo"}]

    snapshot = build_generation_context_snapshot(
        {"recent_generation_history": history},
        theme_text=None,
    )
    history.append({"selected_style": "light_interior_photo"})

    assert snapshot.recent_generation_history == [{"selected_style": "sea_coast_photo"}]


def test_choose_style_clears_custom_style_description_without_overwriting_theme(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "en"}

    captured = {}

    async def _fake_run(message, state, *, theme_text, user_telegram_id=None):
        captured["theme_text"] = theme_text
        captured["data"] = await state.get_data()
        captured["user_telegram_id"] = user_telegram_id

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(generation, "_run_generation", _fake_run)

    state = _FakeState(
        {
            "sphere": "inner_peace",
            "theme_text": "Dignity and self-trust",
            "custom_style_description": "old custom style",
            "visual_mode": "photo",
        }
    )
    callback = _FakeCallback(user_id=77)
    callback.data = "style:sea_coast_photo"

    asyncio.run(generation.choose_style(callback, state))

    assert captured["theme_text"] == "Dignity and self-trust"
    assert captured["user_telegram_id"] == 77
    assert captured["data"]["style"] == "sea_coast_photo"
    assert captured["data"]["custom_style_description"] is None
    assert captured["data"]["theme_text"] == "Dignity and self-trust"
    assert callback.message.edits[0] == (
        f"✅ Style selected: {generation._style_confirmation_label('sea_coast_photo', 'en')}",
        None,
    )
    assert callback.message.answers[0][0] == "🌿 Creating your daily focus..."


def test_cancel_custom_style_clears_style_notes_and_preserves_generation_context(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "en"}

    captured = {}

    async def _fake_run(message, state, *, theme_text, user_telegram_id=None):
        captured["theme_text"] = theme_text
        captured["data"] = await state.get_data()
        captured["user_telegram_id"] = user_telegram_id

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(generation, "_run_generation", _fake_run)

    state = _FakeState(
        {
            "theme_text": "Dignity and self-trust",
            "sphere": "relationships",
            "subsphere": "partner",
            "visual_mode": "photo",
            "style": "custom",
            "custom_style_description": "old custom style",
        }
    )
    cancel_callback = _FakeCallback(user_id=77)
    cancel_callback.data = "style:cancel"

    asyncio.run(generation.cancel_custom_style(cancel_callback, state))

    assert state.data["style"] is None
    assert state.data["custom_style_description"] is None
    assert state.data["theme_text"] == "Dignity and self-trust"
    assert state.data["sphere"] == "relationships"
    assert state.data["subsphere"] == "partner"
    assert state.data["visual_mode"] == "photo"
    assert state.state == generation.GenerationState.choosing_style
    assert cancel_callback.message.edits
    assert cancel_callback.answered is True

    style_callback = _FakeCallback(user_id=77)
    style_callback.data = "style:sea_coast_photo"
    asyncio.run(generation.choose_style(style_callback, state))

    assert captured["theme_text"] == "Dignity and self-trust"
    assert captured["user_telegram_id"] == 77
    assert captured["data"]["style"] == "sea_coast_photo"
    assert captured["data"]["custom_style_description"] is None
    assert captured["data"]["visual_mode"] == "photo"


def test_safe_confirm_callback_choice_edits_message_and_clears_markup():
    callback = _FakeCallback()

    asyncio.run(generation.safe_confirm_callback_choice(callback, "✅ Selected"))

    assert callback.message.edits == [("✅ Selected", None)]
    assert callback.message.reply_markup_clears == []
    assert callback.message.answers == []


def test_safe_confirm_callback_choice_falls_back_to_reply_markup_clear():
    callback = _FakeCallback(fail_edit_text=True)

    asyncio.run(generation.safe_confirm_callback_choice(callback, "✅ Selected"))

    assert callback.message.edits == []
    assert callback.message.reply_markup_clears == [None]
    assert callback.message.answers == [("✅ Selected", None)]


def test_safe_confirm_callback_choice_falls_back_to_answer_when_edit_fails():
    callback = _FakeCallback(fail_edit_text=True, fail_edit_reply_markup=True)

    asyncio.run(generation.safe_confirm_callback_choice(callback, "✅ Selected"))

    assert callback.message.edits == []
    assert callback.message.reply_markup_clears == []
    assert callback.message.answers == [("✅ Selected", None)]


def test_choose_sphere_confirms_selection_and_shows_visual_menu(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru"}

    monkeypatch.setattr(generation, "get_user", _fake_get_user)

    state = _FakeState()
    callback = _FakeCallback(user_id=55)
    callback.data = "sphere:home_support"

    asyncio.run(generation.choose_sphere(callback, state))

    assert state.data["sphere"] == "home_support"
    assert state.state == generation.GenerationState.choosing_visual_mode
    assert callback.message.edits[0] == ("✅ Сфера выбрана: 🏡 Дом и опора", None)
    assert callback.message.answers
    assert "визуал" in callback.message.answers[0][0].lower()
    assert callback.answered is True


def test_choose_visual_mode_confirms_selection_and_shows_style_menu(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru"}

    monkeypatch.setattr(generation, "get_user", _fake_get_user)

    state = _FakeState({"sphere": "inner_peace"})
    callback = _FakeCallback(user_id=66)
    callback.data = "visual:photo"

    asyncio.run(generation.choose_visual_mode(callback, state))

    assert state.data["visual_mode"] == "photo"
    assert state.state == generation.GenerationState.choosing_style
    assert callback.message.edits[0] == ("✅ Визуал выбран: 📷 Фото-стиль", None)
    assert callback.message.answers
    assert "стиль изображения" in callback.message.answers[0][0].lower()
    assert callback.answered is True


def test_cmd_new_stops_early_when_daily_limit_is_reached(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru"}

    async def _fake_can_start(_uid, _limit):
        return False, 3

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(generation, "can_start_interactive_generation", _fake_can_start)
    monkeypatch.setattr(generation, "log_rate_limited", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "main_reply_keyboard", lambda language: f"main:{language}")
    monkeypatch.setattr(
        generation,
        "get_settings",
        lambda: SimpleNamespace(disable_daily_generation_limit=False, generation_daily_limit=3),
    )

    state = _FakeState({"theme_text": "stale"})
    message = _FakeMessage(user_id=101)

    asyncio.run(generation.cmd_new(message, state))

    assert state.cleared is True
    assert state.state is None
    assert len(message.answers) == 1
    assert "дневной лимит" in message.answers[0][0].lower()
    assert message.answers[0][1] == "main:ru"


def test_choose_style_clears_inline_keyboard_and_returns_to_main_menu_when_limit_is_reached(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru"}

    async def _fake_can_start(_uid, _limit):
        return False, 5

    async def _unexpected_run(*_args, **_kwargs):
        raise AssertionError("_run_generation should not be called when the limit is reached")

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(generation, "can_start_interactive_generation", _fake_can_start)
    monkeypatch.setattr(generation, "log_rate_limited", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "main_reply_keyboard", lambda language: f"main:{language}")
    monkeypatch.setattr(generation, "_run_generation", _unexpected_run)
    monkeypatch.setattr(
        generation,
        "get_settings",
        lambda: SimpleNamespace(disable_daily_generation_limit=False, generation_daily_limit=5),
    )

    state = _FakeState({"sphere": "inner_peace", "visual_mode": "photo"})
    callback = _FakeCallback(user_id=202, fail_edit_text=True)
    callback.data = "style:sea_coast_photo"

    asyncio.run(generation.choose_style(callback, state))

    assert callback.answered is True
    assert state.cleared is True
    assert callback.message.reply_markup_clears == [None]
    assert len(callback.message.answers) == 1
    assert "дневной лимит" in callback.message.answers[0][0].lower()
    assert callback.message.answers[0][1] == "main:ru"


def test_start_profile_generation_reads_preferences_and_sets_profile_request_context(monkeypatch):
    captured = {}

    async def _fake_get_user(_uid):
        return {"language": "ru", "gender": "female"}

    async def _fake_get_preferences(_uid):
        return {
            "current_focus": "спокойно разобраться с деньгами",
            "life_areas": ["деньги", "работа"],
            "tone_preference": "calm_no_pathos",
        }

    async def _fake_preflight(message, state, theme_text, language, *, user_telegram_id=None):
        captured["theme_text"] = theme_text
        captured["language"] = language
        captured["user_telegram_id"] = user_telegram_id
        captured["state_data"] = await state.get_data()

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(generation, "get_user_profile_preferences", _fake_get_preferences)
    monkeypatch.setattr(generation, "_start_generation_after_preflight", _fake_preflight)
    monkeypatch.setattr(generation, "main_reply_keyboard", lambda language: f"main:{language}")

    state = _FakeState()
    message = _FakeMessage(user_id=501)

    asyncio.run(generation._start_profile_generation(message, state, user_id=501))

    assert captured["theme_text"] == "спокойно разобраться с деньгами"
    assert captured["language"] == "ru"
    assert captured["user_telegram_id"] == 501
    assert captured["state_data"]["generation_request_type"] == "profile_preferences"
    assert captured["state_data"]["use_profile_preferences"] is True
    assert captured["state_data"]["style"] == "auto"
    assert captured["state_data"]["visual_mode"] == "illustration"
    assert captured["state_data"]["sphere"] == "money"
    assert message.answers[0][1] == "main:ru"


def test_start_profile_generation_with_empty_preferences_falls_back_safely(monkeypatch):
    captured = {}

    async def _fake_get_user(_uid):
        return {"language": "ru", "gender": "female"}

    async def _fake_get_preferences(_uid):
        return {}

    async def _fake_preflight(message, state, theme_text, language, *, user_telegram_id=None):
        captured["theme_text"] = theme_text
        captured["state_data"] = await state.get_data()

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(generation, "get_user_profile_preferences", _fake_get_preferences)
    monkeypatch.setattr(generation, "_start_generation_after_preflight", _fake_preflight)
    monkeypatch.setattr(generation, "main_reply_keyboard", lambda language: f"main:{language}")

    state = _FakeState()
    message = _FakeMessage(user_id=502)

    asyncio.run(generation._start_profile_generation(message, state, user_id=502))

    assert captured["theme_text"] is None
    assert captured["state_data"]["sphere"] == "inner_peace"
    assert captured["state_data"]["generation_request_type"] == "profile_preferences"


def test_new_request_from_result_clears_inline_keyboard_and_returns_to_main_menu_when_limit_is_reached(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru"}

    async def _fake_can_start(_uid, _limit):
        return False, 2

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(generation, "can_start_interactive_generation", _fake_can_start)
    monkeypatch.setattr(generation, "log_rate_limited", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "main_reply_keyboard", lambda language: f"main:{language}")
    monkeypatch.setattr(
        generation,
        "get_settings",
        lambda: SimpleNamespace(disable_daily_generation_limit=False, generation_daily_limit=2),
    )

    state = _FakeState()
    callback = _FakeCallback(user_id=303)

    asyncio.run(generation.new_request_from_result(callback, state))

    assert callback.answered is True
    assert state.cleared is True
    assert callback.message.reply_markup_clears == [None]
    assert len(callback.message.answers) == 1
    assert "дневной лимит" in callback.message.answers[0][0].lower()
    assert callback.message.answers[0][1] == "main:ru"


def test_run_generation_passes_theme_and_custom_style_separately_and_stores_last_generation(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "en", "gender": "female"}

    async def _fake_generate_affirmations(**kwargs):
        captured["text_kwargs"] = kwargs
        return ["I trust myself", "I move gently", "I stay present", "I choose clarity"]

    async def _fake_build_enriched_image_prompt(**kwargs):
        captured["prompt_kwargs"] = kwargs
        return "prompt", "template"

    async def _fake_generate_image(**kwargs):
        captured["image_kwargs"] = kwargs
        return "fake_image.png"

    captured = {}
    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(
        generation,
        "get_settings",
        lambda: SimpleNamespace(
            disable_daily_generation_limit=True,
            generation_daily_limit=0,
            llm_image_prompt_enabled=False,
            show_image_debug=False,
            image_model="image-model",
            image_size="1024x1024",
            text_planner_shadow_enabled=False,
            text_planner_controlled_enabled=False,
            scene_planner_shadow_enabled=False,
            scene_planner_image_prompt_enabled=False,
        ),
    )
    monkeypatch.setattr(generation, "generate_affirmations", _fake_generate_affirmations)
    monkeypatch.setattr(generation, "build_enriched_image_prompt", _fake_build_enriched_image_prompt)
    monkeypatch.setattr(generation, "generate_image", _fake_generate_image)
    monkeypatch.setattr(generation, "record_interactive_generation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "log_generation_ok", lambda *_args, **_kwargs: None)

    state = _FakeState(
        {
            "sphere": "relationships",
            "subsphere": "partner",
            "style": "custom",
            "visual_mode": "photo",
            "custom_style_description": "soft coastal editorial photo",
            "recent_generation_history": [{"selected_style": "sea_coast_photo"}],
        }
    )
    message = _FakeMessage(user_id=77)

    asyncio.run(
        generation._run_generation(
            message,
            state,
            theme_text="Dignity and self-trust",
            user_telegram_id=77,
        )
    )

    assert captured["text_kwargs"]["user_text"] == "Dignity and self-trust"
    assert captured["prompt_kwargs"]["user_text"] == "Dignity and self-trust"
    assert captured["prompt_kwargs"]["custom_style_description"] == "soft coastal editorial photo"
    assert captured["image_kwargs"]["user_text"] == "Dignity and self-trust"
    assert captured["image_kwargs"]["custom_style_description"] == "soft coastal editorial photo"
    assert state.data["last_generation"]["theme_text"] == "Dignity and self-trust"
    assert state.data["last_generation"]["custom_style_description"] == "soft coastal editorial photo"
    assert state.data["last_generation"]["style"] == "custom"
    assert state.data["last_generation"]["visual_mode"] == "photo"
    assert state.data["last_generation"]["sphere"] == "relationships"
    assert state.data["last_generation"]["subsphere"] == "partner"
    assert state.data["recent_generation_history"]


def test_run_generation_symbolic_bypasses_scene_planner_and_prompt_override(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "en", "gender": "female"}

    async def _fake_generate_affirmations(**_kwargs):
        return ["I trust my inner rhythm", "I move with calm clarity", "I stay centered", "I choose quiet balance"]

    async def _fake_scene_plan_shadow(**_kwargs):
        return {"scene_plan": {"scene_type": "abstract_light"}}

    async def _fake_generate_image(**kwargs):
        captured["image_kwargs"] = kwargs
        return "fake_image.png"

    captured = {}
    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(
        generation,
        "get_settings",
        lambda: SimpleNamespace(
            disable_daily_generation_limit=True,
            generation_daily_limit=0,
            llm_image_prompt_enabled=True,
            show_image_debug=False,
            image_model="image-model",
            image_size="1024x1024",
            text_planner_shadow_enabled=False,
            text_planner_controlled_enabled=False,
            scene_planner_shadow_enabled=False,
            scene_planner_image_prompt_enabled=True,
        ),
    )
    monkeypatch.setattr(generation, "generate_affirmations", _fake_generate_affirmations)
    monkeypatch.setattr(generation, "build_scene_plan_shadow_best_effort", _fake_scene_plan_shadow)
    monkeypatch.setattr(
        generation,
        "build_controlled_scene_prompt",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("symbolic mode must not use scene planner prompt")),
    )
    monkeypatch.setattr(
        generation,
        "build_enriched_image_prompt",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("symbolic mode must not use enriched prompt override")),
    )
    monkeypatch.setattr(generation, "generate_image", _fake_generate_image)
    monkeypatch.setattr(generation, "record_interactive_generation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "log_generation_ok", lambda *_args, **_kwargs: None)

    state = _FakeState(
        {
            "sphere": "spirituality",
            "subsphere": None,
            "style": "mandala_harmony",
            "visual_mode": "symbolic",
            "recent_generation_history": [],
        }
    )
    message = _FakeMessage(user_id=108)

    asyncio.run(
        generation._run_generation(
            message,
            state,
            theme_text="quiet lake by the window",
            user_telegram_id=108,
        )
    )

    assert captured["image_kwargs"]["visual_mode"] == "symbolic"
    assert captured["image_kwargs"]["resolved_style_override"] == "mandala_harmony"
    assert captured["image_kwargs"]["prompt_override"] is None
    assert captured["image_kwargs"]["image_prompt_trace"] == "template"


def test_run_generation_passes_text_plan_guidance_when_controlled_enabled(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru", "gender": "female"}

    async def _fake_generate_affirmations(**kwargs):
        captured["text_kwargs"] = kwargs
        return ["I trust myself", "I move gently", "I stay present", "I choose clarity"]

    async def _fake_build_enriched_image_prompt(**kwargs):
        return "prompt", "template"

    async def _fake_generate_image(**kwargs):
        return "fake_image.png"

    captured = {}
    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(
        generation,
        "get_settings",
        lambda: SimpleNamespace(
            disable_daily_generation_limit=True,
            generation_daily_limit=0,
            llm_image_prompt_enabled=False,
            show_image_debug=False,
            image_model="image-model",
            image_size="1024x1024",
            text_planner_shadow_enabled=False,
            text_planner_controlled_enabled=True,
            scene_planner_shadow_enabled=False,
            scene_planner_image_prompt_enabled=False,
        ),
    )
    monkeypatch.setattr(generation, "generate_affirmations", _fake_generate_affirmations)
    monkeypatch.setattr(generation, "build_enriched_image_prompt", _fake_build_enriched_image_prompt)
    monkeypatch.setattr(generation, "generate_image", _fake_generate_image)
    monkeypatch.setattr(generation, "record_interactive_generation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "log_generation_ok", lambda *_args, **_kwargs: None)

    state = _FakeState(
        {
            "sphere": "money",
            "subsphere": None,
            "style": "auto",
            "visual_mode": "illustration",
            "recent_generation_history": [],
        }
    )
    message = _FakeMessage(user_id=91)

    asyncio.run(
        generation._run_generation(
            message,
            state,
            theme_text="calm stability",
            user_telegram_id=91,
        )
    )

    guidance = captured["text_kwargs"]["text_plan_guidance"]
    assert guidance is not None
    assert "theme_category: money_stability" in guidance
    assert "avoid: toxic positivity, pressure, productivity framing" in guidance
    assert "Russian grammatical gender: feminine" in guidance
    assert "готова, выбрала, уверена, открыта" in guidance


def test_run_generation_attaches_compact_text_memory_context_metadata_when_enabled(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "en", "gender": "female"}

    async def _fake_generate_affirmations(**kwargs):
        captured["text_kwargs"] = kwargs
        return ["I trust myself", "I move gently", "I stay present", "I choose clarity"]

    async def _fake_build_enriched_image_prompt(**kwargs):
        return "prompt", "template"

    async def _fake_generate_image(**kwargs):
        return "fake_image.png"

    async def _fake_history(**kwargs):
        captured["history_kwargs"] = kwargs

    async def _fake_text_memory_context(*_args, **_kwargs):
        return {
            "limit": 10,
            "overused_text_patterns": ["я выбираю"],
            "overused_soft_action_patterns": ["name_three_things"],
            "recent_focus_titles": ["мягкая опора"],
            "avoid_soft_actions": ["назови три вещи, которые уже помогают"],
        }

    async def _fake_text_memory_context(_uid, limit=10):
        captured["text_memory_limit"] = limit
        return {
            "limit": limit,
            "overused_text_patterns": ["я позволяю", "спокойствие"],
            "recent_focus_titles": ["спокойствие и опора", "деньги и устойчивость"],
            "avoid_soft_actions": ["назови три вещи, которые уже помогают"],
            "avoid_phrases": ["Я позволяю себе паузу без чувства вины."],
            "style_guidance": ["avoid repeating recent affirmation openings"],
        }

    captured = {}
    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(
        generation,
        "get_settings",
        lambda: SimpleNamespace(
            disable_daily_generation_limit=True,
            generation_daily_limit=0,
            llm_image_prompt_enabled=False,
            show_image_debug=False,
            image_model="image-model",
            image_size="1024x1024",
            text_planner_shadow_enabled=False,
            text_planner_controlled_enabled=True,
            text_memory_context_enabled=True,
            scene_planner_shadow_enabled=False,
            scene_planner_image_prompt_enabled=False,
        ),
    )
    monkeypatch.setattr(generation, "generate_affirmations", _fake_generate_affirmations)
    monkeypatch.setattr(generation, "build_enriched_image_prompt", _fake_build_enriched_image_prompt)
    monkeypatch.setattr(generation, "generate_image", _fake_generate_image)
    monkeypatch.setattr(generation, "record_interactive_generation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "log_generation_ok", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "record_generation_history_best_effort", _fake_history)
    monkeypatch.setattr(generation, "get_text_memory_context", _fake_text_memory_context)

    state = _FakeState(
        {
            "sphere": "money",
            "subsphere": None,
            "style": "auto",
            "visual_mode": "illustration",
            "recent_generation_history": [],
        }
    )
    message = _FakeMessage(user_id=92)

    asyncio.run(
        generation._run_generation(
            message,
            state,
            theme_text="calm stability",
            user_telegram_id=92,
        )
    )

    guidance = captured["text_kwargs"]["text_plan_guidance"]
    visual_motifs = captured["history_kwargs"]["visual_motifs"]
    assert captured["text_memory_limit"] == 10
    assert "Text memory / anti-repeat guidance:" in guidance
    assert "overused_text_patterns: я позволяю, спокойствие" in guidance
    assert visual_motifs["text_memory_context"] == {
        "enabled": True,
        "limit": 10,
        "overused_text_patterns": ["я позволяю", "спокойствие"],
        "recent_focus_titles_count": 2,
        "avoid_soft_actions_count": 1,
    }


def test_run_generation_uses_profile_preferences_guidance_and_attaches_profile_metadata(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru", "gender": "female"}

    async def _fake_get_preferences(_uid):
        return {
            "tone_preference": "calm_no_pathos",
            "support_style": "grounding",
            "text_length_preference": "short",
            "current_focus": "спокойно разобраться с деньгами",
            "life_areas": ["деньги", "работа"],
            "avoid_topics": ["конфликт"],
            "avoid_words": ["срочно", "должен"],
        }

    async def _fake_generate_affirmations(**kwargs):
        captured["text_kwargs"] = kwargs
        return ["Я выбираю спокойствие", "Я нахожу опору", "Я дышу свободнее", "Я берегу себя"]

    async def _fake_build_enriched_image_prompt(**kwargs):
        return "prompt", "template"

    async def _fake_generate_image(**kwargs):
        return "fake_image.png"

    async def _fake_history(**kwargs):
        captured["history_kwargs"] = kwargs

    captured = {}
    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(generation, "get_user_profile_preferences", _fake_get_preferences)
    monkeypatch.setattr(
        generation,
        "get_settings",
        lambda: SimpleNamespace(
            disable_daily_generation_limit=True,
            generation_daily_limit=0,
            llm_image_prompt_enabled=False,
            show_image_debug=False,
            image_model="image-model",
            image_size="1024x1024",
            text_planner_shadow_enabled=False,
            text_planner_controlled_enabled=False,
            text_memory_context_enabled=False,
            text_reviewer_shadow_enabled=True,
            orchestrator_shadow_enabled=True,
            scene_planner_shadow_enabled=False,
            scene_planner_image_prompt_enabled=False,
        ),
    )
    monkeypatch.setattr(generation, "generate_affirmations", _fake_generate_affirmations)
    monkeypatch.setattr(generation, "build_enriched_image_prompt", _fake_build_enriched_image_prompt)
    monkeypatch.setattr(generation, "generate_image", _fake_generate_image)
    monkeypatch.setattr(generation, "record_interactive_generation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "log_generation_ok", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "record_generation_history_best_effort", _fake_history)

    state = _FakeState(
        {
            "sphere": "money",
            "subsphere": None,
            "style": "auto",
            "visual_mode": "illustration",
            "recent_generation_history": [],
            "generation_request_type": "profile_preferences",
            "use_profile_preferences": True,
        }
    )
    message = _FakeMessage(user_id=503)

    asyncio.run(
        generation._run_generation(
            message,
            state,
            theme_text=None,
            user_telegram_id=503,
        )
    )

    guidance = captured["text_kwargs"]["text_plan_guidance"]
    visual_motifs = captured["history_kwargs"]["visual_motifs"]
    assert "Profile preference guidance:" in guidance
    assert "preferred_tone: calm_no_pathos" in guidance
    assert "preferred_support_style: grounding" in guidance
    assert "current_focus_context: спокойно разобраться с деньгами" in guidance
    assert "life_areas: деньги, работа" in guidance
    assert "avoid_topics: конфликт" in guidance
    assert "avoid_words: срочно, должен" in guidance
    assert visual_motifs["profile_text_guidance"] == {
        "profile_used": True,
        "profile_preferences_count": 7,
        "profile_current_focus_used": True,
        "profile_avoid_constraints_count": 3,
        "guidance_used": True,
    }
    assert visual_motifs["orchestrator_shadow"]["route"]["profile_preferences"] is True


def test_run_generation_does_not_read_text_memory_or_attach_marker_when_disabled(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "en", "gender": "female"}

    async def _fake_generate_affirmations(**kwargs):
        captured["text_kwargs"] = kwargs
        return ["I trust myself", "I move gently", "I stay present", "I choose clarity"]

    async def _fake_build_enriched_image_prompt(**kwargs):
        return "prompt", "template"

    async def _fake_generate_image(**kwargs):
        return "fake_image.png"

    async def _fake_history(**kwargs):
        captured["history_kwargs"] = kwargs

    async def _unexpected_text_memory(*_args, **_kwargs):
        raise AssertionError("get_text_memory_context should not be called when disabled")

    captured = {}
    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(
        generation,
        "get_settings",
        lambda: SimpleNamespace(
            disable_daily_generation_limit=True,
            generation_daily_limit=0,
            llm_image_prompt_enabled=False,
            show_image_debug=False,
            image_model="image-model",
            image_size="1024x1024",
            text_planner_shadow_enabled=False,
            text_planner_controlled_enabled=True,
            text_memory_context_enabled=False,
            scene_planner_shadow_enabled=False,
            scene_planner_image_prompt_enabled=False,
        ),
    )
    monkeypatch.setattr(generation, "generate_affirmations", _fake_generate_affirmations)
    monkeypatch.setattr(generation, "build_enriched_image_prompt", _fake_build_enriched_image_prompt)
    monkeypatch.setattr(generation, "generate_image", _fake_generate_image)
    monkeypatch.setattr(generation, "record_interactive_generation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "log_generation_ok", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "record_generation_history_best_effort", _fake_history)
    monkeypatch.setattr(generation, "get_text_memory_context", _unexpected_text_memory)

    state = _FakeState(
        {
            "sphere": "money",
            "subsphere": None,
            "style": "auto",
            "visual_mode": "illustration",
            "recent_generation_history": [],
        }
    )
    message = _FakeMessage(user_id=93)

    asyncio.run(
        generation._run_generation(
            message,
            state,
            theme_text="calm stability",
            user_telegram_id=93,
        )
    )

    visual_motifs = captured["history_kwargs"]["visual_motifs"]
    assert "text_memory_context" not in visual_motifs


def test_run_generation_attaches_text_reviewer_shadow_metadata_when_enabled(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru", "gender": "female"}

    async def _fake_generate_affirmations(**kwargs):
        return ["Я открыт новому", "Я выбираю спокойствие", "Я выбираю ясность", "Я нахожу опору"]

    async def _fake_build_enriched_image_prompt(**kwargs):
        return "prompt", "template"

    async def _fake_generate_image(**kwargs):
        return "fake_image.png"

    async def _fake_history(**kwargs):
        captured["history_kwargs"] = kwargs

    async def _fake_text_memory_context(*_args, **_kwargs):
        return {
            "limit": 10,
            "overused_text_patterns": ["я выбираю"],
            "overused_soft_action_patterns": ["name_three_things"],
            "recent_focus_titles": ["мягкая опора"],
            "avoid_soft_actions": ["назови три вещи, которые уже помогают"],
        }

    captured = {}
    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(
        generation,
        "get_settings",
        lambda: SimpleNamespace(
            disable_daily_generation_limit=True,
            generation_daily_limit=0,
            llm_image_prompt_enabled=False,
            show_image_debug=False,
            image_model="image-model",
            image_size="1024x1024",
            text_planner_shadow_enabled=False,
            text_planner_controlled_enabled=False,
            text_memory_context_enabled=False,
            text_reviewer_shadow_enabled=True,
            scene_planner_shadow_enabled=False,
            scene_planner_image_prompt_enabled=False,
        ),
    )
    monkeypatch.setattr(generation, "generate_affirmations", _fake_generate_affirmations)
    monkeypatch.setattr(generation, "build_enriched_image_prompt", _fake_build_enriched_image_prompt)
    monkeypatch.setattr(generation, "generate_image", _fake_generate_image)
    monkeypatch.setattr(generation, "record_interactive_generation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "log_generation_ok", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "record_generation_history_best_effort", _fake_history)

    state = _FakeState(
        {
            "sphere": "inner_peace",
            "subsphere": None,
            "style": "auto",
            "visual_mode": "illustration",
            "recent_generation_history": [],
        }
    )
    message = _FakeMessage(user_id=94)

    asyncio.run(
        generation._run_generation(
            message,
            state,
            theme_text="мягкая опора",
            user_telegram_id=94,
        )
    )

    reviewer_meta = captured["history_kwargs"]["visual_motifs"]["text_reviewer_shadow"]
    assert reviewer_meta["enabled"] is True
    assert reviewer_meta["checks"]["gender_mismatch"] is True
    assert reviewer_meta["score"] < 1.0


def test_run_generation_does_not_attach_text_reviewer_shadow_when_disabled(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru", "gender": "female"}

    async def _fake_generate_affirmations(**kwargs):
        return ["Я открыт новому", "Я выбираю спокойствие", "Я выбираю ясность", "Я нахожу опору"]

    async def _fake_build_enriched_image_prompt(**kwargs):
        return "prompt", "template"

    async def _fake_generate_image(**kwargs):
        return "fake_image.png"

    async def _fake_history(**kwargs):
        captured["history_kwargs"] = kwargs

    captured = {}
    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(
        generation,
        "get_settings",
        lambda: SimpleNamespace(
            disable_daily_generation_limit=True,
            generation_daily_limit=0,
            llm_image_prompt_enabled=False,
            show_image_debug=False,
            image_model="image-model",
            image_size="1024x1024",
            text_planner_shadow_enabled=False,
            text_planner_controlled_enabled=False,
            text_memory_context_enabled=False,
            text_reviewer_shadow_enabled=False,
            scene_planner_shadow_enabled=False,
            scene_planner_image_prompt_enabled=False,
        ),
    )
    monkeypatch.setattr(generation, "generate_affirmations", _fake_generate_affirmations)
    monkeypatch.setattr(generation, "build_enriched_image_prompt", _fake_build_enriched_image_prompt)
    monkeypatch.setattr(generation, "generate_image", _fake_generate_image)
    monkeypatch.setattr(generation, "record_interactive_generation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "log_generation_ok", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "record_generation_history_best_effort", _fake_history)

    state = _FakeState(
        {
            "sphere": "inner_peace",
            "subsphere": None,
            "style": "auto",
            "visual_mode": "illustration",
            "recent_generation_history": [],
        }
    )
    message = _FakeMessage(user_id=95)

    asyncio.run(
        generation._run_generation(
            message,
            state,
            theme_text="мягкая опора",
            user_telegram_id=95,
        )
    )

    assert "text_reviewer_shadow" not in captured["history_kwargs"]["visual_motifs"]


def test_run_generation_attaches_orchestrator_shadow_when_enabled(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru", "gender": "female"}

    async def _fake_generate_affirmations(**kwargs):
        return ["Я выбираю спокойствие", "Я нахожу опору", "Я дышу свободнее", "Я берегу себя"]

    async def _fake_build_enriched_image_prompt(**kwargs):
        return "prompt", "template"

    async def _fake_generate_image(**kwargs):
        return "fake_image.png"

    async def _fake_history(**kwargs):
        captured["history_kwargs"] = kwargs

    async def _fake_text_memory_context(*_args, **_kwargs):
        return {
            "limit": 10,
            "overused_text_patterns": ["я выбираю"],
            "overused_soft_action_patterns": ["name_three_things"],
            "recent_focus_titles": ["мягкая опора"],
            "avoid_soft_actions": ["назови три вещи, которые уже помогают"],
        }

    captured = {}
    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(
        generation,
        "get_settings",
        lambda: SimpleNamespace(
            disable_daily_generation_limit=True,
            generation_daily_limit=0,
            llm_image_prompt_enabled=False,
            show_image_debug=False,
            image_model="image-model",
            image_size="1024x1024",
            text_planner_shadow_enabled=True,
            text_planner_controlled_enabled=True,
            text_memory_context_enabled=True,
            text_reviewer_shadow_enabled=True,
            orchestrator_shadow_enabled=True,
            scene_planner_shadow_enabled=True,
            scene_planner_image_prompt_enabled=False,
        ),
    )
    monkeypatch.setattr(generation, "generate_affirmations", _fake_generate_affirmations)
    monkeypatch.setattr(generation, "build_enriched_image_prompt", _fake_build_enriched_image_prompt)
    monkeypatch.setattr(generation, "generate_image", _fake_generate_image)
    monkeypatch.setattr(generation, "record_interactive_generation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "log_generation_ok", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "record_generation_history_best_effort", _fake_history)
    monkeypatch.setattr(generation, "get_text_memory_context", _fake_text_memory_context)

    state = _FakeState(
        {
            "sphere": "inner_peace",
            "subsphere": None,
            "style": "auto",
            "visual_mode": "illustration",
            "recent_generation_history": [],
        }
    )
    message = _FakeMessage(user_id=96)

    asyncio.run(
        generation._run_generation(
            message,
            state,
            theme_text="мягкая опора",
            user_telegram_id=96,
        )
    )

    orchestrator_meta = captured["history_kwargs"]["visual_motifs"]["orchestrator_shadow"]
    assert orchestrator_meta["enabled"] is True
    assert orchestrator_meta["route"]["text_planner"] is True
    assert orchestrator_meta["route"]["text_memory"] is True
    assert orchestrator_meta["route"]["text_reviewer"] is True
    assert orchestrator_meta["route"]["scene_planner"] is True


def test_run_generation_does_not_attach_orchestrator_shadow_when_disabled(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru", "gender": "female"}

    async def _fake_generate_affirmations(**kwargs):
        return ["Я выбираю спокойствие", "Я нахожу опору", "Я дышу свободнее", "Я берегу себя"]

    async def _fake_build_enriched_image_prompt(**kwargs):
        return "prompt", "template"

    async def _fake_generate_image(**kwargs):
        return "fake_image.png"

    async def _fake_history(**kwargs):
        captured["history_kwargs"] = kwargs

    captured = {}
    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(
        generation,
        "get_settings",
        lambda: SimpleNamespace(
            disable_daily_generation_limit=True,
            generation_daily_limit=0,
            llm_image_prompt_enabled=False,
            show_image_debug=False,
            image_model="image-model",
            image_size="1024x1024",
            text_planner_shadow_enabled=False,
            text_planner_controlled_enabled=False,
            text_memory_context_enabled=False,
            text_reviewer_shadow_enabled=False,
            orchestrator_shadow_enabled=False,
            scene_planner_shadow_enabled=False,
            scene_planner_image_prompt_enabled=False,
        ),
    )
    monkeypatch.setattr(generation, "generate_affirmations", _fake_generate_affirmations)
    monkeypatch.setattr(generation, "build_enriched_image_prompt", _fake_build_enriched_image_prompt)
    monkeypatch.setattr(generation, "generate_image", _fake_generate_image)
    monkeypatch.setattr(generation, "record_interactive_generation", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "log_generation_ok", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(generation, "record_generation_history_best_effort", _fake_history)

    state = _FakeState(
        {
            "sphere": "inner_peace",
            "subsphere": None,
            "style": "auto",
            "visual_mode": "illustration",
            "recent_generation_history": [],
        }
    )
    message = _FakeMessage(user_id=97)

    asyncio.run(
        generation._run_generation(
            message,
            state,
            theme_text="мягкая опора",
            user_telegram_id=97,
        )
    )

    assert "orchestrator_shadow" not in captured["history_kwargs"]["visual_motifs"]


def test_again_affirmation_restores_context_and_passes_theme_text(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "en"}

    captured = {}

    async def _fake_run(message, state, *, theme_text, user_telegram_id=None):
        captured["theme_text"] = theme_text
        captured["data"] = await state.get_data()
        captured["user_telegram_id"] = user_telegram_id

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(generation, "_run_generation", _fake_run)

    state = _FakeState(
        {
            "last_generation": {
                "sphere": "relationships",
                "subsphere": "friends",
                "style": "custom",
                "visual_mode": "mixed",
                "theme_text": "Protect my friendship boundaries",
                "custom_style_description": "warm table scene",
            }
        }
    )
    callback = _FakeCallback(user_id=88)

    asyncio.run(generation.again_affirmation(callback, state))

    assert callback.answered is True
    assert captured["theme_text"] == "Protect my friendship boundaries"
    assert captured["user_telegram_id"] == 88
    assert captured["data"]["sphere"] == "relationships"
    assert captured["data"]["subsphere"] == "friends"
    assert captured["data"]["style"] == "custom"
    assert captured["data"]["visual_mode"] == "mixed"
    assert captured["data"]["custom_style_description"] == "warm table scene"
