import asyncio
from types import SimpleNamespace

import pytest

import database as db
from handlers import smalltalk


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


class _FakeMessage:
    def __init__(self, text, user_id=1001):
        self.text = text
        self.from_user = SimpleNamespace(id=user_id)
        self.answers = []

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))


def _fake_settings(limit):
    return SimpleNamespace(smalltalk_daily_limit=limit)


@pytest.mark.usefixtures("initialized_db")
def test_registered_user_below_limit_gets_smalltalk(monkeypatch):
    async def run():
        await db.create_or_update_user(1001, "u", name="Ann", gender="female")

        monkeypatch.setattr(smalltalk, "get_settings", lambda: _fake_settings(5))
        called = {"count": 0}

        async def _fake_reply(text, language="ru"):
            called["count"] += 1
            return "Привет!"

        monkeypatch.setattr(smalltalk, "generate_smalltalk_reply", _fake_reply)

        msg = _FakeMessage("просто делюсь мыслью")
        await smalltalk.smalltalk(msg, _FakeState())

        assert called["count"] == 1
        assert msg.answers[-1][0] == "Привет!"
        assert await db.get_smalltalk_usage_today(1001) == 1

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_unregistered_user_does_not_invoke_llm(monkeypatch):
    async def run():
        called = {"count": 0}

        async def _fake_reply(*_args, **_kwargs):
            called["count"] += 1
            return "should not happen"

        monkeypatch.setattr(smalltalk, "generate_smalltalk_reply", _fake_reply)

        msg = _FakeMessage("hi there, just chatting", user_id=999)
        await smalltalk.smalltalk(msg, _FakeState())

        assert called["count"] == 0
        assert "/start" in msg.answers[-1][0]
        assert await db.get_user(999) is None

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_incomplete_registration_row_does_not_reach_llm(monkeypatch):
    """A `users` row with no name/gender yet (interrupted onboarding - see
    database.is_onboarding_complete) must not be treated as a completed registration:
    otherwise a user whose /start was interrupted (bot restart, or /cancel mid-registration)
    could reach the paid LLM path before ever finishing onboarding."""

    async def run():
        await db.create_or_update_user(1002, "u")  # no name/gender

        monkeypatch.setattr(smalltalk, "get_settings", lambda: _fake_settings(5))
        called = {"count": 0}

        async def _fake_reply(*_args, **_kwargs):
            called["count"] += 1
            return "ok"

        monkeypatch.setattr(smalltalk, "generate_smalltalk_reply", _fake_reply)

        msg = _FakeMessage("просто общаюсь", user_id=1002)
        await smalltalk.smalltalk(msg, _FakeState())

        assert called["count"] == 0
        assert "/start" in msg.answers[-1][0]

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_registration_with_name_but_no_gender_does_not_reach_llm(monkeypatch):
    """Half-finished registration (name captured, gender step never completed) is the
    interrupted-onboarding case in practice - see database.is_onboarding_complete - and
    must be rejected the same way a fully empty row is."""

    async def run():
        await db.create_or_update_user(1010, "u", name="Ira")  # no gender

        monkeypatch.setattr(smalltalk, "get_settings", lambda: _fake_settings(5))
        called = {"count": 0}

        async def _fake_reply(*_args, **_kwargs):
            called["count"] += 1
            return "ok"

        monkeypatch.setattr(smalltalk, "generate_smalltalk_reply", _fake_reply)

        msg = _FakeMessage("просто общаюсь", user_id=1010)
        await smalltalk.smalltalk(msg, _FakeState())

        assert called["count"] == 0
        assert "/start" in msg.answers[-1][0]

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_daily_limit_blocks_additional_calls(monkeypatch):
    async def run():
        await db.create_or_update_user(1003, "u", name="Bo", gender="male")
        monkeypatch.setattr(smalltalk, "get_settings", lambda: _fake_settings(2))
        called = {"count": 0}

        async def _fake_reply(*_args, **_kwargs):
            called["count"] += 1
            return "ok"

        monkeypatch.setattr(smalltalk, "generate_smalltalk_reply", _fake_reply)

        for i in range(2):
            msg = _FakeMessage(f"болтаю {i}", user_id=1003)
            await smalltalk.smalltalk(msg, _FakeState())

        msg3 = _FakeMessage("ещё сообщение", user_id=1003)
        await smalltalk.smalltalk(msg3, _FakeState())

        assert called["count"] == 2
        assert "2" in msg3.answers[-1][0]
        assert await db.get_smalltalk_usage_today(1003) == 2

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_limit_resets_next_utc_day(monkeypatch):
    async def run():
        await db.create_or_update_user(1004, "u", name="Cy", gender="male")
        monkeypatch.setattr(smalltalk, "get_settings", lambda: _fake_settings(1))

        async def _fake_reply(*_args, **_kwargs):
            return "ok"

        monkeypatch.setattr(smalltalk, "generate_smalltalk_reply", _fake_reply)

        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")
        msg1 = _FakeMessage("привет", user_id=1004)
        await smalltalk.smalltalk(msg1, _FakeState())
        assert msg1.answers[-1][0] == "ok"

        msg2 = _FakeMessage("ещё раз", user_id=1004)
        await smalltalk.smalltalk(msg2, _FakeState())
        assert "1" in msg2.answers[-1][0]

        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-02")
        msg3 = _FakeMessage("новый день", user_id=1004)
        await smalltalk.smalltalk(msg3, _FakeState())
        assert msg3.answers[-1][0] == "ok"

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_provider_failure_releases_reservation(monkeypatch):
    async def run():
        await db.create_or_update_user(1005, "u", name="Dee", gender="female")
        monkeypatch.setattr(smalltalk, "get_settings", lambda: _fake_settings(5))

        async def _raise(*_args, **_kwargs):
            raise RuntimeError("provider down")

        monkeypatch.setattr(smalltalk, "generate_smalltalk_reply", _raise)

        msg = _FakeMessage("привет", user_id=1005)
        await smalltalk.smalltalk(msg, _FakeState())

        assert await db.get_smalltalk_usage_today(1005) == 0
        assert msg.answers  # the friendly fallback was still sent

        # The freed capacity can be used again right away.
        async def _fake_reply(*_args, **_kwargs):
            return "ok"

        monkeypatch.setattr(smalltalk, "generate_smalltalk_reply", _fake_reply)
        msg2 = _FakeMessage("ещё раз", user_id=1005)
        await smalltalk.smalltalk(msg2, _FakeState())
        assert msg2.answers[-1][0] == "ok"

    asyncio.run(run())


class _FailingDeliveryMessage(_FakeMessage):
    """A message whose first send raises, simulating a Telegram delivery failure after
    the LLM reply was already generated."""

    def __init__(self, text, user_id=1001):
        super().__init__(text, user_id)
        self.attempts = 0

    async def answer(self, text, reply_markup=None):
        self.attempts += 1
        raise RuntimeError("telegram delivery failed")


@pytest.mark.usefixtures("initialized_db")
def test_delivery_failure_releases_reservation(monkeypatch):
    """Regression: a successful LLM reply that Telegram then fails to deliver must not
    permanently consume the day's quota (the user never received anything)."""

    async def run():
        await db.create_or_update_user(1009, "u", name="Hana", gender="female")
        monkeypatch.setattr(smalltalk, "get_settings", lambda: _fake_settings(5))

        async def _fake_reply(*_args, **_kwargs):
            return "ok"

        monkeypatch.setattr(smalltalk, "generate_smalltalk_reply", _fake_reply)

        msg = _FailingDeliveryMessage("привет", user_id=1009)
        with pytest.raises(RuntimeError):
            await smalltalk.smalltalk(msg, _FakeState())

        assert msg.attempts == 1
        assert await db.get_smalltalk_usage_today(1009) == 0

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_concurrent_smalltalk_requests_do_not_bypass_quota(monkeypatch):
    async def run():
        await db.create_or_update_user(1006, "u", name="Eli", gender="male")
        monkeypatch.setattr(smalltalk, "get_settings", lambda: _fake_settings(3))
        called = {"count": 0}

        async def _fake_reply(*_args, **_kwargs):
            called["count"] += 1
            await asyncio.sleep(0)
            return "ok"

        monkeypatch.setattr(smalltalk, "generate_smalltalk_reply", _fake_reply)

        messages = [_FakeMessage(f"msg {i}", user_id=1006) for i in range(10)]
        await asyncio.gather(*[smalltalk.smalltalk(m, _FakeState()) for m in messages])

        assert called["count"] == 3
        assert await db.get_smalltalk_usage_today(1006) == 3

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_smalltalk_usage_does_not_consume_generation_quota(monkeypatch):
    async def run():
        await db.create_or_update_user(1007, "u", name="Fay", gender="female")
        monkeypatch.setattr(smalltalk, "get_settings", lambda: _fake_settings(5))

        async def _fake_reply(*_args, **_kwargs):
            return "ok"

        monkeypatch.setattr(smalltalk, "generate_smalltalk_reply", _fake_reply)

        for i in range(3):
            await smalltalk.smalltalk(_FakeMessage(f"hi {i}", user_id=1007), _FakeState())

        assert await db.get_smalltalk_usage_today(1007) == 3
        assert await db.get_generation_usage_today(1007) == 0
        allowed, used = await db.can_start_interactive_generation(1007, 5)
        assert allowed and used == 0

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_cross_midnight_rollover_during_request_does_not_erase_next_day_reservation(monkeypatch):
    """Handler-level integration proof for the Stage 7A cross-midnight release blocker,
    mirrored onto the smalltalk quota path (see the identical
    test_generation_reservation_handler.test_cross_midnight_rollover_during_request_does_not_erase_next_day_reservation
    for the interactive-generation counterpart).

    If the UTC day rolls over *during* this request's paid LLM call (between its own
    reserve and its own later release), and a second, independent request already
    reserved on the new day before this one reaches its release, this request's release -
    which threads through the exact day it reserved on, per `reserve_smalltalk_usage` /
    `release_smalltalk_usage` in database.py - must not erase that other reservation.
    """

    async def _reply_that_crosses_midnight_then_fails(*_args, **_kwargs):
        # Simulate the UTC day rolling over mid-request, and an independent Request B
        # reserving on the new day before this request (Request A) reaches its release.
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-02")
        reserved_b, _day_b = await db.reserve_smalltalk_usage(1012, 5)
        assert reserved_b is True
        raise RuntimeError("provider down")

    async def run():
        await db.create_or_update_user(1012, "u", name="Jo", gender="male")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")
        monkeypatch.setattr(smalltalk, "get_settings", lambda: _fake_settings(5))
        monkeypatch.setattr(smalltalk, "generate_smalltalk_reply", _reply_that_crosses_midnight_then_fails)

        msg = _FakeMessage("привет", user_id=1012)
        # Request A reserves on day 1, then the mocked LLM call above flips "today" to
        # day 2 and has Request B reserve there, before Request A's own failure/release.
        await smalltalk.smalltalk(msg, _FakeState())

        # "Today" is now day 2, where Request B holds a valid reservation of 1. Request A's
        # release (keyed on its own captured day-1 reservation) must not have erased it.
        assert await db.get_smalltalk_usage_today(1012) == 1

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_cancellation_before_reply_does_not_release_reservation(monkeypatch):
    """Requirement 7 (cancellation-safe lifecycle, "if currently supported"): unlike the
    interactive-generation handler (which wraps its paid work in try/finally), the
    smalltalk handler only wraps the LLM call in `except Exception`, and
    `asyncio.CancelledError` is not an `Exception` subclass (Python 3.8+), so it is not
    caught here. This fix only changes which UTC day a release keys off, not this
    exception-handling shape, so a cancellation still propagates without releasing the
    reservation - exactly the same, unaltered behavior as before this fix.
    """

    async def _cancelled_reply(*_args, **_kwargs):
        raise asyncio.CancelledError()

    async def run():
        await db.create_or_update_user(1011, "u", name="Ivy", gender="female")
        monkeypatch.setattr(smalltalk, "get_settings", lambda: _fake_settings(5))
        monkeypatch.setattr(smalltalk, "generate_smalltalk_reply", _cancelled_reply)

        msg = _FakeMessage("привет", user_id=1011)
        with pytest.raises(asyncio.CancelledError):
            await smalltalk.smalltalk(msg, _FakeState())

        # Matches the pre-existing (unaltered) contract: the reservation is not released.
        assert await db.get_smalltalk_usage_today(1011) == 1

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_main_menu_intent_routes_without_calling_llm_or_quota(monkeypatch):
    async def run():
        await db.create_or_update_user(1008, "u", name="Gia", gender="female")
        monkeypatch.setattr(smalltalk, "get_settings", lambda: _fake_settings(5))
        llm_called = {"count": 0}

        async def _fake_reply(*_args, **_kwargs):
            llm_called["count"] += 1
            return "ok"

        monkeypatch.setattr(smalltalk, "generate_smalltalk_reply", _fake_reply)

        routed = {"called": False}

        async def _fake_route(_message, _state, _text, _language):
            routed["called"] = True
            return True

        monkeypatch.setattr("handlers.start.route_main_menu_intent", _fake_route)

        msg = _FakeMessage("создай новый настрой", user_id=1008)
        await smalltalk.smalltalk(msg, _FakeState())

        assert routed["called"] is True
        assert llm_called["count"] == 0
        assert await db.get_smalltalk_usage_today(1008) == 0

    asyncio.run(run())
