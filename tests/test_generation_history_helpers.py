import asyncio
import importlib
import sys
import types
from types import SimpleNamespace

from services import generation_history


def test_extract_telegram_photo_file_id_returns_last_file_id():
    sent_message = SimpleNamespace(
        photo=[
            SimpleNamespace(file_id="file-small"),
            SimpleNamespace(file_id="file-large"),
        ]
    )

    assert generation_history.extract_telegram_photo_file_id(sent_message) == "file-large"


def test_extract_telegram_photo_file_id_returns_none_for_strange_objects():
    assert generation_history.extract_telegram_photo_file_id(None) is None
    assert generation_history.extract_telegram_photo_file_id(object()) is None
    assert generation_history.extract_telegram_photo_file_id(SimpleNamespace(photo=[])) is None
    assert generation_history.extract_telegram_photo_file_id(SimpleNamespace(photo=[object()])) is None


def test_build_visual_motifs_prefers_scene_preset():
    motifs = generation_history.build_visual_motifs(
        image_meta={"scene_preset": "window_still_life", "photo_scene_preset": "ignored"},
        visual_mode="photo",
        selected_style="light_interior_photo",
        color_palette="pearl daylight",
        composition_hint="airy composition",
        sphere="career",
        subsphere=None,
    )

    assert motifs["source"] == "generation_runtime_meta"
    assert motifs["scene_type"] == "window_still_life"
    assert motifs["visual_mode"] == "photo"
    assert motifs["selected_style"] == "light_interior_photo"


def test_build_visual_motifs_falls_back_to_photo_scene_preset():
    motifs = generation_history.build_visual_motifs(
        image_meta={"photo_scene_preset": "coastal_path"},
        sphere="inner_peace",
        subsphere="friends",
    )

    assert motifs["scene_type"] == "coastal_path"
    assert motifs["sphere"] == "inner_peace"
    assert motifs["subsphere"] == "friends"


def test_record_generation_history_best_effort_swallows_database_errors(monkeypatch):
    async def _boom(**_kwargs):
        raise RuntimeError("db is down")

    monkeypatch.setattr(generation_history, "save_generation_history", _boom)

    result = asyncio.run(
        generation_history.record_generation_history_best_effort(
            telegram_user_id=1,
            request_type="manual",
            focus_title="Focus",
        )
    )

    assert result is None


class _FakeState:
    def __init__(self):
        self.data = {}

    async def update_data(self, **kwargs):
        self.data.update(kwargs)


class _FakeMessage:
    def __init__(self):
        self.answers = []

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))


class _FakeCallback:
    def __init__(self):
        self.from_user = SimpleNamespace(id=42)
        self.message = _FakeMessage()

    async def answer(self):
        return None


def test_subscription_more_marks_request_type_as_extra_mood(monkeypatch):
    fake_scheduler = types.ModuleType("scheduler")
    fake_scheduler.last_subscription_affirmations = {}
    monkeypatch.setitem(sys.modules, "scheduler", fake_scheduler)
    sys.modules.pop("handlers.subscribe", None)
    subscribe = importlib.import_module("handlers.subscribe")

    async def _fake_get_user(_uid):
        return {"language": "ru"}

    captured = {}

    async def _fake_start_generation(message, state, *, theme_text, language, user_telegram_id=None):
        captured["theme_text"] = theme_text
        captured["language"] = language
        captured["user_telegram_id"] = user_telegram_id

    monkeypatch.setattr(subscribe, "get_user", _fake_get_user)
    monkeypatch.setattr(
        subscribe,
        "last_subscription_affirmations",
        {
            42: {
                "sphere": "money",
                "subsphere": None,
                "style": "auto",
                "style_mode": "auto",
                "visual_mode": "photo",
            }
        },
    )
    monkeypatch.setattr("handlers.generation._start_generation_after_preflight", _fake_start_generation)

    state = _FakeState()
    callback = _FakeCallback()

    asyncio.run(subscribe.subscription_more(callback, state))

    assert state.data["generation_request_type"] == "extra_mood"
    assert captured["theme_text"] is None
    assert captured["language"] == "ru"
    assert captured["user_telegram_id"] == 42
