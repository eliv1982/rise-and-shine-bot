"""Regression tests for the Stage 4 onboarding contract.

A `users` row can exist before registration is finished (RegistrationState.waiting_for_name /
waiting_for_gender), and the FSM state that tracks progress through registration lives only in
aiogram's in-memory storage (bot.py's MemoryStorage), so a bot restart or /cancel mid-
registration can leave a row behind that other handlers must not mistake for a completed
account. database.is_onboarding_complete is the single predicate that decides this; /start must
resume registration at the right step instead of greeting the user as "returning", and the
command handlers that require a real account (smalltalk, /new, /subscribe, /profile, /language)
must all redirect back to /start rather than silently proceeding.
"""
import asyncio
from types import SimpleNamespace

import pytest

import database as db
from handlers import generation, start, subscribe
from states import GenerationState, RegistrationState


class _FakeState:
    def __init__(self, state=None, **data):
        self.state = state
        self.data = dict(data)

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def set_state(self, state):
        self.state = state

    async def get_state(self):
        return self.state

    async def clear(self):
        self.state = None
        self.data = {}


class _FakeMessage:
    def __init__(self, user_id, username="u"):
        self.from_user = SimpleNamespace(id=user_id, username=username)
        self.answers = []

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))


def test_is_onboarding_complete_predicate():
    assert db.is_onboarding_complete(None) is False
    assert db.is_onboarding_complete({}) is False
    assert db.is_onboarding_complete({"name": "Ann"}) is False
    assert db.is_onboarding_complete({"name": None, "gender": "female"}) is False
    assert db.is_onboarding_complete({"name": "", "gender": "female"}) is False
    assert db.is_onboarding_complete({"name": "Ann", "gender": ""}) is False
    assert db.is_onboarding_complete({"name": "Ann", "gender": "female"}) is True
    # Whitespace-only values must not count as set.
    assert db.is_onboarding_complete({"name": "   ", "gender": "female"}) is False


@pytest.mark.usefixtures("initialized_db")
def test_start_resumes_registration_at_name_step_for_nameless_row():
    """A row created (e.g. by an interrupted /start) before a name was ever captured must
    resume exactly like a brand-new registration, not be greeted as a returning user."""

    async def run():
        await db.create_or_update_user(1, "u")

        state = _FakeState()
        msg = _FakeMessage(1)
        await start.cmd_start(msg, state)

        assert state.state == RegistrationState.waiting_for_name
        assert "как тебя зовут" in msg.answers[-1][0].lower()

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_start_resumes_registration_at_gender_step_when_name_known():
    """Name captured but gender never chosen (registration interrupted between the two
    steps): /start must resume at the gender step, not treat the row as complete."""

    async def run():
        await db.create_or_update_user(2, "u", name="Nina")

        state = _FakeState()
        msg = _FakeMessage(2)
        await start.cmd_start(msg, state)

        assert state.state == RegistrationState.waiting_for_gender
        assert "Nina" in msg.answers[-1][0]

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_start_greets_fully_onboarded_user_as_returning():
    async def run():
        await db.create_or_update_user(3, "u", name="Nina", gender="female")

        state = _FakeState(state="stale-state")
        msg = _FakeMessage(3)
        await start.cmd_start(msg, state)

        assert state.state is None
        assert "возвращением" in msg.answers[-1][0].lower()

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
@pytest.mark.parametrize("user_id", [10])
def test_new_redirects_unknown_user_to_start(user_id):
    async def run():
        state = _FakeState()
        msg = _FakeMessage(user_id)
        await generation.cmd_new(msg, state)

        assert "/start" in msg.answers[-1][0]
        assert state.state != GenerationState.choosing_sphere

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_new_redirects_partial_onboarding_to_start():
    async def run():
        await db.create_or_update_user(11, "u", name="Nina")  # no gender yet

        state = _FakeState()
        msg = _FakeMessage(11)
        await generation.cmd_new(msg, state)

        assert "/start" in msg.answers[-1][0]
        assert state.state != GenerationState.choosing_sphere

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_new_proceeds_for_fully_onboarded_user():
    async def run():
        await db.create_or_update_user(12, "u", name="Nina", gender="female")

        state = _FakeState()
        msg = _FakeMessage(12)
        await generation.cmd_new(msg, state)

        assert state.state == GenerationState.choosing_sphere

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_subscribe_redirects_partial_onboarding_to_start():
    async def run():
        await db.create_or_update_user(20, "u")  # no name/gender

        state = _FakeState()
        msg = _FakeMessage(20)
        await subscribe.cmd_subscribe(msg, state)

        assert "/start" in msg.answers[-1][0]

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_subscribe_proceeds_for_fully_onboarded_user():
    async def run():
        await db.create_or_update_user(21, "u", name="Nina", gender="female")

        state = _FakeState()
        msg = _FakeMessage(21)
        await subscribe.cmd_subscribe(msg, state)

        assert any("Твои подписки" in text for text, _ in msg.answers)

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_profile_redirects_partial_onboarding_to_start():
    async def run():
        await db.create_or_update_user(30, "u", name="Nina")  # no gender

        state = _FakeState()
        msg = _FakeMessage(30)
        await start.cmd_profile(msg, state)

        assert "/start" in msg.answers[-1][0]

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_profile_proceeds_for_fully_onboarded_user():
    async def run():
        await db.create_or_update_user(31, "u", name="Nina", gender="female")

        state = _FakeState()
        msg = _FakeMessage(31)
        await start.cmd_profile(msg, state)

        assert any("Твой профиль" in text for text, _ in msg.answers)

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_language_redirects_partial_onboarding_to_start():
    async def run():
        await db.create_or_update_user(40, "u")  # no name/gender

        state = _FakeState()
        msg = _FakeMessage(40)
        await start.cmd_language(msg, state)

        assert "/start" in msg.answers[-1][0]

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_language_proceeds_for_fully_onboarded_user():
    async def run():
        await db.create_or_update_user(41, "u", name="Nina", gender="female")

        state = _FakeState()
        msg = _FakeMessage(41)
        await start.cmd_language(msg, state)

        assert "Выбери язык" in msg.answers[-1][0]

    asyncio.run(run())
