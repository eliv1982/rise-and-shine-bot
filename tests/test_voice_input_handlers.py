import asyncio
from types import SimpleNamespace

import pytest

from handlers import generation
from states import GenerationState


async def _fake_meta(text: str):
    return {
        "recognized_text_raw": text,
        "recognized_text_final": text,
        "recognized_language": "auto",
        "stt_provider": "yandex",
        "stt_model": "general",
        "stt_attempt_count": 1,
        "stt_language_attempts": ["ru"],
    }


class _FakeState:
    def __init__(self):
        self.data = {}
        self.state = None

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def set_state(self, state):
        self.state = state

    async def get_data(self):
        return dict(self.data)

    async def clear(self):
        self.data = {}
        self.state = None


class _FakeBot:
    async def get_file(self, file_id):
        return SimpleNamespace(file_path=f"remote/{file_id}.ogg")

    async def download_file(self, file_path, destination):
        with open(destination, "wb") as f:
            f.write(b"fake-voice")


class _FakeMessage:
    def __init__(self, *, text=None, language="ru", with_voice=False):
        self.text = text
        self.from_user = SimpleNamespace(id=123)
        self.bot = _FakeBot()
        self.voice = SimpleNamespace(file_id="voice-1", file_unique_id="uniq-1") if with_voice else None
        self.answers = []
        self.language = language

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))


class _FakeCallback:
    def __init__(self, data: str, language: str = "ru"):
        self.data = data
        self.from_user = SimpleNamespace(id=123)
        self.message = _FakeMessage(language=language, with_voice=False)

    async def answer(self):
        return None


def test_voice_theme_input_follows_same_flow_as_text(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru"}

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(generation, "transcribe_audio_with_meta", lambda *_args, **_kwargs: _fake_meta("моя тема"))

    voice_state = _FakeState()
    voice_msg = _FakeMessage(language="ru", with_voice=True)
    asyncio.run(generation.handle_voice_theme_early(voice_msg, voice_state))

    assert voice_state.data["recognized_text_pending"] == "моя тема"
    assert voice_state.data["recognized_text_pending_kind"] == "theme"
    assert "theme_text" not in voice_state.data
    assert any("🎙 Распознано:" in answer for answer, _ in voice_msg.answers)


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("ru", "Не получилось распознать голос 😕\nПопробуй ещё раз или отправь текстом."),
        ("en", "I couldn’t recognize the voice message 😕\nPlease try again or send it as text."),
    ],
)
def test_voice_recognition_failure_returns_friendly_message(monkeypatch, language, expected):
    async def _fake_get_user(_uid):
        return {"language": language}

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    async def _raise_meta(*_args, **_kwargs):
        raise RuntimeError("stt is down")
    monkeypatch.setattr(generation, "transcribe_audio_with_meta", _raise_meta)

    state = _FakeState()
    msg = _FakeMessage(language=language, with_voice=True)
    asyncio.run(generation.handle_voice_theme_early(msg, state))

    assert msg.answers
    assert msg.answers[-1][0] == expected


def test_voice_custom_style_echoes_recognized_text(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "en"}

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(generation, "transcribe_audio_with_meta", lambda *_args, **_kwargs: _fake_meta("soft coastal editorial photo"))

    state = _FakeState()
    state.data["theme_text"] = "theme"
    msg = _FakeMessage(language="en", with_voice=True)
    asyncio.run(generation.handle_voice_custom_style(msg, state))

    assert state.data["recognized_text_pending"] == "soft coastal editorial photo"
    assert state.data["recognized_text_pending_kind"] == "style"
    assert any("🎙 Recognized:" in answer for answer, _ in msg.answers)


def test_generation_menu_state_text_guard_for_sphere(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru"}

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    state = _FakeState()
    msg = _FakeMessage(text="какой-то текст", language="ru", with_voice=False)
    asyncio.run(generation.generation_button_menu_text_guard(msg, state))
    assert "Выбери вариант в меню выше" in msg.answers[-1][0]


def test_generation_menu_state_voice_guard_for_style(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "en"}

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    state = _FakeState()
    msg = _FakeMessage(language="en", with_voice=True)
    asyncio.run(generation.generation_style_menu_voice_guard(msg, state))
    assert "Please choose an image style from the buttons above" in msg.answers[-1][0]


def test_bad_stt_for_custom_style_returns_unclear_and_does_not_generate(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru"}

    called = {"run": False}

    async def _fake_run(*_args, **_kwargs):
        called["run"] = True

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(generation, "transcribe_audio_with_meta", lambda *_args, **_kwargs: _fake_meta("do stoint weh weh weh"))
    monkeypatch.setattr(generation, "_run_generation", _fake_run)

    state = _FakeState()
    state.data["theme_text"] = "тема"
    msg = _FakeMessage(language="ru", with_voice=True)
    asyncio.run(generation.handle_voice_custom_style(msg, state))
    assert any("неразборчивым" in text for text, _ in msg.answers)
    assert called["run"] is False


def test_confirm_recognized_theme_proceeds_to_visual_mode(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru"}

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    state = _FakeState()
    state.data["recognized_text_pending"] = "моя тема"
    cb = _FakeCallback("theme_voice:use", language="ru")
    asyncio.run(generation.handle_theme_voice_recovery(cb, state))
    assert state.data["theme_text"] == "моя тема"
    assert state.state == GenerationState.choosing_visual_mode


def test_confirm_recognized_style_starts_generation(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "en"}

    called = {"run": False}

    async def _fake_run(*_args, **_kwargs):
        called["run"] = True

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(generation, "_run_generation", _fake_run)
    state = _FakeState()
    state.data["recognized_text_pending"] = "ocean travel photo"
    state.data["theme_text"] = "Dignity"
    cb = _FakeCallback("style_voice:use", language="en")
    asyncio.run(generation.handle_style_voice_recovery(cb, state))
    assert state.data["custom_style_description"] == "ocean travel photo"
    assert called["run"] is True


def test_en_ui_russian_text_custom_theme_requests_english(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "en"}

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    state = _FakeState()
    msg = _FakeMessage(text="Достоинство и вера в себя", language="en", with_voice=False)
    asyncio.run(generation.handle_text_theme_early(msg, state))
    assert any("flow in English" in text for text, _ in msg.answers)
    assert state.state is None


def test_ru_ui_english_text_custom_theme_requests_russian(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru"}

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    state = _FakeState()
    msg = _FakeMessage(text="Dignity and self-trust", language="ru", with_voice=False)
    asyncio.run(generation.handle_text_theme_early(msg, state))
    assert any("жду текст на русском" in text for text, _ in msg.answers)
    assert state.state is None


@pytest.mark.parametrize("language,expected", [("ru", "Выбери вариант в меню выше"), ("en", "Please choose an option from the menu above")])
def test_generation_menu_state_text_guard_for_sphere_ru_en(monkeypatch, language, expected):
    async def _fake_get_user(_uid):
        return {"language": language}

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    state = _FakeState()
    msg = _FakeMessage(text="hello", language=language, with_voice=False)
    asyncio.run(generation.generation_button_menu_text_guard(msg, state))
    assert expected in msg.answers[-1][0]


@pytest.mark.parametrize("language,expected", [("ru", "Выбери вариант в меню выше"), ("en", "Please choose an option from the menu above")])
def test_generation_menu_state_voice_guard_for_sphere_ru_en(monkeypatch, language, expected):
    async def _fake_get_user(_uid):
        return {"language": language}

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    state = _FakeState()
    msg = _FakeMessage(language=language, with_voice=True)
    asyncio.run(generation.generation_button_menu_voice_guard(msg, state))
    assert expected in msg.answers[-1][0]


@pytest.mark.parametrize("language,expected", [("ru", "Выбери стиль кнопкой выше"), ("en", "Please choose an image style from the buttons above")])
def test_generation_style_state_text_guard_ru_en(monkeypatch, language, expected):
    async def _fake_get_user(_uid):
        return {"language": language}

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    state = _FakeState()
    msg = _FakeMessage(text="style text", language=language, with_voice=False)
    asyncio.run(generation.generation_style_menu_text_guard(msg, state))
    assert expected in msg.answers[-1][0]


@pytest.mark.parametrize("language,expected", [("ru", "Выбери стиль кнопкой выше"), ("en", "Please choose an image style from the buttons above")])
def test_generation_style_state_voice_guard_ru_en(monkeypatch, language, expected):
    async def _fake_get_user(_uid):
        return {"language": language}

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    state = _FakeState()
    msg = _FakeMessage(language=language, with_voice=True)
    asyncio.run(generation.generation_style_menu_voice_guard(msg, state))
    assert expected in msg.answers[-1][0]
