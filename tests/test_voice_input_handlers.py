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


def test_voice_theme_input_follows_same_flow_as_text(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru"}

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(generation, "transcribe_audio_with_meta", lambda *_args, **_kwargs: _fake_meta("моя тема"))

    text_state = _FakeState()
    text_msg = _FakeMessage(text="моя тема", language="ru", with_voice=False)
    asyncio.run(generation.handle_text_theme_early(text_msg, text_state))

    voice_state = _FakeState()
    voice_msg = _FakeMessage(language="ru", with_voice=True)
    asyncio.run(generation.handle_voice_theme_early(voice_msg, voice_state))

    assert text_state.data["theme_text"] == "моя тема"
    assert voice_state.data["theme_text"] == "моя тема"
    assert text_state.data["sphere"] == voice_state.data["sphere"] == "inner_peace"
    assert text_state.state == voice_state.state == GenerationState.choosing_visual_mode
    assert any("🎙️ Распознано:" in answer for answer, _ in voice_msg.answers)


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

    async def _fake_run_generation(*_args, **_kwargs):
        return None

    monkeypatch.setattr(generation, "get_user", _fake_get_user)
    monkeypatch.setattr(generation, "transcribe_audio_with_meta", lambda *_args, **_kwargs: _fake_meta("soft coastal editorial photo"))
    monkeypatch.setattr(generation, "_run_generation", _fake_run_generation)

    state = _FakeState()
    state.data["theme_text"] = "theme"
    msg = _FakeMessage(language="en", with_voice=True)
    asyncio.run(generation.handle_voice_custom_style(msg, state))

    assert state.data["custom_style_description"] == "soft coastal editorial photo"
    assert any("🎙️ Recognized:" in answer for answer, _ in msg.answers)
