import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message

from database import get_user
from keyboards.inline import new_affirmation_keyboard
from services.language_policy import is_input_language_compatible
from services.main_menu_intents import detect_main_menu_intent
from services.yandex_gpt import generate_smalltalk_reply

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    user = await get_user(message.from_user.id)
    lang = (user or {}).get("language", "ru")
    if lang == "ru":
        text = (
            "Я бот *Rise and Shine Daily*.\n\n"
            "Я помогаю тебе собирать ежедневный ритуал: фокус дня, аффирмации, мягкий шаг и красивый визуал.\n\n"
            "/start — регистрация или приветствие\n"
            "/new — новый настрой дня\n"
            "/subscribe — подписка на ежедневный ритуал\n"
            "/unsubscribe — отменить подписку\n"
            "/profile — профиль\n"
            "/language — сменить язык (русский / English)\n"
            "/cancel — выйти из текущего диалога"
        )
    else:
        text = (
            "I'm the *Rise and Shine Daily* bot.\n\n"
            "I help you create a daily ritual: focus of the day, affirmations, a gentle step and a beautiful visual.\n\n"
            "/start — sign up or greeting\n"
            "/new — new daily focus\n"
            "/subscribe — daily ritual subscription\n"
            "/unsubscribe — cancel subscription\n"
            "/profile — your profile\n"
            "/language — change language (Russian / English)\n"
            "/cancel — exit current dialog"
        )
    await message.answer(text, parse_mode="Markdown")


@router.message(default_state)
async def smalltalk(message: Message, state: FSMContext) -> None:
    # Команды обрабатываются другими хендлерами
    if message.text and message.text.startswith("/"):
        return

    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    text = message.text or ""
    if is_input_language_compatible(text, language) and detect_main_menu_intent(text, language):
        from handlers.start import route_main_menu_intent

        if await route_main_menu_intent(message, state, text, language):
            return

    try:
        reply = await generate_smalltalk_reply(text, language=language)
    except Exception as exc:
        logger.exception("Smalltalk failed: %s", exc)
        if language == "ru":
            await message.answer(
                "Я здесь, чтобы помогать с ежедневным настроем. Хочешь создать новый?",
                reply_markup=new_affirmation_keyboard(language),
            )
        else:
            await message.answer(
                "I'm here to help with your daily focus. Want to create a new one?",
                reply_markup=new_affirmation_keyboard(language),
            )
        return

    await message.answer(reply, reply_markup=new_affirmation_keyboard(language))

