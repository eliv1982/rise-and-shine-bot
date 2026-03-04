import asyncio
import datetime as dt
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types import FSInputFile

from database import get_due_subscriptions
from services.openai_image import generate_image
from services.yandex_gpt import generate_affirmations
from utils import gender_display

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def send_daily_affirmations(bot: Bot) -> None:
    now = dt.datetime.now()
    subs = await get_due_subscriptions(now)
    if not subs:
        return

    for sub in subs:
        user_id = sub["user_id"]
        sphere = sub["sphere"]
        subsphere = sub.get("subsphere")
        style = sub["image_style"]
        language = sub["language"]
        gender = sub.get("user_gender")

        gender_hint = gender_display(gender, language=language)

        try:
            affirmations_task = generate_affirmations(
                sphere=sphere,
                language=language,
                user_text=None,
                subsphere=subsphere,
                gender_hint=gender_hint,
                gender=gender,
            )
            image_task = generate_image(
                style=style,
                sphere=sphere,
                user_text=None,
                subsphere=subsphere,
            )
            affirmations, image_path = await asyncio.gather(affirmations_task, image_task)
        except Exception as exc:
            logger.exception("Daily generation failed for user %s: %s", user_id, exc)
            continue

        text_lines = []
        name = sub.get("user_name")
        if language == "ru":
            if name:
                text_lines.append(f"{name}, твоя ежедневная аффирмация:")
            else:
                text_lines.append("Твоя ежедневная аффирмация:")
        else:
            if name:
                text_lines.append(f"{name}, your daily affirmation:")
            else:
                text_lines.append("Your daily affirmation:")

        for a in affirmations:
            text_lines.append(f"• {a}")

        caption = "\n\n".join(text_lines)

        try:
            photo = FSInputFile(image_path)
            await bot.send_photo(chat_id=user_id, photo=photo, caption=caption)
        except Exception as exc:
            logger.exception("Failed to send daily affirmation to user %s: %s", user_id, exc)


def setup_scheduler(bot: Bot) -> None:
    scheduler.add_job(send_daily_affirmations, "cron", minute="*", args=[bot])
    scheduler.start()

