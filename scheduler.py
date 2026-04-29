import datetime as dt
import json
import logging
import os
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
from services.ritual_config import (
    get_focus_for_date,
    get_sphere_label,
    get_weekly_balance_sphere,
    resolve_style,
)
from services.yandex_gpt import build_enriched_image_prompt, generate_affirmations
from utils import gender_display

logger = logging.getLogger(__name__)

MOSCOW = ZoneInfo("Europe/Moscow")

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
        subscription_mode = sub.get("subscription_mode") or ("weekly_balance" if sphere == "random" else "sphere_focus")
        today = now.date()

        if subscription_mode == "weekly_balance" or sphere == "random":
            sphere = get_weekly_balance_sphere(user_id, today)
            subsphere = None
        else:
            sphere = sub.get("subscription_sphere") or sphere

        focus = get_focus_for_date(user_id, sphere, today)
        focus_text = focus["en"] if language == "en" else focus["ru"]
        micro_step = focus["micro_step_en"] if language == "en" else focus["micro_step_ru"]
        image_hint = focus.get("image_hint_en")
        style_mode = sub.get("subscription_style_mode") or style
        style = resolve_style(style_mode, sphere, user_id=user_id, day=today, focus_key=focus["key"])

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
                focus=focus_text,
                micro_theme=micro_step,
                sphere_label=get_sphere_label(sphere, language),
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
                image_hint=image_hint,
                focus=focus_text,
                resolved_style=style,
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
                image_hint=image_hint,
                resolved_style_override=style,
                focus_key=focus["key"],
                color_mood=color_mood,
                composition_hint=composition_hint,
            )
        except Exception as exc:
            logger.exception("Daily generation failed for user %s: %s", user_id, exc)
            log_generation_fail(user_id, "subscription", "daily", str(exc))
            continue

        text_lines = []
        name = sub.get("user_name")
        if language == "ru":
            if name:
                text_lines.append(f"{name}, твой настрой на сегодня 🌿")
            else:
                text_lines.append("Твой настрой на сегодня 🌿")
        else:
            if name:
                text_lines.append(f"{name}, your focus for today 🌿")
            else:
                text_lines.append("Your focus for today 🌿")

        if language == "ru":
            text_lines.append(f"Фокус дня: {focus_text}")
        else:
            text_lines.append(f"Focus of the day: {focus_text}")

        for a in affirmations:
            text_lines.append(f"• {a}")

        if language == "ru":
            text_lines.append(f"Мягкий шаг дня:\n{micro_step}")
        else:
            text_lines.append(f"Gentle step of the day:\n{micro_step}")

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
                meta["subscription_mode"] = subscription_mode
                meta["focus"] = focus
                meta["focus_key"] = focus["key"]
                meta["micro_step"] = micro_step
                meta["style_mode"] = style_mode
                meta["requested_style"] = style_mode
                meta["selected_style"] = style
                meta["color_palette"] = color_mood
                meta["composition_hint"] = composition_hint
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning("Could not update subscription meta %s: %s", meta_path, e)

        last_subscription_affirmations[user_id] = {
            "affirmations": affirmations,
            "gender": gender,
            "language": language,
            "sphere": sphere,
            "subsphere": subsphere,
            "style": style,
            "style_mode": style_mode,
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

