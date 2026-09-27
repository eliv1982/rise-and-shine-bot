"""Regression tests for the ``sub:open`` / ``sub:change`` photo-message routing.

``handlers/generation.py`` used to register its own ``sub:open`` callback handler
that called ``cmd_subscribe(callback.message, state)`` - reading
``callback.message.from_user.id`` (the bot's own id, since ``callback.message`` is
the bot's outgoing message) instead of the id of the user who clicked the button.
It was masked because ``subscribe.router`` is included first in ``bot.py`` and
already owned the same callback data, so the buggy handler never actually ran -
but that made correctness depend on router registration order rather than on the
routing being unambiguous.

The fix consolidates ``sub:open`` into exactly one handler
(``handlers.subscribe.sub_open_from_result``), which uses ``callback.from_user.id``
and sends a new message (the generation/delivery result it is clicked from is a
photo message, so its caption cannot be edited in place).

``sub:change`` (from ``subscription_after_keyboard``, attached to the daily-delivery
photo sent by ``scheduler.py``) had the same structural bug: it used to be grouped
with ``sub:dash`` under ``sub_dashboard_callback``, which calls
``callback.message.edit_text`` - a call Telegram rejects on a media message. The fix
moves ``sub:change`` into the same media-safe ``sub_open_from_result`` handler used
by ``sub:open``, rather than adding a second handler for it.
"""
import asyncio
from types import SimpleNamespace

import pytest

import database as db
from handlers import generation, subscribe

USER_ID = 951
BOT_ID = 1  # distinct from USER_ID: simulates callback.message.from_user being the bot


class _FakeState:
    def __init__(self):
        self.cleared = False

    async def clear(self):
        self.cleared = True


class _FakeMessage:
    """A generation/delivery result: a photo message sent by the bot."""

    def __init__(self):
        self.from_user = SimpleNamespace(id=BOT_ID)
        self.edits = []
        self.answers = []

    async def edit_text(self, text, reply_markup=None):
        self.edits.append((text, reply_markup))

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))


class _FakeCallback:
    def __init__(self, data):
        self.data = data
        self.from_user = SimpleNamespace(id=USER_ID)  # the user who actually clicked
        self.message = _FakeMessage()
        self.answered = False

    async def answer(self, text=None):
        self.answered = True


async def _matching_handlers(router, data):
    event = SimpleNamespace(data=data)
    matches = []
    for handler in router.callback_query.handlers:
        result, _ = await handler.check(event)
        if result:
            matches.append(handler.callback)
    return matches


def test_sub_open_is_routed_exactly_once():
    """Exactly one registered handler across the app matches ``sub:open``."""

    async def run():
        generation_matches = await _matching_handlers(generation.router, "sub:open")
        subscribe_matches = await _matching_handlers(subscribe.router, "sub:open")
        assert generation_matches == []
        assert subscribe_matches == [subscribe.sub_open_from_result]

    asyncio.run(run())


def test_sub_change_is_routed_exactly_once_to_the_media_safe_handler():
    """``sub:change`` must resolve to exactly one handler: the media-safe one.

    It must not also match ``sub_dashboard_callback`` (the ``edit_text``-based
    handler for ``sub:dash``), and no other router may shadow or duplicate it.
    """

    async def run():
        generation_matches = await _matching_handlers(generation.router, "sub:change")
        subscribe_matches = await _matching_handlers(subscribe.router, "sub:change")
        assert generation_matches == []
        assert subscribe_matches == [subscribe.sub_open_from_result]

    asyncio.run(run())


@pytest.fixture
def sub_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "sub_open.db"))

    async def setup():
        await db.init_db()
        await db.create_or_update_user(USER_ID, "u", name="U", language="ru")

    asyncio.run(setup())


def test_sub_open_uses_clicking_user_not_message_author(sub_db):
    """The canonical handler must read callback.from_user.id, not callback.message.from_user.id."""

    async def run():
        # Only USER_ID (the clicking user) has a subscription; BOT_ID (callback.message's
        # author) has none. If the handler regressed to reading callback.message.from_user.id,
        # the dashboard would wrongly show zero active subscriptions.
        await db.create_subscription(
            USER_ID, "random", None, "auto", "ru", 8, 0,
            subscription_mode="weekly_balance",
        )

        callback = _FakeCallback("sub:open")
        state = _FakeState()

        await subscribe.sub_open_from_result(callback, state)

        # A new message was sent (the photo result's caption was never edited).
        assert callback.message.edits == []
        assert len(callback.message.answers) == 1
        assert callback.answered is True
        assert state.cleared is True

        dashboard_text = callback.message.answers[-1][0]
        assert "Активных подписок: 1/" in dashboard_text

    asyncio.run(run())


def test_sub_change_from_photo_message_uses_clicking_user_and_never_edits(sub_db):
    """``sub:change`` clicked on the daily-delivery photo must behave like ``sub:open``.

    Regression coverage for the Stage 5 follow-up bug: ``sub:change`` is only ever
    attached (via ``subscription_after_keyboard``) to a photo message sent by
    ``scheduler.py``, so it must never call ``edit_text`` on that message, and it
    must use ``callback.from_user.id`` (the clicking user), not
    ``callback.message.from_user.id`` (the bot, as the message author).
    """

    async def run():
        # Only USER_ID (the clicking user) has a subscription; BOT_ID (the photo
        # message's author) has none. Reading the wrong id would show 0 subscriptions.
        await db.create_subscription(
            USER_ID, "random", None, "auto", "ru", 8, 0,
            subscription_mode="weekly_balance",
        )

        callback = _FakeCallback("sub:change")
        state = _FakeState()

        await subscribe.sub_open_from_result(callback, state)

        # The photo message's caption was never edited - a new message was sent.
        assert callback.message.edits == []
        assert len(callback.message.answers) == 1
        assert callback.answered is True
        assert state.cleared is True

        dashboard_text = callback.message.answers[-1][0]
        assert "Активных подписок: 1/" in dashboard_text

    asyncio.run(run())
