"""Scheduled daily deliveries: tick, claim, generate, send, confirm.

Delivery contract
-----------------
* A *logical delivery* is one subscription's ritual for one calendar day, identified by
  ``(subscription_id, delivery_date)`` with the date taken in MOSCOW (the scheduler's
  timezone). It is tracked in the durable ``subscription_deliveries`` ledger; nothing
  about correctness lives in process memory.
* Every tick recomputes what is due from the database. A slot is due from its scheduled
  minute until CATCHUP_WINDOW later, so a missed tick, a long tick or a restart does not
  lose a delivery, and an outage longer than the window does not produce stale rituals.
* An attempt first *claims* the delivery with one atomic statement (unique key + guarded
  UPDATE). Only one claimant wins, so overlapping ticks or an accidental second process
  cannot process the same delivery concurrently - *provided* the claim is not stolen out
  from under a still-running attempt. That in turn requires the whole attempt to finish
  well inside CLAIM_LEASE; see ATTEMPT_TIMEOUT_SECONDS below and the assertion pinning
  that relationship. The claim also fixes the visual mode.
* ``sent`` is recorded right after Telegram accepts the message and is terminal: a
  completed delivery is never generated or sent again.
* An attempt that fails before Telegram confirms (text, image, send) is released as
  ``failed`` and retried after RETRY_BACKOFF, at most MAX_DELIVERY_ATTEMPTS times inside
  the window. A permanent Telegram error (bot blocked) is abandoned at once.
* Due deliveries run concurrently, bounded by SCHEDULER_MAX_CONCURRENCY; a failure in one
  never affects another.

Not guaranteed: exactly-once. Telegram cannot be enlisted in the database transaction,
so if the process dies (or the ledger write fails) after Telegram accepted the message
but before ``sent`` is stored, the claim expires after CLAIM_LEASE and the delivery is
retried, which sends it again. Likewise a send that times out on the client side may
already have been delivered. Duplicates are limited to that window; a silent miss is
treated as the worse failure for a daily ritual.
"""
import asyncio
import datetime as dt
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import FSInputFile

from config import (
    get_image_provider_config,
    get_scheduler_max_concurrency,
    get_settings,
    get_text_provider_config,
)
from database import (
    claim_subscription_delivery,
    get_active_subscriptions_for_delivery,
    get_last_sent_visual_mode,
    get_subscription_deliveries,
    mark_subscription_delivery_failed,
    mark_subscription_delivery_sent,
)
from keyboards.inline import subscription_after_keyboard
from monitoring import (
    log_delivery_event,
    log_generation_fail,
    log_generation_ok,
    log_image_prompt_llm_fallback,
)
from services.delivery_schedule import (
    CATCHUP_LOG_THRESHOLD,
    CATCHUP_WINDOW,
    CLAIM_LEASE,
    MAX_DELIVERY_ATTEMPTS,
    RETRY_BACKOFF,
    DueDelivery,
    candidate_delivery_dates,
    find_due_deliveries,
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
    effective_subscription_style_mode,
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

MOSCOW = ZoneInfo("Europe/Moscow")

# Планировщик в московском времени, чтобы cron срабатывал по Москве
scheduler = AsyncIOScheduler(timezone=MOSCOW)

# Кэш последних аффирмаций по подписке для кнопки «Озвучить»
last_subscription_affirmations: dict[int, dict] = {}

# Safety net for one whole attempt (generation + send), from just after the claim to just
# before the post-send bookkeeping. Provider calls carry their own timeouts (text 60s,
# image 240s by default); this only bounds a pathological hang so a stuck delivery cannot
# hold a concurrency slot - or its claim - forever.
ATTEMPT_TIMEOUT_SECONDS = 600
# The claim-lease safety invariant: a claim is only ever reclaimed once CLAIM_LEASE has
# elapsed since it was made (see services.delivery_schedule / database.claim_subscription_
# delivery), so an attempt that is still genuinely running must never be allowed to run
# longer than CLAIM_LEASE, or its claim could be stolen while it is still in flight -
# producing exactly the duplicate-send-from-two-workers scenario the ledger exists to
# prevent. ATTEMPT_TIMEOUT_SECONDS bounds the only unbounded part of that duration (the
# work inside _deliver_subscription, wrapped below in asyncio.wait_for), so it is what
# actually has to stay under CLAIM_LEASE - not just "should". The margin below absorbs the
# small extra gap between claimed_at being set and wait_for's timer starting (the claim's
# own DB round-trip plus a little synchronous bookkeeping); it is headroom, not itself
# load-bearing for correctness.
_LEASE_SAFETY_MARGIN_SECONDS = 60
assert ATTEMPT_TIMEOUT_SECONDS + _LEASE_SAFETY_MARGIN_SECONDS <= CLAIM_LEASE.total_seconds(), (
    "ATTEMPT_TIMEOUT_SECONDS must stay well below CLAIM_LEASE, or a still-running attempt's "
    "claim could be stolen before it finishes"
)
# APScheduler: one tick at a time (the ledger makes overlapping ticks unnecessary), late
# ticks are merged into one, and a tick delayed by up to a minute still runs. Recovery of
# missed slots is the ledger's job, not APScheduler's misfire handling.
SCHEDULER_MISFIRE_GRACE_SECONDS = 60
# Confirming `sent` is the one write that must not be lost after Telegram accepted the message.
_COMPLETION_WRITE_ATTEMPTS = 3
_COMPLETION_WRITE_RETRY_DELAY_SECONDS = 0.5

# Outputs cleanup: a background sweep of old generated/temp files (see cleanup_outputs.py),
# unrelated to the delivery ledger above. Runs on this same scheduler as its own job with its
# own id so it cannot collide with `daily_affirmations`. Hours/day cadence is plenty for a
# retention window measured in days, so this is a plain constant rather than a new setting.
OUTPUTS_CLEANUP_INTERVAL_HOURS = 6
OUTPUTS_CLEANUP_MISFIRE_GRACE_SECONDS = 900

_STAGE_GENERATION = "generation"
_STAGE_SEND = "send"
_STAGE_POST_SEND = "post_send"


@dataclass
class _Attempt:
    """Where an in-flight delivery attempt is, to classify a failure afterwards."""

    stage: str = _STAGE_GENERATION


async def send_daily_affirmations(bot: Bot, now: dt.datetime | None = None) -> None:
    """One scheduler tick: attempt every subscription delivery that is due at ``now``."""
    now = now or dt.datetime.now(MOSCOW)
    try:
        due = await _find_due_deliveries(now)
    except Exception:
        logger.exception("Could not determine due subscription deliveries")
        return
    if not due:
        return

    concurrency = get_scheduler_max_concurrency()
    log_delivery_event("tick", moscow_time=now.strftime("%H:%M"), due=len(due), concurrency=concurrency)

    # Timestamps written by a delivery follow the tick's clock as it advances, so work
    # that waited for a free slot is not recorded as if it had started at the tick start.
    tick_started = time.monotonic()

    def clock() -> dt.datetime:
        return now + dt.timedelta(seconds=time.monotonic() - tick_started)

    semaphore = asyncio.Semaphore(concurrency)

    async def run_one(item: DueDelivery) -> None:
        # The claim happens inside the slot, so a queued delivery is not "in progress".
        async with semaphore:
            await _process_due_delivery(bot, item, clock)

    results = await asyncio.gather(*(run_one(item) for item in due), return_exceptions=True)
    for item, result in zip(due, results):
        if isinstance(result, Exception):
            logger.error(
                "Unexpected error processing subscription %s", item.subscription_id, exc_info=result
            )


async def _find_due_deliveries(now: dt.datetime) -> list[DueDelivery]:
    subscriptions = await get_active_subscriptions_for_delivery()
    if not subscriptions:
        return []
    ledger_rows = await get_subscription_deliveries(candidate_delivery_dates(now))
    return find_due_deliveries(
        subscriptions,
        ledger_rows,
        now,
        window=CATCHUP_WINDOW,
        max_attempts=MAX_DELIVERY_ATTEMPTS,
        retry_backoff=RETRY_BACKOFF,
        lease=CLAIM_LEASE,
    )


async def _resolve_delivery_visual_mode(due: DueDelivery) -> str:
    """Visual mode for this logical delivery.

    An existing ledger row already fixed it, so retries, catch-ups and restarts keep it
    (unless the user has since removed that mode from the subscription). A new delivery
    picks with anti-repeat against the last *confirmed* delivery; the pick is persisted
    by the claim, which makes it the delivery's mode from then on.
    """
    sub = due.subscription
    allowed_visual_modes = get_allowed_visual_modes(sub)
    persisted = (due.ledger_row or {}).get("visual_mode")
    if persisted in allowed_visual_modes:
        return persisted
    style_mode = effective_subscription_style_mode(
        allowed_visual_modes, sub.get("subscription_style_mode") or sub["image_style"]
    )
    last_sent_mode = None
    if len(allowed_visual_modes) > 1:
        last_sent_mode = await get_last_sent_visual_mode(sub["id"], due.delivery_date.isoformat())
    return resolve_subscription_visual_mode(allowed_visual_modes, style_mode, last_sent_mode)


async def _process_due_delivery(bot: Bot, due: DueDelivery, clock) -> None:
    """Claim one due delivery, run it, and record the outcome. Never raises."""
    sub = due.subscription
    user_id = sub["user_id"]
    fields = {
        "subscription_id": sub["id"],
        "user_id": user_id,
        "delivery_date": due.delivery_date.isoformat(),
    }
    try:
        visual_mode = await _resolve_delivery_visual_mode(due)
        delivery = await claim_subscription_delivery(
            subscription_id=sub["id"],
            user_id=user_id,
            delivery_date=fields["delivery_date"],
            visual_mode=visual_mode,
            now=clock(),
            max_attempts=MAX_DELIVERY_ATTEMPTS,
            retry_backoff=RETRY_BACKOFF,
            lease=CLAIM_LEASE,
        )
    except Exception:
        # Nothing was sent; the next tick sees the same due delivery and tries again.
        logger.exception("Could not claim subscription delivery %s", fields)
        return
    if delivery is None:
        log_delivery_event("skipped", reason="not_claimable", **fields)
        return

    lateness = clock() - due.scheduled_at
    log_delivery_event(
        "claimed",
        attempt=delivery["attempts"],
        visual_mode=delivery["visual_mode"],
        catchup=lateness >= CATCHUP_LOG_THRESHOLD,
        late_minutes=int(lateness.total_seconds() // 60),
        **fields,
    )
    attempt = _Attempt()
    try:
        await asyncio.wait_for(
            _deliver_subscription(bot, sub, delivery, due.delivery_date, attempt, clock),
            timeout=ATTEMPT_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        await _release_failed_attempt(delivery, attempt, exc, clock, fields)
        return
    log_delivery_event("completed", attempt=delivery["attempts"], **fields)


def _is_permanent_send_error(exc: Exception) -> bool:
    # The user blocked the bot / deactivated the account: retrying cannot succeed and
    # every retry would spend a paid image generation.
    return isinstance(exc, TelegramForbiddenError)


async def _release_failed_attempt(delivery: dict, attempt: _Attempt, exc: Exception, clock, fields: dict) -> None:
    if attempt.stage == _STAGE_POST_SEND:
        # Telegram already accepted the message; the ledger must not say otherwise.
        logger.error("Delivery %s errored after the message was sent", fields, exc_info=exc)
        return
    step = "send" if attempt.stage == _STAGE_SEND else "daily"
    logger.error(
        "Subscription delivery failed at %s stage for user %s: %s",
        attempt.stage,
        fields["user_id"],
        exc,
        exc_info=exc,
    )
    log_generation_fail(fields["user_id"], "subscription", step, str(exc) or type(exc).__name__)
    permanent = _is_permanent_send_error(exc)
    retryable = not permanent and delivery["attempts"] < MAX_DELIVERY_ATTEMPTS
    try:
        await mark_subscription_delivery_failed(
            delivery["id"],
            delivery["attempts"],
            f"{attempt.stage}: {type(exc).__name__}: {exc}",
            retryable=retryable,
            now=clock(),
        )
    except Exception:
        # The claim simply expires after CLAIM_LEASE and the delivery is retried then.
        logger.exception("Could not record failed attempt for %s", fields)
    log_delivery_event(
        "failed",
        stage=attempt.stage,
        attempt=delivery["attempts"],
        retryable=retryable,
        error=type(exc).__name__,
        **fields,
    )


async def _confirm_delivery_sent(delivery: dict, clock) -> None:
    """Persist ``sent``; retried briefly because losing it risks a duplicate later."""
    for attempt_number in range(1, _COMPLETION_WRITE_ATTEMPTS + 1):
        try:
            await mark_subscription_delivery_sent(delivery["id"], clock())
            return
        except Exception:
            logger.exception(
                "Could not record delivery %s as sent (write %s/%s)",
                delivery["id"],
                attempt_number,
                _COMPLETION_WRITE_ATTEMPTS,
            )
            if attempt_number < _COMPLETION_WRITE_ATTEMPTS:
                await asyncio.sleep(_COMPLETION_WRITE_RETRY_DELAY_SECONDS)
    logger.error(
        "Delivery %s (user %s, %s) WAS SENT but could not be recorded; it may be re-sent after the claim expires",
        delivery["id"],
        delivery["user_id"],
        delivery["delivery_date"],
    )


async def _deliver_subscription(
    bot: Bot,
    sub: dict,
    delivery: dict,
    delivery_date: dt.date,
    attempt: _Attempt,
    clock,
) -> None:
    """Generate and send one claimed delivery. Raises on any failure before Telegram confirms."""
    user_id = sub["user_id"]
    sphere = sub["sphere"]
    subsphere = sub.get("subsphere")
    style = sub["image_style"]
    language = sub["language"]
    gender = sub.get("user_gender")
    subscription_mode = sub.get("subscription_mode") or ("weekly_balance" if sphere == "random" else "sphere_focus")
    allowed_visual_modes = get_allowed_visual_modes(sub)
    # A multi-mode pool or a style from another mode must not leak a concrete
    # style downstream; the rest of the run only sees the effective style mode.
    style_mode = effective_subscription_style_mode(
        allowed_visual_modes, sub.get("subscription_style_mode") or style
    )
    # The mode was fixed when this logical delivery was first claimed (ledger row),
    # so a retry, a catch-up or a restart generates the same kind of image.
    visual_mode = delivery["visual_mode"]
    today = delivery_date

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

    attempt.stage = _STAGE_SEND
    photo = FSInputFile(image_path)
    keyboard = subscription_after_keyboard(language)
    sent_message = await bot.send_photo(
        chat_id=user_id,
        photo=photo,
        caption=caption,
        reply_markup=keyboard,
    )
    # The message is out. Persist that before any bookkeeping that could fail.
    attempt.stage = _STAGE_POST_SEND
    await _confirm_delivery_sent(delivery, clock)
    try:
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
    except Exception:
        logger.exception("Post-send bookkeeping failed for user %s; the message was delivered", user_id)


async def _run_outputs_cleanup_job() -> None:
    """APScheduler job wrapper: cleanup_outputs.run_outputs_cleanup already isolates its own
    errors and never raises, but a scheduled job must never be able to take the process down
    regardless, so this stays defensive too."""
    try:
        from cleanup_outputs import run_outputs_cleanup

        await run_outputs_cleanup()
    except Exception:
        logger.exception("Outputs cleanup job failed")


def setup_scheduler(bot: Bot) -> None:
    scheduler.add_job(
        send_daily_affirmations,
        "cron",
        minute="*",
        args=[bot],
        id="daily_affirmations",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=SCHEDULER_MISFIRE_GRACE_SECONDS,
    )
    scheduler.add_job(
        _run_outputs_cleanup_job,
        "interval",
        hours=OUTPUTS_CLEANUP_INTERVAL_HOURS,
        id="outputs_cleanup",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=OUTPUTS_CLEANUP_MISFIRE_GRACE_SECONDS,
    )
    scheduler.start()
