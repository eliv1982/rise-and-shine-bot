import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message

from config import get_settings
from database import (
    get_smalltalk_usage_today,
    get_user,
    is_onboarding_complete,
    release_smalltalk_usage,
    reserve_smalltalk_usage,
)
from keyboards.inline import new_affirmation_keyboard
from monitoring import log_smalltalk_rate_limited, log_smalltalk_unregistered_rejected
from services.language_policy import is_input_language_compatible
from services.main_menu_intents import detect_main_menu_intent
from services.yandex_gpt import generate_smalltalk_reply

router = Router()
logger = logging.getLogger(__name__)


def _registration_required_text(language: str) -> str:
    if language == "ru":
        return "Давай сначала познакомимся 🌿\nНапиши /start, чтобы начать."
    return "Let's get you set up first 🌿\nSend /start to begin."


def _smalltalk_limit_reached_text(language: str, limit: int) -> str:
    if language == "ru":
        return (
            f"Сегодня уже {limit} сообщений в свободном чате — это дневной лимит. "
            "Продолжим завтра! А пока можешь создать новый настрой дня."
        )
    return (
        f"You've reached today's limit of {limit} chat messages. "
        "Let's continue tomorrow! Meanwhile, you can create a new daily focus."
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    user = await get_user(message.from_user.id)
    lang = (user or {}).get("language", "ru")
    if lang == "ru":
        text = (
            "Я бот *Rise and Shine Daily*.\n\n"
            "Я помогаю тебе собирать ежедневный ритуал: фокус дня, аффирмации, мягкий шаг и красивый визуал.\n\n"
            "/start — приветствие и главное меню\n"
            "/new — создать настрой вручную\n"
            "/subscribe — настроить подписки\n"
            "/unsubscribe — отменить подписку\n"
            "/profile — профиль и персональные настройки\n"
            "/language — сменить язык\n"
            "/cancel — сбросить текущий диалог\n"
            "/reset — удалить регистрацию\n"
            "/help — справка"
        )
    else:
        text = (
            "I'm the *Rise and Shine Daily* bot.\n\n"
            "I help you create a daily ritual: focus of the day, affirmations, a gentle step and a beautiful visual.\n\n"
            "/start — greeting and main menu\n"
            "/new — create mood manually\n"
            "/subscribe — manage subscriptions\n"
            "/unsubscribe — cancel subscription\n"
            "/profile — profile and personal settings\n"
            "/language — change language\n"
            "/cancel — reset current dialog\n"
            "/reset — delete registration\n"
            "/help — help"
        )
    await message.answer(text, parse_mode="Markdown")


@router.message(default_state)
async def smalltalk(message: Message, state: FSMContext) -> None:
    # Команды обрабатываются другими хендлерами
    if message.text and message.text.startswith("/"):
        return

    user = await get_user(message.from_user.id)
    if not is_onboarding_complete(user):
        # Anonymous/unregistered users, and users whose registration was interrupted
        # before name+gender were both collected, must not reach the paid LLM path.
        log_smalltalk_unregistered_rejected(message.from_user.id)
        language = (user or {}).get("language", "ru")
        await message.answer(_registration_required_text(language))
        return

    language = (user or {}).get("language", "ru")
    text = message.text or ""
    if is_input_language_compatible(text, language) and detect_main_menu_intent(text, language):
        from handlers.start import route_main_menu_intent

        if await route_main_menu_intent(message, state, text, language):
            return

    settings = get_settings()
    limit = settings.smalltalk_daily_limit
    limit_enabled = limit > 0
    if limit_enabled:
        reserved = await reserve_smalltalk_usage(message.from_user.id, limit)
        if not reserved:
            used = await get_smalltalk_usage_today(message.from_user.id)
            log_smalltalk_rate_limited(message.from_user.id, used, limit)
            await message.answer(
                _smalltalk_limit_reached_text(language, limit),
                reply_markup=new_affirmation_keyboard(language),
            )
            return

    try:
        reply = await generate_smalltalk_reply(text, language=language)
    except Exception as exc:
        logger.exception("Smalltalk failed: %s", exc)
        if limit_enabled:
            # The reservation was made before the call; release it since no reply was produced.
            await release_smalltalk_usage(message.from_user.id)
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

    try:
        await message.answer(reply, reply_markup=new_affirmation_keyboard(language))
    except Exception:
        if limit_enabled:
            # The LLM produced a reply, but Telegram never delivered it to the user;
            # release the reservation rather than charge them for a message they never saw.
            await release_smalltalk_usage(message.from_user.id)
        raise

