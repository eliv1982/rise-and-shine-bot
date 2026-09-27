"""Regression tests for Stage 4 item G: subscription setup's relationship-subfocus path.

Root cause: SubscriptionState.choosing_relationship_subsphere and its handler
(sub_choose_relationship_subsphere) existed, and the manual /new flow already supported
sphere=relationships -> subfocus -> visual selection with matching persistence
(subscriptions.subsphere) and scheduler delivery (scheduler._deliver_subscription reads
sub["subsphere"]). But handlers/subscribe.py's sphere-selection handler (sub_choose_sphere)
never transitioned into that state for sphere == "relationships", either when adding a new
subscription or when editing an existing one's sphere - so the state was unreachable and every
relationship subscription silently lost its subfocus.
"""
import asyncio
from types import SimpleNamespace

import pytest

import database as db
from handlers import subscribe
from states import SubscriptionState

USER_ID = 601


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


def _callback_data(markup) -> set[str]:
    return {button.callback_data for row in markup.inline_keyboard for button in row}


@pytest.fixture
def sub_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "relationship_subsphere.db"))

    async def setup():
        await db.init_db()
        await db.create_or_update_user(USER_ID, "u", name="U", language="ru")

    asyncio.run(setup())


# ---------------------------------------------------------------------------
# New subscription: relationships sphere reaches subfocus selection.
# ---------------------------------------------------------------------------


def test_choosing_relationships_sphere_reaches_subfocus_step(sub_db):
    async def run():
        state = _FakeState(
            SubscriptionState.choosing_sphere,
            language="ru",
            subscription_action="add",
            subscription_mode="sphere_focus",
        )
        callback = await _click(subscribe.sub_choose_sphere, "sphere:relationships", state)

        assert state.state == SubscriptionState.choosing_relationship_subsphere
        assert state.data["sphere"] == "relationships"
        markup = callback.message.edits[-1][1]
        assert _callback_data(markup) == {"subsphere:partner", "subsphere:colleagues", "subsphere:friends"}

    asyncio.run(run())


def test_non_relationships_sphere_still_skips_subfocus_step(sub_db):
    async def run():
        state = _FakeState(
            SubscriptionState.choosing_sphere,
            language="ru",
            subscription_action="add",
            subscription_mode="sphere_focus",
        )
        await _click(subscribe.sub_choose_sphere, "sphere:money", state)

        assert state.state == SubscriptionState.choosing_visual_mode
        assert state.data["subsphere"] is None

    asyncio.run(run())


async def _finish_new_relationship_subscription(subsphere_callback: str) -> dict:
    """Walk sphere:relationships -> subsphere -> visual -> style -> hour -> minute -> confirm."""
    state = _FakeState(
        SubscriptionState.choosing_sphere,
        language="ru",
        subscription_action="add",
        subscription_mode="sphere_focus",
    )
    await _click(subscribe.sub_choose_sphere, "sphere:relationships", state)
    await _click(subscribe.sub_choose_relationship_subsphere, subsphere_callback, state)
    assert state.state == SubscriptionState.choosing_visual_mode

    await _click(subscribe.sub_choose_visual_mix, "visualmix:illustration", state)
    await _click(subscribe.sub_choose_style, "style:auto", state)
    await _click(subscribe.sub_choose_hour, "hour:8", state)
    await _click(subscribe.sub_choose_minute, "minute:0", state)
    await _click(subscribe.sub_confirm, "sub:confirm", state)

    (saved,) = await db.get_active_subscriptions(USER_ID)
    return saved


def test_subfocus_persists_into_new_subscription(sub_db):
    async def run():
        saved = await _finish_new_relationship_subscription("subsphere:partner")
        assert saved["sphere"] == "relationships"
        assert saved["subsphere"] == "partner"
        assert saved["subscription_sphere"] == "relationships"

    asyncio.run(run())


# ---------------------------------------------------------------------------
# Editing an existing subscription's sphere.
# ---------------------------------------------------------------------------


async def _create_relationship_subscription(subsphere: str = "partner") -> int:
    return await db.create_subscription(
        user_id=USER_ID,
        sphere="relationships",
        subsphere=subsphere,
        image_style="auto",
        language="ru",
        hour=8,
        minute=0,
        subscription_mode="sphere_focus",
        subscription_sphere="relationships",
        subscription_style_mode="auto",
        visual_mode="illustration",
        allowed_visual_modes=["illustration"],
    )


def test_editing_sphere_to_relationships_reaches_subfocus_then_persists(sub_db):
    """Editing an existing (non-relationship) subscription's sphere to relationships must
    also collect a subfocus before saving, not silently drop it like sub_choose_sphere's
    edit branch used to (it forced subsphere=None unconditionally)."""

    async def run():
        sub_id = await db.create_subscription(
            user_id=USER_ID,
            sphere="money",
            subsphere=None,
            image_style="auto",
            language="ru",
            hour=8,
            minute=0,
            subscription_mode="sphere_focus",
            subscription_sphere="money",
            subscription_style_mode="auto",
            visual_mode="illustration",
            allowed_visual_modes=["illustration"],
        )
        state = _FakeState()
        await state.update_data(edit_subscription_id=sub_id, partial_edit_field="sphere")

        callback = await _click(subscribe.sub_choose_sphere, "sphere:relationships", state)
        # Not yet saved: still mid-flow, waiting for the subfocus pick.
        assert state.state == SubscriptionState.choosing_relationship_subsphere
        unsaved = await db.get_subscription_by_id(sub_id, USER_ID)
        assert unsaved["sphere"] == "money"

        await _click(subscribe.sub_choose_relationship_subsphere, "subsphere:colleagues", state)

        saved = await db.get_subscription_by_id(sub_id, USER_ID)
        assert saved["sphere"] == "relationships"
        assert saved["subsphere"] == "colleagues"
        assert saved["subscription_sphere"] == "relationships"
        # The partial-edit flow clears state when it finishes, like every other subfield edit.
        assert state.state is None

    asyncio.run(run())


def test_editing_relationship_subscription_can_change_subfocus(sub_db):
    async def run():
        sub_id = await _create_relationship_subscription("partner")
        state = _FakeState()
        await state.update_data(edit_subscription_id=sub_id, partial_edit_field="sphere")

        await _click(subscribe.sub_choose_sphere, "sphere:relationships", state)
        await _click(subscribe.sub_choose_relationship_subsphere, "subsphere:friends", state)

        saved = await db.get_subscription_by_id(sub_id, USER_ID)
        assert saved["subsphere"] == "friends"

    asyncio.run(run())


def test_editing_away_from_relationships_clears_stale_subfocus(sub_db):
    async def run():
        sub_id = await _create_relationship_subscription("partner")
        state = _FakeState()
        await state.update_data(edit_subscription_id=sub_id, partial_edit_field="sphere")

        await _click(subscribe.sub_choose_sphere, "sphere:money", state)

        saved = await db.get_subscription_by_id(sub_id, USER_ID)
        assert saved["sphere"] == "money"
        assert saved["subsphere"] is None

    asyncio.run(run())
