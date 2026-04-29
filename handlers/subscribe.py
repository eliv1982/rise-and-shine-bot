import logging
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from database import deactivate_subscription, get_user, update_user_language, upsert_subscription
from keyboards.inline import (
    language_keyboard,
    sphere_keyboard,
    sphere_keyboard_for_subscription,
    style_keyboard_for_subscription,
    subscription_mode_keyboard,
    subscription_confirm_keyboard,
    subscription_time_keyboard_hours,
    subscription_time_keyboard_minutes,
)
from scheduler import last_subscription_affirmations
from services.speechkit_tts import synthesize_affirmations_with_pauses
from services.ritual_config import get_sphere_label, get_style_label, is_tts_available
from states import SubscriptionState

router = Router()
logger = logging.getLogger(__name__)


def _sphere_display(sphere: str, language: str) -> str:
    """Человекочитаемое название сферы для подтверждения подписки."""
    if sphere == "random":
        return "Баланс недели" if language == "ru" else "Weekly balance"
    return get_sphere_label(sphere, language)


def _style_display(style: str, language: str) -> str:
    """Человекочитаемое название стиля для подтверждения подписки."""
    if style == "random":
        style = "random_suitable"
    return get_style_label(style, language)


def _sub_language(state_data: dict, user: Optional[dict]) -> str:
    """Язык в потоке подписки: из state или из профиля."""
    return (state_data or {}).get("language") or (user or {}).get("language", "ru")


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    await state.set_state(SubscriptionState.choosing_language)
    text_ru = "Выбери язык для ежедневных аффирмаций:"
    text_en = "Choose language for your daily affirmations:"
    text = text_ru if language == "ru" else text_en
    await message.answer(text, reply_markup=language_keyboard())


@router.callback_query(SubscriptionState.choosing_language, F.data.startswith("lang:"))
async def sub_choose_language(callback: CallbackQuery, state: FSMContext) -> None:
    lang = callback.data.split(":", maxsplit=1)[1]
    if lang not in ("ru", "en"):
        await callback.answer()
        return
    await state.update_data(language=lang)
    await state.set_state(SubscriptionState.choosing_mode)
    text_ru = (
        "Выбери режим подписки:\n\n"
        "🌿 Баланс недели — каждый день новая сфера без повторов в течение недели.\n"
        "🎯 Фокус на сфере — каждый день новый фокус внутри выбранной сферы."
    )
    text_en = (
        "Choose subscription mode:\n\n"
        "🌿 Weekly balance — a different life area every day, without repeats during the week.\n"
        "🎯 Focus on one area — a new daily focus within the selected life area."
    )
    text = text_ru if lang == "ru" else text_en
    await callback.message.edit_text(text, reply_markup=subscription_mode_keyboard(lang))
    await callback.answer()


@router.callback_query(SubscriptionState.choosing_mode, F.data.startswith("submode:"))
async def sub_choose_mode(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    data = await state.get_data()
    language = _sub_language(data, user)
    mode = callback.data.split(":", maxsplit=1)[1]
    if mode not in ("weekly_balance", "sphere_focus"):
        await callback.answer()
        return
    await state.update_data(subscription_mode=mode)
    if mode == "weekly_balance":
        await state.update_data(sphere="random", subsphere=None)
        await state.set_state(SubscriptionState.choosing_style)
        await callback.message.edit_text(
            "Выбери стиль изображения:" if language == "ru" else "Choose image style:",
            reply_markup=style_keyboard_for_subscription(language),
        )
    else:
        await state.set_state(SubscriptionState.choosing_sphere)
        await callback.message.edit_text(
            "Выбери сферу для ежедневного фокуса:" if language == "ru" else "Choose an area for daily focus:",
            reply_markup=sphere_keyboard_for_subscription(language),
        )
    await callback.answer()


@router.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: Message, state: FSMContext) -> None:
    await deactivate_subscription(message.from_user.id)
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    if language == "ru":
        await message.answer("Ежедневная подписка отключена.")
    else:
        await message.answer("Daily subscription disabled.")


@router.callback_query(SubscriptionState.choosing_sphere, F.data.startswith("sphere:"))
async def sub_choose_sphere(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    data = await state.get_data()
    language = _sub_language(data, user)
    sphere = callback.data.split(":", maxsplit=1)[1]
    await state.update_data(sphere=sphere, subsphere=None)
    await state.set_state(SubscriptionState.choosing_style)
    await callback.message.edit_text(
        "Выбери стиль изображения:" if language == "ru" else "Choose image style:",
        reply_markup=style_keyboard_for_subscription(language),
    )
    await callback.answer()


@router.callback_query(SubscriptionState.choosing_relationship_subsphere, F.data.startswith("subsphere:"))
async def sub_choose_relationship_subsphere(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    data = await state.get_data()
    language = _sub_language(data, user)
    subsphere = callback.data.split(":", maxsplit=1)[1]
    await state.update_data(subsphere=subsphere)
    await state.set_state(SubscriptionState.choosing_style)
    await callback.message.edit_text(
        "Выбери стиль изображения:" if language == "ru" else "Choose image style:",
        reply_markup=style_keyboard_for_subscription(language),
    )
    await callback.answer()


@router.callback_query(SubscriptionState.choosing_style, F.data.startswith("style:"))
async def sub_choose_style(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    data = await state.get_data()
    language = _sub_language(data, user)
    style = callback.data.split(":", maxsplit=1)[1]
    await state.update_data(style=style)
    await state.set_state(SubscriptionState.choosing_hour)
    await callback.message.edit_text(
        "Выбери час (по времени бота):" if language == "ru" else "Choose hour (bot time):",
        reply_markup=subscription_time_keyboard_hours(language),
    )
    await callback.answer()


@router.callback_query(SubscriptionState.choosing_hour, F.data.startswith("hour:"))
async def sub_choose_hour(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    data = await state.get_data()
    language = _sub_language(data, user)
    hour = int(callback.data.split(":", maxsplit=1)[1])
    await state.update_data(hour=hour)
    await state.set_state(SubscriptionState.choosing_minute)
    await callback.message.edit_text(
        "Выбери минуты:" if language == "ru" else "Choose minutes:",
        reply_markup=subscription_time_keyboard_minutes(language),
    )
    await callback.answer()


@router.callback_query(SubscriptionState.choosing_minute, F.data.startswith("minute:"))
async def sub_choose_minute(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    data = await state.get_data()
    language = _sub_language(data, user)
    minute = int(callback.data.split(":", maxsplit=1)[1])
    await state.update_data(minute=minute)
    await state.set_state(SubscriptionState.confirming)
    data = await state.get_data()
    sphere = data.get("sphere")
    style = data.get("style")
    hour = int(data["hour"])
    mode = data.get("subscription_mode", "weekly_balance")
    sphere_label = _sphere_display(sphere, language)
    style_label = _style_display(style, language)
    time_str = f"{hour:02d}:{minute:02d}"
    if language == "ru":
        mode_label = "Баланс недели" if mode == "weekly_balance" else "Фокус на сфере"
        text = f"Подтверди подписку:\n\n• Режим: {mode_label}\n• Сфера: {sphere_label}\n• Стиль: {style_label}\n• Время: {time_str}"
    else:
        mode_label = "Weekly balance" if mode == "weekly_balance" else "Focus on one area"
        text = f"Confirm subscription:\n\n• Mode: {mode_label}\n• Area: {sphere_label}\n• Style: {style_label}\n• Time: {time_str}"
    await callback.message.edit_text(text, reply_markup=subscription_confirm_keyboard(language))
    await callback.answer()


@router.callback_query(SubscriptionState.confirming, F.data == "sub:cancel")
async def sub_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    user = await get_user(callback.from_user.id)
    language = _sub_language(data, user)
    await state.clear()
    if language == "ru":
        await callback.message.edit_text("Подписка отменена.")
    else:
        await callback.message.edit_text("Subscription cancelled.")
    await callback.answer()


@router.callback_query(SubscriptionState.confirming, F.data == "sub:confirm")
async def sub_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    user = await get_user(callback.from_user.id)
    language = _sub_language(data, user)
    sphere = data["sphere"]
    subsphere = None if sphere == "random" else data.get("subsphere")
    subscription_mode = data.get("subscription_mode", "weekly_balance")
    subscription_sphere = None if subscription_mode == "weekly_balance" else sphere
    await upsert_subscription(
        user_id=callback.from_user.id,
        sphere=sphere,
        subsphere=subsphere,
        image_style=data["style"],
        language=language,
        hour=int(data["hour"]),
        minute=int(data["minute"]),
        subscription_mode=subscription_mode,
        subscription_sphere=subscription_sphere,
        subscription_style_mode=data["style"],
    )
    await update_user_language(callback.from_user.id, language)
    await state.clear()
    time_str = f"{data['hour']:02d}:{data['minute']:02d}"
    if language == "ru":
        await callback.message.edit_text(f"Подписка сохранена. Рассылка в {time_str}.")
    else:
        await callback.message.edit_text(f"Subscription saved. Delivery at {time_str}.")
    await callback.answer()


@router.callback_query(F.data == "sub:unsubscribe")
async def sub_unsubscribe_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Отменить подписку по кнопке под сообщением рассылки."""
    await callback.answer()
    await state.clear()
    await deactivate_subscription(callback.from_user.id)
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    if language == "ru":
        await callback.message.answer("Подписка отменена.")
    else:
        await callback.message.answer("Subscription cancelled.")


@router.callback_query(F.data == "sub:change")
async def sub_change_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Изменить подписку: заново выбрать язык, режим, стиль, время."""
    await callback.answer()
    await state.clear()
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    await state.set_state(SubscriptionState.choosing_language)
    text_ru = "Изменить подписку. Выбери язык для ежедневных аффирмаций:"
    text_en = "Change subscription. Choose language for your daily affirmations:"
    text = text_ru if language == "ru" else text_en
    await callback.message.answer(text, reply_markup=language_keyboard())


@router.callback_query(F.data == "sub_new:yes")
async def subscription_create_new(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать ручную генерацию из сообщения подписки."""
    await callback.answer()
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    await state.clear()
    await state.update_data(theme_text=None)
    from states import GenerationState

    await state.set_state(GenerationState.choosing_sphere)
    await callback.message.answer(
        "Выбери сферу жизни:" if language == "ru" else "Choose a life area:",
        reply_markup=sphere_keyboard(language),
    )


@router.callback_query(F.data == "sub_more:yes")
async def subscription_more(callback: CallbackQuery, state: FSMContext) -> None:
    """Сгенерировать ещё один ритуал на основе последней подписочной сферы и стиля."""
    await callback.answer()
    user_id = callback.from_user.id
    user = await get_user(user_id)
    language = (user or {}).get("language", "ru")
    cached = last_subscription_affirmations.get(user_id)
    if not cached:
        await callback.message.answer(
            "Нет данных последней подписки. Нажми «Создать новую» или настрой подписку заново."
            if language == "ru"
            else "No recent subscription data. Tap Create new or set up the subscription again."
        )
        return
    await state.update_data(
        sphere=cached.get("sphere") or "inner_peace",
        subsphere=cached.get("subsphere"),
        style=cached.get("style") or cached.get("style_mode") or "auto",
        custom_style_description=None,
    )
    await callback.message.answer("Генерирую ещё..." if language == "ru" else "Generating more...")
    from handlers.generation import _run_generation

    await _run_generation(callback.message, state, theme_text=None, user_telegram_id=user_id)


@router.callback_query(F.data == "sub_tts:yes")
async def subscription_tts(callback: CallbackQuery) -> None:
    """Озвучить последнюю рассылку по подписке."""
    await callback.answer()
    user_id = callback.from_user.id
    user = await get_user(user_id)
    language = (user or {}).get("language", "ru")
    if not is_tts_available(language):
        await callback.message.answer(
            "English audio is coming soon. Audio is currently available in Russian only."
        )
        return
    cached = last_subscription_affirmations.get(user_id)
    if not cached or not cached.get("affirmations"):
        msg_ru = "Нет данных для озвучки. Следующая рассылка по подписке придёт в назначенное время."
        msg_en = "No data to voice. Your next subscription delivery will arrive at the scheduled time."
        await callback.message.answer(msg_ru if language == "ru" else msg_en)
        return
    affirmations = cached["affirmations"]
    gender = cached.get("gender")
    try:
        audio_path = await synthesize_affirmations_with_pauses(
            affirmations, gender=gender, pause_seconds=5.0
        )
        await callback.message.answer_voice(voice=FSInputFile(audio_path))
    except RuntimeError as e:
        await callback.message.answer(str(e))
    except Exception as exc:
        logger.exception("Subscription TTS failed: %s", exc)
        err_ru = "Сервис озвучки временно недоступен. Попробуй позже."
        err_en = "Voice service is temporarily unavailable. Try again later."
        await callback.message.answer(err_ru if language == "ru" else err_en)

