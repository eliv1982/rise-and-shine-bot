import asyncio
import logging
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import get_settings
from database import init_db
from handlers import generation, smalltalk, start, subscribe
from scheduler import setup_scheduler


def setup_logging() -> None:
    import os
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Логи в файл (в Docker: BOT_DATA_DIR → bot.log в этой папке)
    log_dir = os.getenv("BOT_DATA_DIR", "").strip()
    log_path = os.path.join(log_dir, "bot.log") if log_dir else "bot.log"
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Логи в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


async def main() -> None:
    setup_logging()
    settings = get_settings()

    await init_db()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(subscribe.router)  # до start, чтобы lang: в подписке обрабатывался здесь
    dp.include_router(start.router)
    dp.include_router(generation.router)
    dp.include_router(smalltalk.router)

    setup_scheduler(bot)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

