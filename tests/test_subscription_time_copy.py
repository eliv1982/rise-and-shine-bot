"""Regression test for Stage 4 item I: subscription-time copy must not be ambiguous about
which timezone "the entered time" actually is.

The scheduler only ever runs on Moscow time (scheduler.MOSCOW); Stage 4 does not add per-user
timezones. Before this fix, the hour-selection prompts said "bot time" / "по времени бота",
which does not tell the user what that time actually is. They now say Moscow time / MSK
explicitly, both for a new subscription and when editing an existing one's time.
"""
import asyncio
from types import SimpleNamespace

import pytest

import database as db
from handlers import subscribe
from states import SubscriptionState

USER_ID = 901


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
    def __init__(self):
        self.edits = []
        self.answers = []

    async def edit_text(self, text, reply_markup=None):
        self.edits.append((text, reply_markup))

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))


class _FakeCallback:
    def __init__(self, data):
        self.data = data
        self.from_user = SimpleNamespace(id=USER_ID)
        self.message = _FakeMessage()

    async def answer(self, text=None):
        return None


async def _click(handler, data, state):
    callback = _FakeCallback(data)
    await handler(callback, state)
    return callback


@pytest.fixture
def sub_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "time_copy.db"))

    async def setup():
        await db.init_db()
        await db.create_or_update_user(USER_ID, "u", name="U", language="ru")

    asyncio.run(setup())


def test_new_subscription_hour_prompt_names_moscow_time(sub_db):
    async def run():
        state = _FakeState(
            SubscriptionState.choosing_style,
            language="ru",
            subscription_action="add",
            subscription_mode="weekly_balance",
            sphere="random",
            allowed_visual_modes=["illustration"],
        )
        callback = await _click(subscribe.sub_choose_style, "style:auto", state)
        text = callback.message.edits[-1][0]
        assert "МСК" in text

    asyncio.run(run())


def test_edit_time_hour_prompt_names_moscow_time(sub_db):
    async def run():
        sub_id = await db.create_subscription(
            USER_ID, "random", None, "auto", "ru", 8, 0,
            subscription_mode="weekly_balance",
        )
        state = _FakeState()
        callback = await _click(subscribe.sub_edit_field, f"subfield:{sub_id}:time", state)
        text = callback.message.answers[-1][0]
        assert "МСК" in text

    asyncio.run(run())
