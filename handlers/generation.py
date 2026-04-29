import json
import datetime as dt
import logging
import os
import random
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message, PhotoSize

from config import get_outputs_dir, get_settings
from database import can_start_interactive_generation, get_user, record_interactive_generation
from keyboards.inline import (
    after_generation_keyboard,
    relationships_subsphere_keyboard,
    sphere_keyboard,
    style_cancel_keyboard,
    style_keyboard,
    theme_early_cancel_keyboard,
    visual_mode_keyboard,
)
from monitoring import (
    log_generation_fail,
    log_generation_ok,
    log_image_prompt_llm_fallback,
    log_rate_limited,
)
from services.openai_image import _COLOR_MOODS, _COMPOSITION_HINTS, generate_image
from services.ritual_config import (
    get_focus_for_date,
    get_sphere_label,
    is_tts_available,
    normalize_visual_mode,
    resolve_style,
    visual_mode_for_style,
)
from services.speechkit import transcribe_audio
from services.speechkit_tts import synthesize_affirmations_with_pauses
from services.yandex_gpt import build_enriched_image_prompt, generate_affirmations
from states import GenerationState
from utils import gender_display

router = Router()
logger = logging.getLogger(__name__)


def _new_flow_text(language: str) -> str:
    if language == "ru":
        return "🌿 Что создаём?\n\nВыбери сферу, для которой собрать настрой дня:"
    return "🌿 What shall we create?\n\nChoose an area for your daily focus:"


def _visual_mode_text(language: str) -> str:
    return "🎨 Какой визуал тебе ближе?" if language == "ru" else "🎨 Which visual style feels closer to you?"


def _style_choice_text(language: str) -> str:
    return "✨ Выбери стиль изображения:" if language == "ru" else "✨ Choose image style:"


def _creating_text(language: str) -> str:
    return "🌿 Создаю твой настрой дня..." if language == "ru" else "🌿 Creating your daily focus..."


@router.callback_query(F.data == "cmd:new")
async def cb_new_affirmation(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка кнопки создания нового настроя дня после регистрации."""
    await callback.answer()
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    await state.clear()
    await state.update_data(theme_text=None)
    await state.set_state(GenerationState.choosing_sphere)
    await callback.message.answer(
        _new_flow_text(language),
        reply_markup=sphere_keyboard(language),
    )


@router.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    await state.clear()
    await state.update_data(theme_text=None)
    await state.set_state(GenerationState.choosing_sphere)
    await message.answer(
        _new_flow_text(language),
        reply_markup=sphere_keyboard(language),
    )


@router.callback_query(GenerationState.choosing_sphere, F.data == "sphere:custom_theme")
async def choose_custom_theme_early(callback: CallbackQuery, state: FSMContext) -> None:
    """Своя тема в меню сферы: запрос текста или голоса."""
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    await state.set_state(GenerationState.waiting_for_theme_early)
    await callback.message.edit_text(
        (
            "Напиши свою тему или отправь голосовое сообщение."
            if language == "ru"
            else "Type your theme or send a voice message."
        ),
        reply_markup=theme_early_cancel_keyboard(language),
    )
    await callback.answer()


@router.callback_query(GenerationState.waiting_for_theme_early, F.data == "theme_early:cancel")
async def theme_early_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    await state.set_state(GenerationState.choosing_sphere)
    await callback.message.edit_text(
        _new_flow_text(language),
        reply_markup=sphere_keyboard(language),
    )
    await callback.answer()


@router.message(GenerationState.waiting_for_theme_early, F.voice)
async def handle_voice_theme_early(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    voice = message.voice
    if not voice:
        return
    file = await message.bot.get_file(voice.file_id)
    dest_dir = get_outputs_dir()
    os.makedirs(dest_dir, exist_ok=True)
    local_path = os.path.join(dest_dir, f"voice_theme_{message.from_user.id}_{voice.file_unique_id}.ogg")
    await message.bot.download_file(file.file_path, destination=local_path)
    try:
        recognized = await transcribe_audio(local_path, language=language)
    except Exception as exc:
        logger.exception("STT failed (theme early): %s", exc)
        await message.answer(
            "Не удалось распознать голос. Напиши текстом." if language == "ru" else "Could not recognize. Please type."
        )
        return
    await state.update_data(theme_text=recognized, sphere="inner_peace", subsphere=None)
    await state.set_state(GenerationState.choosing_visual_mode)
    await message.answer(
        (f"Тема: «{recognized}».\n\n{_visual_mode_text(language)}" if language == "ru" else f"Theme: “{recognized}”.\n\n{_visual_mode_text(language)}"),
        reply_markup=visual_mode_keyboard(language),
    )


@router.message(GenerationState.waiting_for_theme_early, F.text)
async def handle_text_theme_early(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    text = (message.text or "").strip()
    if not text:
        await message.answer("Напиши тему или нажми «Отмена»." if language == "ru" else "Type your theme or press Cancel.")
        return
    await state.update_data(theme_text=text, sphere="inner_peace", subsphere=None)
    await state.set_state(GenerationState.choosing_visual_mode)
    await message.answer(
        (f"Тема: «{text}».\n\n{_visual_mode_text(language)}" if language == "ru" else f"Theme: “{text}”.\n\n{_visual_mode_text(language)}"),
        reply_markup=visual_mode_keyboard(language),
    )


@router.callback_query(GenerationState.choosing_sphere, F.data.startswith("sphere:"))
async def choose_sphere(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data == "sphere:custom_theme":
        return
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    sphere = callback.data.split(":", maxsplit=1)[1]

    await state.update_data(sphere=sphere)

    if sphere == "relationships":
        await state.set_state(GenerationState.choosing_relationship_subsphere)
        await callback.message.edit_text(
            "Уточни, пожалуйста:" if language == "ru" else "Please specify:",
            reply_markup=relationships_subsphere_keyboard(language),
        )
    else:
        await state.set_state(GenerationState.choosing_visual_mode)
        await callback.message.edit_text(
            _visual_mode_text(language),
            reply_markup=visual_mode_keyboard(language),
        )
    await callback.answer()


@router.callback_query(GenerationState.choosing_relationship_subsphere, F.data.startswith("subsphere:"))
async def choose_relationship_subsphere(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    subsphere = callback.data.split(":", maxsplit=1)[1]

    await state.update_data(subsphere=subsphere)
    await state.set_state(GenerationState.choosing_visual_mode)
    await callback.message.edit_text(
        _visual_mode_text(language),
        reply_markup=visual_mode_keyboard(language),
    )
    await callback.answer()


@router.callback_query(GenerationState.choosing_visual_mode, F.data.startswith("visual:"))
async def choose_visual_mode(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    visual_mode = normalize_visual_mode(callback.data.split(":", maxsplit=1)[1])
    await state.update_data(visual_mode=visual_mode)
    await state.set_state(GenerationState.choosing_style)
    await callback.message.edit_text(
        _style_choice_text(language),
        reply_markup=style_keyboard(language, visual_mode=visual_mode),
    )
    await callback.answer()


@router.callback_query(GenerationState.choosing_style, F.data == "style:custom")
async def choose_custom_style(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    await state.update_data(style="custom")
    await state.set_state(GenerationState.waiting_for_custom_style)
    await callback.message.edit_text(
        (
            "Опиши желаемый стиль изображения текстом или отправь голосовое сообщение."
            if language == "ru"
            else "Describe the desired image style in text or send a voice message."
        ),
        reply_markup=style_cancel_keyboard(language),
    )
    await callback.answer()


@router.callback_query(GenerationState.choosing_style, F.data.startswith("style:"))
async def choose_style(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data == "style:custom":
        return
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    style = callback.data.split(":", maxsplit=1)[1]
    await state.update_data(style=style, custom_style_description=None)
    data = await state.get_data()
    await callback.message.edit_text(
        _creating_text(language)
    )
    await callback.answer()
    await _run_generation(callback.message, state, theme_text=data.get("theme_text"), user_telegram_id=callback.from_user.id)


@router.callback_query(GenerationState.waiting_for_custom_style, F.data == "style:cancel")
async def cancel_custom_style(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    await state.set_state(GenerationState.choosing_style)
    await callback.message.edit_text(
        _style_choice_text(language),
        reply_markup=style_keyboard(language, visual_mode=(await state.get_data()).get("visual_mode", "illustration")),
    )
    await callback.answer()


@router.message(GenerationState.waiting_for_custom_style, F.voice)
async def handle_voice_custom_style(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    voice = message.voice
    if not voice:
        return
    file = await message.bot.get_file(voice.file_id)
    dest_dir = get_outputs_dir()
    os.makedirs(dest_dir, exist_ok=True)
    local_path = os.path.join(dest_dir, f"voice_style_{message.from_user.id}_{voice.file_unique_id}.ogg")
    await message.bot.download_file(file.file_path, destination=local_path)
    try:
        recognized = await transcribe_audio(local_path, language=language)
    except Exception as exc:
        logger.exception("STT failed for custom style: %s", exc)
        await message.answer(
            "Не удалось распознать голос. Напиши текстом." if language == "ru" else "Could not recognize. Please type."
        )
        return
    await state.update_data(custom_style_description=recognized)
    data = await state.get_data()
    await message.answer(_creating_text(language))
    await _run_generation(message, state, theme_text=data.get("theme_text"))


@router.message(GenerationState.waiting_for_custom_style, F.text)
async def handle_text_custom_style(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    text = (message.text or "").strip()
    if not text:
        await message.answer("Напиши описание стиля или нажми «Отмена»." if language == "ru" else "Type style description or press Cancel.")
        return
    await state.update_data(custom_style_description=text)
    data = await state.get_data()
    await message.answer(_creating_text(language))
    await _run_generation(message, state, theme_text=data.get("theme_text"))






async def _run_generation(
    message: Message,
    state: FSMContext,
    theme_text: Optional[str],
    *,
    user_telegram_id: Optional[int] = None,
) -> None:
    """
    user_telegram_id: обязателен для вызовов из callback под сообщением бота (там message.from_user — бот, не человек).
    """
    uid = user_telegram_id if user_telegram_id is not None else message.from_user.id
    user = await get_user(uid)
    language = (user or {}).get("language", "ru")
    gender = (user or {}).get("gender")
    data = await state.get_data()
    settings = get_settings()

    sphere = data.get("sphere")
    subsphere = data.get("subsphere")
    style = data.get("style") or "nature"
    visual_mode = normalize_visual_mode(data.get("visual_mode"))
    custom_style_description = data.get("custom_style_description")

    if not sphere:
        await message.answer("Что-то пошло не так, попробуй начать заново с /new.")
        await state.clear()
        return

    limit_enabled = not settings.disable_daily_generation_limit and settings.generation_daily_limit > 0
    if limit_enabled:
        allowed, used = await can_start_interactive_generation(uid, settings.generation_daily_limit)
        if not allowed:
            log_rate_limited(uid, used, settings.generation_daily_limit)
            if language == "ru":
                await message.answer(
                    f"Сегодня уже {settings.generation_daily_limit} генераций — это дневной лимит. Завтра снова сможешь создать настрой дня.",
                    reply_markup=style_keyboard(language, visual_mode=visual_mode),
                )
            else:
                await message.answer(
                    f"You've reached the daily limit of {settings.generation_daily_limit} generations. Try again tomorrow.",
                    reply_markup=style_keyboard(language, visual_mode=visual_mode),
                )
            await state.set_state(GenerationState.choosing_style)
            return

    gender_hint = gender_display(gender, language=language)
    today = dt.datetime.now().date()
    focus = get_focus_for_date(uid, sphere, today)
    focus_text = focus["en"] if language == "en" else focus["ru"]
    micro_step = focus["micro_step_en"] if language == "en" else focus["micro_step_ru"]
    image_hint = focus.get("image_hint_en")
    resolved_style = resolve_style(style, sphere, user_id=uid, day=today, focus_key=focus["key"], visual_mode=visual_mode)
    effective_visual_mode = visual_mode_for_style(visual_mode, resolved_style)

    try:
        affirmations = await generate_affirmations(
            sphere=sphere,
            language=language,
            user_text=theme_text,
            subsphere=subsphere,
            gender_hint=gender_hint,
            gender=gender,
            focus=focus_text,
            micro_theme=micro_step,
            sphere_label=get_sphere_label(sphere, language),
        )
    except Exception as exc:
        logger.exception("Affirmations generation failed: %s", exc)
        log_generation_fail(uid, "interactive", "affirmations", str(exc))
        await message.answer(
            "Не удалось собрать текст настроя дня. Попробуй ещё раз — выбери стиль ниже или /new."
            if language == "ru"
            else "Could not create the daily focus text. Try again — pick a style below or use /new.",
            reply_markup=style_keyboard(language, visual_mode=visual_mode),
        )
        await state.set_state(GenerationState.choosing_style)
        return

    color_mood = random.choice(_COLOR_MOODS)
    composition_hint = random.choice(_COMPOSITION_HINTS)
    prompt_trace = "template"
    try:
        prompt_final, prompt_trace = await build_enriched_image_prompt(
            style=style,
            sphere=sphere,
            subsphere=subsphere,
            user_text=theme_text,
            custom_style_description=custom_style_description,
            affirmations=affirmations,
            color_mood=color_mood,
            composition_hint=composition_hint,
            use_llm=settings.llm_image_prompt_enabled,
            image_hint=image_hint,
            focus=focus_text,
            resolved_style=resolved_style,
            visual_mode=effective_visual_mode,
        )
        if prompt_trace == "template_fallback":
            log_image_prompt_llm_fallback("llm_unavailable_or_bad_json")
        image_path = await generate_image(
            style=style,
            sphere=sphere,
            user_text=theme_text,
            subsphere=subsphere,
            custom_style_description=custom_style_description,
            prompt_override=prompt_final,
            image_prompt_trace=prompt_trace,
            image_hint=image_hint,
            resolved_style_override=resolved_style,
            visual_mode=effective_visual_mode,
            focus_key=focus["key"],
            color_mood=color_mood,
            composition_hint=composition_hint,
        )
    except Exception as exc:
        logger.exception("Image generation failed: %s", exc)
        log_generation_fail(uid, "interactive", "image", str(exc))
        err_text = str(exc)
        if language == "ru":
            if "Генерация изображения" in err_text or "времени" in err_text:
                msg = err_text + " Попробуй ещё раз — выбери стиль ниже или /new."
            else:
                msg = "Не удалось сгенерировать изображение. Попробуй ещё раз — выбери стиль ниже или /new."
        else:
            if "took too long" in err_text.lower() or "timeout" in err_text.lower():
                msg = err_text + " Try again — pick a style below or /new."
            else:
                msg = "Could not generate the image. Try again — pick a style below or /new."
        await message.answer(msg, reply_markup=style_keyboard(language, visual_mode=visual_mode))
        await state.set_state(GenerationState.choosing_style)
        return

    text_lines = []
    name = (user or {}).get("name")
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
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["affirmations"] = affirmations
            meta["theme_text"] = theme_text
            meta["gender"] = gender
            meta["focus"] = focus
            meta["micro_step"] = micro_step
            meta["visual_mode"] = effective_visual_mode
            meta["requested_style"] = style
            meta["selected_style"] = resolved_style
            meta["resolved_style"] = resolved_style
            meta["focus_key"] = focus["key"]
            meta["color_palette"] = color_mood
            meta["composition_hint"] = composition_hint
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Could not update meta file %s: %s", meta_path, e)

    photo = FSInputFile(image_path)
    await message.answer_photo(photo=photo, caption=caption, reply_markup=after_generation_keyboard(language))

    if limit_enabled:
        await record_interactive_generation(uid)
    log_generation_ok(uid, "interactive", prompt_trace)

    await state.update_data(
        last_generation={
            "sphere": sphere,
            "subsphere": subsphere,
            "style": style,
            "resolved_style": resolved_style,
            "visual_mode": visual_mode,
            "theme_text": theme_text,
            "custom_style_description": custom_style_description,
            "affirmations": affirmations,
            "focus_key": focus["key"],
        }
    )
    await state.set_state(GenerationState.after_result)


@router.callback_query(F.data == "again:yes")
async def again_affirmation(callback: CallbackQuery, state: FSMContext) -> None:
    """Повторная генерация с теми же параметрами (без фильтра по FSM — после рестарта бота состояние могло обнулиться)."""
    await callback.answer()
    data = await state.get_data()
    last = data.get("last_generation")
    if not last:
        user = await get_user(callback.from_user.id)
        language = (user or {}).get("language", "ru")
        await state.clear()
        await callback.message.answer(
            "Не нашла параметры предыдущего настроя. Давай начнём заново с /new."
            if language == "ru"
            else "Could not find previous parameters. Please start again with /new."
        )
        return

    await state.update_data(
        sphere=last.get("sphere"),
        subsphere=last.get("subsphere"),
        style=last.get("style") or "nature",
        visual_mode=last.get("visual_mode") or "illustration",
        custom_style_description=last.get("custom_style_description"),
    )
    await callback.message.answer(
        _creating_text((await get_user(callback.from_user.id) or {}).get("language", "ru"))
    )
    await _run_generation(callback.message, state, theme_text=last.get("theme_text"), user_telegram_id=callback.from_user.id)


@router.callback_query(GenerationState.after_result, F.data == "tts:yes")
async def tts_affirmations(callback: CallbackQuery, state: FSMContext) -> None:
    """Озвучить последние аффирмации через SpeechKit TTS и отправить голосовым сообщением."""
    await callback.answer()
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    if not is_tts_available(language):
        await callback.message.answer(
            "English audio is coming soon. Audio is currently available in Russian only."
        )
        return
    data = await state.get_data()
    last = data.get("last_generation")
    raw = (last or {}).get("affirmations") if last else None
    if not raw:
        await callback.message.answer(
            "Нет текста для озвучки. Сначала создай настрой дня, затем нажми «🔊 Озвучить»."
        )
        return
    # Всегда приводим к списку строк (на случай если FSM сохранил иначе или одна строка с переносами)
    if isinstance(raw, list):
        affirmations = [str(a).strip() for a in raw if a and str(a).strip()]
    else:
        affirmations = [s.strip() for s in str(raw).splitlines() if s.strip()]
    if not affirmations:
        await callback.message.answer(
            "Нет текста для озвучки. Сначала создай настрой дня, затем нажми «🔊 Озвучить»."
        )
        return
    gender = (user or {}).get("gender")
    try:
        audio_path = await synthesize_affirmations_with_pauses(
            affirmations,
            gender=gender,
            pause_seconds=5.0,
        )
    except RuntimeError as e:
        await callback.message.answer(str(e))
        return
    except Exception as exc:
        logger.exception("TTS failed: %s", exc)
        await callback.message.answer("Сервис озвучки временно недоступен. Попробуй позже.")
        return
    voice_file = FSInputFile(audio_path)
    await callback.message.answer_voice(voice=voice_file)


@router.callback_query(GenerationState.after_result, F.data == "new:yes")
async def new_request_from_result(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать новый сценарий выбора после результата (сообщение с фото не редактируем — шлём новое)."""
    await callback.answer()
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    await state.clear()
    await state.update_data(theme_text=None)
    await state.set_state(GenerationState.choosing_sphere)
    await callback.message.answer(
        _new_flow_text(language),
        reply_markup=sphere_keyboard(language),
    )


@router.callback_query(GenerationState.after_result, F.data == "sub:open")
async def open_subscription_from_result(callback: CallbackQuery, state: FSMContext) -> None:
    """Открыть настройку подписки из результата."""
    await callback.answer()
    # Импортируем здесь, чтобы избежать циклических импортов
    from handlers.subscribe import cmd_subscribe

    await cmd_subscribe(callback.message, state)

