"""Subscription visual-mix flow through the real handlers, FSM data and SQLite.

Product rule under test:
- multi-mode subscription -> style stays automatic ("auto" / "random_suitable"),
  no mode-specific style is offered or persisted;
- single-mode subscription -> compatible concrete styles work as before;
- unrelated partial edits never touch the persisted visual mix.
"""

import asyncio
import json
from types import SimpleNamespace

import pytest

import database as db
from handlers import subscribe
from services.ritual_config import ILLUSTRATION_STYLE_KEYS, PHOTO_STYLE_KEYS, SYMBOLIC_STYLE_KEYS
from states import SubscriptionState

USER_ID = 501


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


def _style_callbacks(keys) -> set[str]:
    return {f"style:{key}" for key in keys}


@pytest.fixture
def flow_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "visual_mix_flow.db"))

    async def setup():
        await db.init_db()
        await db.create_or_update_user(USER_ID, "u", name="U", language="ru")

    asyncio.run(setup())


async def _drive_add_flow(preset: str, style_callback: str) -> dict:
    """Walk mix -> style -> hour -> minute -> confirm the way a user would."""
    state = _FakeState(
        SubscriptionState.choosing_visual_mode,
        language="ru",
        subscription_action="add",
        subscription_mode="weekly_balance",
        sphere="random",
    )
    observed: dict = {}

    callback = await _click(subscribe.sub_choose_visual_mix, f"visualmix:{preset}", state)
    observed["style_step_text"], style_markup = callback.message.edits[-1]
    observed["style_step_callbacks"] = _callback_data(style_markup)
    observed["state_after_mix"] = state.state
    observed["data_after_mix"] = dict(state.data)

    await _click(subscribe.sub_choose_style, style_callback, state)
    observed["state_after_style"] = state.state
    observed["style_in_state"] = state.data["style"]

    await _click(subscribe.sub_choose_hour, "hour:8", state)
    callback = await _click(subscribe.sub_choose_minute, "minute:30", state)
    observed["state_after_minute"] = state.state
    observed["confirm_text"] = callback.message.edits[-1][0]

    await _click(subscribe.sub_confirm, "sub:confirm", state)
    (observed["saved"],) = await db.get_active_subscriptions(USER_ID)
    return observed


@pytest.mark.parametrize(
    "preset, expected_modes, style_callback, expected_style, expected_mix_label, expected_style_label",
    [
        # A stale/forged concrete style pick in a multi-mode pool is discarded.
        ("photo_symbolic", ["photo", "symbolic"], "style:sunny_morning_photo", "auto", "Фото + мандалы", "Автоподбор"),
        ("all", ["photo", "illustration", "symbolic"], "style:mandala_harmony", "auto", "Все режимы", "Автоподбор"),
        ("photo_illustration", ["photo", "illustration"], "style:auto", "auto", "Фото + иллюстрация", "Автоподбор"),
        (
            "illustration_symbolic",
            ["illustration", "symbolic"],
            "style:random_suitable",
            "random_suitable",
            "Иллюстрация + мандалы",
            "Разные подходящие стили",
        ),
    ],
)
def test_visual_mix_flow_multi_mode_keeps_style_automatic(
    flow_db, preset, expected_modes, style_callback, expected_style, expected_mix_label, expected_style_label
):
    observed = asyncio.run(_drive_add_flow(preset, style_callback))

    # visualmix:<preset> -> allowed modes collected in FSM data, next step is style.
    assert observed["data_after_mix"]["allowed_visual_modes"] == expected_modes
    assert observed["data_after_mix"]["visual_mode"] == expected_modes[0]
    assert observed["state_after_mix"] == SubscriptionState.choosing_style

    # Multi-mode: only automatic styles are offered, and the user is told why.
    assert observed["style_step_callbacks"] == {"style:auto", "style:random_suitable"}
    assert "автоматически" in observed["style_step_text"]

    # Flow continues normally; a concrete pick never reaches state or the DB.
    assert observed["state_after_style"] == SubscriptionState.choosing_hour
    assert observed["style_in_state"] == expected_style
    assert observed["state_after_minute"] == SubscriptionState.confirming

    # Confirmation text is truthful about both the mix and the style.
    assert expected_mix_label in observed["confirm_text"]
    assert expected_style_label in observed["confirm_text"]

    saved = observed["saved"]
    assert json.loads(saved["allowed_visual_modes_json"]) == expected_modes
    assert saved["visual_mode"] == expected_modes[0]
    assert saved["subscription_style_mode"] == expected_style
    assert saved["image_style"] == expected_style


@pytest.mark.parametrize(
    "preset, mode_style_keys, style_callback, expected_style",
    [
        ("photo", PHOTO_STYLE_KEYS, "style:sunny_morning_photo", "sunny_morning_photo"),
        ("illustration", ILLUSTRATION_STYLE_KEYS, "style:quiet_interior", "quiet_interior"),
        ("symbolic", SYMBOLIC_STYLE_KEYS, "style:botanical_mandala", "botanical_mandala"),
        # A style from another mode is not honored for a single-mode subscription either.
        ("photo", PHOTO_STYLE_KEYS, "style:mandala_harmony", "auto"),
    ],
)
def test_visual_mix_flow_single_mode_keeps_concrete_style_selection(
    flow_db, preset, mode_style_keys, style_callback, expected_style
):
    observed = asyncio.run(_drive_add_flow(preset, style_callback))

    assert observed["data_after_mix"]["allowed_visual_modes"] == [preset]
    assert observed["state_after_mix"] == SubscriptionState.choosing_style
    assert observed["style_step_callbacks"] == {
        "style:auto",
        "style:random_suitable",
        *_style_callbacks(mode_style_keys),
    }
    assert "автоматически" not in observed["style_step_text"]
    assert observed["state_after_style"] == SubscriptionState.choosing_hour
    assert observed["state_after_minute"] == SubscriptionState.confirming

    saved = observed["saved"]
    assert json.loads(saved["allowed_visual_modes_json"]) == [preset]
    assert saved["subscription_style_mode"] == expected_style
    assert saved["image_style"] == expected_style


async def _create_subscription(**overrides) -> int:
    values = dict(
        user_id=USER_ID,
        sphere="random",
        subsphere=None,
        image_style="auto",
        language="ru",
        hour=8,
        minute=0,
        subscription_mode="weekly_balance",
        subscription_sphere=None,
        subscription_style_mode="auto",
        visual_mode="illustration",
        allowed_visual_modes=["illustration"],
    )
    values.update(overrides)
    return await db.create_subscription(**values)


def test_editing_single_mode_into_multi_mode_resets_concrete_style_to_auto(flow_db):
    async def run():
        sub_id = await _create_subscription(
            image_style="sunny_morning_photo",
            subscription_style_mode="sunny_morning_photo",
            visual_mode="photo",
            allowed_visual_modes=["photo"],
        )
        state = _FakeState(SubscriptionState.choosing_visual_mode)
        await state.update_data(edit_subscription_id=sub_id, partial_edit_field="visual")

        await _click(subscribe.sub_choose_visual_mix, "visualmix:photo_symbolic", state)

        saved = await db.get_subscription_by_id(sub_id, USER_ID)
        assert json.loads(saved["allowed_visual_modes_json"]) == ["photo", "symbolic"]
        assert saved["subscription_style_mode"] == "auto"
        assert saved["image_style"] == "auto"

        # Asking to pick a style afterwards offers only automatic styles, and a
        # forged concrete pick is discarded instead of persisted.
        callback = await _click(subscribe.sub_visual_style_followup, f"substylepick:{sub_id}:yes", state)
        assert _callback_data(callback.message.edits[-1][1]) == {"style:auto", "style:random_suitable"}
        await _click(subscribe.sub_choose_style, "style:sunny_morning_photo", state)

        saved = await db.get_subscription_by_id(sub_id, USER_ID)
        assert json.loads(saved["allowed_visual_modes_json"]) == ["photo", "symbolic"]
        assert saved["subscription_style_mode"] == "auto"
        assert saved["image_style"] == "auto"

    asyncio.run(run())


def test_editing_multi_mode_into_single_mode_allows_concrete_style_again(flow_db):
    async def run():
        sub_id = await _create_subscription(
            visual_mode="photo", allowed_visual_modes=["photo", "symbolic"]
        )
        state = _FakeState(SubscriptionState.choosing_visual_mode)
        await state.update_data(edit_subscription_id=sub_id, partial_edit_field="visual")

        await _click(subscribe.sub_choose_visual_mix, "visualmix:photo", state)
        callback = await _click(subscribe.sub_visual_style_followup, f"substylepick:{sub_id}:yes", state)
        assert _callback_data(callback.message.edits[-1][1]) == {
            "style:auto",
            "style:random_suitable",
            *_style_callbacks(PHOTO_STYLE_KEYS),
        }
        await _click(subscribe.sub_choose_style, "style:cozy_home_photo", state)

        saved = await db.get_subscription_by_id(sub_id, USER_ID)
        assert json.loads(saved["allowed_visual_modes_json"]) == ["photo"]
        assert saved["subscription_style_mode"] == "cozy_home_photo"

    asyncio.run(run())


def test_edit_style_entry_for_multi_mode_subscription_offers_only_automatic_styles(flow_db):
    async def run():
        # Row saved before the product rule: multi-mode pool + concrete style.
        sub_id = await _create_subscription(
            image_style="sunny_morning_photo",
            subscription_style_mode="sunny_morning_photo",
            visual_mode="photo",
            allowed_visual_modes=["photo", "illustration"],
        )
        state = _FakeState()

        callback = await _click(subscribe.sub_edit_field, f"subfield:{sub_id}:style", state)

        text, markup = callback.message.answers[-1]
        assert _callback_data(markup) == {"style:auto", "style:random_suitable"}
        assert "автоматически" in text
        assert state.state == SubscriptionState.choosing_style

    asyncio.run(run())


async def _edit_time(sub_id, state):
    await _click(subscribe.sub_edit_field, f"subfield:{sub_id}:time", state)
    await _click(subscribe.sub_choose_hour, "hour:21", state)
    await _click(subscribe.sub_choose_minute, "minute:45", state)


async def _edit_language(sub_id, state):
    await _click(subscribe.sub_edit_language_selected, f"sublangedit:{sub_id}:en", state)


async def _edit_sphere(sub_id, state):
    await _click(subscribe.sub_edit_field, f"subfield:{sub_id}:sphere", state)
    await _click(subscribe.sub_choose_sphere, "sphere:money", state)


@pytest.mark.parametrize(
    "edit, expected_changes",
    [
        (_edit_time, {"hour": 21, "minute": 45}),
        (_edit_language, {"language": "en"}),
        (_edit_sphere, {"sphere": "money", "subscription_sphere": "money"}),
    ],
)
def test_partial_edit_of_unrelated_field_preserves_visual_mix(flow_db, edit, expected_changes):
    async def run():
        # Deliberately not "visual_mode first" ordering, to catch re-derivation.
        original_modes = ["illustration", "symbolic", "photo"]
        sub_id = await _create_subscription(
            sphere="inner_peace",
            subscription_mode="sphere_focus",
            subscription_sphere="inner_peace",
            visual_mode="illustration",
            allowed_visual_modes=original_modes,
        )
        before = await db.get_subscription_by_id(sub_id, USER_ID)

        await edit(sub_id, _FakeState())

        after = await db.get_subscription_by_id(sub_id, USER_ID)
        for column, value in expected_changes.items():
            assert after[column] == value
        assert json.loads(after["allowed_visual_modes_json"]) == original_modes
        for column in ("visual_mode", "subscription_style_mode", "image_style"):
            assert after[column] == before[column]

    asyncio.run(run())
