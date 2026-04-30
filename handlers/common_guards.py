from aiogram.types import Message

from handlers.common_messages import menu_choose_option_text, menu_choose_style_text


async def answer_menu_option_guard(message: Message, language: str) -> None:
    await message.answer(menu_choose_option_text(language))


async def answer_menu_style_guard(message: Message, language: str) -> None:
    await message.answer(menu_choose_style_text(language))
