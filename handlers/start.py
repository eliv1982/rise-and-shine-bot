import logging
import os
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import get_outputs_dir
from database import (
    create_or_update_user,
    delete_user_completely,
    get_active_subscriptions,
    get_user,
    get_user_profile_preferences,
    merge_user_profile_preferences,
    update_user_language,
    update_user_profile_preferences,
    update_user_profile,
)
from keyboards.inline import (
    gender_keyboard,
    language_keyboard,
    main_reply_keyboard,
    new_affirmation_keyboard,
    profile_back_keyboard,
    profile_gender_keyboard,
    profile_keyboard,
    profile_language_keyboard,
    profile_support_style_keyboard,
    profile_text_edit_keyboard,
    profile_text_length_keyboard,
    profile_tone_keyboard,
    start_menu_keyboard,
)
from database import MAX_ACTIVE_SUBSCRIPTIONS
from handlers.common_messages import (
    main_menu_mismatch_text as _main_menu_mismatch_text,
    voice_language_mismatch_text as _voice_language_mismatch_text,
    voice_recognition_failed_text as _voice_recognition_failed_text,
    voice_recognized_echo_text as _voice_recognized_echo_text,
    voice_unclear_text as _voice_unclear_text,
)
from services.subscription_ui import build_subscription_summary, build_subscriptions_summary, gender_profile_label
from services.main_menu_intents import _normalize_intent_text, detect_main_menu_intent
from services.speechkit_stt import transcribe_audio_with_meta
from services.voice_input import VoiceInputProcessor
from states import ProfileEditState, RegistrationState
from utils import display_name_for_language, extract_name_from_introduction, is_input_language_compatible

router = Router()
logger = logging.getLogger(__name__)

_PROFILE_TEXT_PROMPTS = {
    "ru": {
        "name": "Как к тебе обращаться? Напиши имя для общения.",
        "current_focus": "Напиши текущий фокус одной короткой фразой. Например: восстановиться, спокойно разобраться с деньгами.",
        "avoid_topics": "Напиши темы через запятую, которых лучше избегать. Например: давление, конфликт, болезни.\nЧтобы очистить, отправь `-`.",
        "avoid_words": "Напиши слова или формулировки через запятую, которых лучше избегать. Например: должен, срочно, продуктивность.\nЧтобы очистить, отправь `-`.",
        "life_areas": "Напиши важные жизненные сферы через запятую. Например: работа, отношения, дом.\nЧтобы очистить, отправь `-`.",
    },
    "en": {
        "name": "How should I address you? Send the name you'd like me to use.",
        "current_focus": "Send your current focus in one short phrase.",
        "avoid_topics": "Send topics to avoid, separated by commas. Send `-` to clear.",
        "avoid_words": "Send words or phrases to avoid, separated by commas. Send `-` to clear.",
        "life_areas": "Send important life areas, separated by commas. Send `-` to clear.",
    },
}
_PROFILE_PLACEHOLDER = {"ru": "не задано", "en": "not set"}
_PROFILE_TONE_LABELS = {
    "calm_no_pathos": {"ru": "Спокойно, без пафоса", "en": "Calm, no pathos"},
    "warm_soft": {"ru": "Мягко и бережно", "en": "Warm and gentle"},
    "energetic": {"ru": "Бодро и поддерживающе", "en": "Energetic and supportive"},
    "lightly_ironic": {"ru": "С лёгкой иронией", "en": "Lightly ironic"},
    "poetic": {"ru": "Поэтично", "en": "Poetic"},
}
_PROFILE_SUPPORT_STYLE_LABELS = {
    "support": {"ru": "Поддержать", "en": "Support"},
    "grounding": {"ru": "Заземлить", "en": "Ground"},
    "focus": {"ru": "Помочь собраться", "en": "Help focus"},
    "gentle_action": {"ru": "Дать маленький шаг", "en": "Give a gentle step"},
    "no_advice": {"ru": "Без советов, только настрой", "en": "No advice, only mood"},
}
_PROFILE_TEXT_LENGTH_LABELS = {
    "short": {"ru": "Коротко", "en": "Short"},
    "standard": {"ru": "Стандартно", "en": "Standard"},
    "detailed": {"ru": "Подробнее", "en": "Detailed"},
}


def _profile_label(options: dict[str, dict[str, str]], value: Optional[str], language: str) -> str:
    if not value:
        return _PROFILE_PLACEHOLDER.get(language, "—")
    return options.get(value, {}).get(language, value)


def _profile_list_label(values: object, language: str) -> str:
    if not isinstance(values, list) or not values:
        return _PROFILE_PLACEHOLDER.get(language, "—")
    return ", ".join(str(value) for value in values)


def build_profile_summary_text(
    user: dict,
    preferences: dict,
    subscriptions_summary: str,
    subscriptions_count: int,
    language: str,
) -> str:
    name = display_name_for_language(user.get("name"), language) or "—"
    gender_label = gender_profile_label(user.get("gender"), language)
    tone_label = _profile_label(_PROFILE_TONE_LABELS, preferences.get("tone_preference"), language)
    support_label = _profile_label(_PROFILE_SUPPORT_STYLE_LABELS, preferences.get("support_style"), language)
    length_label = _profile_label(_PROFILE_TEXT_LENGTH_LABELS, preferences.get("text_length_preference"), language)
    current_focus = preferences.get("current_focus") or _PROFILE_PLACEHOLDER.get(language, "—")
    avoid_topics = _profile_list_label(preferences.get("avoid_topics"), language)
    avoid_words = _profile_list_label(preferences.get("avoid_words"), language)
    life_areas = _profile_list_label(preferences.get("life_areas"), language)

    if language == "ru":
        return (
            f"👤 Твой профиль\n\n"
            f"💬 Как обращаться: {name}\n"
            f"🧍 Пол: {gender_label}\n"
            f"🌐 Язык: Русский\n"
            f"🎨 Тон общения: {tone_label}\n"
            f"🤝 Формат поддержки: {support_label}\n"
            f"📝 Длина текста: {length_label}\n"
            f"🧭 Жизненные сферы: {life_areas}\n"
            f"🎯 Текущий фокус: {current_focus}\n"
            f"🚫 Избегать тем: {avoid_topics}\n"
            f"🧹 Избегать слов: {avoid_words}\n\n"
            f"🧾 Подписки: {subscriptions_count}/{MAX_ACTIVE_SUBSCRIPTIONS}\n{subscriptions_summary}"
        )

    return (
        f"👤 Your profile\n\n"
        f"💬 How to address you: {name}\n"
        f"🧍 Pronouns: {gender_label}\n"
        f"🌐 Language: English\n"
        f"🎨 Tone: {tone_label}\n"
        f"🤝 Support style: {support_label}\n"
        f"📝 Text length: {length_label}\n"
        f"🧭 Life areas: {life_areas}\n"
        f"🎯 Current focus: {current_focus}\n"
        f"🚫 Avoid topics: {avoid_topics}\n"
        f"🧹 Avoid words: {avoid_words}\n\n"
        f"🧾 Subscriptions: {subscriptions_count}/{MAX_ACTIVE_SUBSCRIPTIONS}\n{subscriptions_summary}"
    )


async def _build_profile_view(*, user_id: int, user: Optional[dict] = None) -> tuple[str, object, str]:
    user = user or await get_user(user_id)
    if not user:
        return "Похоже, мы ещё не знакомы. Напиши /start.", None, "ru"

    lang = (user or {}).get("language", "ru")
    preferences = await get_user_profile_preferences(user_id)
    subscriptions = await get_active_subscriptions(user_id)
    subscriptions_summary = build_subscriptions_summary(subscriptions, lang)
    count = len(subscriptions)
    text = build_profile_summary_text(user, preferences, subscriptions_summary, count, lang)
    markup = profile_keyboard(lang, has_subscription=bool(subscriptions))
    return text, markup, lang


async def _show_profile(
    message: Message,
    state: FSMContext,
    *,
    user_id: int,
    user: Optional[dict] = None,
    edit: bool = False,
) -> None:
    text, markup, _lang = await _build_profile_view(user_id=user_id, user=user)
    if edit:
        try:
            await message.edit_text(text, reply_markup=markup)
            return
        except Exception:
            pass
    await message.answer(text, reply_markup=markup)


async def _edit_or_answer(message: Message, text: str, reply_markup=None) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except Exception:
        await message.answer(text, reply_markup=reply_markup)


async def _return_to_main_menu(message: Message, language: str) -> None:
    text = "🏠 Главное меню снова внизу." if language == "ru" else "🏠 The main menu is available below."
    await message.answer(text, reply_markup=main_reply_keyboard(language))


def _greet_returning(name: Optional[str], gender: Optional[str]) -> str:
    ready = "Готова" if gender == "female" else "Готов"
    if name:
        return f"С возвращением, {name} 🌿\n\n{ready} создать новый настрой дня или посмотреть подписки?"
    if gender == "female":
        return "С возвращением 🌿\n\nГотова создать новый настрой дня или посмотреть подписки?"
    return "С возвращением 🌿\n\nГотов создать новый настрой дня или посмотреть подписки?"


def _welcome_new_user(language: str = "ru") -> str:
    if language == "en":
        return (
            "Hi! I'm Rise and Shine, I help you create your daily focus 🌿\n\n"
            "Here you can get:\n"
            "— a focus of the day,\n"
            "— 4 affirmations,\n"
            "— a gentle step for the day,\n"
            "— and a beautiful image in your chosen style.\n\n"
            "Let’s get acquainted. What’s your name?"
        )
    return (
        "Привет! Я Rise and Shine, помогаю собирать твой настрой дня 🌿\n\n"
        "Здесь можно получить:\n"
        "— фокус дня,\n"
        "— 4 аффирмации,\n"
        "— мягкий шаг на день,\n"
        "— и красивую картинку в выбранном стиле.\n\n"
        "Давай познакомимся. Как тебя зовут?"
    )


async def route_main_menu_intent(message: Message, state: FSMContext, recognized_text: str, language: str) -> bool:
    intent = detect_main_menu_intent(recognized_text, language)
    if intent == "create_mood":
        from handlers.generation import cmd_new

        await cmd_new(message, state)
        return True
    if intent == "manage_subscriptions":
        await _route_to_subscriptions(message, state)
        return True
    if intent == "profile":
        await cmd_profile(message, state)
        return True
    if intent == "language":
        await cmd_language(message, state)
        return True
    return False


async def _route_to_subscriptions(message: Message, state: FSMContext) -> None:
    from handlers.subscribe import cmd_subscribe

    await cmd_subscribe(message, state)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    username = message.from_user.username

    user = await get_user(user_id)
    if user:
        await state.clear()
        lang = (user or {}).get("language", "ru")
        if lang == "en":
            name = display_name_for_language(user.get("name"), "en") or "there"
            text = (
                f"Welcome back, {name} 🌿\n\n"
                "Would you like to create a new daily focus or check your subscriptions?"
            )
        else:
            text = _greet_returning(user.get("name"), user.get("gender"))
        await message.answer(text, reply_markup=main_reply_keyboard(lang))
        return

    # Новый пользователь
    await create_or_update_user(user_id=user_id, username=username)
    await state.set_state(RegistrationState.waiting_for_name)
    await message.answer(_welcome_new_user("ru"))


@router.message(RegistrationState.waiting_for_name)
async def process_name(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw:
        await message.answer("Пожалуйста, назови своё имя.")
        return

    name = extract_name_from_introduction(raw)
    if not name:
        name = raw
        if len(name) > 50:
            await message.answer("Пожалуйста, напиши просто своё имя.")
            return

    user_id = message.from_user.id
    await update_user_profile(user_id=user_id, name=name)

    await state.set_state(RegistrationState.waiting_for_gender)
    await message.answer(
        f"Приятно познакомиться, {name}! Выбери обращение — это поможет точнее формулировать настрой дня:",
        reply_markup=gender_keyboard(language="ru"),
    )


@router.message(RegistrationState.waiting_for_name, F.voice)
async def process_name_voice(message: Message, state: FSMContext) -> None:
    voice = message.voice
    if not voice:
        return
    file = await message.bot.get_file(voice.file_id)
    dest_dir = get_outputs_dir()
    os.makedirs(dest_dir, exist_ok=True)
    local_path = f"{dest_dir}/voice_name_{message.from_user.id}_{voice.file_unique_id}.ogg"
    try:
        await message.bot.download_file(file.file_path, destination=local_path)
        stt_meta = await transcribe_audio_with_meta(local_path, language="ru")
        recognized = str(stt_meta.get("recognized_text_final") or "")
    except Exception:
        await message.answer(_voice_recognition_failed_text("ru"))
        return
    await message.answer(_voice_recognized_echo_text("ru", recognized))
    raw = recognized.strip()
    if not raw:
        await message.answer("Пожалуйста, назови своё имя.")
        return
    name = extract_name_from_introduction(raw)
    if not name:
        name = raw
        if len(name) > 50:
            await message.answer("Пожалуйста, напиши просто своё имя.")
            return
    user_id = message.from_user.id
    await update_user_profile(user_id=user_id, name=name)
    await state.set_state(RegistrationState.waiting_for_gender)
    await message.answer(
        f"Приятно познакомиться, {name}! Выбери обращение — это поможет точнее формулировать настрой дня:",
        reply_markup=gender_keyboard(language="ru"),
    )


@router.callback_query(RegistrationState.waiting_for_gender, F.data.startswith("gender:"))
async def process_gender_callback(callback: CallbackQuery, state: FSMContext) -> None:
    gender = callback.data.split(":", maxsplit=1)[1]
    user_id = callback.from_user.id

    await update_user_profile(user_id=user_id, gender=gender)
    await update_user_language(user_id=user_id, language="ru")
    await state.clear()

    user = await get_user(user_id)
    name = user.get("name") if user else None
    text = "Отлично! Теперь ты можешь создать свой первый настрой дня."
    if name:
        text = f"Отлично, {name}! Теперь ты можешь создать свой первый настрой дня."

    await callback.message.edit_text(text, reply_markup=new_affirmation_keyboard("ru"))
    await callback.message.answer("🏠 Главное меню теперь доступно снизу.", reply_markup=main_reply_keyboard("ru"))
    await callback.answer()


@router.callback_query(F.data.startswith("gender:"))
async def update_gender_from_profile(callback: CallbackQuery, state: FSMContext) -> None:
    """Обновление обращения из профиля."""
    current = await state.get_state()
    if current == RegistrationState.waiting_for_gender.state:
        return
    gender = callback.data.split(":", maxsplit=1)[1]
    await update_user_profile(user_id=callback.from_user.id, gender=gender)
    user = await get_user(callback.from_user.id)
    lang = (user or {}).get("language", "ru")
    text = "👤 Обращение обновлено." if lang == "ru" else "👤 Pronouns updated."
    await callback.answer()
    await callback.message.answer(text, reply_markup=main_reply_keyboard(lang))


@router.message(Command("language"))
async def cmd_language(message: Message, state: FSMContext) -> None:
    """Выбор языка: русский / English."""
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала напиши /start.")
        return
    lang = (user or {}).get("language", "ru")
    text_ru = "Выбери язык общения:"
    text_en = "Choose your language:"
    text = text_ru if lang == "ru" else text_en
    await message.answer(text, reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def cmd_language_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Смена языка по кнопке после /language (не в процессе подписки)."""
    current = await state.get_state()
    if current and current.startswith("SubscriptionState:"):
        return
    lang = callback.data.split(":", maxsplit=1)[1]
    if lang not in ("ru", "en"):
        await callback.answer()
        return
    await update_user_language(callback.from_user.id, lang)
    await state.clear()
    if lang == "ru":
        await callback.message.edit_text("Язык изменён на русский. Дальше буду общаться по-русски.")
        await callback.message.answer("🌿 Язык обновлён. Нижнее меню тоже переключилось на русский.", reply_markup=main_reply_keyboard("ru"))
    else:
        await callback.message.edit_text("Language set to English. I'll use English from now on.")
        await callback.message.answer("🌿 Language updated. The bottom menu is now in English.", reply_markup=main_reply_keyboard("en"))
    await callback.answer()


@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext) -> None:
    await _show_profile(message, state, user_id=message.from_user.id)


@router.callback_query(F.data == "profile:open")
async def profile_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await _show_profile(callback.message, state, user_id=callback.from_user.id, edit=True)


@router.callback_query(F.data == "profile:menu")
async def profile_menu_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await get_user(callback.from_user.id)
    lang = (user or {}).get("language", "ru")
    await callback.answer()
    await _return_to_main_menu(callback.message, lang)


@router.callback_query(F.data == "profile_edit:gender")
async def profile_edit_gender(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    lang = (user or {}).get("language", "ru")
    text = "Выбери обращение:" if lang == "ru" else "Choose pronouns:"
    selected_gender = (user or {}).get("gender")
    await callback.answer()
    await _edit_or_answer(callback.message, text, reply_markup=profile_gender_keyboard(lang, selected_gender))


@router.callback_query(F.data.startswith("profile_gender:"))
async def profile_set_gender(callback: CallbackQuery, state: FSMContext) -> None:
    gender = callback.data.split(":", maxsplit=1)[1]
    await update_user_profile(user_id=callback.from_user.id, gender=gender)
    user = await get_user(callback.from_user.id)
    lang = (user or {}).get("language", "ru")
    text = "✅ Обращение обновлено." if lang == "ru" else "✅ Pronouns updated."
    await callback.answer(text)
    await _show_profile(callback.message, state, user_id=callback.from_user.id, user=user, edit=True)


@router.callback_query(F.data == "profile_edit:language")
async def profile_edit_language(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    lang = (user or {}).get("language", "ru")
    text = "Выбери язык профиля:" if lang == "ru" else "Choose profile language:"
    await callback.answer()
    await _edit_or_answer(callback.message, text, reply_markup=profile_language_keyboard(lang, lang))


@router.callback_query(F.data.startswith("profile_lang:"))
async def profile_set_language(callback: CallbackQuery, state: FSMContext) -> None:
    lang = callback.data.split(":", maxsplit=1)[1]
    if lang not in ("ru", "en"):
        await callback.answer()
        return
    await update_user_language(callback.from_user.id, lang)
    text = "✅ Язык профиля обновлён." if lang == "ru" else "✅ Profile language updated."
    await callback.answer(text)
    user = await get_user(callback.from_user.id)
    await _show_profile(callback.message, state, user_id=callback.from_user.id, user=user, edit=True)


@router.callback_query(F.data == "profile_edit:tone_preference")
async def profile_edit_tone(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    lang = (user or {}).get("language", "ru")
    preferences = await get_user_profile_preferences(callback.from_user.id)
    text = "Выбери тон общения:" if lang == "ru" else "Choose a tone:"
    await callback.answer()
    await _edit_or_answer(
        callback.message,
        text,
        reply_markup=profile_tone_keyboard(lang, preferences.get("tone_preference")),
    )


@router.callback_query(F.data == "profile_edit:support_style")
async def profile_edit_support_style(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    lang = (user or {}).get("language", "ru")
    preferences = await get_user_profile_preferences(callback.from_user.id)
    text = "Выбери формат поддержки:" if lang == "ru" else "Choose a support style:"
    await callback.answer()
    await _edit_or_answer(
        callback.message,
        text,
        reply_markup=profile_support_style_keyboard(lang, preferences.get("support_style")),
    )


@router.callback_query(F.data == "profile_edit:text_length_preference")
async def profile_edit_text_length(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    lang = (user or {}).get("language", "ru")
    preferences = await get_user_profile_preferences(callback.from_user.id)
    text = "Выбери желаемую длину текста:" if lang == "ru" else "Choose preferred text length:"
    await callback.answer()
    await _edit_or_answer(
        callback.message,
        text,
        reply_markup=profile_text_length_keyboard(lang, preferences.get("text_length_preference")),
    )


@router.callback_query(F.data.startswith("profile_pref:"))
async def profile_set_preference_callback(callback: CallbackQuery, state: FSMContext) -> None:
    _, field, value = callback.data.split(":", maxsplit=2)
    await merge_user_profile_preferences(callback.from_user.id, {field: value})
    user = await get_user(callback.from_user.id)
    lang = (user or {}).get("language", "ru")
    text = "✅ Профиль обновлён." if lang == "ru" else "✅ Profile updated."
    await callback.answer(text)
    await _show_profile(callback.message, state, user_id=callback.from_user.id, user=user, edit=True)


@router.callback_query(F.data.startswith("profile_clear:"))
async def profile_clear_preference_callback(callback: CallbackQuery, state: FSMContext) -> None:
    field = callback.data.split(":", maxsplit=1)[1]
    if field == "name":
        await callback.answer()
        return
    if field in {"tone_preference", "support_style", "text_length_preference", "current_focus"}:
        patch = {field: ""}
    else:
        patch = {field: []}
    await merge_user_profile_preferences(callback.from_user.id, patch)
    user = await get_user(callback.from_user.id)
    lang = (user or {}).get("language", "ru")
    text = "✅ Поле очищено." if lang == "ru" else "✅ Preference cleared."
    await callback.answer(text)
    await _show_profile(callback.message, state, user_id=callback.from_user.id, user=user, edit=True)


async def _start_profile_text_edit(
    callback: CallbackQuery,
    state: FSMContext,
    *,
    field: str,
    target_state,
    allow_clear: bool,
) -> None:
    user = await get_user(callback.from_user.id)
    lang = (user or {}).get("language", "ru")
    await state.set_state(target_state)
    await callback.answer()
    await callback.message.answer(
        _PROFILE_TEXT_PROMPTS[lang][field],
        reply_markup=profile_text_edit_keyboard(lang, field, allow_clear=allow_clear),
    )


@router.callback_query(F.data == "profile_edit:name")
async def profile_edit_name(callback: CallbackQuery, state: FSMContext) -> None:
    await _start_profile_text_edit(
        callback,
        state,
        field="name",
        target_state=ProfileEditState.editing_name,
        allow_clear=False,
    )


@router.callback_query(F.data == "profile_edit:current_focus")
async def profile_edit_current_focus(callback: CallbackQuery, state: FSMContext) -> None:
    await _start_profile_text_edit(
        callback,
        state,
        field="current_focus",
        target_state=ProfileEditState.editing_current_focus,
        allow_clear=True,
    )


@router.callback_query(F.data == "profile_edit:avoid_topics")
async def profile_edit_avoid_topics(callback: CallbackQuery, state: FSMContext) -> None:
    await _start_profile_text_edit(
        callback,
        state,
        field="avoid_topics",
        target_state=ProfileEditState.editing_avoid_topics,
        allow_clear=True,
    )


@router.callback_query(F.data == "profile_edit:avoid_words")
async def profile_edit_avoid_words(callback: CallbackQuery, state: FSMContext) -> None:
    await _start_profile_text_edit(
        callback,
        state,
        field="avoid_words",
        target_state=ProfileEditState.editing_avoid_words,
        allow_clear=True,
    )


@router.callback_query(F.data == "profile_edit:life_areas")
async def profile_edit_life_areas(callback: CallbackQuery, state: FSMContext) -> None:
    await _start_profile_text_edit(
        callback,
        state,
        field="life_areas",
        target_state=ProfileEditState.editing_life_areas,
        allow_clear=True,
    )


async def _save_profile_text_field(
    message: Message,
    state: FSMContext,
    *,
    field: str,
    is_name: bool = False,
    allow_clear: bool = False,
) -> None:
    user = await get_user(message.from_user.id)
    lang = (user or {}).get("language", "ru")
    raw = (message.text or "").strip()
    if not raw:
        await message.answer(_PROFILE_TEXT_PROMPTS[lang][field], reply_markup=profile_text_edit_keyboard(lang, field, allow_clear=allow_clear))
        return

    if is_name:
        if len(raw) > 50:
            await message.answer("Пожалуйста, напиши короткое имя для общения." if lang == "ru" else "Please send a short display name.")
            return
        await update_user_profile(message.from_user.id, name=raw)
    else:
        value = "" if raw == "-" else raw
        patch_value = value if field == "current_focus" else [item.strip() for item in value.split(",")] if value else []
        await merge_user_profile_preferences(message.from_user.id, {field: patch_value})

    await state.clear()
    user = await get_user(message.from_user.id)
    success = "✅ Профиль обновлён." if lang == "ru" else "✅ Profile updated."
    await message.answer(success, reply_markup=main_reply_keyboard((user or {}).get("language", lang)))
    await _show_profile(message, state, user_id=message.from_user.id, user=user)


@router.message(ProfileEditState.editing_name)
async def profile_process_name(message: Message, state: FSMContext) -> None:
    await _save_profile_text_field(message, state, field="name", is_name=True)


@router.message(ProfileEditState.editing_current_focus)
async def profile_process_current_focus(message: Message, state: FSMContext) -> None:
    await _save_profile_text_field(message, state, field="current_focus", allow_clear=True)


@router.message(ProfileEditState.editing_avoid_topics)
async def profile_process_avoid_topics(message: Message, state: FSMContext) -> None:
    await _save_profile_text_field(message, state, field="avoid_topics", allow_clear=True)


@router.message(ProfileEditState.editing_avoid_words)
async def profile_process_avoid_words(message: Message, state: FSMContext) -> None:
    await _save_profile_text_field(message, state, field="avoid_words", allow_clear=True)


@router.message(ProfileEditState.editing_life_areas)
async def profile_process_life_areas(message: Message, state: FSMContext) -> None:
    await _save_profile_text_field(message, state, field="life_areas", allow_clear=True)


@router.message(StateFilter(None), F.text.in_({"👤 Профиль", "👤 Profile"}))
async def main_menu_profile(message: Message, state: FSMContext) -> None:
    await state.clear()
    await cmd_profile(message, state)


@router.message(StateFilter(None), F.text.in_({"🌿 Создать настрой", "🌿 Create mood", "🌿 Create focus"}))
async def main_menu_create(message: Message, state: FSMContext) -> None:
    from handlers.generation import cmd_new

    await cmd_new(message, state)


@router.message(StateFilter(None), F.text.in_({"✨ По моему профилю", "✨ From my profile"}))
async def main_menu_profile_generation(message: Message, state: FSMContext) -> None:
    from handlers.generation import _start_profile_generation

    await _start_profile_generation(
        message,
        state,
        user_id=message.from_user.id,
    )


@router.message(StateFilter(None), F.text.in_({"⚙️ Подписки", "⚙️ Subscriptions"}))
async def main_menu_subscriptions(message: Message, state: FSMContext) -> None:
    from handlers.subscribe import cmd_subscribe

    await cmd_subscribe(message, state)


@router.message(StateFilter(None), F.text.in_({"❓ Помощь", "❓ Help"}))
async def main_menu_help(message: Message, state: FSMContext) -> None:
    from handlers.smalltalk import cmd_help

    await cmd_help(message)


@router.message(StateFilter(None), F.text, ~F.text.startswith("/"))
async def main_menu_text_router(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    text = (message.text or "").strip()
    if not text:
        return
    if not is_input_language_compatible(text, language):
        await message.answer(_main_menu_mismatch_text(language), reply_markup=main_reply_keyboard(language))
        return
    routed = await route_main_menu_intent(message, state, text, language)
    if routed:
        return
    if language == "ru":
        await message.answer(
            "Я не совсем поняла, что ты хочешь сделать 🌿\nВыбери действие в меню ниже.",
            reply_markup=main_reply_keyboard(language),
        )
    else:
        await message.answer(
            "I’m not fully sure what you want to do 🌿\nPlease choose an option from the menu below.",
            reply_markup=main_reply_keyboard(language),
        )


@router.message(StateFilter(None), F.voice)
async def main_menu_voice_router(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    processor = VoiceInputProcessor(stt_transcriber=transcribe_audio_with_meta)
    result = await processor.process(
        message,
        state,
        language=language,
        pending_kind="menu",
        store_pending=False,
    )
    if result.status == "stt_failed":
        await message.answer(_voice_recognition_failed_text(language), reply_markup=main_reply_keyboard(language))
        return

    recognized = result.text or ""
    await message.answer(_voice_recognized_echo_text(language, recognized), reply_markup=main_reply_keyboard(language))
    if result.status == "unclear":
        await message.answer(_voice_unclear_text(language), reply_markup=main_reply_keyboard(language))
        return
    if result.status == "language_mismatch":
        await message.answer(_voice_language_mismatch_text(language), reply_markup=main_reply_keyboard(language))
        return

    if await route_main_menu_intent(message, state, recognized, language):
        return

    if language == "ru":
        await message.answer(
            "Я не совсем поняла, что ты хочешь сделать 🌿\nВыбери действие в меню ниже.",
            reply_markup=main_reply_keyboard(language),
        )
    else:
        await message.answer(
            "I’m not fully sure what you want to do 🌿\nPlease choose an option from the menu below.",
            reply_markup=main_reply_keyboard(language),
        )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Выход из текущего диалога (сброс FSM)."""
    user = await get_user(message.from_user.id)
    lang = (user or {}).get("language", "ru")
    current = await state.get_state()
    if not current:
        await message.answer("Нечего отменять." if lang == "ru" else "Nothing to cancel.")
        return
    await state.clear()
    await message.answer(
        "❌ Отменено. Можно выбрать действие в нижнем меню."
        if lang == "ru"
        else "❌ Cancelled. You can choose an action from the bottom menu.",
        reply_markup=main_reply_keyboard(lang),
    )


@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext) -> None:
    """Полный сброс регистрации пользователя, чтобы пройти её заново."""
    user = await get_user(message.from_user.id)
    lang = (user or {}).get("language", "ru")
    await delete_user_completely(message.from_user.id)
    await state.clear()
    if lang == "ru":
        await message.answer("Я удалил твою регистрацию. Напиши /start, чтобы познакомиться заново и правильно сохранить имя.")
    else:
        await message.answer("I've deleted your registration. Send /start to sign up again and save your name.")

