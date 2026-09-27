import asyncio
import logging
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from cleanup_outputs import run_outputs_cleanup
from config import get_settings
from database import init_db
from handlers import generation, smalltalk, start, subscribe
from scheduler import scheduler, setup_scheduler

logger = logging.getLogger(__name__)


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


async def stop_scheduler_on_shutdown() -> None:
    """Registered as a dp.shutdown hook: aiogram already handles SIGTERM/SIGINT
    (loop.add_signal_handler) and runs shutdown hooks as soon as polling stops,
    before closing the bot session - earlier than main()'s own finally block.

    The scheduler is told to stop here too, without waiting for an in-flight
    delivery to finish: Stage 2's durable claim lease (scheduler.CLAIM_LEASE)
    already reclaims and retries an interrupted delivery after restart with its
    persisted visual mode intact (see tests/test_scheduler_delivery.py), so
    cancelling keeps deploys fast instead of blocking up to
    ATTEMPT_TIMEOUT_SECONDS (600s) for whatever happened to be running.
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)


async def main() -> None:
    setup_logging()
    settings = get_settings()

    await init_db()
    await run_outputs_cleanup()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(subscribe.router)  # до start, чтобы lang: в подписке обрабатывался здесь
    dp.include_router(start.router)
    dp.include_router(generation.router)
    dp.include_router(smalltalk.router)

    setup_scheduler(bot)
    dp.shutdown.register(stop_scheduler_on_shutdown)

    try:
        await dp.start_polling(bot)
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except asyncio.CancelledError:
        logger.info("Bot polling cancelled")

