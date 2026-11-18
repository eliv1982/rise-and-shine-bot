"""FIX-01: production dispatcher order, real FSM/storage, offline Telegram transport."""

from datetime import datetime, timezone
from hashlib import sha256
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage, SendVoice
from aiogram.types import CallbackQuery, Chat, InlineKeyboardMarkup, Message, MessageEntity, Update, User, Voice

import database as db
from bot import create_dispatcher
from handlers import generation, start, subscribe
from services.language_policy import interface_language
from handlers.common_messages import menu_choose_option_text, menu_choose_style_text
from keyboards.inline import main_reply_keyboard
from services.subscription_ui import build_subscriptions_summary
from states import GenerationState, ProfileEditState, RegistrationState, SubscriptionState

USER_ID = 7701
NOW = datetime(2026, 11, 17, tzinfo=timezone.utc)
ACTIVE_STATES = [
    None, *RegistrationState.__all_states__, *GenerationState.__all_states__,
    *SubscriptionState.__all_states__, *ProfileEditState.__all_states__,
]
BUTTON_STATES = [
    *[state for state in GenerationState.__all_states__ if state.state not in {
        GenerationState.waiting_for_theme_early.state,
        GenerationState.waiting_for_custom_style.state,
        GenerationState.after_result.state,
    }],
    *SubscriptionState.__all_states__,
]


def utf16_length(text):
    return len(text.encode("utf-16-le")) // 2


class RecordingSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.edit_error = None
        self.chat_messages = {}
        self.next_message_id = 1000

    async def close(self):
        pass

    async def stream_content(self, *args, **kwargs):
        raise AssertionError("No network allowed")
        yield b""  # Make this an async generator, as required by BaseSession.

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, (SendMessage, EditMessageText)):
            if utf16_length(method.text) > 4096:
                raise TelegramBadRequest(method=method, message="Bad Request: message is too long")
            if isinstance(method, EditMessageText) and self.edit_error:
                raise self.edit_error
            if isinstance(method, EditMessageText):
                message_id = method.message_id
                previous = self.chat_messages.get(message_id)
                if previous and previous.text == method.text and previous.reply_markup == method.reply_markup:
                    raise TelegramBadRequest(method=method, message="Bad Request: message is not modified")
            else:
                message_id = self.next_message_id
                self.next_message_id += 1
            message = Message(
                message_id=message_id, date=NOW,
                chat=Chat(id=USER_ID, type="private"), text=method.text,
                from_user=User(id=bot.id, is_bot=True, first_name="Bot"),
                reply_markup=method.reply_markup if isinstance(method.reply_markup, InlineKeyboardMarkup) else None,
            )
            self.chat_messages[message_id] = message
            return message
        if isinstance(method, AnswerCallbackQuery):
            return True
        raise AssertionError(f"Unexpected Telegram request: {type(method).__name__}")

    @property
    def messages(self):
        return [call for call in self.calls if isinstance(call, (SendMessage, EditMessageText))]


class App:
    def __init__(self, dispatcher, bot):
        self.dispatcher = dispatcher
        self.bot = bot
        self.session = bot.session
        self.state = dispatcher.fsm.get_context(bot=bot, chat_id=USER_ID, user_id=USER_ID)

    async def send(self, text=None, *, callback=None, callback_message=None, voice=False):
        user = User(id=USER_ID, is_bot=False, first_name="Anna")
        payload = dict(message_id=123, date=NOW, chat=Chat(id=USER_ID, type="private"))
        if callback:
            message = callback_message or self.session.chat_messages.get(123) or Message(**payload, text="Existing menu", from_user=User(
                id=self.bot.id, is_bot=True, first_name="Bot",
            ))
            update = Update(update_id=1, callback_query=CallbackQuery(
                id="click", from_user=user, chat_instance="test", message=message, data=callback,
            ))
        else:
            if voice:
                payload["voice"] = Voice(file_id="voice", file_unique_id="unique", duration=1)
            if text and text.startswith("/"):
                payload["entities"] = [MessageEntity(type="bot_command", offset=0, length=len(text))]
            update = Update(update_id=1, message=Message(**payload, from_user=user, text=text))
        await self.dispatcher.feed_update(self.bot, update)


@pytest.fixture(scope="module")
def dispatcher():
    # The same factory and router order that polling uses; attach routers only once.
    return create_dispatcher()


def test_profile_handlers_are_registered_once(dispatcher):
    message_handlers = [handler.callback for router in dispatcher.chain_tail for handler in router.message.handlers]
    callback_handlers = [handler.callback for router in dispatcher.chain_tail for handler in router.callback_query.handlers]
    assert message_handlers.count(start.cmd_profile) == 1
    assert message_handlers.count(start.main_menu_profile) == 1
    assert callback_handlers.count(start.profile_callback) == 1


@pytest_asyncio.fixture
async def app(dispatcher, initialized_db, monkeypatch):
    monkeypatch.setattr(generation, "_run_generation", AsyncMock(side_effect=AssertionError("Unexpected generation")))
    bot = Bot(token="123456:offline-test-token", session=RecordingSession())
    app = App(dispatcher, bot)
    await app.state.clear()
    await db.create_or_update_user(USER_ID, "anna", name="Anna", gender="female", language="ru")
    await db.update_user_profile_preferences(USER_ID, {
        "current_focus": "saved focus", "avoid_words": ["rush"], "life_areas": ["home"],
    })
    await db.create_subscription(USER_ID, "random", None, "auto", "ru", 8, 30, subscription_mode="weekly_balance")
    yield app
    await app.state.clear()
    await bot.session.close()


async def snapshot():
    return await db.get_user(USER_ID), await db.get_user_profile_preferences(USER_ID), await db.get_active_subscriptions(USER_ID)


@pytest.mark.asyncio
@pytest.mark.parametrize("target", ["ru", "en"])
@pytest.mark.parametrize("initial_state", ACTIVE_STATES, ids=lambda s: s.state if s else "idle")
async def test_language_command_cancels_every_active_flow_and_refreshes_keyboard(app, target, initial_state):
    await db.update_user_language(USER_ID, "en" if target == "ru" else "ru")
    before_preferences = await db.get_user_profile_preferences(USER_ID)
    before_subscriptions = await db.get_active_subscriptions(USER_ID)
    completed = {"last_generation": {"sphere": "money", "use_profile_preferences": True}, "recent_generation_history": [{"selected_style": "nature"}]}
    await app.state.set_state(initial_state)
    await app.state.update_data(**completed, content_language="en", theme_text="unfinished input", partial_edit_field="time")
    await app.send("/language")
    assert await app.state.get_state() is None
    assert await app.state.get_data() == completed
    selector = app.session.messages[-1].reply_markup
    assert {b.callback_data for row in selector.inline_keyboard for b in row} == {"ui_lang:ru", "ui_lang:en"}
    await app.send(callback=f"ui_lang:{target}")
    assert (await db.get_user(USER_ID))["language"] == target
    assert app.session.messages[-1].reply_markup == main_reply_keyboard(target)
    assert sum(isinstance(c, AnswerCallbackQuery) for c in app.session.calls) == 1
    assert await app.state.get_data() == completed
    assert await db.get_user_profile_preferences(USER_ID) == before_preferences
    assert await db.get_active_subscriptions(USER_ID) == before_subscriptions


@pytest.mark.asyncio
@pytest.mark.parametrize("target", ["ru", "en"])
@pytest.mark.parametrize("source", ["profile", "global"])
@pytest.mark.parametrize("initial_state", [SubscriptionState.choosing_language, SubscriptionState.confirming, GenerationState.waiting_for_theme_early, ProfileEditState.editing_current_focus])
async def test_language_callback_during_active_flow_has_interface_ownership(app, target, source, initial_state):
    await db.update_user_language(USER_ID, "en" if target == "ru" else "ru")
    before_subscriptions = await db.get_active_subscriptions(USER_ID)
    await app.state.set_state(initial_state)
    await app.state.update_data(content_language="ru", edit_subscription_id=1)
    await app.send(callback=f"{'profile_lang' if source == 'profile' else 'ui_lang'}:{target}")
    assert await app.state.get_state() is None
    assert await app.state.get_data() == {}
    assert (await db.get_user(USER_ID))["language"] == target
    keyboard_messages = [m for m in app.session.messages if isinstance(m, SendMessage) and getattr(m.reply_markup, "keyboard", None)]
    assert keyboard_messages[-1].reply_markup == main_reply_keyboard(target)
    assert any(isinstance(c, AnswerCallbackQuery) for c in app.session.calls)
    assert await db.get_active_subscriptions(USER_ID) == before_subscriptions


@pytest.mark.asyncio
@pytest.mark.parametrize("ui,content", [("ru", "en"), ("en", "ru")])
@pytest.mark.parametrize("action", ["save", "edit", "cancel"])
async def test_subscription_setup_uses_interface_language_and_preserves_content_choice(app, ui, content, action):
    await db.update_user_language(USER_ID, ui)
    before = await snapshot()
    await app.send(callback="sub:add")
    assert {b.callback_data for row in app.session.messages[-1].reply_markup.inline_keyboard for b in row} == {"sub_lang:ru", "sub_lang:en"}
    await app.send(callback=f"sub_lang:{content}")
    if action == "edit":
        await app.state.update_data(subscription_action="edit", edit_subscription_id=before[2][0]["id"])
    assert "Выбери режим" in app.session.messages[-1].text if ui == "ru" else "Choose subscription mode" in app.session.messages[-1].text
    assert (await app.state.get_data())["content_language"] == content
    assert (await db.get_user(USER_ID))["language"] == ui
    for callback in ("submode:weekly_balance", "visualmix:photo", "style:auto", "hour:10", "minute:15"):
        await app.send(callback=callback)
    confirmation = app.session.messages[-1].text
    assert "Подтверди подписку" in confirmation if ui == "ru" else "Confirm subscription" in confirmation
    assert "Язык контента: Английский" in confirmation if ui == "ru" else "Content language: Russian" in confirmation
    await app.send(callback="sub:confirm" if action in ("save", "edit") else "sub:cancel")
    assert await app.state.get_state() is None
    assert (await db.get_user(USER_ID))["language"] == ui
    assert await db.get_user_profile_preferences(USER_ID) == before[1]
    subscriptions = await db.get_active_subscriptions(USER_ID)
    if action == "save":
        assert len(subscriptions) == len(before[2]) + 1
        assert next(s for s in subscriptions if s["hour"] == 10)["language"] == content
        assert "Подписка добавлена" in app.session.messages[-1].text if ui == "ru" else "Subscription added" in app.session.messages[-1].text
    elif action == "edit":
        assert len(subscriptions) == len(before[2])
        assert subscriptions[0]["language"] == content
        assert "Подписка обновлена" in app.session.messages[-1].text if ui == "ru" else "Subscription updated" in app.session.messages[-1].text
    else:
        assert subscriptions == before[2]
        assert "Твои подписки" in app.session.messages[-1].text if ui == "ru" else "Your subscriptions" in app.session.messages[-1].text


@pytest.mark.asyncio
@pytest.mark.parametrize("ui,content", [("ru", "en"), ("en", "ru")])
async def test_subscription_partial_edits_keep_global_and_existing_content_languages_separate(app, ui, content):
    await db.update_user_language(USER_ID, ui)
    subscription_id = (await db.get_active_subscriptions(USER_ID))[0]["id"]
    await app.send(callback=f"subfield:{subscription_id}:language")
    await app.send(callback=f"sublangedit:{subscription_id}:{content}")
    assert "Язык подписки обновлён" in app.session.messages[-1].text if ui == "ru" else "Subscription language updated" in app.session.messages[-1].text
    assert (await db.get_user(USER_ID))["language"] == ui
    assert (await db.get_subscription_by_id(subscription_id, USER_ID))["language"] == content
    await app.send(callback=f"subfield:{subscription_id}:time")
    await app.send(callback="hour:11")
    await app.send(callback="minute:20")
    saved = await db.get_subscription_by_id(subscription_id, USER_ID)
    assert saved["language"] == content
    assert (saved["hour"], saved["minute"]) == (11, 20)
    assert interface_language(await db.get_user(USER_ID)) == ui
    await app.send(callback="sub:dash")
    assert "Язык контента: Английский" in app.session.messages[-1].text if ui == "ru" else "Content language: Russian" in app.session.messages[-1].text


@pytest.mark.asyncio
@pytest.mark.parametrize("callback", ["lang:en", "sub_lang:en", "ui_lang:xx", "profile_lang:xx"])
async def test_stale_or_invalid_language_callbacks_are_acknowledged_without_mutation(app, callback):
    before = await snapshot()
    await app.send(callback=callback)
    assert await snapshot() == before
    assert sum(isinstance(c, AnswerCallbackQuery) for c in app.session.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("ui,content", [("ru", "en"), ("en", "ru")])
async def test_subscription_audio_uses_content_language_and_localizes_messages(app, monkeypatch, ui, content):
    await db.update_user_language(USER_ID, ui)
    monkeypatch.setitem(subscribe.last_subscription_affirmations, USER_ID, {
        "affirmations": ["Мой отдых важен"] * 4 if content == "ru" else ["My rest matters"] * 4,
        "language": content, "gender": "female",
    })
    synthesize = AsyncMock(return_value="offline-audio.ogg")
    monkeypatch.setattr(subscribe, "synthesize_affirmations_with_pauses", synthesize)
    await app.send(callback="sub_tts:yes")
    if content == "ru":
        synthesize.assert_awaited_once()
        assert any(isinstance(call, SendVoice) for call in app.session.calls)
    else:
        synthesize.assert_not_awaited()
        assert "Озвучка на английском скоро появится" in app.session.messages[-1].text


@pytest.mark.asyncio
@pytest.mark.parametrize("ui", ["ru", "en"])
async def test_subscription_audio_errors_use_interface_language(app, monkeypatch, ui):
    await db.update_user_language(USER_ID, ui)
    monkeypatch.setitem(subscribe.last_subscription_affirmations, USER_ID, {
        "affirmations": ["Мой отдых важен"] * 4, "language": "ru",
    })
    monkeypatch.setattr(subscribe, "synthesize_affirmations_with_pauses", AsyncMock(side_effect=RuntimeError("Ошибка сервиса")))
    await app.send(callback="sub_tts:yes")
    text = app.session.messages[-1].text
    assert "Сервис озвучки временно недоступен" in text if ui == "ru" else "Voice service is temporarily unavailable" in text


async def collect_profile_pages(app, first):
    pages = [first]
    while True:
        next_buttons = [
            button for row in pages[-1].reply_markup.inline_keyboard for button in row
            if button.text == "➡️"
        ]
        if not next_buttons:
            return pages
        assert len(pages) < 100, "Profile navigation loop"
        await app.send(callback=next_buttons[0].callback_data, callback_message=pages[-1])
        pages.append(app.session.chat_messages[first.message_id])


def profile_page_contents(pages):
    if len(pages) == 1:
        return pages[0].text
    title = pages[0].text.partition("\n")[0].rsplit(" (", 1)[0]
    for index, page in enumerate(pages):
        assert page.text.startswith(f"{title} ({index + 1}/{len(pages)})\n")
    return title + "\n" + "".join(page.text.partition("\n")[2] for page in pages)


@pytest.mark.asyncio
@pytest.mark.parametrize("initial_state", ACTIVE_STATES, ids=lambda s: s.state if s else "idle")
@pytest.mark.parametrize(("language", "button", "title"), [
    ("ru", "👤 Профиль", "👤 Твой профиль"), ("en", "👤 Profile", "👤 Your profile"),
])
async def test_profile_button_from_all_relevant_states(app, initial_state, language, button, title):
    await db.update_user_language(USER_ID, language)
    before = await snapshot()
    await app.state.set_state(initial_state)
    await app.state.update_data(language="en" if language == "ru" else "ru", stale="discard")
    await app.send(button)
    assert len(app.session.messages) == 1
    assert app.session.messages[0].text.startswith(title)
    assert await app.state.get_state() is None
    assert await app.state.get_data() == {}
    assert await snapshot() == before


@pytest.mark.asyncio
@pytest.mark.parametrize("initial_state", [GenerationState.choosing_style, SubscriptionState.choosing_style, ProfileEditState.editing_current_focus])
@pytest.mark.parametrize("entry", ["/profile", "profile:open"])
async def test_command_and_inline_profile_open(app, initial_state, entry):
    before = await snapshot()
    await app.state.set_state(initial_state)
    await app.state.update_data(stale="discard")
    await app.send(entry if entry.startswith("/") else None, callback=None if entry.startswith("/") else entry)
    assert len(app.session.messages) == 1
    assert app.session.messages[0].text.startswith("👤 Твой профиль")
    assert isinstance(app.session.messages[0], EditMessageText if entry == "profile:open" else SendMessage)
    assert await app.state.get_state() is None
    assert await app.state.get_data() == {}
    assert await snapshot() == before


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["ru", "en"])
async def test_profile_recognizes_a_stale_keyboard_language(app, language):
    await db.update_user_language(USER_ID, language)
    await app.state.set_state(ProfileEditState.editing_current_focus)
    before = await snapshot()
    await app.send("👤 Profile" if language == "ru" else "👤 Профиль")
    assert app.session.messages[0].text.startswith("👤 Твой профиль" if language == "ru" else "👤 Your profile")
    assert await app.state.get_state() is None
    assert await snapshot() == before


@pytest.mark.asyncio
@pytest.mark.parametrize("initial_state", RegistrationState.__all_states__, ids=lambda s: s.state)
async def test_profile_does_not_interrupt_incomplete_onboarding(app, initial_state):
    await db.delete_user_completely(USER_ID)
    await db.create_or_update_user(USER_ID, "anna")
    await app.state.set_state(initial_state)
    await app.state.update_data(keep="registration")
    before = await snapshot()
    await app.send("👤 Профиль")
    assert "/start" in app.session.messages[0].text
    assert await app.state.get_state() == initial_state.state
    assert await app.state.get_data() == {"keep": "registration"}
    assert await snapshot() == before


@pytest.mark.asyncio
@pytest.mark.parametrize("initial_state", ProfileEditState.__all_states__, ids=lambda s: s.state)
@pytest.mark.parametrize("button", [
    button.text
    for language in ("ru", "en")
    for row in main_reply_keyboard(language).keyboard
    for button in row
    if button.text not in {"👤 Профиль", "👤 Profile"}
] + ["🌿 Create focus"])
async def test_other_navigation_buttons_are_never_saved_as_profile_values(app, initial_state, button):
    before = await snapshot()
    await app.state.set_state(initial_state)
    await app.send(button)
    assert await snapshot() == before
    assert await app.state.get_state() == initial_state.state
    assert len(app.session.messages) == 1
    assert app.session.messages[0].reply_markup.inline_keyboard


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["ru", "en"])
async def test_profile_edit_callbacks_and_legitimate_input_still_work(app, language):
    await db.update_user_language(USER_ID, language)
    await app.send(callback="profile_edit:current_focus")
    assert await app.state.get_state() == ProfileEditState.editing_current_focus.state
    await app.send("спокойствие" if language == "ru" else "calm")
    assert await app.state.get_state() is None
    preferences = await db.get_user_profile_preferences(USER_ID)
    assert preferences["current_focus"] == ("спокойствие" if language == "ru" else "calm")
    assert preferences["avoid_words"] == ["rush"]
    await app.send(callback="profile_edit:avoid_words")
    await app.send("-")
    assert "avoid_words" not in await db.get_user_profile_preferences(USER_ID)


@pytest.mark.asyncio
@pytest.mark.parametrize("error_message", [
    "Bad Request: message can't be edited",
    "Bad Request: message to edit not found",
    "Bad Request: there is no text in the message to edit",
    "Bad Request: message is not modified: specified new message content is the same",
])
async def test_inline_profile_handles_expected_edit_errors(app, error_message):
    app.session.edit_error = TelegramBadRequest(
        method=EditMessageText(chat_id=USER_ID, message_id=123, text="profile"), message=error_message,
    )
    await app.send(callback="profile:open")
    if "message is not modified" in error_message:
        assert len(app.session.messages) == 1
    else:
        assert len(app.session.messages) == 2
        assert isinstance(app.session.messages[-1], SendMessage)
        assert app.session.messages[-1].text == app.session.messages[0].text


@pytest.mark.asyncio
@pytest.mark.parametrize("error_type", [TelegramBadRequest, TelegramNetworkError, RuntimeError])
async def test_inline_profile_does_not_mask_unrelated_errors(app, error_type):
    if error_type is RuntimeError:
        error = RuntimeError("unexpected programming error")
    else:
        error = error_type(
            method=EditMessageText(chat_id=USER_ID, message_id=123, text="profile"), message="unrelated failure",
        )
    app.session.edit_error = error
    with pytest.raises(error_type) as caught:
        await app.send(callback="profile:open")
    assert caught.value is error
    assert len(app.session.messages) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("initial_state", BUTTON_STATES, ids=lambda s: s.state)
@pytest.mark.parametrize("voice", [False, True])
@pytest.mark.parametrize("language", ["ru", "en"])
async def test_state_specific_menu_guards_are_reachable(app, initial_state, voice, language):
    await db.update_user_language(USER_ID, language)
    await app.state.set_state(initial_state)
    await app.state.update_data(language=language)
    before = await app.state.get_data()
    await app.send(None if voice else "unexpected text", voice=voice)
    assert len(app.session.messages) == 1
    expected = menu_choose_style_text(language) if initial_state.state.endswith("choosing_style") else menu_choose_option_text(language)
    assert app.session.messages[0].text == expected
    assert await app.state.get_state() == initial_state.state
    assert await app.state.get_data() == before


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["ru", "en"])
@pytest.mark.parametrize("entry", ["button", "inline", "save"])
async def test_oversized_profile_preserves_and_displays_all_preferences(app, language, entry):
    await db.update_user_language(USER_ID, language)
    preferences = {
        "current_focus": "🌿focus" * 900,
        "avoid_topics": ["тема" * 1500, "other topic"],
        "avoid_words": ["word" * 1400],
        "life_areas": ["home" * 1300],
    }
    await db.update_user_profile_preferences(USER_ID, preferences)
    if entry == "save":
        await app.state.set_state(ProfileEditState.editing_current_focus)
        preferences["current_focus"] = "new focus" * 400
        await app.send(preferences["current_focus"])
        assert "updated" in app.session.messages[0].text or "обновлён" in app.session.messages[0].text
        messages = app.session.messages[1:]
    else:
        await app.send("👤 Профиль" if language == "ru" else "👤 Profile", callback="profile:open" if entry == "inline" else None)
        messages = app.session.messages
    # Oversized views occupy one message, with all remaining content reachable in order.
    assert len(messages) == 1
    first = app.session.chat_messages[messages[0].message_id] if entry == "inline" else app.session.chat_messages[app.session.next_message_id - 1]
    before_navigation = len(app.session.messages)
    pages = await collect_profile_pages(app, first)
    assert len(pages) > 1
    assert all(0 < utf16_length(page.text) <= 4096 for page in pages)
    expected = start.build_profile_summary_text(
        await db.get_user(USER_ID), preferences,
        build_subscriptions_summary(await db.get_active_subscriptions(USER_ID), language), 1, language,
    )
    assert profile_page_contents(pages) == expected
    for page in pages[:-1]:
        assert all(button.callback_data.startswith("profile:page:") for row in page.reply_markup.inline_keyboard for button in row)
    assert any(button.callback_data == "profile_edit:name" for row in pages[-1].reply_markup.inline_keyboard for button in row)
    assert all(isinstance(call, EditMessageText) for call in app.session.messages[before_navigation:])
    assert await db.get_user_profile_preferences(USER_ID) == preferences
    assert await app.state.get_state() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["ru", "en"])
@pytest.mark.parametrize("entry", ["button", "inline", "save"])
@pytest.mark.parametrize("value", [
    "e" + "\u0301" * 9000,
    "👩" + "\u200d💻" * 3000,
], ids=["combining", "zwj"])
async def test_indivisible_oversized_preference_remains_fully_navigable(app, language, entry, value):
    await db.update_user_language(USER_ID, language)
    preferences = {"current_focus": value, "avoid_words": ["saved tail"]}
    await db.update_user_profile_preferences(USER_ID, preferences)
    if entry == "save":
        await app.state.set_state(ProfileEditState.editing_current_focus)
        await app.send(value)
    elif entry == "inline":
        await app.send(callback="profile:open")
    else:
        await app.send("👤 Профиль" if language == "ru" else "👤 Profile")
    before = await snapshot()
    first_id = 123 if entry == "inline" else app.session.next_message_id - 1
    first = app.session.chat_messages[first_id]
    pages = await collect_profile_pages(app, first)
    expected, markup, _ = await start._build_profile_view(user_id=USER_ID)
    assert len(pages) > 2
    assert profile_page_contents(pages) == expected
    assert value in profile_page_contents(pages)
    revision = sha256(expected.encode("utf-8")).hexdigest()[:12]
    for page in pages:
        assert 0 < utf16_length(page.text) <= 4096
        assert all(
            button.callback_data.endswith(f":{revision}")
            for row in page.reply_markup.inline_keyboard for button in row
            if button.callback_data.startswith("profile:page:")
        )
    assert pages[-1].reply_markup.inline_keyboard[1:] == markup.inline_keyboard
    assert await db.get_user_profile_preferences(USER_ID) == preferences
    assert await snapshot() == before
    assert await app.state.get_state() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(("size", "message_count"), [(4095, 1), (4096, 1), (4097, 2)])
async def test_profile_at_telegram_message_boundary(app, size, message_count):
    user, _, subscriptions = await snapshot()
    summary = build_subscriptions_summary(subscriptions, "ru")
    base = start.build_profile_summary_text(user, {"current_focus": "x"}, summary, 1, "ru")
    # Emoji plus a long unbroken value exercises both UTF-16 counting and hard splits.
    preferences = {"current_focus": "🌿" + "x" * (size - utf16_length(base) - 1)}
    await db.update_user_profile_preferences(USER_ID, preferences)
    await app.send("👤 Профиль")
    assert len(app.session.messages) == 1
    first = app.session.chat_messages[app.session.next_message_id - 1]
    pages = await collect_profile_pages(app, first)
    assert len(pages) == message_count
    assert all(utf16_length(page.text) <= 4096 for page in pages)
    expected = start.build_profile_summary_text(user, preferences, summary, 1, "ru")
    assert utf16_length(expected) == size
    assert profile_page_contents(pages) == expected


@pytest.mark.asyncio
async def test_repeated_oversized_inline_profile_open_does_not_append_messages(app):
    await db.update_user_profile_preferences(USER_ID, {"current_focus": "focus " * 2300})
    await app.send(callback="profile:open")
    first = app.session.chat_messages[123]
    for _ in range(3):
        await app.send(callback="profile:open")
        assert app.session.chat_messages[123] == first
    assert len(app.session.chat_messages) == 1
    assert all(isinstance(call, EditMessageText) for call in app.session.messages)
    assert await app.state.get_data() == {}
    pages = await collect_profile_pages(app, first)
    expected, _, _ = await start._build_profile_view(user_id=USER_ID)
    assert profile_page_contents(pages) == expected


@pytest.mark.asyncio
async def test_changed_continuation_is_refreshed_even_when_first_page_is_identical(app):
    preferences = {"current_focus": "x" * 11000, "avoid_words": ["old tail"]}
    await db.update_user_profile_preferences(USER_ID, preferences)
    await app.send(callback="profile:open")
    previous = app.session.chat_messages[123]
    stale_next = previous.reply_markup.inline_keyboard[0][0].callback_data
    preferences["avoid_words"] = ["changed tail"]
    await db.update_user_profile_preferences(USER_ID, preferences)
    await app.send(callback="profile:open")
    current = app.session.chat_messages[123]
    assert current.text == previous.text
    assert current.reply_markup != previous.reply_markup  # Revision covers the whole Profile.
    await app.send(callback=stale_next, callback_message=previous)
    assert app.session.chat_messages[123] == current  # Stale buttons restart at current page one.
    pages = await collect_profile_pages(app, current)
    expected, _, _ = await start._build_profile_view(user_id=USER_ID)
    assert profile_page_contents(pages) == expected
    assert "changed tail" in pages[-1].text
    assert "old tail" not in profile_page_contents(pages)
    assert len(app.session.chat_messages) == 1
    assert all(isinstance(call, EditMessageText) for call in app.session.messages)


@pytest.mark.asyncio
async def test_stale_page_button_after_profile_shrinks_and_out_of_range_page(app):
    await db.update_user_profile_preferences(USER_ID, {"current_focus": "x" * 13000})
    await app.send(callback="profile:open")
    first = app.session.chat_messages[123]
    next_data = first.reply_markup.inline_keyboard[0][0].callback_data
    revision = next_data.rsplit(":", 1)[1]
    await app.send(callback=f"profile:page:9999999999:{revision}")
    assert "profile_edit:name" in str(app.session.chat_messages[123].reply_markup)
    await db.update_user_profile_preferences(USER_ID, {"current_focus": "short"})
    await app.send(callback=next_data)
    expected, markup, _ = await start._build_profile_view(user_id=USER_ID)
    assert app.session.chat_messages[123].text == expected
    assert app.session.chat_messages[123].reply_markup == markup
    assert len(app.session.chat_messages) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("page_index", [0, 1, 3])
@pytest.mark.parametrize("error_message", [
    "Bad Request: message can't be edited",
    "Bad Request: message to edit not found",
    "Bad Request: there is no text in the message to edit",
])
async def test_oversized_profile_edit_failure_falls_back_to_complete_navigable_view(app, page_index, error_message):
    await db.update_user_profile_preferences(USER_ID, {"current_focus": "x" * 13000})
    source = None
    callback = "profile:open"
    for _ in range(page_index):
        await app.send(callback=callback, callback_message=source)
        source = app.session.chat_messages[123]
        callback = next(button.callback_data for row in source.reply_markup.inline_keyboard for button in row if button.text == "➡️")
    previous_messages = dict(app.session.chat_messages)
    app.session.edit_error = TelegramBadRequest(
        method=EditMessageText(chat_id=USER_ID, message_id=123, text="profile"), message=error_message,
    )
    before = len(app.session.messages)
    await app.send(callback=callback, callback_message=source)
    attempt, fallback = app.session.messages[before:]
    assert isinstance(attempt, EditMessageText)
    assert isinstance(fallback, SendMessage)
    assert attempt.text == fallback.text
    assert attempt.reply_markup == fallback.reply_markup
    assert all(app.session.chat_messages[key] == value for key, value in previous_messages.items())
    replacement = app.session.chat_messages[app.session.next_message_id - 1]
    app.session.edit_error = None
    # Every page, including earlier pages, remains accessible from the fallback.
    for _ in range(page_index):
        back = next(button.callback_data for row in replacement.reply_markup.inline_keyboard for button in row if button.text == "⬅️")
        await app.send(callback=back, callback_message=replacement)
        replacement = app.session.chat_messages[replacement.message_id]
    pages = await collect_profile_pages(app, replacement)
    expected, markup, _ = await start._build_profile_view(user_id=USER_ID)
    assert profile_page_contents(pages) == expected
    assert pages[-1].reply_markup.inline_keyboard[1:] == markup.inline_keyboard
    assert sum(isinstance(call, SendMessage) for call in app.session.messages) == 1
    assert all(0 < utf16_length(call.text) <= 4096 for call in app.session.messages)


@pytest.mark.asyncio
@pytest.mark.parametrize("error_type", [TelegramBadRequest, TelegramNetworkError, RuntimeError])
async def test_oversized_page_edit_does_not_mask_unrelated_failures(app, error_type):
    await db.update_user_profile_preferences(USER_ID, {"current_focus": "x" * 9000})
    await app.send(callback="profile:open")
    first = app.session.chat_messages[123]
    next_data = first.reply_markup.inline_keyboard[0][0].callback_data
    error = RuntimeError("unexpected") if error_type is RuntimeError else error_type(
        method=EditMessageText(chat_id=USER_ID, message_id=123, text="profile"), message="unrelated failure",
    )
    app.session.edit_error = error
    with pytest.raises(error_type) as caught:
        await app.send(callback=next_data)
    assert caught.value is error
    assert app.session.chat_messages == {123: first}
    assert all(isinstance(call, EditMessageText) for call in app.session.messages)


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["ru", "en"])
async def test_generation_and_subscription_controls_still_route(app, language):
    await db.update_user_language(USER_ID, language)
    await app.send("/new")
    await app.send(callback="sphere:money")
    assert await app.state.get_state() == GenerationState.choosing_visual_mode.state
    await app.send(callback="visual:photo")
    assert await app.state.get_state() == GenerationState.choosing_style.state
    await app.send(callback="nav:back_to_visual")
    assert await app.state.get_state() == GenerationState.choosing_visual_mode.state
    # Persistent Create mood remains a legitimate control in generation menus.
    await app.send("🌿 Создать настрой" if language == "ru" else "🌿 Create mood")
    assert await app.state.get_state() == GenerationState.choosing_sphere.state
    await app.send("/subscribe")
    await app.send(callback="sub:add")
    await app.send(callback=f"sub_lang:{language}")
    assert await app.state.get_state() == SubscriptionState.choosing_mode.state
    await app.send(callback="submode:weekly_balance")
    await app.send(callback="visualmix:photo")
    await app.send(callback="style:auto")
    await app.send(callback="hour:10")
    await app.send(callback="minute:15")
    assert await app.state.get_state() == SubscriptionState.confirming.state
    await app.send(callback="sub:confirm")
    assert await app.state.get_state() is None
    subscriptions = await db.get_active_subscriptions(USER_ID)
    assert len(subscriptions) == 2
    saved = next(sub for sub in subscriptions if sub["hour"] == 10)
    assert saved["minute"] == 15
    assert saved["language"] == language
    assert saved["visual_mode"] == "photo"


@pytest.mark.asyncio
@pytest.mark.parametrize("initial_state", SubscriptionState.__all_states__, ids=lambda s: s.state)
@pytest.mark.parametrize("language", ["ru", "en"])
@pytest.mark.parametrize("button", ["🌿 Создать настрой", "🌿 Create mood", "🌿 Create focus"])
async def test_create_button_exits_subscription_flow_without_changing_saved_data(app, initial_state, language, button):
    await db.update_user_language(USER_ID, language)
    before = await snapshot()
    subscription_id = before[2][0]["id"]
    await app.state.set_state(initial_state)
    await app.state.update_data(
        language="en" if language == "ru" else "ru",
        edit_subscription_id=subscription_id, partial_edit_field="time",
        subscription_mode="sphere_focus", sphere="money", hour=23, minute=55,
        stale="discard",
    )
    await app.send(button)
    assert await app.state.get_state() == GenerationState.choosing_sphere.state
    assert await app.state.get_data() == {"theme_text": None}
    assert await snapshot() == before
    assert len(app.session.messages) == 1
    message = app.session.messages[0]
    assert message.text == generation._new_flow_text(language)
    assert any(
        button.callback_data == "sphere:money"
        for row in message.reply_markup.inline_keyboard for button in row
    )
