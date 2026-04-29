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
    update_user_language,
    update_user_profile,
)
from keyboards.inline import (
    gender_keyboard,
    language_keyboard,
    main_reply_keyboard,
    new_affirmation_keyboard,
    profile_keyboard,
    start_menu_keyboard,
)
from database import MAX_ACTIVE_SUBSCRIPTIONS
from services.subscription_ui import build_subscription_summary, build_subscriptions_summary, gender_profile_label
from services.speechkit import transcribe_audio
from services.speechkit_stt import get_stt_debug_info
from states import RegistrationState
from utils import extract_name_from_introduction

router = Router()
logger = logging.getLogger(__name__)


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


def _voice_recognition_failed_text(language: str) -> str:
    if language == "ru":
        return "Не получилось распознать голос 😕\nПопробуй ещё раз или отправь текстом."
    return "I couldn’t recognize the voice message 😕\nPlease try again or send it as text."


def _voice_recognized_echo_text(language: str, recognized_text: str) -> str:
    clipped = recognized_text.strip()
    if len(clipped) > 140:
        clipped = clipped[:137] + "..."
    if language == "ru":
        return f"🎙️ Распознала: \"{clipped}\""
    return f"🎙️ I recognized: \"{clipped}\""


def _voice_intent(recognized_text: str) -> str:
    low = recognized_text.lower()
    if any(token in low for token in ("подпис", "subscription", "subscribe", "subs")):
        return "subscriptions"
    if any(token in low for token in ("профил", "profile", "account")):
        return "profile"
    if any(token in low for token in ("созд", "new", "create", "ритуал", "настрой", "affirmation", "focus")):
        return "create"
    return "unknown"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    username = message.from_user.username

    user = await get_user(user_id)
    if user:
        await state.clear()
        lang = (user or {}).get("language", "ru")
        if lang == "en":
            name = user.get("name") or "there"
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
        recognized = await transcribe_audio(local_path, language="ru")
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
    if lang == "ru":
        await callback.message.edit_text("Язык изменён на русский. Дальше буду общаться по-русски.")
        await callback.message.answer("🌿 Язык обновлён. Нижнее меню тоже переключилось на русский.", reply_markup=main_reply_keyboard("ru"))
    else:
        await callback.message.edit_text("Language set to English. I'll use English from now on.")
        await callback.message.answer("🌿 Language updated. The bottom menu is now in English.", reply_markup=main_reply_keyboard("en"))
    await callback.answer()


@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Похоже, мы ещё не знакомы. Напиши /start.")
        return

    lang = (user or {}).get("language", "ru")
    name = user.get("name") or "—"
    gender_label = gender_profile_label(user.get("gender"), lang)
    subscriptions = await get_active_subscriptions(message.from_user.id)
    subscriptions_summary = build_subscriptions_summary(subscriptions, lang)
    count = len(subscriptions)
    if lang == "ru":
        text = (
            f"👤 Твой профиль\n\n"
            f"Имя: {name}\n"
            f"Обращение: {gender_label}\n\n"
            f"🧾 Подписки: {count}/{MAX_ACTIVE_SUBSCRIPTIONS}\n{subscriptions_summary}\n\n"
            "Чтобы изменить имя — просто напиши новое.\n"
            "Чтобы изменить обращение — выбери кнопку ниже."
        )
    else:
        text = (
            f"👤 Your profile\n\n"
            f"Name: {name}\n"
            f"Pronouns: {gender_label}\n\n"
            f"🧾 Subscriptions: {count}/{MAX_ACTIVE_SUBSCRIPTIONS}\n{subscriptions_summary}\n\n"
            "To change your name, just send a new one.\n"
            "To change form of address, use the buttons below."
        )
    await message.answer(text, reply_markup=profile_keyboard(lang, has_subscription=bool(subscriptions)))


@router.callback_query(F.data == "profile:open")
async def profile_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await cmd_profile(callback.message, state)


@router.message(F.text.in_({"👤 Профиль", "👤 Profile"}))
async def main_menu_profile(message: Message, state: FSMContext) -> None:
    await state.clear()
    await cmd_profile(message, state)


@router.message(F.text.in_({"🌿 Создать настрой", "🌿 Create mood", "🌿 Create focus"}))
async def main_menu_create(message: Message, state: FSMContext) -> None:
    from handlers.generation import cmd_new

    await cmd_new(message, state)


@router.message(F.text.in_({"⚙️ Подписки", "⚙️ Subscriptions"}))
async def main_menu_subscriptions(message: Message, state: FSMContext) -> None:
    from handlers.subscribe import cmd_subscribe

    await cmd_subscribe(message, state)


@router.message(StateFilter(None), F.voice)
async def main_menu_voice_router(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    voice = message.voice
    if not voice:
        return
    file = await message.bot.get_file(voice.file_id)
    dest_dir = get_outputs_dir()
    os.makedirs(dest_dir, exist_ok=True)
    local_path = f"{dest_dir}/voice_menu_{message.from_user.id}_{voice.file_unique_id}.ogg"
    try:
        await message.bot.download_file(file.file_path, destination=local_path)
        recognized = await transcribe_audio(local_path, language=language)
    except Exception:
        await message.answer(_voice_recognition_failed_text(language), reply_markup=main_reply_keyboard(language))
        return

    stt_meta = get_stt_debug_info(language)
    await state.update_data(last_stt_meta=stt_meta, last_recognized_text=recognized)
    await message.answer(_voice_recognized_echo_text(language, recognized), reply_markup=main_reply_keyboard(language))

    intent = _voice_intent(recognized)
    if intent == "create":
        from handlers.generation import cmd_new

        await cmd_new(message, state)
        return
    if intent == "subscriptions":
        from handlers.subscribe import cmd_subscribe

        await cmd_subscribe(message, state)
        return
    if intent == "profile":
        await cmd_profile(message, state)
        return

    if language == "ru":
        await message.answer("Могу помочь создать настрой дня, открыть подписки или профиль. Выбери действие ниже 👇", reply_markup=main_reply_keyboard(language))
    else:
        await message.answer("I can create your daily focus, open subscriptions, or show your profile. Choose an action below 👇", reply_markup=main_reply_keyboard(language))


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

