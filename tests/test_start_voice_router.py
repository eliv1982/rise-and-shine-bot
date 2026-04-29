import asyncio
from types import SimpleNamespace

from handlers import start
from states import RegistrationState


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

    async def _fake_transcribe(*_args, **_kwargs):
        return "create new ritual please"

    called = {"new": False}

    async def _fake_cmd_new(_message, _state):
        called["new"] = True

    monkeypatch.setattr(start, "get_user", _fake_get_user)
    monkeypatch.setattr(start, "transcribe_audio", _fake_transcribe)
    monkeypatch.setattr("handlers.generation.cmd_new", _fake_cmd_new)

    state = _FakeState()
    msg = _FakeMessage()
    asyncio.run(start.main_menu_voice_router(msg, state))

    assert called["new"] is True
    assert any("🎙️ I recognized:" in text for text, _ in msg.answers)


def test_main_menu_voice_unknown_intent_returns_friendly_hint(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru"}

    async def _fake_transcribe(*_args, **_kwargs):
        return "просто делюсь мыслью"

    monkeypatch.setattr(start, "get_user", _fake_get_user)
    monkeypatch.setattr(start, "transcribe_audio", _fake_transcribe)

    state = _FakeState()
    msg = _FakeMessage()
    asyncio.run(start.main_menu_voice_router(msg, state))

    assert any("🎙️ Распознала:" in text for text, _ in msg.answers)
    assert any("Я распознала голос, но не уверена, что именно нужно сделать 🌿" in text for text, _ in msg.answers)


def test_registration_name_voice_uses_recognized_name(monkeypatch):
    async def _fake_transcribe(*_args, **_kwargs):
        return "Меня зовут Алиса"

    saved = {"name": None}

    async def _fake_update_profile(user_id, name=None, **_kwargs):
        saved["name"] = name

    monkeypatch.setattr(start, "transcribe_audio", _fake_transcribe)
    monkeypatch.setattr(start, "update_user_profile", _fake_update_profile)

    state = _FakeState()
    state.state = RegistrationState.waiting_for_name
    msg = _FakeMessage()
    asyncio.run(start.process_name_voice(msg, state))

    assert saved["name"] == "Алиса"
    assert state.state == RegistrationState.waiting_for_gender
