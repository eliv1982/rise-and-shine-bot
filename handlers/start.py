import logging
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import (
    create_or_update_user,
    delete_user_completely,
    get_subscription,
    get_user,
    update_user_language,
    update_user_profile,
)
from keyboards.inline import gender_keyboard, language_keyboard, new_affirmation_keyboard, profile_keyboard
from services.ritual_config import get_sphere_label, get_style_label, get_visual_mode_label, normalize_visual_mode
from states import RegistrationState
from utils import extract_name_from_introduction

router = Router()
logger = logging.getLogger(__name__)


def _greet_returning(name: Optional[str], gender: Optional[str]) -> str:
    if gender == "female":
        if name:
            return f"С возвращением, {name}!"
        return "Рада тебя видеть снова!"
    if name:
        return f"С возвращением, {name}!"
    return "Рад тебя видеть снова!"


def _gender_profile_label(gender: Optional[str], language: str) -> str:
    if language == "en":
        if gender == "female":
            return "feminine"
        if gender == "male":
            return "masculine"
        return "not specified"
    if gender == "female":
        return "женский род"
    if gender == "male":
        return "мужской род"
    return "не указано"


def _subscription_mode_label(mode: str, language: str) -> str:
    if mode == "sphere_focus":
        return "🎯 Фокус на сфере" if language == "ru" else "🎯 Focus on one area"
    return "🌿 Баланс недели" if language == "ru" else "🌿 Weekly balance"


def _profile_style_label(style: Optional[str], language: str) -> str:
    style = style or "auto"
    if style in ("auto", "random"):
        return "🎨 Автоподбор" if language == "ru" else "🎨 Auto"
    if style == "random_suitable":
        return "🔀 Разные подходящие стили" if language == "ru" else "🔀 Different suitable styles"
    return get_style_label(style, language)


def build_subscription_summary(subscription: Optional[dict], language: str = "ru") -> str:
    if not subscription:
        if language == "en":
            return "No active subscriptions yet.\nYou can set up your daily ritual with /subscribe."
        return "Пока нет активных подписок.\nНастроить ежедневный ритуал можно командой /subscribe."

    mode = subscription.get("subscription_mode") or (
        "weekly_balance" if subscription.get("sphere") == "random" else "sphere_focus"
    )
    visual_mode = normalize_visual_mode(subscription.get("visual_mode"))
    style = subscription.get("subscription_style_mode") or subscription.get("image_style") or "auto"
    hour = int(subscription.get("hour", 0))
    minute = int(subscription.get("minute", 0))
    time_str = f"{hour:02d}:{minute:02d}"

    lines = [f"1. {_subscription_mode_label(mode, language)}"]
    if mode == "sphere_focus":
        sphere = subscription.get("subscription_sphere") or subscription.get("sphere") or "inner_peace"
        label = get_sphere_label(sphere, language)
        lines.append(f"Сфера: {label}" if language == "ru" else f"Area: {label}")
    lines.append(f"Время: {time_str}" if language == "ru" else f"Time: {time_str}")
    lines.append(
        f"Визуал: {get_visual_mode_label(visual_mode, language)}"
        if language == "ru"
        else f"Visual: {get_visual_mode_label(visual_mode, language)}"
    )
    lines.append(f"Стиль: {_profile_style_label(style, language)}" if language == "ru" else f"Style: {_profile_style_label(style, language)}")
    return "\n".join(lines)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    username = message.from_user.username

    user = await get_user(user_id)
    if user:
        await state.clear()
        lang = (user or {}).get("language", "ru")
        text = _greet_returning(user.get("name"), user.get("gender"))
        await message.answer(text, reply_markup=new_affirmation_keyboard(lang))
        return

    # Новый пользователь
    await create_or_update_user(user_id=user_id, username=username)
    await state.set_state(RegistrationState.waiting_for_name)
    await message.answer("Привет! Давай познакомимся. Как тебя зовут?")


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
    text = "Обращение обновлено." if lang == "ru" else "Form of address updated."
    await callback.answer()
    await callback.message.answer(text)


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
        await callback.message.answer("Готово.", reply_markup=new_affirmation_keyboard("ru"))
    else:
        await callback.message.edit_text("Language set to English. I'll use English from now on.")
        await callback.message.answer("Done.", reply_markup=new_affirmation_keyboard("en"))
    await callback.answer()


@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Похоже, мы ещё не знакомы. Напиши /start.")
        return

    lang = (user or {}).get("language", "ru")
    name = user.get("name") or "—"
    gender_label = _gender_profile_label(user.get("gender"), lang)
    subscription = await get_subscription(message.from_user.id)
    subscriptions_summary = build_subscription_summary(subscription, lang)
    if lang == "ru":
        text = (
            f"👤 Твой профиль\n\n"
            f"Имя: {name}\n"
            f"Обращение: {gender_label}\n\n"
            f"🌿 Подписки:\n{subscriptions_summary}\n\n"
            "Чтобы изменить имя — просто напиши новое.\n"
            "Чтобы изменить обращение — выбери кнопку ниже."
        )
    else:
        text = (
            f"👤 Your profile\n\n"
            f"Name: {name}\n"
            f"Form of address: {gender_label}\n\n"
            f"🌿 Subscriptions:\n{subscriptions_summary}\n\n"
            "To change your name, just send a new one.\n"
            "To change form of address, use the buttons below."
        )
    await message.answer(text, reply_markup=profile_keyboard(lang, has_subscription=bool(subscription)))


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
        "Отменено. Напиши /new, чтобы создать настрой дня." if lang == "ru" else "Cancelled. Send /new to create a daily focus."
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

