import asyncio
import os
from types import SimpleNamespace

import pytest

from config import get_outputs_dir
from handlers import start
from services.voice_input import VoiceInputProcessor
from states import RegistrationState


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

    async def get_state(self):
        return self.state

    async def clear(self):
        self.data = {}
        self.state = None


class _FakeBot:
    """Writes a real (tiny) file to `destination`, like aiogram's real download_file."""

    async def get_file(self, file_id):
        return SimpleNamespace(file_path=f"remote/{file_id}.ogg")

    async def download_file(self, file_path, destination):
        with open(destination, "wb") as f:
            f.write(b"fake-voice-bytes")


class _FakeMessage:
    def __init__(self, user_id=42, file_unique_id="uniq-1"):
        self.from_user = SimpleNamespace(id=user_id)
        self.bot = _FakeBot()
        self.voice = SimpleNamespace(file_id="voice-1", file_unique_id=file_unique_id)
        self.answers = []

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))


def _voice_input_path(pending_kind: str, user_id: int, file_unique_id: str) -> str:
    return os.path.join(get_outputs_dir(), f"voice_{pending_kind}_{user_id}_{file_unique_id}.ogg")


def _name_voice_path(user_id: int, file_unique_id: str) -> str:
    return os.path.join(get_outputs_dir(), f"voice_name_{user_id}_{file_unique_id}.ogg")


def test_voice_input_processor_removes_temp_file_on_success(sqlite_db_path):
    async def run():
        processor = VoiceInputProcessor(stt_transcriber=lambda *_a, **_k: _fake_meta("моя тема"))
        state = _FakeState()
        msg = _FakeMessage(file_unique_id="ok-1")
        path = _voice_input_path("theme", msg.from_user.id, "ok-1")

        result = await processor.process(msg, state, language="ru", pending_kind="theme")

        assert result.status == "ok"
        assert not os.path.exists(path)

    asyncio.run(run())


def test_voice_input_processor_removes_temp_file_on_stt_failure(sqlite_db_path):
    async def run():
        async def _raise(*_a, **_k):
            raise RuntimeError("stt down")

        processor = VoiceInputProcessor(stt_transcriber=_raise)
        state = _FakeState()
        msg = _FakeMessage(file_unique_id="fail-1")
        path = _voice_input_path("theme", msg.from_user.id, "fail-1")

        result = await processor.process(msg, state, language="ru", pending_kind="theme")

        assert result.status == "stt_failed"
        assert not os.path.exists(path)

    asyncio.run(run())


def test_voice_input_processor_removes_temp_file_on_unclear_result(sqlite_db_path):
    async def run():
        processor = VoiceInputProcessor(stt_transcriber=lambda *_a, **_k: _fake_meta("do stoint weh weh weh"))
        state = _FakeState()
        msg = _FakeMessage(file_unique_id="unclear-1")
        path = _voice_input_path("style", msg.from_user.id, "unclear-1")

        result = await processor.process(msg, state, language="en", pending_kind="style")

        assert result.status == "unclear"
        assert not os.path.exists(path)

    asyncio.run(run())


def test_voice_input_processor_removes_temp_file_on_language_mismatch(sqlite_db_path):
    async def run():
        processor = VoiceInputProcessor(stt_transcriber=lambda *_a, **_k: _fake_meta("достоинство и вера"))
        state = _FakeState()
        msg = _FakeMessage(file_unique_id="mismatch-1")
        path = _voice_input_path("theme", msg.from_user.id, "mismatch-1")

        result = await processor.process(msg, state, language="en", pending_kind="theme")

        assert result.status == "language_mismatch"
        assert not os.path.exists(path)

    asyncio.run(run())


def test_voice_input_processor_cleanup_failure_is_isolated(sqlite_db_path, monkeypatch):
    """A cleanup error (e.g. file locked) must not replace the real STT result/exception."""

    async def run():
        logged = {}

        def _fake_log(path, error):
            logged["path"] = path
            logged["error"] = error

        monkeypatch.setattr("services.voice_input.log_voice_cleanup_failed", _fake_log)

        real_remove = os.remove

        def _raising_remove(path):
            if path.endswith(".ogg"):
                raise OSError("simulated: file still in use")
            return real_remove(path)

        monkeypatch.setattr(os, "remove", _raising_remove)

        processor = VoiceInputProcessor(stt_transcriber=lambda *_a, **_k: _fake_meta("моя тема"))
        state = _FakeState()
        msg = _FakeMessage(file_unique_id="locked-1")

        result = await processor.process(msg, state, language="ru", pending_kind="theme")

        assert result.status == "ok"  # the real result survives the cleanup failure
        assert result.text == "моя тема"
        assert logged.get("error") == "simulated: file still in use"

    asyncio.run(run())


def test_registration_name_voice_removes_temp_file_on_success(sqlite_db_path, monkeypatch):
    async def run():
        saved = {}

        async def _fake_update_profile(user_id, name=None, **_kwargs):
            saved["name"] = name

        monkeypatch.setattr(start, "transcribe_audio_with_meta", lambda *_a, **_k: _fake_meta("Меня зовут Алиса"))
        monkeypatch.setattr(start, "update_user_profile", _fake_update_profile)

        state = _FakeState()
        state.state = RegistrationState.waiting_for_name
        msg = _FakeMessage(user_id=77, file_unique_id="name-ok")
        path = _name_voice_path(77, "name-ok")

        await start.process_name_voice(msg, state)

        assert saved["name"] == "Алиса"
        assert not os.path.exists(path)

    asyncio.run(run())


def test_registration_name_voice_removes_temp_file_on_stt_failure(sqlite_db_path, monkeypatch):
    async def run():
        async def _raise(*_a, **_k):
            raise RuntimeError("stt down")

        monkeypatch.setattr(start, "transcribe_audio_with_meta", _raise)

        state = _FakeState()
        state.state = RegistrationState.waiting_for_name
        msg = _FakeMessage(user_id=88, file_unique_id="name-fail")
        path = _name_voice_path(88, "name-fail")

        await start.process_name_voice(msg, state)

        assert any("Не получилось распознать" in text for text, _ in msg.answers)
        assert not os.path.exists(path)

    asyncio.run(run())
