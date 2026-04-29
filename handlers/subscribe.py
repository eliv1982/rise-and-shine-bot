import logging
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from database import (
    MAX_ACTIVE_SUBSCRIPTIONS,
    count_active_subscriptions,
    create_subscription,
    deactivate_subscription,
    get_active_subscriptions,
    get_subscription_by_id,
    get_user,
    update_subscription,
    update_user_language,
)
from keyboards.inline import (
    language_keyboard,
    sphere_keyboard,
    sphere_keyboard_for_subscription,
    style_keyboard_for_subscription,
    subscription_dashboard_keyboard,
    subscription_delete_confirm_keyboard,
    subscription_edit_keyboard,
    subscription_mode_keyboard,
    subscription_saved_keyboard,
    subscription_select_keyboard,
    subscription_confirm_keyboard,
    subscription_time_keyboard_hours,
    subscription_time_keyboard_minutes,
    visual_mode_keyboard,
)
from scheduler import last_subscription_affirmations
from services.speechkit_tts import synthesize_affirmations_with_pauses
from services.ritual_config import get_sphere_label, get_style_label, get_visual_mode_label, is_tts_available, normalize_visual_mode
from services.subscription_ui import build_dashboard_text, build_subscription_summary
from states import SubscriptionState

router = Router()
logger = logging.getLogger(__name__)


def _new_flow_text(language: str) -> str:
    if language == "ru":
        return "🌿 Что создаём?\n\nВыбери сферу, для которой собрать настрой дня:"
    return "🌿 What shall we create?\n\nChoose an area for your daily focus:"


def _visual_mode_text(language: str) -> str:
    return "🎨 Какой визуал тебе ближе?" if language == "ru" else "🎨 Which visual style feels closer to you?"


def _style_choice_text(language: str) -> str:
    return "✨ Выбери стиль изображения:" if language == "ru" else "✨ Choose image style:"


def _creating_text(language: str) -> str:
    return "🌿 Создаю твой настрой дня..." if language == "ru" else "🌿 Creating your daily focus..."


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


def _limit_text(language: str) -> str:
    if language == "en":
        return "You already have 3 active subscriptions. Please edit or delete one first."
    return "У тебя уже 3 активные подписки. Сначала измени или удали одну из них."


def _setup_intro(language: str, action: str = "add") -> str:
    if action == "edit":
        if language == "en":
            return "✏️ Edit subscription\n\nChoose subscription language:"
        return "✏️ Изменить подписку\n\nВыбери язык подписки:"
    if language == "en":
        return "➕ Add subscription\n\nChoose subscription language:"
    return "➕ Добавить подписку\n\nВыбери язык подписки:"


async def _show_dashboard_message(message: Message, user_id: int, language: str) -> None:
    subscriptions = await get_active_subscriptions(user_id)
    await message.answer(
        build_dashboard_text(subscriptions, language),
        reply_markup=subscription_dashboard_keyboard(language, len(subscriptions)),
    )


async def _show_dashboard_callback(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    subscriptions = await get_active_subscriptions(callback.from_user.id)
    await state.clear()
    await callback.message.edit_text(
        build_dashboard_text(subscriptions, language),
        reply_markup=subscription_dashboard_keyboard(language, len(subscriptions)),
    )
    await callback.answer()


async def _start_subscription_setup(
    callback: CallbackQuery,
    state: FSMContext,
    *,
    action: str,
    subscription_id: Optional[int] = None,
) -> None:
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    if action == "add" and await count_active_subscriptions(callback.from_user.id) >= MAX_ACTIVE_SUBSCRIPTIONS:
        await callback.message.answer(_limit_text(language))
        await _show_dashboard_message(callback.message, callback.from_user.id, language)
        await callback.answer()
        return
    await state.clear()
    await state.update_data(subscription_action=action, edit_subscription_id=subscription_id)
    await state.set_state(SubscriptionState.choosing_language)
    await callback.message.answer(_setup_intro(language, action), reply_markup=language_keyboard())
    await callback.answer()


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    await state.clear()
    await _show_dashboard_message(message, message.from_user.id, language)


@router.callback_query(F.data.in_({"sub:dash", "sub:open", "sub:change"}))
async def sub_dashboard_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await _show_dashboard_callback(callback, state)


@router.callback_query(F.data == "sub:cancel_dash")
async def sub_cancel_dashboard(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    await state.clear()
    await callback.message.edit_text("Готово." if language == "ru" else "Done.")
    await callback.answer()


@router.callback_query(F.data == "sub:add")
async def sub_add_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await _start_subscription_setup(callback, state, action="add")


@router.callback_query(SubscriptionState.choosing_language, F.data.startswith("lang:"))
async def sub_choose_language(callback: CallbackQuery, state: FSMContext) -> None:
    lang = callback.data.split(":", maxsplit=1)[1]
    if lang not in ("ru", "en"):
        await callback.answer()
        return
    await state.update_data(language=lang)
    await state.set_state(SubscriptionState.choosing_mode)
    text_ru = (
        "🌿 Настроим ежедневный ритуал\n\n"
        "Выбери режим подписки:\n\n"
        "🌿 Баланс недели — каждый день новая сфера без повторов в течение недели.\n"
        "🎯 Фокус на сфере — каждый день новый фокус внутри выбранной сферы."
    )
    text_en = (
        "🌿 Let's set up your daily ritual\n\n"
        "Choose subscription mode:\n\n"
        "🌿 Weekly balance — a different area every day, without repeats during the week.\n"
        "🎯 Focus on one area — a new daily focus within the selected area."
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
        await state.set_state(SubscriptionState.choosing_visual_mode)
        await callback.message.edit_text(
            _visual_mode_text(language),
            reply_markup=visual_mode_keyboard(language, for_subscription=True),
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
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    await state.clear()
    subscriptions = await get_active_subscriptions(message.from_user.id)
    if not subscriptions:
        await message.answer(
            "Активных подписок нет." if language == "ru" else "No active subscriptions."
        )
        return
    if len(subscriptions) == 1:
        subscription_id = int(subscriptions[0]["id"])
        text = "Удалить подписку?" if language == "ru" else "Delete subscription?"
        await message.answer(text, reply_markup=subscription_delete_confirm_keyboard(language, subscription_id))
        return
    text = "🗑 Какую подписку удалить?" if language == "ru" else "🗑 Which subscription do you want to delete?"
    await message.answer(text, reply_markup=subscription_select_keyboard(subscriptions, language, "delete"))


@router.callback_query(SubscriptionState.choosing_sphere, F.data.startswith("sphere:"))
async def sub_choose_sphere(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    data = await state.get_data()
    language = _sub_language(data, user)
    sphere = callback.data.split(":", maxsplit=1)[1]
    await state.update_data(sphere=sphere, subsphere=None)
    await state.set_state(SubscriptionState.choosing_visual_mode)
    await callback.message.edit_text(
        _visual_mode_text(language),
        reply_markup=visual_mode_keyboard(language, for_subscription=True),
    )
    await callback.answer()


@router.callback_query(SubscriptionState.choosing_relationship_subsphere, F.data.startswith("subsphere:"))
async def sub_choose_relationship_subsphere(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    data = await state.get_data()
    language = _sub_language(data, user)
    subsphere = callback.data.split(":", maxsplit=1)[1]
    await state.update_data(subsphere=subsphere)
    await state.set_state(SubscriptionState.choosing_visual_mode)
    await callback.message.edit_text(
        _visual_mode_text(language),
        reply_markup=visual_mode_keyboard(language, for_subscription=True),
    )
    await callback.answer()


@router.callback_query(SubscriptionState.choosing_visual_mode, F.data.startswith("visual:"))
async def sub_choose_visual_mode(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    data = await state.get_data()
    language = _sub_language(data, user)
    visual_mode = normalize_visual_mode(callback.data.split(":", maxsplit=1)[1])
    await state.update_data(visual_mode=visual_mode)
    await state.set_state(SubscriptionState.choosing_style)
    await callback.message.edit_text(
        _style_choice_text(language),
        reply_markup=style_keyboard_for_subscription(language, visual_mode=visual_mode),
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
    visual_mode = normalize_visual_mode(data.get("visual_mode"))
    hour = int(data["hour"])
    mode = data.get("subscription_mode", "weekly_balance")
    sphere_label = _sphere_display(sphere, language)
    style_label = _style_display(style, language)
    time_str = f"{hour:02d}:{minute:02d}"
    if language == "ru":
        mode_label = "Баланс недели" if mode == "weekly_balance" else "Фокус на сфере"
        visual_label = get_visual_mode_label(visual_mode, language)
        text = f"Подтверди подписку:\n\n• Режим: {mode_label}\n• Визуально: {visual_label}\n• Сфера: {sphere_label}\n• Стиль: {style_label}\n• Время: {time_str}"
    else:
        mode_label = "Weekly balance" if mode == "weekly_balance" else "Focus on one area"
        visual_label = get_visual_mode_label(visual_mode, language)
        text = f"Confirm subscription:\n\n• Mode: {mode_label}\n• Visual: {visual_label}\n• Area: {sphere_label}\n• Style: {style_label}\n• Time: {time_str}"
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
    await _show_dashboard_message(callback.message, callback.from_user.id, language)


@router.callback_query(SubscriptionState.confirming, F.data == "sub:confirm")
async def sub_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    user = await get_user(callback.from_user.id)
    language = _sub_language(data, user)
    sphere = data["sphere"]
    subsphere = None if sphere == "random" else data.get("subsphere")
    subscription_mode = data.get("subscription_mode", "weekly_balance")
    subscription_sphere = None if subscription_mode == "weekly_balance" else sphere
    action = data.get("subscription_action", "add")
    edit_subscription_id = data.get("edit_subscription_id")
    try:
        if action == "edit" and edit_subscription_id:
            updated = await update_subscription(
                subscription_id=int(edit_subscription_id),
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
                visual_mode=normalize_visual_mode(data.get("visual_mode")),
            )
            if not updated:
                raise ValueError("subscription_not_found")
            saved_subscription = await get_subscription_by_id(int(edit_subscription_id), callback.from_user.id)
        else:
            subscription_id = await create_subscription(
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
                visual_mode=normalize_visual_mode(data.get("visual_mode")),
            )
            saved_subscription = await get_subscription_by_id(subscription_id, callback.from_user.id)
    except ValueError as exc:
        if str(exc) == "active_subscription_limit_reached":
            await callback.message.edit_text(_limit_text(language))
        else:
            await callback.message.edit_text(
                "Не удалось сохранить подписку. Открой /subscribe и попробуй ещё раз."
                if language == "ru"
                else "Could not save the subscription. Open /subscribe and try again."
            )
        await state.clear()
        await callback.answer()
        return
    await update_user_language(callback.from_user.id, language)
    await state.clear()
    count = await count_active_subscriptions(callback.from_user.id)
    summary = build_subscription_summary(saved_subscription, language)
    if language == "ru":
        title = "Подписка обновлена" if action == "edit" else "Подписка добавлена"
        text = f"Готово 🌿\n\n{title}:\n{summary}\n\nАктивных подписок: {count}/{MAX_ACTIVE_SUBSCRIPTIONS}"
    else:
        title = "Subscription updated" if action == "edit" else "Subscription added"
        text = f"Done 🌿\n\n{title}:\n{summary}\n\nActive subscriptions: {count}/{MAX_ACTIVE_SUBSCRIPTIONS}"
    await callback.message.edit_text(text, reply_markup=subscription_saved_keyboard(language, count))
    await callback.answer()


@router.callback_query(F.data == "sub:unsubscribe")
async def sub_unsubscribe_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Backward-compatible callback from old messages: open deletion flow."""
    await state.clear()
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    subscriptions = await get_active_subscriptions(callback.from_user.id)
    if not subscriptions:
        await callback.message.answer("Активных подписок нет." if language == "ru" else "No active subscriptions.")
        await callback.answer()
        return
    if len(subscriptions) == 1:
        subscription_id = int(subscriptions[0]["id"])
        await callback.message.answer(
            "Удалить подписку?" if language == "ru" else "Delete subscription?",
            reply_markup=subscription_delete_confirm_keyboard(language, subscription_id),
        )
    else:
        await callback.message.answer(
            "🗑 Какую подписку удалить?" if language == "ru" else "🗑 Which subscription do you want to delete?",
            reply_markup=subscription_select_keyboard(subscriptions, language, "delete"),
        )
    await callback.answer()


@router.callback_query(F.data == "sub:edit")
async def sub_edit_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбрать подписку для редактирования."""
    await callback.answer()
    await state.clear()
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    subscriptions = await get_active_subscriptions(callback.from_user.id)
    if not subscriptions:
        await callback.message.answer("Активных подписок нет." if language == "ru" else "No active subscriptions.")
        return
    if len(subscriptions) == 1:
        subscription_id = int(subscriptions[0]["id"])
        await callback.message.answer(
            "✏️ Что изменить?" if language == "ru" else "✏️ What would you like to change?",
            reply_markup=subscription_edit_keyboard(language, subscription_id),
        )
        return
    await callback.message.answer(
        "✏️ Какую подписку изменить?" if language == "ru" else "✏️ Which subscription do you want to edit?",
        reply_markup=subscription_select_keyboard(subscriptions, language, "edit"),
    )


@router.callback_query(F.data.startswith("subedit:"))
async def sub_edit_selected(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    subscription_id = int(callback.data.split(":", maxsplit=1)[1])
    subscription = await get_subscription_by_id(subscription_id, callback.from_user.id)
    if not subscription:
        await callback.message.answer("Подписка не найдена." if language == "ru" else "Subscription not found.")
        return
    await callback.message.answer(
        "✏️ Что изменить?" if language == "ru" else "✏️ What would you like to change?",
        reply_markup=subscription_edit_keyboard(language, subscription_id),
    )


@router.callback_query(F.data.startswith("subreconf:"))
async def sub_reconfigure_selected(callback: CallbackQuery, state: FSMContext) -> None:
    subscription_id = int(callback.data.split(":", maxsplit=1)[1])
    subscription = await get_subscription_by_id(subscription_id, callback.from_user.id)
    if not subscription:
        user = await get_user(callback.from_user.id)
        language = (user or {}).get("language", "ru")
        await callback.message.answer("Подписка не найдена." if language == "ru" else "Subscription not found.")
        await callback.answer()
        return
    await _start_subscription_setup(callback, state, action="edit", subscription_id=subscription_id)


@router.callback_query(F.data == "sub:delete")
async def sub_delete_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    subscriptions = await get_active_subscriptions(callback.from_user.id)
    if not subscriptions:
        await callback.message.answer("Активных подписок нет." if language == "ru" else "No active subscriptions.")
        return
    if len(subscriptions) == 1:
        subscription_id = int(subscriptions[0]["id"])
        await callback.message.answer(
            "Удалить подписку?" if language == "ru" else "Delete subscription?",
            reply_markup=subscription_delete_confirm_keyboard(language, subscription_id),
        )
        return
    await callback.message.answer(
        "🗑 Какую подписку удалить?" if language == "ru" else "🗑 Which subscription do you want to delete?",
        reply_markup=subscription_select_keyboard(subscriptions, language, "delete"),
    )


@router.callback_query(F.data.startswith("subdel:"))
async def sub_delete_selected(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    subscription_id = int(callback.data.split(":", maxsplit=1)[1])
    subscription = await get_subscription_by_id(subscription_id, callback.from_user.id)
    if not subscription:
        await callback.message.answer("Подписка не найдена." if language == "ru" else "Subscription not found.")
        return
    await callback.message.answer(
        "Удалить подписку?" if language == "ru" else "Delete subscription?",
        reply_markup=subscription_delete_confirm_keyboard(language, subscription_id),
    )


@router.callback_query(F.data.startswith("subdelok:"))
async def sub_delete_confirmed(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    subscription_id = int(callback.data.split(":", maxsplit=1)[1])
    await deactivate_subscription(callback.from_user.id, subscription_id)
    count = await count_active_subscriptions(callback.from_user.id)
    text = (
        f"Подписка удалена 🗑\n\nАктивных подписок: {count}/{MAX_ACTIVE_SUBSCRIPTIONS}"
        if language == "ru"
        else f"Subscription deleted 🗑\n\nActive subscriptions: {count}/{MAX_ACTIVE_SUBSCRIPTIONS}"
    )
    await callback.message.answer(text, reply_markup=subscription_saved_keyboard(language, count))


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
        _new_flow_text(language),
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
        visual_mode=cached.get("visual_mode") or "illustration",
        custom_style_description=None,
    )
    await callback.message.answer(_creating_text(language))
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

