import datetime as dt
import json
import logging
import os
import random
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types import FSInputFile

from config import get_settings
from database import get_due_subscriptions
from keyboards.inline import subscription_after_keyboard
from monitoring import (
    log_generation_fail,
    log_generation_ok,
    log_image_prompt_llm_fallback,
)
from services.openai_image import _COLOR_MOODS, _COMPOSITION_HINTS, generate_image
from services.yandex_gpt import build_enriched_image_prompt, generate_affirmations
from utils import build_focus_of_day, gender_display

logger = logging.getLogger(__name__)

MOSCOW = ZoneInfo("Europe/Moscow")

# Сферы для опции «разные сферы каждый день»
SUBSCRIPTION_SPHERES = [
    "career",
    "health",
    "money",
    "relationships",
    "self_realization",
    "spirituality",
    "inner_peace",
]

# Подсферы для relationships (при случайной сфере)
RELATIONSHIP_SUBSPHERES = ["partner", "colleagues", "friends"]

# Стили для опции «разный стиль каждый день»
SUBSCRIPTION_STYLES = [
    "realistic",
    "cartoon",
    "mandala",
    "sacred_geometry",
    "nature",
    "cosmos",
    "abstract",
]

# Планировщик в московском времени, чтобы cron срабатывал по Москве
scheduler = AsyncIOScheduler(timezone=MOSCOW)

# Кэш последних аффирмаций по подписке для кнопки «Озвучить»
last_subscription_affirmations: dict[int, dict] = {}


async def send_daily_affirmations(bot: Bot) -> None:
    now = dt.datetime.now(MOSCOW)
    subs = await get_due_subscriptions(now)
    if not subs:
        return
    logger.info("Subscription run at Moscow time %s, sending to %s user(s)", now.strftime("%H:%M"), len(subs))

    for sub in subs:
        user_id = sub["user_id"]
        sphere = sub["sphere"]
        subsphere = sub.get("subsphere")
        style = sub["image_style"]
        language = sub["language"]
        gender = sub.get("user_gender")

        # Опция «разные сферы каждый день»: выбираем сферу случайно
        if sphere == "random":
            sphere = random.choice(SUBSCRIPTION_SPHERES)
            subsphere = random.choice(RELATIONSHIP_SUBSPHERES) if sphere == "relationships" else None
        # Опция «разный стиль каждый день»: выбираем стиль случайно
        if style == "random":
            style = random.choice(SUBSCRIPTION_STYLES)

        gender_hint = gender_display(gender, language=language)
        settings = get_settings()

        try:
            affirmations = await generate_affirmations(
                sphere=sphere,
                language=language,
                user_text=None,
                subsphere=subsphere,
                gender_hint=gender_hint,
                gender=gender,
            )
            color_mood = random.choice(_COLOR_MOODS)
            composition_hint = random.choice(_COMPOSITION_HINTS)
            prompt_final, prompt_trace = await build_enriched_image_prompt(
                style=style,
                sphere=sphere,
                subsphere=subsphere,
                user_text=None,
                custom_style_description=None,
                affirmations=affirmations,
                color_mood=color_mood,
                composition_hint=composition_hint,
                use_llm=settings.llm_image_prompt_enabled,
            )
            if prompt_trace == "template_fallback":
                log_image_prompt_llm_fallback("subscription_llm_fallback")
            image_path = await generate_image(
                style=style,
                sphere=sphere,
                user_text=None,
                subsphere=subsphere,
                custom_style_description=None,
                prompt_override=prompt_final,
                image_prompt_trace=prompt_trace,
            )
        except Exception as exc:
            logger.exception("Daily generation failed for user %s: %s", user_id, exc)
            log_generation_fail(user_id, "subscription", "daily", str(exc))
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

        focus = build_focus_of_day(sphere, language=language, subsphere=subsphere)
        if language == "ru":
            text_lines.append(f"Фокус дня: {focus}")
        else:
            text_lines.append(f"Focus of the day: {focus}")

        for a in affirmations:
            text_lines.append(f"• {a}")

        caption = "\n\n".join(text_lines)

        meta_path = image_path.replace(".png", "_meta.json")
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta["affirmations"] = affirmations
                meta["theme_text"] = None
                meta["gender"] = gender
                meta["source"] = "subscription"
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning("Could not update subscription meta %s: %s", meta_path, e)

        last_subscription_affirmations[user_id] = {
            "affirmations": affirmations,
            "gender": gender,
        }

        try:
            photo = FSInputFile(image_path)
            keyboard = subscription_after_keyboard(language)
            await bot.send_photo(
                chat_id=user_id,
                photo=photo,
                caption=caption,
                reply_markup=keyboard,
            )
            log_generation_ok(user_id, "subscription", prompt_trace)
            logger.info("Sent daily affirmation to user %s with TTS button", user_id)
        except Exception as exc:
            logger.exception("Failed to send daily affirmation to user %s: %s", user_id, exc)
            log_generation_fail(user_id, "subscription", "send", str(exc))


def setup_scheduler(bot: Bot) -> None:
    scheduler.add_job(send_daily_affirmations, "cron", minute="*", args=[bot])
    scheduler.start()

