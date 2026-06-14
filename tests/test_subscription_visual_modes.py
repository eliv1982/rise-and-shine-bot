import asyncio
import json
import random

import pytest

import database as db
import scheduler
from keyboards.inline import subscription_select_keyboard
from services.ritual_config import (
    VISUAL_MIX_PRESETS,
    get_allowed_visual_modes,
    pick_subscription_visual_mode,
    resolve_subscription_visual_mode,
)


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


def test_resolve_subscription_visual_mode_concrete_symbolic_style_resolves_to_symbolic():
    rng = random.Random(0)
    for _ in range(10):
        mode = resolve_subscription_visual_mode(
            ["photo", "symbolic"], selected_style="mandala_harmony", rng=rng
        )
        assert mode == "symbolic"


def test_resolve_subscription_visual_mode_concrete_photo_style_resolves_to_photo():
    rng = random.Random(0)
    for _ in range(10):
        mode = resolve_subscription_visual_mode(
            ["photo", "symbolic"], selected_style="sunny_morning_photo", rng=rng
        )
        assert mode == "photo"


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
# Scheduled generation: mode selection is constrained to allowed_visual_modes
# ---------------------------------------------------------------------------


class _FakeBot:
    async def send_photo(self, **kwargs):
        raise AssertionError("send_photo should not be reached in this test")


def _patch_scheduler_dependencies(monkeypatch, captured_visual_modes):
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
        captured_visual_modes.append(kwargs["visual_mode"])
        raise RuntimeError("stop before sending - image generation not under test")

    monkeypatch.setattr(scheduler, "build_text_plan_shadow_best_effort", fake_text_plan_shadow)
    monkeypatch.setattr(scheduler, "build_scene_plan_shadow_best_effort", fake_scene_plan_shadow)
    monkeypatch.setattr(scheduler, "generate_affirmations", fake_generate_affirmations)
    monkeypatch.setattr(scheduler, "build_text_reviewer_shadow_best_effort", fake_text_reviewer_shadow)
    monkeypatch.setattr(scheduler, "build_enriched_image_prompt", fake_build_enriched_image_prompt)
    monkeypatch.setattr(scheduler, "generate_image", fake_generate_image)
    monkeypatch.setattr(scheduler, "is_text_planner_controlled_enabled", lambda *_a, **_k: False)
    monkeypatch.setattr(scheduler, "is_scene_planner_image_prompt_enabled", lambda *_a, **_k: False)


def _base_subscription(allowed_visual_modes):
    return {
        "id": 1,
        "user_id": 100,
        "sphere": "random",
        "subsphere": None,
        "image_style": "auto",
        "language": "ru",
        "hour": 8,
        "minute": 0,
        "subscription_mode": "weekly_balance",
        "subscription_sphere": None,
        "subscription_style_mode": "auto",
        "visual_mode": allowed_visual_modes[0],
        "allowed_visual_modes_json": json.dumps(allowed_visual_modes),
        "user_gender": None,
        "user_name": "Tester",
    }


@pytest.mark.parametrize(
    "allowed_visual_modes",
    [
        ["photo", "symbolic"],
        ["illustration", "symbolic"],
        ["photo", "illustration", "symbolic"],
    ],
)
def test_scheduled_run_uses_only_allowed_visual_modes(monkeypatch, allowed_visual_modes):
    async def run():
        captured: list[str] = []
        _patch_scheduler_dependencies(monkeypatch, captured)
        scheduler._last_subscription_visual_mode.clear()

        sub = _base_subscription(allowed_visual_modes)

        async def fake_get_due_subscriptions(_now):
            return [sub]

        monkeypatch.setattr(scheduler, "get_due_subscriptions", fake_get_due_subscriptions)

        for _ in range(10):
            await scheduler.send_daily_affirmations(_FakeBot())

        assert captured
        assert all(mode in allowed_visual_modes for mode in captured)

    asyncio.run(run())


def test_scheduled_run_anti_repeat_prefers_alternative_mode(monkeypatch):
    async def run():
        captured: list[str] = []
        _patch_scheduler_dependencies(monkeypatch, captured)
        scheduler._last_subscription_visual_mode.clear()

        allowed_visual_modes = ["photo", "symbolic"]
        sub = _base_subscription(allowed_visual_modes)

        async def fake_get_due_subscriptions(_now):
            return [sub]

        monkeypatch.setattr(scheduler, "get_due_subscriptions", fake_get_due_subscriptions)

        for _ in range(6):
            await scheduler.send_daily_affirmations(_FakeBot())

        # With two allowed modes and anti-repeat, consecutive runs should not
        # always pick the same mode.
        assert len(set(captured)) == 2

    asyncio.run(run())

