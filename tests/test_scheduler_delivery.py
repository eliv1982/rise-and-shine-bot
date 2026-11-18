"""Scheduler delivery contract (Corrective Stage 2 / audit finding D1).

Exercises scheduler.send_daily_affirmations against a real temporary SQLite database
(the subscription_deliveries ledger is what makes these guarantees durable), with every
external provider and Telegram mocked. No real network calls, no real sleeps beyond a
few milliseconds used to prove concurrency.
"""
import asyncio
import json
import importlib
import random
import uuid

import aiohttp
import pytest

from services.yandex_gpt import GeneratedCardText

import database as db
import scheduler
from services import yandex_gpt as provider
from services.ritual_config import get_focus_for_date
from services.delivery_schedule import CATCHUP_WINDOW, CLAIM_LEASE, RETRY_BACKOFF


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


class _FakeSentMessage:
    photo: list = []


class _FakeBot:
    def __init__(self):
        self.sent: list[dict] = []

    async def send_photo(self, **kwargs):
        self.sent.append(kwargs)
        return _FakeSentMessage()


def _install_common_stubs(monkeypatch, module=scheduler):
    """Stub every LLM/shadow helper with a fast, deterministic, network-free result."""

    async def fake_text_plan_shadow(**_kwargs):
        return None

    async def fake_scene_plan_shadow(**_kwargs):
        return None

    async def fake_generate_affirmations(**_kwargs):
        return GeneratedCardText(_kwargs.get("focus") or "Test focus", ["Affirmation one", "Affirmation two", "Affirmation three"])

    def fake_text_reviewer_shadow(**_kwargs):
        return None

    async def fake_build_enriched_image_prompt(**_kwargs):
        return "a calm scene", "template"

    monkeypatch.setattr(module, "build_text_plan_shadow_best_effort", fake_text_plan_shadow)
    monkeypatch.setattr(module, "build_scene_plan_shadow_best_effort", fake_scene_plan_shadow)
    monkeypatch.setattr(module, "generate_card_text", fake_generate_affirmations)
    monkeypatch.setattr(module, "build_text_reviewer_shadow_best_effort", fake_text_reviewer_shadow)
    monkeypatch.setattr(module, "build_enriched_image_prompt", fake_build_enriched_image_prompt)
    monkeypatch.setattr(module, "is_text_planner_controlled_enabled", lambda *_a, **_k: False)
    monkeypatch.setattr(module, "is_scene_planner_image_prompt_enabled", lambda *_a, **_k: False)


def _install_generate_image(monkeypatch, tmp_path, calls, *, fail_if=None, delay=0.0, module=scheduler):
    """Fake generate_image: records kwargs, optionally delays, optionally fails.

    ``fail_if(kwargs, call_index)`` (1-based, across all calls to this fake) decides
    whether that particular call raises instead of "succeeding".
    """

    async def fake_generate_image(**kwargs):
        calls.append(kwargs)
        if delay:
            await asyncio.sleep(delay)
        if fail_if and fail_if(kwargs, len(calls)):
            raise RuntimeError("simulated generation failure")
        path = tmp_path / f"{uuid.uuid4().hex}.png"
        path.write_bytes(b"fake-png-bytes")
        return str(path)

    monkeypatch.setattr(module, "generate_image", fake_generate_image)


async def _make_subscription(user_id: int, hour: int, minute: int, allowed_visual_modes, *, sphere="money", style="auto"):
    await db.create_or_update_user(user_id, f"u{user_id}", name=f"User{user_id}")
    return await db.create_subscription(
        user_id,
        sphere,
        None,
        style,
        "ru",
        hour,
        minute,
        subscription_mode="sphere_focus",
        subscription_sphere=sphere,
        subscription_style_mode=style,
        visual_mode=allowed_visual_modes[0],
        allowed_visual_modes=allowed_visual_modes,
    )


MOSCOW = scheduler.MOSCOW


def _at(day: int, hour: int, minute: int):
    import datetime as dt

    return dt.datetime(2030, 3, day, hour, minute, tzinfo=MOSCOW)


def _plus(moment, **timedelta_kwargs):
    import datetime as dt

    return moment + dt.timedelta(**timedelta_kwargs)


# ---------------------------------------------------------------------------
# 1. One due subscription is delivered.
# ---------------------------------------------------------------------------


def test_one_due_subscription_is_delivered(initialized_db, monkeypatch, tmp_path):
    async def run():
        _install_common_stubs(monkeypatch)
        calls: list[dict] = []
        _install_generate_image(monkeypatch, tmp_path, calls)
        sub_id = await _make_subscription(1, 8, 0, ["photo"])
        bot = _FakeBot()

        await scheduler.send_daily_affirmations(bot, now=_at(1, 8, 0))

        assert len(bot.sent) == 1
        assert len(calls) == 1
        rows = await db.get_subscription_deliveries(["2030-03-01"])
        assert len(rows) == 1
        assert rows[0]["subscription_id"] == sub_id
        assert rows[0]["status"] == "sent"
        assert rows[0]["attempts"] == 1

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 2. Multiple due subscriptions are processed concurrently, not serially.
# ---------------------------------------------------------------------------


def test_multiple_due_subscriptions_processed_concurrently(initialized_db, monkeypatch, tmp_path):
    async def run():
        _install_common_stubs(monkeypatch)
        concurrency = 3
        monkeypatch.setattr(scheduler, "get_scheduler_max_concurrency", lambda: concurrency)

        active = 0
        max_active = 0
        # Released only once `concurrency` deliveries are simultaneously inside
        # generate_image. Until then every caller blocks here, so none of them can
        # finish first - the only way this coroutine ever proceeds is if all
        # `concurrency` deliveries were in flight at once. That is a deterministic
        # fact about execution order, not an inference from wall-clock duration.
        all_active = asyncio.Event()

        async def fake_generate_image(**kwargs):
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            if active >= concurrency:
                all_active.set()
            await all_active.wait()
            active -= 1
            path = tmp_path / f"{uuid.uuid4().hex}.png"
            path.write_bytes(b"fake-png-bytes")
            return str(path)

        monkeypatch.setattr(scheduler, "generate_image", fake_generate_image)
        for i in range(concurrency):
            await _make_subscription(10 + i, 8, 0, ["photo"], sphere="money")
        bot = _FakeBot()

        # A generous fixed ceiling, not a threshold being measured against: if the
        # barrier above is ever wrong this fails fast instead of hanging on
        # scheduler.py's own 600s ATTEMPT_TIMEOUT_SECONDS.
        await asyncio.wait_for(scheduler.send_daily_affirmations(bot, now=_at(2, 8, 0)), timeout=5)

        assert len(bot.sent) == 3
        # All `concurrency` deliveries were inside generate_image at the same time.
        assert max_active == concurrency

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 3. One subscription's failure does not stop another's delivery.
# ---------------------------------------------------------------------------


def test_one_subscription_failure_does_not_block_another(initialized_db, monkeypatch, tmp_path):
    async def run():
        _install_common_stubs(monkeypatch)
        calls: list[dict] = []
        _install_generate_image(monkeypatch, tmp_path, calls, fail_if=lambda kwargs, _n: kwargs["sphere"] == "money")
        failing_id = await _make_subscription(20, 8, 0, ["photo"], sphere="money")
        ok_id = await _make_subscription(21, 8, 0, ["photo"], sphere="career")
        bot = _FakeBot()

        await scheduler.send_daily_affirmations(bot, now=_at(3, 8, 0))

        assert len(bot.sent) == 1
        rows = {r["subscription_id"]: r for r in await db.get_subscription_deliveries(["2030-03-03"])}
        assert rows[failing_id]["status"] == "failed"
        assert rows[ok_id]["status"] == "sent"

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 4. An already-completed logical delivery is not sent again.
# ---------------------------------------------------------------------------


def test_completed_delivery_is_not_sent_again(initialized_db, monkeypatch, tmp_path):
    async def run():
        _install_common_stubs(monkeypatch)
        calls: list[dict] = []
        _install_generate_image(monkeypatch, tmp_path, calls)
        await _make_subscription(30, 8, 0, ["photo"])
        bot = _FakeBot()

        await scheduler.send_daily_affirmations(bot, now=_at(4, 8, 0))
        await scheduler.send_daily_affirmations(bot, now=_at(4, 8, 1))
        await scheduler.send_daily_affirmations(bot, now=_at(4, 9, 0))

        assert len(bot.sent) == 1
        assert len(calls) == 1

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 5. Restart / re-run of the scheduler does not duplicate a completed delivery.
# ---------------------------------------------------------------------------


def test_restart_does_not_duplicate_completed_delivery(initialized_db, monkeypatch, tmp_path):
    async def run():
        _install_common_stubs(monkeypatch)
        calls: list[dict] = []
        _install_generate_image(monkeypatch, tmp_path, calls)
        await _make_subscription(40, 8, 0, ["photo"])
        bot = _FakeBot()

        await scheduler.send_daily_affirmations(bot, now=_at(5, 8, 0))
        assert len(bot.sent) == 1

        # Simulate a process restart: reload the module so any hypothetical
        # process-local state (there is none left by design - see module docstring)
        # cannot be the reason a duplicate send does or doesn't happen.
        reloaded = importlib.reload(scheduler)
        try:
            _install_common_stubs(monkeypatch, module=reloaded)
            _install_generate_image(monkeypatch, tmp_path, calls, module=reloaded)
            await reloaded.send_daily_affirmations(bot, now=_at(5, 8, 5))
        finally:
            importlib.reload(scheduler)

        assert len(bot.sent) == 1
        assert len(calls) == 1

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 6. A missed exact minute is caught up within the allowed window.
# ---------------------------------------------------------------------------


def test_missed_minute_is_caught_up_within_window(initialized_db, monkeypatch, tmp_path):
    async def run():
        assert CATCHUP_WINDOW.total_seconds() / 60 > 90  # keep the test's premise valid
        _install_common_stubs(monkeypatch)
        calls: list[dict] = []
        _install_generate_image(monkeypatch, tmp_path, calls)
        await _make_subscription(50, 8, 0, ["photo"])
        bot = _FakeBot()

        # The scheduler tick that should have fired at 08:00 never ran (process was
        # down); the next tick that does run is at 09:30, still inside the window.
        await scheduler.send_daily_affirmations(bot, now=_at(6, 9, 30))

        assert len(bot.sent) == 1
        rows = await db.get_subscription_deliveries(["2030-03-06"])
        assert rows[0]["status"] == "sent"

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 7. A too-old missed delivery is not backfilled.
# ---------------------------------------------------------------------------


def test_too_old_missed_delivery_is_not_backfilled(initialized_db, monkeypatch, tmp_path):
    async def run():
        _install_common_stubs(monkeypatch)
        calls: list[dict] = []
        _install_generate_image(monkeypatch, tmp_path, calls)
        await _make_subscription(60, 8, 0, ["photo"])
        bot = _FakeBot()

        # Well past the catch-up window: outage was too long, do not send a stale ritual.
        scheduled_at = _at(7, 8, 0)
        too_late = _plus(scheduled_at, seconds=CATCHUP_WINDOW.total_seconds() + 3600)
        await scheduler.send_daily_affirmations(bot, now=too_late)

        assert len(bot.sent) == 0
        assert len(calls) == 0
        rows = await db.get_subscription_deliveries(["2030-03-07"])
        assert rows == []

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 8 & 9. Failed delivery is retryable; a successful retry completes and stops.
# ---------------------------------------------------------------------------


def test_failed_delivery_retries_then_completes_and_stops(initialized_db, monkeypatch, tmp_path):
    async def run():
        _install_common_stubs(monkeypatch)
        calls: list[dict] = []
        # Fail only the very first attempt; every later attempt succeeds.
        _install_generate_image(monkeypatch, tmp_path, calls, fail_if=lambda _k, n: n == 1)
        await _make_subscription(70, 8, 0, ["photo"])
        bot = _FakeBot()

        scheduled_at = _at(8, 8, 0)

        # First attempt: fails.
        await scheduler.send_daily_affirmations(bot, now=scheduled_at)
        assert len(bot.sent) == 0
        rows = await db.get_subscription_deliveries(["2030-03-08"])
        assert rows[0]["status"] == "failed"
        assert rows[0]["attempts"] == 1

        # Still inside the backoff window: not yet eligible for another attempt.
        too_soon = _plus(scheduled_at, seconds=RETRY_BACKOFF.total_seconds() - 60)
        await scheduler.send_daily_affirmations(bot, now=too_soon)
        assert len(calls) == 1
        assert len(bot.sent) == 0

        # Past the backoff: retried, and this attempt succeeds.
        retry_now = _plus(scheduled_at, seconds=RETRY_BACKOFF.total_seconds() + 60)
        await scheduler.send_daily_affirmations(bot, now=retry_now)
        assert len(bot.sent) == 1
        assert len(calls) == 2
        rows = await db.get_subscription_deliveries(["2030-03-08"])
        assert rows[0]["status"] == "sent"
        assert rows[0]["attempts"] == 2

        # A later tick must not run it a third time.
        await scheduler.send_daily_affirmations(bot, now=_plus(retry_now, minutes=30))
        assert len(bot.sent) == 1
        assert len(calls) == 2

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 10. Visual mode is stable across a retry.
# ---------------------------------------------------------------------------


def test_visual_mode_is_stable_across_retry(initialized_db, monkeypatch, tmp_path):
    async def run():
        random.seed(4242)
        _install_common_stubs(monkeypatch)
        calls: list[dict] = []
        _install_generate_image(monkeypatch, tmp_path, calls, fail_if=lambda _k, n: n == 1)
        await _make_subscription(80, 8, 0, ["photo", "symbolic", "illustration"])
        bot = _FakeBot()

        scheduled_at = _at(9, 8, 0)
        await scheduler.send_daily_affirmations(bot, now=scheduled_at)  # fails
        retry_now = _plus(scheduled_at, seconds=RETRY_BACKOFF.total_seconds() + 60)
        await scheduler.send_daily_affirmations(bot, now=retry_now)

        assert len(calls) == 2
        assert calls[0]["visual_mode"] == calls[1]["visual_mode"]
        assert len(bot.sent) == 1

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 11. Visual mode is stable across a simulated restart.
# ---------------------------------------------------------------------------


def test_visual_mode_is_stable_across_simulated_restart(initialized_db, monkeypatch, tmp_path):
    async def run():
        random.seed(777)
        _install_common_stubs(monkeypatch)
        calls: list[dict] = []
        _install_generate_image(monkeypatch, tmp_path, calls, fail_if=lambda _k, n: n == 1)
        await _make_subscription(90, 8, 0, ["photo", "symbolic", "illustration"])
        bot = _FakeBot()

        scheduled_at = _at(10, 8, 0)
        await scheduler.send_daily_affirmations(bot, now=scheduled_at)  # fails, mode persisted

        reloaded = importlib.reload(scheduler)
        try:
            _install_common_stubs(monkeypatch, module=reloaded)
            _install_generate_image(monkeypatch, tmp_path, calls, fail_if=lambda _k, n: False, module=reloaded)
            retry_now = _plus(scheduled_at, seconds=RETRY_BACKOFF.total_seconds() + 60)
            await reloaded.send_daily_affirmations(bot, now=retry_now)
        finally:
            importlib.reload(scheduler)

        assert len(calls) == 2
        assert calls[0]["visual_mode"] == calls[1]["visual_mode"]
        assert len(bot.sent) == 1

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 12 & 13. Multi-mode rotates across days; single-mode stays fixed.
# ---------------------------------------------------------------------------


def test_multi_mode_visual_selection_varies_across_days(initialized_db, monkeypatch, tmp_path):
    async def run():
        random.seed(99)
        _install_common_stubs(monkeypatch)
        calls: list[dict] = []
        _install_generate_image(monkeypatch, tmp_path, calls)
        await _make_subscription(100, 8, 0, ["photo", "symbolic"])
        bot = _FakeBot()

        for day in range(11, 17):
            await scheduler.send_daily_affirmations(bot, now=_at(day, 8, 0))

        modes = [c["visual_mode"] for c in calls]
        assert len(modes) == 6
        assert len(set(modes)) == 2

    asyncio.run(run())


def test_single_mode_subscription_visual_mode_stays_fixed(initialized_db, monkeypatch, tmp_path):
    async def run():
        _install_common_stubs(monkeypatch)
        calls: list[dict] = []
        _install_generate_image(monkeypatch, tmp_path, calls)
        await _make_subscription(101, 8, 0, ["illustration"])
        bot = _FakeBot()

        for day in range(18, 22):
            await scheduler.send_daily_affirmations(bot, now=_at(day, 8, 0))

        modes = {c["visual_mode"] for c in calls}
        assert modes == {"illustration"}

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 14. Symbolic mode still bypasses ordinary scene-planner image-prompt processing.
# ---------------------------------------------------------------------------


def test_symbolic_mode_bypasses_scene_planner_prompt(initialized_db, monkeypatch, tmp_path):
    async def run():
        _install_common_stubs(monkeypatch)
        # Flip this on to prove symbolic mode does not go through it regardless.
        monkeypatch.setattr(scheduler, "is_scene_planner_image_prompt_enabled", lambda *_a, **_k: True)
        calls: list[dict] = []
        _install_generate_image(monkeypatch, tmp_path, calls)
        await _make_subscription(110, 8, 0, ["symbolic"], style="mandala_harmony")
        bot = _FakeBot()

        await scheduler.send_daily_affirmations(bot, now=_at(23, 8, 0))

        assert len(calls) == 1
        assert calls[0]["visual_mode"] == "symbolic"
        assert calls[0]["prompt_override"] is None
        assert calls[0]["image_prompt_trace"] == "template"

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 15. Concurrent processing respects the configured bound.
# ---------------------------------------------------------------------------


def test_concurrency_respects_configured_bound(initialized_db, monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(scheduler, "get_scheduler_max_concurrency", lambda: 2)
        _install_common_stubs(monkeypatch)
        in_flight = {"current": 0, "max": 0}

        async def fake_generate_image(**kwargs):
            in_flight["current"] += 1
            in_flight["max"] = max(in_flight["max"], in_flight["current"])
            await asyncio.sleep(0.05)
            in_flight["current"] -= 1
            path = tmp_path / f"{uuid.uuid4().hex}.png"
            path.write_bytes(b"x")
            return str(path)

        monkeypatch.setattr(scheduler, "generate_image", fake_generate_image)
        for i in range(5):
            await _make_subscription(120 + i, 8, 0, ["photo"], sphere="money")
        bot = _FakeBot()

        await scheduler.send_daily_affirmations(bot, now=_at(24, 8, 0))

        assert len(bot.sent) == 5
        assert in_flight["max"] <= 2

    asyncio.run(run())


# ---------------------------------------------------------------------------
# 16. Database uniqueness/idempotency guard works under concurrent claim attempts.
# ---------------------------------------------------------------------------


def test_concurrent_claim_attempts_only_one_wins(initialized_db):
    async def run():
        import datetime as dt

        sub_id = await _make_subscription(130, 8, 0, ["photo"])
        now = dt.datetime.now(dt.timezone.utc)
        kwargs = dict(
            subscription_id=sub_id,
            user_id=130,
            delivery_date="2030-03-25",
            visual_mode="photo",
            now=now,
            max_attempts=3,
            retry_backoff=RETRY_BACKOFF,
            lease=CATCHUP_WINDOW,
        )
        results = await asyncio.gather(*(db.claim_subscription_delivery(**kwargs) for _ in range(25)))
        winners = [r for r in results if r is not None]
        assert len(winners) == 1

        rows = await db.get_subscription_deliveries(["2030-03-25"])
        assert len(rows) == 1
        assert rows[0]["attempts"] == 1

    asyncio.run(run())


# ---------------------------------------------------------------------------
# Claim-lease safety invariant: max attempt duration < CLAIM_LEASE.
#
# A still-running attempt must never have its claim stolen. That is only true because
# ATTEMPT_TIMEOUT_SECONDS (the one thing that can make an attempt run long) is kept
# well under CLAIM_LEASE (the one thing that lets a claim be reclaimed) - see the
# assertion next to those constants in scheduler.py. These tests pin both halves of
# that relationship: the invariant itself, and the claim/reclaim behavior it protects.
# ---------------------------------------------------------------------------


def test_attempt_timeout_stays_safely_below_claim_lease():
    # Reads the live constants rather than duplicating numbers, so this fails the moment
    # either one changes in a way that would let a live worker's claim be stolen.
    assert scheduler.ATTEMPT_TIMEOUT_SECONDS > 0
    assert scheduler._LEASE_SAFETY_MARGIN_SECONDS > 0
    assert (
        scheduler.ATTEMPT_TIMEOUT_SECONDS + scheduler._LEASE_SAFETY_MARGIN_SECONDS
        <= CLAIM_LEASE.total_seconds()
    )


def test_in_progress_claim_within_lease_cannot_be_reclaimed(initialized_db):
    async def run():
        import datetime as dt

        sub_id = await _make_subscription(140, 8, 0, ["photo"])
        t0 = dt.datetime.now(dt.timezone.utc)
        kwargs = dict(
            subscription_id=sub_id,
            user_id=140,
            delivery_date="2030-04-01",
            visual_mode="photo",
            max_attempts=3,
            retry_backoff=RETRY_BACKOFF,
            lease=CLAIM_LEASE,
        )
        first = await db.claim_subscription_delivery(now=t0, **kwargs)
        assert first is not None and first["attempts"] == 1

        # One second short of the lease: the first attempt must still be presumed alive,
        # exactly what protects a genuinely slow (but still running) worker.
        still_within_lease = t0 + dt.timedelta(seconds=CLAIM_LEASE.total_seconds() - 1)
        second = await db.claim_subscription_delivery(now=still_within_lease, **kwargs)
        assert second is None

        rows = await db.get_subscription_deliveries(["2030-04-01"])
        assert rows[0]["attempts"] == 1
        assert rows[0]["status"] == "in_progress"

    asyncio.run(run())


def test_in_progress_claim_past_lease_can_be_reclaimed(initialized_db):
    async def run():
        import datetime as dt

        sub_id = await _make_subscription(141, 8, 0, ["photo"])
        t0 = dt.datetime.now(dt.timezone.utc)
        kwargs = dict(
            subscription_id=sub_id,
            user_id=141,
            delivery_date="2030-04-01",
            visual_mode="photo",
            max_attempts=3,
            retry_backoff=RETRY_BACKOFF,
            lease=CLAIM_LEASE,
        )
        first = await db.claim_subscription_delivery(now=t0, **kwargs)
        assert first is not None and first["attempts"] == 1

        # One second past the lease: the original attempt is presumed dead (it should have
        # finished within ATTEMPT_TIMEOUT_SECONDS, safely under the lease) and is reclaimed.
        past_lease = t0 + dt.timedelta(seconds=CLAIM_LEASE.total_seconds() + 1)
        second = await db.claim_subscription_delivery(now=past_lease, **kwargs)
        assert second is not None
        assert second["attempts"] == 2

    asyncio.run(run())


# ---------------------------------------------------------------------------
# Stage 4 item G: a relationship-sphere subscription's persisted subfocus must reach
# generation, the same way handlers/generation.py's manual /new flow already does.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Stage 5 item M: every tick touches the heartbeat file Docker's HEALTHCHECK
# (scripts/healthcheck.py) reads, whether or not anything is due.
# ---------------------------------------------------------------------------


def test_tick_touches_heartbeat_even_with_nothing_due(initialized_db, monkeypatch):
    async def run():
        import os

        import config

        heartbeat_path = config.get_heartbeat_path()
        assert not os.path.exists(heartbeat_path)

        bot = _FakeBot()
        await scheduler.send_daily_affirmations(bot, now=_at(1, 8, 0))  # nothing due

        assert os.path.isfile(heartbeat_path)

    asyncio.run(run())


# ---------------------------------------------------------------------------
# Stage 5 item D: shutdown cancelling an in-flight attempt must not corrupt the
# ledger. A cancelled attempt is never released (asyncio.CancelledError is a
# BaseException, not caught by _process_due_delivery's `except Exception`), so the
# claim is simply left `in_progress` - exactly like a process that died mid-attempt -
# and is reclaimed once CLAIM_LEASE elapses, the same recovery path already proven
# for a crash. This is deliberate (see scheduler.py's ATTEMPT_TIMEOUT_SECONDS/
# CLAIM_LEASE comments and bot.py's shutdown hook): shutdown cancels rather than
# waiting for in-flight work to finish.
# ---------------------------------------------------------------------------


def test_cancelled_attempt_is_not_marked_sent_and_stays_in_progress(initialized_db, monkeypatch, tmp_path):
    async def run():
        _install_common_stubs(monkeypatch)
        calls: list[dict] = []

        async def fake_generate_image(**kwargs):
            calls.append(kwargs)
            raise asyncio.CancelledError()

        monkeypatch.setattr(scheduler, "generate_image", fake_generate_image)
        await _make_subscription(150, 8, 0, ["photo"])
        bot = _FakeBot()

        scheduled_at = _at(12, 8, 0)
        await scheduler.send_daily_affirmations(bot, now=scheduled_at)

        assert len(bot.sent) == 0
        rows = await db.get_subscription_deliveries(["2030-03-12"])
        assert len(rows) == 1
        assert rows[0]["status"] == "in_progress"  # neither sent nor failed/abandoned
        assert rows[0]["attempts"] == 1

    asyncio.run(run())


def test_cancelled_attempt_is_reclaimed_after_lease_and_keeps_visual_mode(initialized_db, monkeypatch, tmp_path):
    async def run():
        random.seed(4343)
        _install_common_stubs(monkeypatch)
        calls: list[dict] = []

        async def fake_generate_image_cancels_once(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise asyncio.CancelledError()
            path = tmp_path / f"{uuid.uuid4().hex}.png"
            path.write_bytes(b"fake-png-bytes")
            return str(path)

        monkeypatch.setattr(scheduler, "generate_image", fake_generate_image_cancels_once)
        await _make_subscription(151, 8, 0, ["photo", "symbolic", "illustration"])
        bot = _FakeBot()

        scheduled_at = _at(13, 8, 0)
        await scheduler.send_daily_affirmations(bot, now=scheduled_at)  # cancelled, left in_progress

        # Still within the lease: presumed alive, must not be reclaimed yet.
        still_within_lease = _plus(scheduled_at, seconds=CLAIM_LEASE.total_seconds() - 60)
        await scheduler.send_daily_affirmations(bot, now=still_within_lease)
        assert len(calls) == 1
        assert len(bot.sent) == 0

        # Past the lease: the abandoned claim is reclaimed and this attempt succeeds.
        past_lease = _plus(scheduled_at, seconds=CLAIM_LEASE.total_seconds() + 60)
        await scheduler.send_daily_affirmations(bot, now=past_lease)

        assert len(bot.sent) == 1
        assert len(calls) == 2
        assert calls[0]["visual_mode"] == calls[1]["visual_mode"]  # persisted mode survives
        rows = await db.get_subscription_deliveries(["2030-03-13"])
        assert rows[0]["status"] == "sent"
        assert rows[0]["attempts"] == 2

    asyncio.run(run())


def test_relationship_subscription_delivery_uses_persisted_subsphere(initialized_db, monkeypatch, tmp_path):
    async def run():
        _install_common_stubs(monkeypatch)
        captured: dict = {}

        async def fake_generate_affirmations(**kwargs):
            captured.update(kwargs)
            return GeneratedCardText(kwargs.get("focus") or "Test focus", ["Affirmation one", "Affirmation two", "Affirmation three"])

        monkeypatch.setattr(scheduler, "generate_card_text", fake_generate_affirmations)
        calls: list[dict] = []
        _install_generate_image(monkeypatch, tmp_path, calls)

        await db.create_or_update_user(1, "u1", name="User1")
        await db.create_subscription(
            user_id=1,
            sphere="relationships",
            subsphere="colleagues",
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
        bot = _FakeBot()

        await scheduler.send_daily_affirmations(bot, now=_at(1, 8, 0))

        assert len(bot.sent) == 1
        assert captured.get("sphere") == "relationships"
        assert captured.get("subsphere") == "colleagues"

    asyncio.run(run())


@pytest.mark.parametrize("ui,content", [("ru", "en"), ("en", "ru")])
@pytest.mark.parametrize("invalid", [False, True])
def test_scheduled_content_and_delivery_controls_have_separate_languages(initialized_db, monkeypatch, tmp_path, ui, content, invalid):
    _install_common_stubs(monkeypatch)
    monkeypatch.setattr(scheduler, "generate_card_text", provider.generate_card_text)
    image_calls = []
    _install_generate_image(monkeypatch, tmp_path, image_calls)
    requests = []
    localized = "Calm financial decisions" if content == "en" else "Спокойные финансовые решения"
    phrases = ["I trust my pace", "My judgment matters", "I can choose calmly", "My experience supports me"] if content == "en" else [
        "Я берегу свой ритм", "Моё мнение важно", "Мне доступен спокойный выбор", "Мой опыт поддерживает меня",
    ]

    class Response:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def json(self):
            raw = {"focus": "Исходный фокус" if content == "en" else "Source focus", "affirmations": phrases} if invalid else {"focus": localized, "affirmations": phrases}
            return {"choices": [{"message": {"content": json.dumps(raw)}, "finish_reason": "stop"}]}

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        def post(self, url, **kwargs):
            requests.append(kwargs["json"])
            return Response()

    monkeypatch.setattr(provider.aiohttp, "ClientSession", Session)

    async def run():
        await db.create_or_update_user(1, "offline", name="Елена", gender="female", language=ui)
        await db.update_user_profile_preferences(1, {"current_focus": "Original profile context"})
        sub_id = await db.create_subscription(1, "money", None, "auto", content, 8, 0, subscription_mode="sphere_focus", subscription_sphere="money")
        before_preferences = await db.get_user_profile_preferences(1)
        bot = _FakeBot()
        await scheduler.send_daily_affirmations(bot, now=_at(1, 8, 0))
        assert len(requests) == 1
        payload = requests[0]
        assert payload["model"] == "gpt-6-luna"
        source = get_focus_for_date(1, "money", _at(1, 8, 0).date())
        assert source[content] in payload["messages"][1]["content"]
        assert "Language: English." in payload["messages"][1]["content"] if content == "en" else "Язык: русский." in payload["messages"][1]["content"]
        rows = await db.get_subscription_deliveries(["2030-03-01"])
        assert (await db.get_user(1))["language"] == ui
        assert (await db.get_subscription_by_id(sub_id, 1))["language"] == content
        assert await db.get_user_profile_preferences(1) == before_preferences
        if invalid:
            assert not bot.sent and not image_calls
            assert rows[0]["status"] == "abandoned"
            return
        assert rows[0]["status"] == "sent"
        assert len(bot.sent) == len(image_calls) == 1
        caption = bot.sent[0]["caption"]
        assert ("Focus of the day: " if content == "en" else "Фокус дня: ") + localized in caption
        assert ("Elena, your daily focus" if content == "en" else "Елена, твой настрой на сегодня") in caption
        assert source[f"micro_step_{content}"] in caption
        assert all(f"• {phrase}" in caption for phrase in phrases)
        buttons = {b.callback_data: b.text for row in bot.sent[0]["reply_markup"].inline_keyboard for b in row}
        assert buttons["sub:change"] == ("⚙️ Настроить подписки" if ui == "ru" else "⚙️ Manage subscriptions")
        assert ("sub_tts:yes" in buttons) == (content == "ru")
        if content == "ru":
            assert buttons["sub_tts:yes"] == "🔊 Listen"

    asyncio.run(run())


@pytest.mark.parametrize("ui,content", [("ru", "en"), ("en", "ru")])
def test_scheduled_delivery_refreshes_ui_changed_during_generation(initialized_db, monkeypatch, tmp_path, ui, content):
    _install_common_stubs(monkeypatch)
    calls = []
    _install_generate_image(monkeypatch, tmp_path, calls)
    original_image = scheduler.generate_image

    async def image_with_language_switch(**kwargs):
        await db.update_user_language(1, ui)
        return await original_image(**kwargs)

    monkeypatch.setattr(scheduler, "generate_image", image_with_language_switch)

    async def run():
        await db.create_or_update_user(1, "offline", name="User", language=content)
        sub_id = await db.create_subscription(1, "money", None, "auto", content, 8, 0)
        bot = _FakeBot()
        await scheduler.send_daily_affirmations(bot, now=_at(1, 8, 0))
        assert len(bot.sent) == 1
        assert ("Фокус дня:" if content == "ru" else "Focus of the day:") in bot.sent[0]["caption"]
        buttons = {b.callback_data: b.text for row in bot.sent[0]["reply_markup"].inline_keyboard for b in row}
        assert buttons["sub:change"] == ("⚙️ Настроить подписки" if ui == "ru" else "⚙️ Manage subscriptions")
        assert (await db.get_subscription_by_id(sub_id, 1))["language"] == content

    asyncio.run(run())


@pytest.fixture
def card_transport(monkeypatch):
    """Run real production text parsing with a completely mocked HTTP boundary."""
    state = {
        "status": 200,
        "raw": json.dumps({"focus": "Спокойный рост", "affirmations": ["Мой опыт важен"] * 4}),
        "calls": [],
        "body_reads": 0,
    }

    class Response:
        @property
        def status(self):
            return state["status"]

        async def __aenter__(self):
            if state.get("error"):
                raise state["error"]
            return self

        async def __aexit__(self, *_):
            return False

        async def json(self):
            if state.get("json_error"):
                raise state["json_error"]
            return state.get("data", {"choices": [{"message": {"content": state["raw"]}, "finish_reason": "stop"}]})

        async def text(self):
            state["body_reads"] += 1
            return "PRIVATE_PROVIDER_RESPONSE"

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        def post(self, url, **kwargs):
            state["calls"].append(kwargs["json"])
            return Response()

    _install_common_stubs(monkeypatch)
    monkeypatch.setattr(scheduler, "generate_card_text", provider.generate_card_text)
    monkeypatch.setattr(scheduler, "last_subscription_affirmations", {})
    monkeypatch.setattr(provider.aiohttp, "ClientSession", Session)
    return state


@pytest.mark.parametrize("failure", [
    "malformed", "missing_focus", "invalid_type", "wrong_count", "wrong_focus_language",
    "foreign_affirmation_0", "foreign_affirmation_1", "foreign_affirmation_2", "foreign_affirmation_3",
    "mixed_language", "neutral_only", "envelope", "response_json", "response_mime", "truncated", "refused",
])
def test_scheduled_validation_failure_abandons_once_without_paid_retry(
    initialized_db, monkeypatch, tmp_path, card_transport, caplog, failure,
):
    payload = json.loads(card_transport["raw"])
    if failure == "missing_focus":
        payload.pop("focus")
    elif failure == "invalid_type":
        payload["affirmations"] = "PRIVATE_PERSONALIZED_CONTENT"
    elif failure == "wrong_count":
        payload["affirmations"].pop()
    elif failure == "wrong_focus_language":
        payload["focus"] = "I trust PRIVATE_PERSONALIZED_CONTENT"
    elif failure.startswith("foreign_affirmation_"):
        payload["affirmations"][int(failure[-1])] = "I trust PRIVATE_PERSONALIZED_CONTENT"
    elif failure == "mixed_language":
        payload["affirmations"][2] = "Я feel calm and choose PRIVATE_PERSONALIZED_CONTENT"
    elif failure == "neutral_only":
        payload["affirmations"][3] = "2026 🌿"
    card_transport["raw"] = "PRIVATE_PERSONALIZED_CONTENT {malformed" if failure == "malformed" else json.dumps(payload)
    if failure == "envelope":
        card_transport["data"] = {"choices": [{"message": {"content": {"private": "PRIVATE_PERSONALIZED_CONTENT"}}}]}
    elif failure == "response_json":
        card_transport["json_error"] = ValueError("PRIVATE_PROVIDER_RESPONSE")
    elif failure == "response_mime":
        card_transport["json_error"] = aiohttp.ContentTypeError(None, (), message="PRIVATE_PROVIDER_RESPONSE")
    elif failure in ("truncated", "refused"):
        card_transport["data"] = {"choices": [{
            "message": {"content": "PRIVATE_PROVIDER_RESPONSE", "refusal": failure == "refused"},
            "finish_reason": "length" if failure == "truncated" else "stop",
        }]}
    image_calls = []
    _install_generate_image(monkeypatch, tmp_path, image_calls)

    async def run():
        sub_id = await _make_subscription(901, 8, 0, ["photo"])
        bot = _FakeBot()
        for minute in (0, 16, 32, 48):
            await scheduler.send_daily_affirmations(bot, now=_at(1, 8, minute))
        rows = await db.get_subscription_deliveries(["2030-03-01"])
        assert len(rows) == len(card_transport["calls"]) == 1
        row = rows[0]
        assert row["subscription_id"] == sub_id
        assert row["status"] == "abandoned" and row["attempts"] == 1 and row["sent_at"] is None
        assert "ProviderOutputValidationError" in row["last_error"]
        assert not bot.sent and not image_calls and not scheduler.last_subscription_affirmations
        assert await db.get_generation_usage_today(901) == 0
        for secret in ("PRIVATE_PERSONALIZED_CONTENT", "PRIVATE_PROVIDER_RESPONSE"):
            assert secret not in caplog.text and secret not in row["last_error"]
        assert card_transport["body_reads"] == 0

    asyncio.run(run())


@pytest.mark.parametrize("failure", ["connection", "timeout", "rate_limit", "temporary_provider", "api_error"])
@pytest.mark.parametrize("recover", [True, False])
def test_scheduled_transient_text_errors_preserve_backoff_attempts_and_accounting(
    initialized_db, monkeypatch, tmp_path, card_transport, caplog, failure, recover,
):
    if failure == "connection":
        card_transport["error"] = aiohttp.ClientConnectionError("PRIVATE_PROVIDER_RESPONSE")
    elif failure == "timeout":
        card_transport["error"] = asyncio.TimeoutError("PRIVATE_PROVIDER_RESPONSE")
    elif failure in ("rate_limit", "temporary_provider"):
        card_transport["status"] = 429 if failure == "rate_limit" else 503
    else:
        card_transport["data"] = {"error": {"message": "PRIVATE_PROVIDER_RESPONSE"}}
    image_calls = []
    _install_generate_image(monkeypatch, tmp_path, image_calls)

    async def run():
        await _make_subscription(902, 8, 0, ["photo", "illustration"])
        bot = _FakeBot()
        await scheduler.send_daily_affirmations(bot, now=_at(2, 8, 0))
        row = (await db.get_subscription_deliveries(["2030-03-02"]))[0]
        visual_mode = row["visual_mode"]
        assert row["status"] == "failed" and row["attempts"] == 1 and row["sent_at"] is None
        assert len(card_transport["calls"]) == 1 and not bot.sent and not image_calls
        await scheduler.send_daily_affirmations(bot, now=_at(2, 8, 14))
        assert len(card_transport["calls"]) == 1
        if recover:
            card_transport.pop("error", None)
            card_transport.pop("data", None)
            card_transport["status"] = 200
        for minute in (16, 32, 48):
            await scheduler.send_daily_affirmations(bot, now=_at(2, 8, minute))
        row = (await db.get_subscription_deliveries(["2030-03-02"]))[0]
        expected_attempts = 2 if recover else 3
        assert row["status"] == ("sent" if recover else "abandoned")
        assert row["attempts"] == len(card_transport["calls"]) == expected_attempts
        assert row["visual_mode"] == visual_mode
        assert len(bot.sent) == len(image_calls) == (1 if recover else 0)
        assert bool(row["sent_at"]) is recover
        assert await db.get_generation_usage_today(902) == 0  # Scheduled calls never use the interactive quota.
        assert "PRIVATE_PROVIDER_RESPONSE" not in caplog.text
        assert "PRIVATE_PROVIDER_RESPONSE" not in (row["last_error"] or "")
        assert card_transport["body_reads"] == 0

    asyncio.run(run())


@pytest.mark.parametrize("field", ["focus", 0, 1, 2, 3])
@pytest.mark.parametrize("language", ["ru", "en"])
@pytest.mark.parametrize("case", ["hyphen", "quotation", "quoted_bypass", "wrong_outside_quote", "spoof"])
def test_fix04b_delivery_policy_uses_one_request_and_preserves_profile(
    initialized_db, monkeypatch, tmp_path, card_transport, field, language, case,
):
    texts = {
        "ru": {
            "hyphen": "Я Python-разработчик и работаю с IT-специалистом.",
            "quotation": "Я помню фразу «I am calm».",
            "quoted_bypass": "«I am calm»",
            "wrong_outside_quote": "Я помню фразу «I am calm», and I trust myself.",
            "spoof": "Я учу Pуthon-разработчика.",
        },
        "en": {
            "hyphen": "I enjoy reading Иван-Петров and practise йога.",
            "quotation": "I repeat the words «Я спокоен» every morning.",
            "quoted_bypass": "«Я спокоен»",
            "wrong_outside_quote": "I repeat the words «Я спокоен», и я верю в себя.",
            "spoof": "I enjoy reading Пушкuн.",
        },
    }
    text = texts[language][case]
    payload = {
        "focus": "Спокойный рост" if language == "ru" else "Gentle growth",
        "affirmations": ["Мой опыт важен" if language == "ru" else "My experience matters"] * 4,
    }
    if field == "focus":
        payload["focus"] = text
    else:
        payload["affirmations"][field] = text
    card_transport["raw"] = json.dumps(payload, ensure_ascii=False)
    image_calls = []
    _install_generate_image(monkeypatch, tmp_path, image_calls)
    valid = case in {"hyphen", "quotation"}

    async def run():
        ui_language = "en" if language == "ru" else "ru"
        await db.create_or_update_user(903, "offline", name="User", language=ui_language)
        preferences = {"current_focus": "Я Python-разработчик; I remember «Я спокоен» and ‘I am calm’."}
        await db.update_user_profile_preferences(903, preferences)
        before = await db.get_user_profile_preferences(903)
        sub_id = await db.create_subscription(903, "money", None, "auto", language, 8, 0)
        bot = _FakeBot()
        for minute in (0, 16, 32, 48):
            await scheduler.send_daily_affirmations(bot, now=_at(1, 8, minute))
        rows = await db.get_subscription_deliveries(["2030-03-01"])
        assert len(rows) == len(card_transport["calls"]) == 1
        row = rows[0]
        assert row["subscription_id"] == sub_id and row["attempts"] == 1
        assert row["status"] == ("sent" if valid else "abandoned")
        assert bool(row["sent_at"]) is valid
        assert len(bot.sent) == len(image_calls) == int(valid)
        assert bool(scheduler.last_subscription_affirmations) is valid
        if valid:
            # Double quotation marks may be HTML escaped by Telegram formatting.
            assert text in bot.sent[0]["caption"]
        else:
            assert "ProviderOutputValidationError" in row["last_error"]
        assert (await db.get_user(903))["language"] == ui_language
        assert (await db.get_subscription_by_id(sub_id, 903))["language"] == language
        assert await db.get_user_profile_preferences(903) == before
        assert before["current_focus"] == preferences["current_focus"]
        assert await db.get_generation_usage_today(903) == 0
        assert card_transport["body_reads"] == 0

    asyncio.run(run())
