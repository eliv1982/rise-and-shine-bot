import asyncio
from types import SimpleNamespace

from handlers import start
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
        self.state = None


class _FakeBot:
    async def get_file(self, file_id):
        return SimpleNamespace(file_path=f"remote/{file_id}.ogg")

    async def download_file(self, file_path, destination):
        with open(destination, "wb") as f:
            f.write(b"voice")


class _FakeMessage:
    def __init__(self, with_voice=True):
        self.from_user = SimpleNamespace(id=55)
        self.bot = _FakeBot()
        self.voice = SimpleNamespace(file_id="id1", file_unique_id="uq1") if with_voice else None
        self.answers = []

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))


def test_main_menu_voice_routes_to_create_intent(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "en"}

    called = {"new": False}

    async def _fake_cmd_new(_message, _state):
        called["new"] = True

    monkeypatch.setattr(start, "get_user", _fake_get_user)
    monkeypatch.setattr(start, "transcribe_audio_with_meta", lambda *_args, **_kwargs: _fake_meta("create new ritual please"))
    monkeypatch.setattr("handlers.generation.cmd_new", _fake_cmd_new)

    state = _FakeState()
    msg = _FakeMessage()
    asyncio.run(start.main_menu_voice_router(msg, state))

    assert called["new"] is True
    assert any("🎙️ Recognized:" in text for text, _ in msg.answers)


def test_main_menu_voice_transliterated_intent_routes_to_create(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "en"}

    called = {"new": False}

    async def _fake_cmd_new(_message, _state):
        called["new"] = True

    monkeypatch.setattr(start, "get_user", _fake_get_user)
    monkeypatch.setattr(start, "transcribe_audio_with_meta", lambda *_args, **_kwargs: _fake_meta("sozday nastroi"))
    monkeypatch.setattr("handlers.generation.cmd_new", _fake_cmd_new)

    state = _FakeState()
    msg = _FakeMessage()
    asyncio.run(start.main_menu_voice_router(msg, state))
    assert called["new"] is True


def test_main_menu_voice_unknown_intent_returns_friendly_hint(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru"}

    monkeypatch.setattr(start, "get_user", _fake_get_user)
    monkeypatch.setattr(start, "transcribe_audio_with_meta", lambda *_args, **_kwargs: _fake_meta("просто делюсь мыслью"))

    state = _FakeState()
    msg = _FakeMessage()
    asyncio.run(start.main_menu_voice_router(msg, state))

    assert any("🎙️ Распознано:" in text for text, _ in msg.answers)
    assert any("Я распознала голос, но не уверена, что именно нужно сделать 🌿" in text for text, _ in msg.answers)


def test_registration_name_voice_uses_recognized_name(monkeypatch):
    saved = {"name": None}

    async def _fake_update_profile(user_id, name=None, **_kwargs):
        saved["name"] = name

    monkeypatch.setattr(start, "transcribe_audio_with_meta", lambda *_args, **_kwargs: _fake_meta("Меня зовут Алиса"))
    monkeypatch.setattr(start, "update_user_profile", _fake_update_profile)

    state = _FakeState()
    state.state = RegistrationState.waiting_for_name
    msg = _FakeMessage()
    asyncio.run(start.process_name_voice(msg, state))

    assert saved["name"] == "Алиса"
    assert state.state == RegistrationState.waiting_for_gender


def test_language_change_clears_state_and_shows_main_menu(monkeypatch):
    async def _fake_update_user_language(_uid, _lang):
        return None

    monkeypatch.setattr(start, "update_user_language", _fake_update_user_language)

    class _FakeCallback:
        def __init__(self):
            self.data = "lang:en"
            self.from_user = SimpleNamespace(id=12)
            self.message = SimpleNamespace(
                edited=[],
                answered=[],
                edit_text=self._edit_text,
                answer=self._answer,
            )

        async def _edit_text(self, text):
            self.message.edited.append(text)

        async def _answer(self, text, reply_markup=None):
            self.message.answered.append((text, reply_markup))

        async def answer(self):
            return None

    class _State:
        def __init__(self):
            self.cleared = False

        async def get_state(self):
            return None

        async def clear(self):
            self.cleared = True

    callback = _FakeCallback()
    state = _State()
    asyncio.run(start.cmd_language_callback(callback, state))
    assert state.cleared is True
    assert any("Language updated" in text for text, _ in callback.message.answered)


def test_language_change_then_voice_routing_still_works(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "en"}

    async def _fake_update_user_language(_uid, _lang):
        return None

    called = {"new": False}

    async def _fake_cmd_new(_message, _state):
        called["new"] = True

    monkeypatch.setattr(start, "get_user", _fake_get_user)
    monkeypatch.setattr(start, "update_user_language", _fake_update_user_language)
    monkeypatch.setattr(start, "transcribe_audio_with_meta", lambda *_args, **_kwargs: _fake_meta("create focus"))
    monkeypatch.setattr("handlers.generation.cmd_new", _fake_cmd_new)

    class _FakeCallback:
        def __init__(self):
            self.data = "lang:en"
            self.from_user = SimpleNamespace(id=22)
            self.message = SimpleNamespace(edit_text=self._edit_text, answer=self._answer)

        async def _edit_text(self, _text):
            return None

        async def _answer(self, _text, reply_markup=None):
            return None

        async def answer(self):
            return None

    state = _FakeState()
    callback = _FakeCallback()
    asyncio.run(start.cmd_language_callback(callback, state))
    msg = _FakeMessage()
    msg.from_user = SimpleNamespace(id=22)
    asyncio.run(start.main_menu_voice_router(msg, state))
    assert called["new"] is True
