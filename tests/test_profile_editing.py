import asyncio
from types import SimpleNamespace

from handlers import start
from states import ProfileEditState


class _FakeState:
    def __init__(self):
        self.state = None

    async def set_state(self, state):
        self.state = state

    async def get_state(self):
        return self.state

    async def clear(self):
        self.state = None


class _FakeMessage:
    def __init__(self, user_id=77, text=None):
        self.from_user = SimpleNamespace(id=user_id)
        self.text = text
        self.answers = []
        self.edits = []

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))

    async def edit_text(self, text, reply_markup=None):
        self.edits.append((text, reply_markup))


class _FakeCallback:
    def __init__(self, data, user_id=77):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = _FakeMessage(user_id=user_id)
        self.answered = []

    async def answer(self, text=None):
        self.answered.append(text)
        return None


def test_profile_name_edit_callback_sets_explicit_state(monkeypatch):
    async def _fake_get_user(_uid):
        return {"language": "ru", "name": "Алина", "gender": "female"}

    monkeypatch.setattr(start, "get_user", _fake_get_user)

    state = _FakeState()
    callback = _FakeCallback("profile_edit:name")
    asyncio.run(start.profile_edit_name(callback, state))

    assert state.state == ProfileEditState.editing_name
    assert any("Как к тебе обращаться" in text for text, _ in callback.message.answers)


def test_profile_choice_callback_updates_preferences(monkeypatch):
    captured = {}
    current_prefs = {"tone_preference": "warm_soft"}

    async def _fake_merge(_uid, patch):
        captured["patch"] = patch
        current_prefs.update(patch)
        return True

    async def _fake_get_user(_uid):
        return {"language": "ru", "name": "Алина", "gender": "female"}

    async def _fake_get_prefs(_uid):
        return dict(current_prefs)

    async def _fake_get_subscriptions(_uid):
        return []

    monkeypatch.setattr(start, "merge_user_profile_preferences", _fake_merge)
    monkeypatch.setattr(start, "get_user", _fake_get_user)
    monkeypatch.setattr(start, "get_user_profile_preferences", _fake_get_prefs)
    monkeypatch.setattr(start, "get_active_subscriptions", _fake_get_subscriptions)

    state = _FakeState()
    callback = _FakeCallback("profile_pref:tone_preference:poetic")
    asyncio.run(start.profile_set_preference_callback(callback, state))

    assert captured["patch"] == {"tone_preference": "poetic"}
    assert callback.message.edits
    assert "🎨 Тон общения: Поэтично" in callback.message.edits[-1][0]


def test_profile_support_style_choice_persists_in_summary(monkeypatch):
    async def _fake_merge(_uid, patch):
        return True

    async def _fake_get_user(_uid):
        return {"language": "ru", "name": "Алина", "gender": "female"}

    async def _fake_get_prefs(_uid):
        return {"support_style": "grounding"}

    async def _fake_get_subscriptions(_uid):
        return []

    monkeypatch.setattr(start, "merge_user_profile_preferences", _fake_merge)
    monkeypatch.setattr(start, "get_user", _fake_get_user)
    monkeypatch.setattr(start, "get_user_profile_preferences", _fake_get_prefs)
    monkeypatch.setattr(start, "get_active_subscriptions", _fake_get_subscriptions)

    state = _FakeState()
    callback = _FakeCallback("profile_pref:support_style:grounding")
    asyncio.run(start.profile_set_preference_callback(callback, state))

    assert "🤝 Формат поддержки: Заземлить" in callback.message.edits[-1][0]


def test_profile_text_length_choice_persists_in_summary(monkeypatch):
    async def _fake_merge(_uid, patch):
        return True

    async def _fake_get_user(_uid):
        return {"language": "ru", "name": "Алина", "gender": "female"}

    async def _fake_get_prefs(_uid):
        return {"text_length_preference": "detailed"}

    async def _fake_get_subscriptions(_uid):
        return []

    monkeypatch.setattr(start, "merge_user_profile_preferences", _fake_merge)
    monkeypatch.setattr(start, "get_user", _fake_get_user)
    monkeypatch.setattr(start, "get_user_profile_preferences", _fake_get_prefs)
    monkeypatch.setattr(start, "get_active_subscriptions", _fake_get_subscriptions)

    state = _FakeState()
    callback = _FakeCallback("profile_pref:text_length_preference:detailed")
    asyncio.run(start.profile_set_preference_callback(callback, state))

    assert "📝 Длина текста: Подробнее" in callback.message.edits[-1][0]


def test_profile_choice_keyboard_marks_selected_option():
    markup = start.profile_tone_keyboard("ru", "calm_no_pathos")
    texts = [button.text for row in markup.inline_keyboard for button in row]
    assert "✅ Спокойно, без пафоса" in texts


def test_profile_callback_refreshes_by_editing_existing_message(monkeypatch):
    async def _fake_merge(_uid, patch):
        return True

    async def _fake_get_user(_uid):
        return {"language": "ru", "name": "Алина", "gender": "female"}

    async def _fake_get_prefs(_uid):
        return {"tone_preference": "poetic"}

    async def _fake_get_subscriptions(_uid):
        return []

    monkeypatch.setattr(start, "merge_user_profile_preferences", _fake_merge)
    monkeypatch.setattr(start, "get_user", _fake_get_user)
    monkeypatch.setattr(start, "get_user_profile_preferences", _fake_get_prefs)
    monkeypatch.setattr(start, "get_active_subscriptions", _fake_get_subscriptions)

    state = _FakeState()
    callback = _FakeCallback("profile_pref:tone_preference:poetic")
    asyncio.run(start.profile_set_preference_callback(callback, state))

    assert callback.message.edits
    assert not any("Профиль обновлён" in text for text, _ in callback.message.answers)


def test_profile_list_text_input_normalizes_values(monkeypatch):
    captured = {}

    async def _fake_merge(_uid, patch):
        captured["patch"] = patch
        return True

    async def _fake_get_user(_uid):
        return {"language": "ru", "name": "Алина", "gender": "female"}

    async def _fake_get_prefs(_uid):
        return {"avoid_words": ["давление"]}

    async def _fake_get_subscriptions(_uid):
        return []

    monkeypatch.setattr(start, "merge_user_profile_preferences", _fake_merge)
    monkeypatch.setattr(start, "get_user", _fake_get_user)
    monkeypatch.setattr(start, "get_user_profile_preferences", _fake_get_prefs)
    monkeypatch.setattr(start, "get_active_subscriptions", _fake_get_subscriptions)

    state = _FakeState()
    state.state = ProfileEditState.editing_avoid_words
    message = _FakeMessage(text=" давление, срочно ,  мягче ")
    asyncio.run(start.profile_process_avoid_words(message, state))

    assert captured["patch"] == {"avoid_words": ["давление", "срочно", "мягче"]}
    assert state.state is None


def test_profile_name_text_input_updates_user_name_explicitly(monkeypatch):
    captured = {}

    async def _fake_update_user_profile(_uid, name=None, **_kwargs):
        captured["name"] = name

    async def _fake_get_user(_uid):
        return {"language": "ru", "name": "Алина", "gender": "female"}

    async def _fake_get_prefs(_uid):
        return {}

    async def _fake_get_subscriptions(_uid):
        return []

    monkeypatch.setattr(start, "update_user_profile", _fake_update_user_profile)
    monkeypatch.setattr(start, "get_user", _fake_get_user)
    monkeypatch.setattr(start, "get_user_profile_preferences", _fake_get_prefs)
    monkeypatch.setattr(start, "get_active_subscriptions", _fake_get_subscriptions)

    state = _FakeState()
    state.state = ProfileEditState.editing_name
    message = _FakeMessage(text="Лина")
    asyncio.run(start.profile_process_name(message, state))

    assert captured["name"] == "Лина"
    assert state.state is None


def test_profile_edit_state_avoids_main_menu_router_collision():
    assert ProfileEditState.editing_name.state != "None"
