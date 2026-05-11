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
