"""Handler-level regression tests for the atomic interactive-generation reservation.

These exercise `handlers.generation._run_generation` against a real (temp) SQLite
database rather than mocking the database layer, to prove the reservation is taken
before any paid provider call, and released whenever the flow does not end in a
delivered Telegram message. See test_generation_reservation.py for the pure
database-layer reservation/release/concurrency tests.
"""
import asyncio
from types import SimpleNamespace

import pytest

import database as db
from handlers import generation


class _FakeState:
    def __init__(self, data=None):
        self.data = dict(data or {})
        self.state = None
        self.cleared = False

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def set_state(self, state):
        self.state = state

    async def clear(self):
        self.data = {}
        self.state = None
        self.cleared = True


class _FakeMessage:
    def __init__(self, user_id=123, *, fail_photo=False):
        self.from_user = SimpleNamespace(id=user_id)
        self.answers = []
        self.photos = []
        self.fail_photo = fail_photo

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))

    async def answer_photo(self, photo, caption=None, reply_markup=None):
        if self.fail_photo:
            raise RuntimeError("telegram send failed")
        self.photos.append((photo, caption, reply_markup))
        return SimpleNamespace(photo=[SimpleNamespace(file_id="fake_file_id")])


def _settings(*, generation_daily_limit, disable_daily_generation_limit=False, **overrides):
    base = dict(
        disable_daily_generation_limit=disable_daily_generation_limit,
        generation_daily_limit=generation_daily_limit,
        llm_image_prompt_enabled=False,
        show_image_debug=False,
        image_model="image-model",
        image_size="1024x1024",
        text_planner_shadow_enabled=False,
        text_planner_controlled_enabled=False,
        scene_planner_shadow_enabled=False,
        scene_planner_image_prompt_enabled=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _state(**overrides):
    data = dict(
        sphere="inner_peace",
        subsphere=None,
        style="auto",
        visual_mode="illustration",
        custom_style_description=None,
    )
    data.update(overrides)
    return _FakeState(data)


async def _fake_get_user(_uid):
    return {"language": "en", "gender": "female"}


async def _fake_generate_affirmations(**_kwargs):
    return ["I trust myself", "I move gently", "I stay present", "I choose clarity"]


async def _fake_build_enriched_image_prompt(**_kwargs):
    return "prompt", "template"


async def _fake_generate_image(**_kwargs):
    return "fake_image.png"


def _patch_successful_providers(monkeypatch):
    monkeypatch.setattr(generation, "generate_affirmations", _fake_generate_affirmations)
    monkeypatch.setattr(generation, "build_enriched_image_prompt", _fake_build_enriched_image_prompt)
    monkeypatch.setattr(generation, "generate_image", _fake_generate_image)
    monkeypatch.setattr(generation, "log_generation_ok", lambda *_a, **_k: None)


@pytest.mark.usefixtures("initialized_db")
def test_at_limit_generation_performs_zero_paid_provider_calls(monkeypatch):
    async def _unexpected_affirmations(**_kwargs):
        raise AssertionError("generate_affirmations must not be called when quota is exhausted")

    async def _unexpected_image(**_kwargs):
        raise AssertionError("generate_image must not be called when quota is exhausted")

    async def run():
        await db.create_or_update_user(301, "u", name="Test", gender="female")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")
        # Exhaust the quota before the handler ever runs.
        for _ in range(2):
            assert await db.reserve_generation_usage(301, 2) is True

        monkeypatch.setattr(generation, "get_user", _fake_get_user)
        monkeypatch.setattr(generation, "get_settings", lambda: _settings(generation_daily_limit=2))
        monkeypatch.setattr(generation, "generate_affirmations", _unexpected_affirmations)
        monkeypatch.setattr(generation, "generate_image", _unexpected_image)

        message = _FakeMessage(user_id=301)
        state = _state()

        await generation._run_generation(message, state, theme_text=None, user_telegram_id=301)

        assert message.photos == []
        assert len(message.answers) == 1
        assert "daily limit" in message.answers[0][0].lower()
        # No additional reservation was made beyond the two that exhausted the cap.
        assert await db.get_generation_usage_today(301) == 2

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_successful_generation_consumes_exactly_one_quota_unit(monkeypatch):
    async def run():
        await db.create_or_update_user(302, "u", name="Test", gender="female")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        monkeypatch.setattr(generation, "get_user", _fake_get_user)
        monkeypatch.setattr(generation, "get_settings", lambda: _settings(generation_daily_limit=5))
        _patch_successful_providers(monkeypatch)

        message = _FakeMessage(user_id=302)
        state = _state()

        await generation._run_generation(message, state, theme_text="Dignity and self-trust", user_telegram_id=302)

        assert len(message.photos) == 1
        assert await db.get_generation_usage_today(302) == 1

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_text_provider_failure_releases_the_reservation(monkeypatch):
    async def _failing_affirmations(**_kwargs):
        raise RuntimeError("provider down")

    async def run():
        await db.create_or_update_user(303, "u", name="Test", gender="female")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        monkeypatch.setattr(generation, "get_user", _fake_get_user)
        monkeypatch.setattr(generation, "get_settings", lambda: _settings(generation_daily_limit=5))
        monkeypatch.setattr(generation, "generate_affirmations", _failing_affirmations)

        message = _FakeMessage(user_id=303)
        state = _state()

        await generation._run_generation(message, state, theme_text="Dignity and self-trust", user_telegram_id=303)

        assert message.photos == []
        # The reservation taken before the paid call must be released, not left charged.
        assert await db.get_generation_usage_today(303) == 0

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_image_generation_failure_releases_the_reservation(monkeypatch):
    async def _failing_image(**_kwargs):
        raise RuntimeError("image provider down")

    async def run():
        await db.create_or_update_user(304, "u", name="Test", gender="female")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        monkeypatch.setattr(generation, "get_user", _fake_get_user)
        monkeypatch.setattr(generation, "get_settings", lambda: _settings(generation_daily_limit=5))
        monkeypatch.setattr(generation, "generate_affirmations", _fake_generate_affirmations)
        monkeypatch.setattr(generation, "build_enriched_image_prompt", _fake_build_enriched_image_prompt)
        monkeypatch.setattr(generation, "generate_image", _failing_image)

        message = _FakeMessage(user_id=304)
        state = _state()

        await generation._run_generation(message, state, theme_text="Dignity and self-trust", user_telegram_id=304)

        assert message.photos == []
        assert await db.get_generation_usage_today(304) == 0

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_telegram_send_failure_releases_the_reservation(monkeypatch):
    async def run():
        await db.create_or_update_user(305, "u", name="Test", gender="female")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        monkeypatch.setattr(generation, "get_user", _fake_get_user)
        monkeypatch.setattr(generation, "get_settings", lambda: _settings(generation_daily_limit=5))
        _patch_successful_providers(monkeypatch)

        message = _FakeMessage(user_id=305, fail_photo=True)
        state = _state()

        with pytest.raises(RuntimeError, match="telegram send failed"):
            await generation._run_generation(message, state, theme_text="Dignity and self-trust", user_telegram_id=305)

        assert await db.get_generation_usage_today(305) == 0

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_generation_cancellation_before_delivery_releases_the_reservation(monkeypatch):
    """asyncio.CancelledError is not an Exception subclass (Python 3.8+), so a plain
    `except Exception` around the paid call would not release the reservation if the
    task is cancelled mid-flight. The try/finally lifecycle in `_run_generation` must
    still release it."""

    async def _cancelled_affirmations(**_kwargs):
        raise asyncio.CancelledError()

    async def run():
        await db.create_or_update_user(306, "u", name="Test", gender="female")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        monkeypatch.setattr(generation, "get_user", _fake_get_user)
        monkeypatch.setattr(generation, "get_settings", lambda: _settings(generation_daily_limit=5))
        monkeypatch.setattr(generation, "generate_affirmations", _cancelled_affirmations)

        message = _FakeMessage(user_id=306)
        state = _state()

        with pytest.raises(asyncio.CancelledError):
            await generation._run_generation(message, state, theme_text="Dignity and self-trust", user_telegram_id=306)

        assert await db.get_generation_usage_today(306) == 0

    asyncio.run(run())


@pytest.mark.usefixtures("initialized_db")
def test_disabled_daily_limit_skips_reservation_entirely(monkeypatch):
    async def run():
        await db.create_or_update_user(307, "u", name="Test", gender="female")
        monkeypatch.setattr(db, "_utc_today_iso", lambda: "2030-01-01")

        monkeypatch.setattr(generation, "get_user", _fake_get_user)
        monkeypatch.setattr(
            generation,
            "get_settings",
            lambda: _settings(generation_daily_limit=0, disable_daily_generation_limit=True),
        )
        _patch_successful_providers(monkeypatch)

        message = _FakeMessage(user_id=307)
        state = _state()

        await generation._run_generation(message, state, theme_text="Dignity and self-trust", user_telegram_id=307)

        assert len(message.photos) == 1
        # Unlimited generation never writes a generation_limits row.
        assert await db.get_generation_usage_today(307) == 0

    asyncio.run(run())
