import logging
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import create_or_update_user, delete_user_completely, get_user, update_user_language, update_user_profile
from keyboards.inline import gender_keyboard, new_affirmation_keyboard
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


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id
    username = message.from_user.username

    user = await get_user(user_id)
    if user:
        await state.clear()
        text = _greet_returning(user.get("name"), user.get("gender"))
        await message.answer(text, reply_markup=new_affirmation_keyboard("ru"))
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
        f"Приятно познакомиться, {name}! Выбери свой пол (это поможет точнее подбирать аффирмации):",
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
    text = "Отлично! Теперь ты можешь создать свою первую аффирмацию."
    if name:
        text = f"Отлично, {name}! Теперь ты можешь создать свою первую аффирмацию."

    await callback.message.edit_text(text, reply_markup=new_affirmation_keyboard("ru"))
    await callback.answer()


@router.message(Command("language"))
async def cmd_language(message: Message, state: FSMContext) -> None:
    """Бот работает только на русском."""
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала напиши /start.")
        return
    await update_user_language(message.from_user.id, "ru")
    await message.answer("Бот работает только на русском языке.")


@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Похоже, мы ещё не знакомы. Напиши /start.")
        return

    name = user.get("name") or "—"
    gender = user.get("gender") or "—"
    await message.answer(
        f"Твой профиль:\n\nИмя: {name}\nПол: {gender}\n\n"
        "Чтобы изменить имя — просто напиши его.\n"
        "Чтобы изменить пол — выбери кнопку ниже.",
        reply_markup=gender_keyboard(language="ru"),
    )
    # Упростим: изменение имени — без FSM, просто следующее текстовое сообщение


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Выход из текущего диалога (сброс FSM)."""
    current = await state.get_state()
    if not current:
        await message.answer("Нечего отменять.")
        return
    await state.clear()
    await message.answer("Отменено. Напиши /new для новой аффирмации.")


@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext) -> None:
    """
    Полный сброс регистрации пользователя, чтобы пройти её заново.
    """
    await delete_user_completely(message.from_user.id)
    await state.clear()
    await message.answer(
        "Я удалил твою регистрацию. Напиши /start, чтобы познакомиться заново и правильно сохранить имя."
    )

