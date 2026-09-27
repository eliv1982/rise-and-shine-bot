from typing import Any, Optional

from aiogram.types import Message

from database import is_onboarding_complete
from handlers.common_messages import menu_choose_option_text, menu_choose_style_text


async def answer_menu_option_guard(message: Message, language: str) -> None:
    await message.answer(menu_choose_option_text(language))


async def answer_menu_style_guard(message: Message, language: str) -> None:
    await message.answer(menu_choose_style_text(language))


def onboarding_incomplete_text(language: str) -> str:
    if language == "ru":
        return "Давай закончим знакомство 🌿\nНапиши /start, чтобы продолжить регистрацию."
    return "Let's finish getting you set up first 🌿\nSend /start to continue registration."


async def require_onboarded_user(message: Message, user: Optional[dict[str, Any]]) -> bool:
    """True once ``user`` has completed onboarding; otherwise answers with a redirect to
    /start and returns False.

    A ``users`` row can exist before registration finished (see database.is_onboarding_
    complete), so a caller must not treat "a row exists" as "ready for normal bot use" -
    only this predicate. Callers that already have the FSM state cleared/managed elsewhere
    are unaffected: this only sends a message and reports whether to proceed.
    """
    if is_onboarding_complete(user):
        return True
    language = (user or {}).get("language", "ru")
    await message.answer(onboarding_incomplete_text(language))
    return False
