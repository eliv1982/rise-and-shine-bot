import asyncio
import datetime as dt
import json
import random

import pytest

import database as db
import scheduler
from keyboards.inline import style_keyboard_for_subscription, subscription_select_keyboard
from services.ritual_config import (
    ILLUSTRATION_STYLE_KEYS,
    PHOTO_STYLE_KEYS,
    VISUAL_MIX_PRESETS,
    effective_subscription_style_mode,
    get_allowed_visual_modes,
    get_visual_mode_for_style,
    pick_subscription_visual_mode,
    resolve_subscription_visual_mode,
)
from services.subscription_ui import format_subscription_summary


# ---------------------------------------------------------------------------
# Backward compatibility & persistence
# ---------------------------------------------------------------------------


def test_legacy_single_visual_mode_subscription_still_works(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "legacy.db"))
        await db.init_db()
        await db.create_or_update_user(1, "u", name="U")
        await db.create_subscription(1, "random", None, "auto", "ru", 8, 0, visual_mode="photo")

        sub = await db.get_subscription(1)
        assert sub["visual_mode"] == "photo"
        assert sub.get("allowed_visual_modes_json") is None
        # Falls back to a single-mode list derived from visual_mode.
        assert get_allowed_visual_modes(sub) == ["photo"]

    asyncio.run(run())


def test_legacy_mixed_subscription_falls_back_to_photo_and_illustration(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "legacy_mixed.db"))
        await db.init_db()
        await db.create_or_update_user(2, "u", name="U")
        await db.create_subscription(2, "random", None, "auto", "ru", 8, 0, visual_mode="mixed")

        sub = await db.get_subscription(2)
        assert get_allowed_visual_modes(sub) == ["photo", "illustration"]

    asyncio.run(run())


def test_allowed_visual_modes_persisted_and_read_back(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "allowed.db"))
        await db.init_db()
        await db.create_or_update_user(3, "u", name="U")
        sub_id = await db.create_subscription(
            3,
            "random",
            None,
            "auto",
            "ru",
            8,
            0,
            visual_mode="photo",
            allowed_visual_modes=["photo", "symbolic"],
        )

        sub = await db.get_subscription_by_id(sub_id, 3)
        assert json.loads(sub["allowed_visual_modes_json"]) == ["photo", "symbolic"]
        assert get_allowed_visual_modes(sub) == ["photo", "symbolic"]

    asyncio.run(run())


def test_update_subscription_persists_allowed_visual_modes(monkeypatch, tmp_path):
    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "update_allowed.db"))
        await db.init_db()
        await db.create_or_update_user(4, "u", name="U")
        sub_id = await db.create_subscription(4, "random", None, "auto", "ru", 8, 0, visual_mode="illustration")

        updated = await db.update_subscription(
            subscription_id=sub_id,
            user_id=4,
            sphere="random",
            subsphere=None,
            image_style="auto",
            language="ru",
            hour=8,
            minute=0,
            visual_mode="illustration",
            allowed_visual_modes=["illustration", "symbolic", "photo"],
        )
        assert updated is True

        sub = await db.get_subscription_by_id(sub_id, 4)
        assert get_allowed_visual_modes(sub) == ["illustration", "symbolic", "photo"]

    asyncio.run(run())


# ---------------------------------------------------------------------------
# Preset mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "preset_key, expected",
    [
        ("photo", ["photo"]),
        ("illustration", ["illustration"]),
        ("symbolic", ["symbolic"]),
        ("photo_illustration", ["photo", "illustration"]),
        ("photo_symbolic", ["photo", "symbolic"]),
        ("illustration_symbolic", ["illustration", "symbolic"]),
        ("all", ["photo", "illustration", "symbolic"]),
    ],
)
def test_visual_mix_presets_map_to_expected_modes(preset_key, expected):
    assert VISUAL_MIX_PRESETS[preset_key] == expected


# ---------------------------------------------------------------------------
# pick_subscription_visual_mode (used for scheduled generation)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "allowed",
    [
        ["photo", "symbolic"],
        ["illustration", "symbolic"],
        ["photo", "illustration", "symbolic"],
    ],
)
def test_pick_subscription_visual_mode_only_chooses_from_allowed(allowed):
    rng = random.Random(0)
    for _ in range(50):
        mode = pick_subscription_visual_mode(allowed, rng=rng)
        assert mode in allowed


def test_pick_subscription_visual_mode_avoids_repeating_last_when_alternative_exists():
    rng = random.Random(1)
    allowed = ["photo", "symbolic"]
    for _ in range(20):
        mode = pick_subscription_visual_mode(allowed, last_visual_mode="photo", rng=rng)
        assert mode == "symbolic"


def test_pick_subscription_visual_mode_falls_back_when_only_one_allowed():
    # No alternative exists, so repeating the only allowed mode is fine.
    mode = pick_subscription_visual_mode(["photo"], last_visual_mode="photo")
    assert mode == "photo"


def test_pick_subscription_visual_mode_empty_allowed_falls_back_to_illustration():
    assert pick_subscription_visual_mode([], last_visual_mode=None) == "illustration"


# ---------------------------------------------------------------------------
# resolve_subscription_visual_mode: concrete style / visual mode compatibility
# ---------------------------------------------------------------------------


def test_resolve_subscription_visual_mode_single_mode_ignores_style_and_uses_its_mode():
    rng = random.Random(0)
    assert resolve_subscription_visual_mode(["symbolic"], selected_style="mandala_harmony", rng=rng) == "symbolic"
    assert resolve_subscription_visual_mode(["photo"], selected_style="sunny_morning_photo", rng=rng) == "photo"


@pytest.mark.parametrize(
    "allowed, concrete_style",
    [
        (["photo", "symbolic"], "mandala_harmony"),
        (["photo", "symbolic"], "sunny_morning_photo"),
        (["photo", "illustration"], "sunny_morning_photo"),
        (["photo", "illustration", "symbolic"], "cozy_home_photo"),
    ],
)
def test_resolve_subscription_visual_mode_multi_mode_never_pinned_by_concrete_style(allowed, concrete_style):
    # A concrete style used to pin the mode (e.g. photo + mandalas + a photo
    # style always resolved to photo). In a multi-mode pool the runtime must
    # keep choosing among all allowed modes.
    rng = random.Random(0)
    seen = {resolve_subscription_visual_mode(allowed, concrete_style, rng=rng) for _ in range(60)}
    assert len(seen) > 1
    assert seen <= set(allowed)


def test_resolve_subscription_visual_mode_auto_style_uses_allowed_and_anti_repeat():
    rng = random.Random(1)
    allowed = ["photo", "symbolic"]
    for _ in range(20):
        mode = resolve_subscription_visual_mode(
            allowed, selected_style="auto", last_visual_mode="photo", rng=rng
        )
        assert mode == "symbolic"


def test_resolve_subscription_visual_mode_incompatible_style_falls_back_to_allowed():
    # A photo style was saved, but the subscription's allowed modes no longer
    # include "photo" (e.g. edited later) - must not crash, fall back gracefully.
    rng = random.Random(0)
    for _ in range(10):
        mode = resolve_subscription_visual_mode(
            ["illustration", "symbolic"], selected_style="sunny_morning_photo", rng=rng
        )
        assert mode in ("illustration", "symbolic")


# ---------------------------------------------------------------------------
# Subscription select keyboard: visual mix icon for combo subscriptions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "allowed_visual_modes, expected_icon",
    [
        (["photo"], "📷"),
        (["illustration"], "🖌"),
        (["symbolic"], "🪷"),
        (["photo", "illustration"], "🔀"),
        (["photo", "symbolic"], "🌿"),
        (["illustration", "symbolic"], "✨"),
        (["photo", "illustration", "symbolic"], "🌈"),
    ],
)
def test_subscription_select_keyboard_shows_visual_mix_icon(allowed_visual_modes, expected_icon):
    sub = {
        "id": 1,
        "hour": 8,
        "minute": 0,
        "sphere": "random",
        "subscription_mode": "weekly_balance",
        "allowed_visual_modes_json": json.dumps(allowed_visual_modes),
    }
    keyboard = subscription_select_keyboard([sub], "ru", "edit")
    button_text = keyboard.inline_keyboard[0][0].text
    assert expected_icon in button_text


# ---------------------------------------------------------------------------
# Scheduled generation: mode selection is constrained to allowed_visual_modes.
#
# The mode is now chosen when a logical delivery (subscription_id, date) is first
# claimed and persisted in the subscription_deliveries ledger (see
# services/delivery_schedule.py and scheduler.py), so these tests drive
# scheduler.send_daily_affirmations across several distinct logical days against a
# real temporary database instead of looping the same day in memory - that in-memory
# loop is exactly the pre-Stage-2 bug (mode chosen from a process-local dict, updated
# before delivery was confirmed sent).
# ---------------------------------------------------------------------------


class _FakeSentMessage:
    photo: list = []


class _FakeBot:
    def __init__(self):
        self.sent: list[dict] = []

    async def send_photo(self, **kwargs):
        self.sent.append(kwargs)
        return _FakeSentMessage()


def _patch_scheduler_dependencies_for_success(monkeypatch, tmp_path, captured_calls):
    """Stub every LLM/shadow call and let generation succeed, writing a real image file
    so FSInputFile(image_path) and the send step both work without any network access.
    """
    counter = {"n": 0}

    async def fake_text_plan_shadow(**_kwargs):
        return None

    async def fake_scene_plan_shadow(**_kwargs):
        return None

    async def fake_generate_affirmations(**_kwargs):
        return ["Affirmation one", "Affirmation two", "Affirmation three"]

    def fake_text_reviewer_shadow(**_kwargs):
        return None

    async def fake_build_enriched_image_prompt(**_kwargs):
        return "a calm scene", "template"

    async def fake_generate_image(**kwargs):
        captured_calls.append(kwargs)
        counter["n"] += 1
        path = tmp_path / f"img_{counter['n']}.png"
        path.write_bytes(b"fake-png-bytes")
        return str(path)

    monkeypatch.setattr(scheduler, "build_text_plan_shadow_best_effort", fake_text_plan_shadow)
    monkeypatch.setattr(scheduler, "build_scene_plan_shadow_best_effort", fake_scene_plan_shadow)
    monkeypatch.setattr(scheduler, "generate_affirmations", fake_generate_affirmations)
    monkeypatch.setattr(scheduler, "build_text_reviewer_shadow_best_effort", fake_text_reviewer_shadow)
    monkeypatch.setattr(scheduler, "build_enriched_image_prompt", fake_build_enriched_image_prompt)
    monkeypatch.setattr(scheduler, "generate_image", fake_generate_image)
    monkeypatch.setattr(scheduler, "is_text_planner_controlled_enabled", lambda *_a, **_k: False)
    monkeypatch.setattr(scheduler, "is_scene_planner_image_prompt_enabled", lambda *_a, **_k: False)


def _run_scheduled_daily_deliveries(monkeypatch, tmp_path, allowed_visual_modes, style="auto", days=8):
    """Create one subscription and run `days` consecutive daily 08:00 deliveries for it.

    Each day is a distinct logical delivery (different delivery_date), so every call
    to send_daily_affirmations is expected to generate and send exactly one message;
    returns the kwargs captured from each generate_image call, oldest first.
    """
    captured_calls: list[dict] = []

    async def run():
        monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "sched.db"))
        await db.init_db()
        await db.create_or_update_user(500, "u", name="Tester")
        await db.create_subscription(
            500,
            "random",
            None,
            style,
            "ru",
            8,
            0,
            subscription_mode="weekly_balance",
            subscription_style_mode=style,
            visual_mode=allowed_visual_modes[0],
            allowed_visual_modes=allowed_visual_modes,
        )
        _patch_scheduler_dependencies_for_success(monkeypatch, tmp_path, captured_calls)
        fake_bot = _FakeBot()
        for day in range(1, days + 1):
            now = dt.datetime(2030, 1, day, 8, 0, tzinfo=scheduler.MOSCOW)
            await scheduler.send_daily_affirmations(fake_bot, now=now)
        assert len(fake_bot.sent) == days, "every distinct day must be delivered exactly once"

    asyncio.run(run())
    assert len(captured_calls) == days
    return captured_calls


@pytest.mark.parametrize(
    "allowed_visual_modes",
    [
        ["photo", "symbolic"],
        ["illustration", "symbolic"],
        ["photo", "illustration", "symbolic"],
    ],
)
def test_scheduled_delivery_uses_only_allowed_visual_modes(monkeypatch, tmp_path, allowed_visual_modes):
    random.seed(20240601)
    calls = _run_scheduled_daily_deliveries(monkeypatch, tmp_path, allowed_visual_modes, days=10)
    modes = [call["visual_mode"] for call in calls]
    assert modes
    assert all(mode in allowed_visual_modes for mode in modes)


def test_scheduled_delivery_anti_repeat_alternates_across_days(monkeypatch, tmp_path):
    # With exactly two allowed modes, avoiding the previous *confirmed* delivery's mode
    # forces strict day-to-day alternation - deterministic, no seed needed.
    random.seed(1)
    allowed_visual_modes = ["photo", "symbolic"]
    calls = _run_scheduled_daily_deliveries(monkeypatch, tmp_path, allowed_visual_modes, days=6)
    modes = [call["visual_mode"] for call in calls]
    assert len(set(modes)) == 2
    assert all(modes[i] != modes[i + 1] for i in range(len(modes) - 1))


# ---------------------------------------------------------------------------
# Product rule: multi-mode subscriptions keep style automatic; single-mode
# subscriptions keep compatible concrete styles; incompatible styles -> auto
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "allowed, style, expected",
    [
        # Single mode: compatible concrete styles are kept.
        (["photo"], "sunny_morning_photo", "sunny_morning_photo"),
        (["photo"], "bright_photo_card", "bright_photo_card"),  # alias of sunny_morning_photo
        (["illustration"], "bright_nature_card", "bright_nature_card"),
        (["illustration"], "realistic", "realistic"),  # legacy key -> illustration
        (["symbolic"], "mandala_harmony", "mandala_harmony"),
        # Single mode: incompatible or unknown styles fall back to auto.
        (["photo"], "mandala_harmony", "auto"),
        (["illustration"], "sunny_morning_photo", "auto"),
        (["symbolic"], "bright_nature_card", "auto"),
        (["photo"], "definitely_not_a_style", "auto"),
        # Multi-mode: any concrete style falls back to auto ...
        (["photo", "illustration"], "mandala_harmony", "auto"),
        (["illustration", "symbolic"], "sunny_morning_photo", "auto"),
        (["photo", "symbolic"], "sunny_morning_photo", "auto"),
        (["photo", "illustration", "symbolic"], "cozy_home_photo", "auto"),
        # ... while non-pinning styles are kept, in every pool.
        (["photo", "symbolic"], "auto", "auto"),
        (["photo", "symbolic"], "random_suitable", "random_suitable"),
        (["photo"], "random_suitable", "random_suitable"),
        (["photo", "symbolic"], None, "auto"),
    ],
)
def test_effective_subscription_style_mode(allowed, style, expected):
    assert effective_subscription_style_mode(allowed, style) == expected


def test_style_keyboard_for_subscription_offers_no_concrete_style_for_multi_mode():
    for allowed in (
        ["photo", "illustration"],
        ["photo", "symbolic"],
        ["illustration", "symbolic"],
        ["photo", "illustration", "symbolic"],
    ):
        keyboard = style_keyboard_for_subscription("ru", visual_mode=allowed)
        callbacks = {button.callback_data for row in keyboard.inline_keyboard for button in row}
        assert callbacks == {"style:auto", "style:random_suitable"}, allowed


@pytest.mark.parametrize(
    "visual_mode, expected_keys",
    [
        ("photo", PHOTO_STYLE_KEYS),
        (["photo"], PHOTO_STYLE_KEYS),
        (["illustration"], ILLUSTRATION_STYLE_KEYS),
    ],
)
def test_style_keyboard_for_subscription_keeps_concrete_styles_for_single_mode(visual_mode, expected_keys):
    keyboard = style_keyboard_for_subscription("ru", visual_mode=visual_mode)
    callbacks = {button.callback_data for row in keyboard.inline_keyboard for button in row}
    assert callbacks == {"style:auto", "style:random_suitable", *(f"style:{key}" for key in expected_keys)}


def test_summary_reports_effective_style_for_multi_mode_row_with_persisted_concrete_style():
    # Pre-existing row: multi-mode pool + concrete style. Runtime treats the
    # style as auto, so the summary must not claim a concrete style.
    legacy_row = {
        "id": 1,
        "hour": 8,
        "minute": 0,
        "sphere": "random",
        "subscription_mode": "weekly_balance",
        "subscription_style_mode": "sunny_morning_photo",
        "image_style": "sunny_morning_photo",
        "allowed_visual_modes_json": json.dumps(["photo", "symbolic"]),
    }
    text = format_subscription_summary(legacy_row, "en")
    assert "Photo + mandalas" in text
    assert "Style: 🎨 Auto" in text
    assert "Sunny morning" not in text


def test_summary_keeps_concrete_style_for_single_mode_row():
    row = {
        "id": 1,
        "hour": 8,
        "minute": 0,
        "sphere": "random",
        "subscription_mode": "weekly_balance",
        "subscription_style_mode": "sunny_morning_photo",
        "image_style": "sunny_morning_photo",
        "allowed_visual_modes_json": json.dumps(["photo"]),
    }
    text = format_subscription_summary(row, "en")
    assert "Sunny morning" in text


def test_summary_reports_auto_for_legacy_mixed_row_with_concrete_style():
    # visual_mode="mixed" without allowed_visual_modes_json resolves to
    # [photo, illustration] - a multi-mode pool.
    legacy_mixed_row = {
        "id": 1,
        "hour": 8,
        "minute": 0,
        "sphere": "random",
        "subscription_mode": "weekly_balance",
        "subscription_style_mode": "sunny_morning_photo",
        "image_style": "sunny_morning_photo",
        "visual_mode": "mixed",
    }
    text = format_subscription_summary(legacy_mixed_row, "en")
    assert "Style: 🎨 Auto" in text


# ---------------------------------------------------------------------------
# Scheduled generation: the style actually handed to image generation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "allowed_visual_modes, persisted_style",
    [
        (["photo", "illustration"], "mandala_harmony"),
        (["illustration", "symbolic"], "sunny_morning_photo"),
        (["photo", "symbolic"], "sunny_morning_photo"),
        (["photo", "illustration", "symbolic"], "cozy_home_photo"),
    ],
)
def test_scheduled_multi_mode_with_persisted_concrete_style_stays_multi_mode(
    monkeypatch, tmp_path, allowed_visual_modes, persisted_style
):
    random.seed(20240602)
    calls = _run_scheduled_daily_deliveries(monkeypatch, tmp_path, allowed_visual_modes, persisted_style, days=12)

    # The concrete style must not pin the mode: every allowed mode is used ...
    assert {call["visual_mode"] for call in calls} == set(allowed_visual_modes)
    for call in calls:
        # ... and the style handed downstream always belongs to the chosen mode.
        assert call["style"] == call["resolved_style_override"]
        assert get_visual_mode_for_style(call["style"]) == call["visual_mode"]


@pytest.mark.parametrize(
    "allowed_visual_modes, incompatible_style, mode_style_keys",
    [
        (["photo"], "mandala_harmony", PHOTO_STYLE_KEYS),
        (["illustration"], "sunny_morning_photo", ILLUSTRATION_STYLE_KEYS),
        (["photo"], "bright_nature_card", PHOTO_STYLE_KEYS),
    ],
)
def test_scheduled_single_mode_drops_incompatible_style_to_auto(
    monkeypatch, tmp_path, allowed_visual_modes, incompatible_style, mode_style_keys
):
    calls = _run_scheduled_daily_deliveries(monkeypatch, tmp_path, allowed_visual_modes, incompatible_style, days=4)

    for call in calls:
        assert call["visual_mode"] == allowed_visual_modes[0]
        assert call["style"] != incompatible_style
        assert call["style"] in mode_style_keys
        assert call["resolved_style_override"] == call["style"]


@pytest.mark.parametrize(
    "allowed_visual_modes, concrete_style",
    [
        (["photo"], "living_nature_photo"),
        (["illustration"], "minimal_botanical"),
        (["symbolic"], "botanical_mandala"),
    ],
)
def test_scheduled_single_mode_keeps_compatible_concrete_style(
    monkeypatch, tmp_path, allowed_visual_modes, concrete_style
):
    calls = _run_scheduled_daily_deliveries(monkeypatch, tmp_path, allowed_visual_modes, concrete_style, days=4)

    for call in calls:
        assert call["visual_mode"] == allowed_visual_modes[0]
        assert call["style"] == concrete_style
        assert call["resolved_style_override"] == concrete_style
