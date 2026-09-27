"""Regression test for Stage 4 item J: /reset must clear FSM state along with DB data.

handlers/start.py's cmd_reset already called delete_user_completely then state.clear(); this
pins that contract so a future change cannot silently drop the state.clear() call and leave a
stale mid-flow FSM state (e.g. a generation or subscription wizard) behind after a user resets.
"""
import asyncio
from types import SimpleNamespace

import pytest

import database as db
from handlers import start
from states import GenerationState


class _FakeState:
    def __init__(self, state=None, **data):
        self.state = state
        self.data = dict(data)
        self.cleared = False

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
        self.cleared = True


class _FakeMessage:
    def __init__(self, user_id):
        self.from_user = SimpleNamespace(id=user_id, username="u")
        self.answers = []

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))


@pytest.mark.usefixtures("initialized_db")
def test_reset_clears_fsm_state_and_deletes_user_data():
    async def run():
        await db.create_or_update_user(801, "u", name="Nina", gender="female")
        await db.record_interactive_generation(801)

        state = _FakeState(GenerationState.choosing_style, sphere="money", theme_text="stale")
        msg = _FakeMessage(801)

        await start.cmd_reset(msg, state)

        assert state.cleared is True
        assert state.state is None
        assert state.data == {}
        assert await db.get_user(801) is None
        assert await db.get_generation_usage_today(801) == 0
        assert "/start" in msg.answers[-1][0]

    asyncio.run(run())
