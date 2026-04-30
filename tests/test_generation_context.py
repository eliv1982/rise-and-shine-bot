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
    def __init__(self, user_id=123):
        self.from_user = SimpleNamespace(id=user_id)
        self.answers = []
        self.photos = []
        self.edits = []

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))

    async def answer_photo(self, photo, caption=None, reply_markup=None):
        self.photos.append((photo, caption, reply_markup))

    async def edit_text(self, text, reply_markup=None):
        self.edits.append((text, reply_markup))


class _FakeCallback:
    def __init__(self, user_id=123):
        self.from_user = SimpleNamespace(id=user_id)
        self.message = _FakeMessage(user_id=user_id)
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
