import datetime as dt
import json
import logging
import os
import random

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types import FSInputFile

from config import get_image_provider_config, get_settings, get_text_provider_config
from database import get_due_subscriptions
from keyboards.inline import subscription_after_keyboard
from monitoring import (
    log_generation_fail,
    log_generation_ok,
    log_image_prompt_llm_fallback,
)
from services.generation_history import (
    build_visual_motifs,
    extract_telegram_photo_file_id,
    record_generation_history_best_effort,
)
from services.openai_image import _COLOR_MOODS, _COMPOSITION_HINTS, generate_image
from services.orchestrator_shadow import (
    attach_orchestrator_shadow_to_metadata,
    build_orchestrator_shadow_best_effort,
)
from services.scene_planner import (
    build_fallback_scene_plan,
    normalize_scene_family,
    normalize_scene_plan,
    resolve_scene_style_family,
)
from services.scene_prompt_builder import (
    build_controlled_scene_prompt,
    is_living_nature_style,
    is_scene_planner_image_prompt_enabled,
    select_photo_scene_preset_override,
    should_use_llm_image_prompt_for_fallback,
)
from services.scene_planner_shadow import (
    attach_scene_plan_shadow_to_visual_motifs,
    build_scene_plan_shadow_best_effort,
)
from services.text_planner import build_fallback_text_plan
from services.text_memory import get_text_memory_context
from services.text_prompt_builder import (
    build_text_generation_guidance,
    is_text_planner_controlled_enabled,
)
from services.text_planner_shadow import (
    attach_text_plan_shadow_to_metadata,
    build_text_plan_shadow_best_effort,
)
from services.text_reviewer_shadow import (
    attach_text_reviewer_shadow_to_metadata,
    build_text_reviewer_shadow_best_effort,
)
from services.ritual_config import (
    get_allowed_visual_modes,
    get_focus_for_date,
    get_sphere_label,
    get_weekly_balance_sphere,
    resolve_style,
    resolve_subscription_visual_mode,
    visual_mode_for_style,
)
from services.visual_memory import get_visual_memory_context
from services.yandex_gpt import build_enriched_image_prompt, generate_affirmations
from utils import gender_display

logger = logging.getLogger(__name__)

MOSCOW = pytz.timezone("Europe/Moscow")

# Планировщик в московском времени, чтобы cron срабатывал по Москве
scheduler = AsyncIOScheduler(timezone=MOSCOW)

# Кэш последних аффирмаций по подписке для кнопки «Озвучить»
last_subscription_affirmations: dict[int, dict] = {}

# Anti-repeat: last visual mode used per subscription, to avoid back-to-back repeats
_last_subscription_visual_mode: dict[int, str] = {}


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
        allowed_visual_modes = get_allowed_visual_modes(sub)
        subscription_id = sub.get("id")
        style_mode = sub.get("subscription_style_mode") or style
        visual_mode = resolve_subscription_visual_mode(
            allowed_visual_modes, style_mode, _last_subscription_visual_mode.get(subscription_id)
        )
        _last_subscription_visual_mode[subscription_id] = visual_mode
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
        style = resolve_style(style_mode, sphere, user_id=user_id, day=today, focus_key=focus["key"], visual_mode=visual_mode)
        effective_visual_mode = visual_mode_for_style(visual_mode, style)

        gender_hint = gender_display(gender, language=language)
        settings = get_settings()
        text_provider = get_text_provider_config()
        image_provider = get_image_provider_config()
        text_plan_shadow_payload = await build_text_plan_shadow_best_effort(
            sphere=sphere,
            subsphere=subsphere,
            focus_title=focus_text,
            user_custom_topic=None,
            language=language,
            recent_text_context=None,
            settings=settings,
        )
        text_plan = None
        text_memory_context = None
        if is_text_planner_controlled_enabled(settings):
            if isinstance(text_plan_shadow_payload, dict):
                candidate_text_plan = text_plan_shadow_payload.get("text_plan")
                if isinstance(candidate_text_plan, dict):
                    text_plan = candidate_text_plan
            if text_plan is None:
                text_plan = build_fallback_text_plan(
                    sphere=sphere,
                    subsphere=subsphere,
                    focus_title=focus_text,
                    user_custom_topic=None,
                    language=language,
                    recent_text_context=None,
                )
            if getattr(settings, "text_memory_context_enabled", False):
                text_memory_context = await get_text_memory_context(user_id, limit=10)
        text_plan_guidance = build_text_generation_guidance(
            text_plan=text_plan,
            language=language,
            gender_hint=gender_hint,
            text_memory_context=text_memory_context,
        )
        text_prompt_controlled_meta = None
        if text_plan_guidance:
            text_prompt_controlled_meta = {
                "enabled": True,
                "source": "text_plan_local_fallback",
                "theme_category": (text_plan or {}).get("theme_category"),
                "tone": (text_plan or {}).get("tone"),
                "guidance_used": True,
            }
        text_memory_context_meta = None
        if isinstance(text_memory_context, dict) and text_memory_context:
            text_memory_context_meta = {
                "enabled": True,
                "limit": text_memory_context.get("limit", 10),
                "overused_text_patterns": list(text_memory_context.get("overused_text_patterns") or []),
                "recent_focus_titles_count": len(text_memory_context.get("recent_focus_titles") or []),
                "avoid_soft_actions_count": len(text_memory_context.get("avoid_soft_actions") or []),
            }

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
                text_plan_guidance=text_plan_guidance,
            )
            text_reviewer_shadow_payload = build_text_reviewer_shadow_best_effort(
                affirmations=affirmations,
                soft_action=micro_step,
                focus_title=focus_text,
                language=language,
                gender_hint=gender_hint,
                text_plan=text_plan,
                text_memory_context=text_memory_context,
                settings=settings,
            )
            scene_plan_shadow_payload = await build_scene_plan_shadow_best_effort(
                telegram_user_id=user_id,
                focus_title=focus_text,
                affirmations=affirmations,
                soft_action=micro_step,
                language=language,
                settings=settings,
                selected_style=style_mode,
                resolved_style=style,
                visual_mode=effective_visual_mode,
                style_mode=style_mode,
                sphere=sphere,
                subsphere=subsphere,
            )
            color_mood = random.choice(_COLOR_MOODS)
            composition_hint = random.choice(_COMPOSITION_HINTS)
            photo_scene_preset_override = None
            scene_prompt_controlled_meta = None
            prompt_trace = "template"
            prompt_final = None
            if effective_visual_mode != "symbolic" and is_scene_planner_image_prompt_enabled(settings):
                try:
                    scene_plan = None
                    if isinstance(scene_plan_shadow_payload, dict):
                        candidate_scene_plan = scene_plan_shadow_payload.get("scene_plan")
                        if isinstance(candidate_scene_plan, dict):
                            scene_plan = candidate_scene_plan
                    if scene_plan is None:
                        visual_memory_context = await get_visual_memory_context(user_id, limit=10)
                        scene_plan = normalize_scene_plan(
                            build_fallback_scene_plan(
                                focus_title=focus_text,
                                visual_memory_context=visual_memory_context,
                                selected_style=style_mode,
                                resolved_style=style,
                                visual_mode=effective_visual_mode,
                                style_mode=style_mode,
                                sphere=sphere,
                                subsphere=subsphere,
                            ),
                            visual_memory_context=visual_memory_context,
                        )
                    prompt_final = build_controlled_scene_prompt(
                        scene_plan=scene_plan,
                        focus_title=focus_text,
                        visual_mode=effective_visual_mode,
                        selected_style=style_mode,
                        resolved_style=style,
                        color_palette=color_mood,
                        composition_hint=composition_hint,
                        sphere=sphere,
                        subsphere=subsphere,
                        language=language,
                    )
                    if prompt_final:
                        prompt_trace = "scene_planner_local"
                        photo_scene_preset_override = select_photo_scene_preset_override(
                            scene_plan=scene_plan,
                            selected_style=style_mode,
                            resolved_style=style,
                            visual_mode=effective_visual_mode,
                        )
                        scene_prompt_controlled_meta = {
                            "enabled": True,
                            "photo_scene_preset_override": photo_scene_preset_override,
                            "prompt_source": "scene_planner_local",
                            "used_scene_type": scene_plan.get("scene_type"),
                            "used_scene_family": normalize_scene_family(scene_plan.get("scene_type")),
                            "style_family": resolve_scene_style_family(
                                selected_style=style_mode,
                                resolved_style=style,
                                visual_mode=effective_visual_mode,
                                style_mode=style_mode,
                                sphere=sphere,
                                subsphere=subsphere,
                                focus_title=focus_text,
                            ),
                            "candidate_pool_name": resolve_scene_style_family(
                                selected_style=style_mode,
                                resolved_style=style,
                                visual_mode=effective_visual_mode,
                                style_mode=style_mode,
                                sphere=sphere,
                                subsphere=subsphere,
                                focus_title=focus_text,
                            ),
                            "living_nature_constraints_applied": is_living_nature_style(
                                selected_style=style_mode,
                                resolved_style=style,
                                visual_mode=effective_visual_mode,
                            ),
                        }
                except Exception:
                    logger.exception("Controlled subscription scene prompt build failed for user %s", user_id)
                    prompt_final = None
            if effective_visual_mode == "symbolic":
                prompt_final = None
                prompt_trace = "template"
            elif not prompt_final:
                prompt_final, prompt_trace = await build_enriched_image_prompt(
                    style=style,
                    sphere=sphere,
                    subsphere=subsphere,
                    user_text=None,
                    custom_style_description=None,
                    affirmations=affirmations,
                    color_mood=color_mood,
                    composition_hint=composition_hint,
                    use_llm=should_use_llm_image_prompt_for_fallback(
                        scene_planner_image_prompt_enabled=is_scene_planner_image_prompt_enabled(settings),
                        llm_image_prompt_enabled=settings.llm_image_prompt_enabled,
                    ),
                    image_hint=image_hint,
                    focus=focus_text,
                    resolved_style=style,
                    visual_mode=effective_visual_mode,
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
                visual_mode=effective_visual_mode,
                focus_key=focus["key"],
                color_mood=color_mood,
                composition_hint=composition_hint,
                photo_scene_preset_override=photo_scene_preset_override,
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
                text_lines.append(f"{name}, your daily focus 🌿")
            else:
                text_lines.append("Your daily focus 🌿")

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
        image_meta = {}
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta["affirmations"] = affirmations
                meta["theme_text"] = None
                meta["gender"] = gender
                meta["source"] = "subscription"
                meta["subscription_mode"] = subscription_mode
                meta["visual_mode"] = effective_visual_mode
                meta["focus"] = focus
                meta["focus_key"] = focus["key"]
                meta["micro_step"] = micro_step
                meta["style_mode"] = style_mode
                meta["requested_style"] = style_mode
                meta["selected_style"] = style
                meta["color_palette"] = color_mood
                meta["composition_hint"] = composition_hint
                image_meta = meta
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
            "visual_mode": visual_mode,
        }

        try:
            photo = FSInputFile(image_path)
            keyboard = subscription_after_keyboard(language)
            sent_message = await bot.send_photo(
                chat_id=user_id,
                photo=photo,
                caption=caption,
                reply_markup=keyboard,
            )
            log_generation_ok(user_id, "subscription", prompt_trace)
            scene_type = image_meta.get("scene_preset") or image_meta.get("photo_scene_preset")
            telegram_image_file_id = extract_telegram_photo_file_id(sent_message)
            visual_motifs = build_visual_motifs(
                image_meta=image_meta,
                visual_mode=effective_visual_mode,
                selected_style=style,
                color_palette=color_mood,
                composition_hint=composition_hint,
                sphere=sphere,
                subsphere=subsphere,
            )
            visual_motifs = attach_scene_plan_shadow_to_visual_motifs(
                visual_motifs,
                scene_plan_shadow_payload,
            )
            visual_motifs = attach_text_plan_shadow_to_metadata(
                visual_motifs,
                text_plan_shadow_payload,
            )
            visual_motifs = attach_text_reviewer_shadow_to_metadata(
                visual_motifs,
                text_reviewer_shadow_payload,
            )
            if scene_prompt_controlled_meta is not None:
                visual_motifs["scene_prompt_controlled"] = scene_prompt_controlled_meta
            if text_prompt_controlled_meta is not None:
                visual_motifs["text_prompt_controlled"] = text_prompt_controlled_meta
            if text_memory_context_meta is not None:
                visual_motifs["text_memory_context"] = text_memory_context_meta
            orchestrator_shadow_payload = build_orchestrator_shadow_best_effort(
                settings=settings,
                language=language,
                sphere=sphere,
                subsphere=subsphere,
                focus_title=focus_text,
                selected_style=style,
                visual_mode=effective_visual_mode,
                text_plan_shadow=text_plan_shadow_payload,
                text_prompt_controlled=text_prompt_controlled_meta,
                text_memory_context=text_memory_context,
                text_reviewer_shadow=text_reviewer_shadow_payload,
                scene_plan_shadow=scene_plan_shadow_payload,
                scene_prompt_controlled=scene_prompt_controlled_meta,
            )
            visual_motifs = attach_orchestrator_shadow_to_metadata(visual_motifs, orchestrator_shadow_payload)
            await record_generation_history_best_effort(
                telegram_user_id=user_id,
                request_type="subscription",
                focus_title=focus_text,
                affirmations=affirmations,
                soft_action=micro_step,
                text_model=getattr(text_provider, "model", None),
                image_model=getattr(image_provider, "model", None),
                image_prompt=prompt_final,
                telegram_image_file_id=telegram_image_file_id,
                scene_type=scene_type,
                visual_motifs=visual_motifs,
            )
            logger.info("Sent daily affirmation to user %s with TTS button", user_id)
        except Exception as exc:
            logger.exception("Failed to send daily affirmation to user %s: %s", user_id, exc)
            log_generation_fail(user_id, "subscription", "send", str(exc))


def setup_scheduler(bot: Bot) -> None:
    scheduler.add_job(send_daily_affirmations, "cron", minute="*", args=[bot])
    scheduler.start()

