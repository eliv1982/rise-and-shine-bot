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

from config import (
    get_image_provider_config,
    get_outputs_dir,
    get_settings,
    get_text_provider_config,
    get_tts_provider_config,
)
from database import can_start_interactive_generation, get_user, record_interactive_generation
from keyboards.inline import (
    after_generation_keyboard,
    main_reply_keyboard,
    relationships_subsphere_keyboard,
    sphere_keyboard,
    style_cancel_keyboard,
    style_keyboard,
    theme_early_cancel_keyboard,
    voice_confirm_keyboard,
    voice_recovery_keyboard,
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
    has_coastal_intent,
    is_tts_available,
    normalize_visual_mode,
    resolve_style,
    visual_mode_for_style,
)
from services.speechkit_stt import transcribe_audio_with_meta
from services.speechkit_tts import synthesize_affirmations_with_pauses
from services.yandex_gpt import build_enriched_image_prompt, generate_affirmations
from states import GenerationState
from utils import display_name_for_language, gender_display, is_gibberish_text, is_input_language_compatible

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


def _voice_recognition_failed_text(language: str) -> str:
    if language == "ru":
        return "Не получилось распознать голос 😕\nПопробуй ещё раз или отправь текстом."
    return "I couldn’t recognize the voice message 😕\nPlease try again or send it as text."


def _voice_recognized_echo_text(language: str, recognized_text: str) -> str:
    clipped = recognized_text.strip()
    if len(clipped) > 140:
        clipped = clipped[:137] + "..."
    if language == "ru":
        return f"🎙 Распознано: \"{clipped}\""
    return f"🎙 Recognized: \"{clipped}\""


def _voice_unclear_text(language: str) -> str:
    if language == "ru":
        return "Я распознала голос, но текст получился неразборчивым 😕\nПопробуй ещё раз или отправь словами."
    return "I recognized the voice message, but the text looks unclear 😕\nPlease try again or send it as text."


def _voice_language_mismatch_text(language: str) -> str:
    if language == "ru":
        return "Похоже, голос распознан на другом языке 🌿\nОтправь голосовое или текст на русском."
    return "I recognized speech in another language 🌿\nPlease send voice or text in English."


def _text_language_mismatch_text(language: str) -> str:
    if language == "ru":
        return "В этом режиме я жду текст на русском 🌿\nНапиши тему или стиль по-русски."
    return "I can work with this flow in English 🌿\nPlease send the theme or style in English."


def _menu_choose_option_text(language: str) -> str:
    if language == "ru":
        return "Выбери вариант в меню выше 🌿\nЕсли хочешь написать свою тему — нажми «Своя тема»."
    return "Please choose an option from the menu above 🌿\nIf you want to write your own theme, choose “Custom theme”."


def _menu_choose_style_text(language: str) -> str:
    if language == "ru":
        return "Выбери стиль кнопкой выше 🎨\nЕсли хочешь описать стиль своими словами — выбери «Свой стиль»."
    return "Please choose an image style from the buttons above 🎨\nIf you want to describe your own style, choose “Custom style”."


def _build_image_debug_block(meta: dict, *, model: str, image_size: str) -> str:
    lines = [
        "DEBUG:",
        f"visual_mode: {meta.get('visual_mode') or '—'}",
        f"requested_style: {meta.get('requested_style') or '—'}",
        f"selected_style: {meta.get('selected_style') or meta.get('resolved_style') or '—'}",
        f"prompt_branch: {meta.get('prompt_branch') or '—'}",
    ]
    scene_preset = meta.get("scene_preset") or meta.get("photo_scene_preset")
    if scene_preset:
        lines.append(f"scene_preset: {scene_preset}")
    lines.extend(
        [
            f"text_provider: {meta.get('text_provider') or '—'}",
            f"image_provider: {meta.get('image_provider') or '—'}",
            f"tts_provider: {meta.get('tts_provider') or '—'}",
            f"text_model: {meta.get('text_model') or '—'}",
            f"model: {meta.get('model') or model}",
            f"tts_model: {meta.get('tts_model') or '—'}",
            f"voice: {meta.get('voice') or '—'}",
            f"stt_provider: {meta.get('stt_provider') or '—'}",
            f"stt_model: {meta.get('stt_model') or '—'}",
            f"stt_language: {meta.get('stt_language') or '—'}",
            f"recognized_language: {meta.get('recognized_language') or '—'}",
            f"image_size: {meta.get('image_size') or meta.get('size') or image_size}",
        ]
    )
    return "\n".join(lines)


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
        stt_meta = await transcribe_audio_with_meta(local_path, language=language)
        recognized = str(stt_meta.get("recognized_text_final") or "")
    except Exception as exc:
        logger.exception("STT failed (theme early): %s", exc)
        await message.answer(_voice_recognition_failed_text(language))
        return
    await state.update_data(last_stt_meta=stt_meta, last_recognized_text=recognized)
    if is_gibberish_text(recognized):
        await message.answer(
            _voice_unclear_text(language),
            reply_markup=voice_recovery_keyboard(language, scope="theme_voice"),
        )
        return
    if not is_input_language_compatible(recognized, language):
        await message.answer(
            _voice_language_mismatch_text(language),
            reply_markup=voice_recovery_keyboard(language, scope="theme_voice"),
        )
        return
    await message.answer(
        (
            f"{_voice_recognized_echo_text(language, recognized)}\n\nИспользовать этот текст?"
            if language == "ru"
            else f"{_voice_recognized_echo_text(language, recognized)}\n\nUse this text?"
        ),
        reply_markup=voice_confirm_keyboard(language, scope="theme_voice"),
    )
    await state.update_data(recognized_text_pending=recognized, recognized_text_pending_kind="theme")


@router.message(GenerationState.waiting_for_theme_early, F.text)
async def handle_text_theme_early(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    text = (message.text or "").strip()
    if not text:
        await message.answer("Напиши тему или нажми «Отмена»." if language == "ru" else "Type your theme or press Cancel.")
        return
    if not is_input_language_compatible(text, language):
        await message.answer(_text_language_mismatch_text(language))
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
    await callback.message.edit_text(_creating_text(language))
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


@router.callback_query(GenerationState.waiting_for_theme_early, F.data.startswith("theme_voice:"))
async def handle_theme_voice_recovery(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    action = callback.data.split(":", maxsplit=1)[1]
    if action == "use":
        pending = str((await state.get_data()).get("recognized_text_pending") or "").strip()
        if not pending:
            await callback.answer()
            await callback.message.answer(
                "Не вижу распознанного текста. Попробуй ещё раз голосом."
                if language == "ru"
                else "I cannot find recognized text. Please try voice again."
            )
            return
        await state.update_data(
            theme_text=pending,
            sphere="inner_peace",
            subsphere=None,
            recognized_text_pending=None,
            recognized_text_pending_kind=None,
        )
        await state.set_state(GenerationState.choosing_visual_mode)
        await callback.message.answer(
            (f"Тема: «{pending}».\n\n{_visual_mode_text(language)}" if language == "ru" else f"Theme: “{pending}”.\n\n{_visual_mode_text(language)}"),
            reply_markup=visual_mode_keyboard(language),
        )
    elif action == "retry_voice":
        await callback.message.answer(
            "Отправь голос с темой ещё раз."
            if language == "ru"
            else "Send your theme by voice once again."
        )
    elif action == "type_text":
        await callback.message.answer(
            "Напиши тему текстом."
            if language == "ru"
            else "Type your theme as text."
        )
    elif action == "back":
        await state.update_data(recognized_text_pending=None, recognized_text_pending_kind=None)
        await state.set_state(GenerationState.choosing_sphere)
        await callback.message.answer(_new_flow_text(language), reply_markup=sphere_keyboard(language))
    elif action == "menu":
        await state.clear()
        await callback.message.answer(
            "🏠 Возвращаю в меню." if language == "ru" else "🏠 Returning to menu.",
            reply_markup=main_reply_keyboard(language),
        )
    await callback.answer()


@router.callback_query(GenerationState.waiting_for_custom_style, F.data.startswith("style_voice:"))
async def handle_style_voice_recovery(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    action = callback.data.split(":", maxsplit=1)[1]
    if action == "use":
        data = await state.get_data()
        pending = str(data.get("recognized_text_pending") or "").strip()
        if not pending:
            await callback.answer()
            await callback.message.answer(
                "Не вижу распознанного текста. Попробуй ещё раз голосом."
                if language == "ru"
                else "I cannot find recognized text. Please try voice again."
            )
            return
        await state.update_data(
            custom_style_description=pending,
            recognized_text_pending=None,
            recognized_text_pending_kind=None,
        )
        await callback.message.answer(_creating_text(language), reply_markup=main_reply_keyboard(language))
        await _run_generation(callback.message, state, theme_text=data.get("theme_text"), user_telegram_id=callback.from_user.id)
    elif action == "retry_voice":
        await callback.message.answer(
            "Отправь голос с описанием стиля ещё раз."
            if language == "ru"
            else "Send your style description by voice once again."
        )
    elif action == "type_text":
        await callback.message.answer(
            "Напиши стиль текстом."
            if language == "ru"
            else "Type your style description as text."
        )
    elif action == "back":
        data = await state.get_data()
        await state.update_data(recognized_text_pending=None, recognized_text_pending_kind=None)
        await state.set_state(GenerationState.choosing_style)
        await callback.message.answer(
            _style_choice_text(language),
            reply_markup=style_keyboard(language, visual_mode=data.get("visual_mode", "illustration")),
        )
    elif action == "menu":
        await state.clear()
        await callback.message.answer(
            "🏠 Возвращаю в меню." if language == "ru" else "🏠 Returning to menu.",
            reply_markup=main_reply_keyboard(language),
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
        stt_meta = await transcribe_audio_with_meta(local_path, language=language)
        recognized = str(stt_meta.get("recognized_text_final") or "")
    except Exception as exc:
        logger.exception("STT failed for custom style: %s", exc)
        await message.answer(_voice_recognition_failed_text(language))
        return
    await state.update_data(last_stt_meta=stt_meta, last_recognized_text=recognized)
    if is_gibberish_text(recognized):
        await message.answer(
            _voice_unclear_text(language),
            reply_markup=voice_recovery_keyboard(language, scope="style_voice"),
        )
        return
    if not is_input_language_compatible(recognized, language):
        await message.answer(
            _voice_language_mismatch_text(language),
            reply_markup=voice_recovery_keyboard(language, scope="style_voice"),
        )
        return
    await message.answer(
        (
            f"{_voice_recognized_echo_text(language, recognized)}\n\nИспользовать этот текст?"
            if language == "ru"
            else f"{_voice_recognized_echo_text(language, recognized)}\n\nUse this text?"
        ),
        reply_markup=voice_confirm_keyboard(language, scope="style_voice"),
    )
    await state.update_data(recognized_text_pending=recognized, recognized_text_pending_kind="style")


@router.message(GenerationState.waiting_for_custom_style, F.text)
async def handle_text_custom_style(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    text = (message.text or "").strip()
    if not text:
        await message.answer("Напиши описание стиля или нажми «Отмена»." if language == "ru" else "Type style description or press Cancel.")
        return
    if not is_input_language_compatible(text, language):
        await message.answer(_text_language_mismatch_text(language))
        return
    await state.update_data(custom_style_description=text)
    data = await state.get_data()
    await message.answer(_creating_text(language), reply_markup=main_reply_keyboard(language))
    await _run_generation(message, state, theme_text=data.get("theme_text"))


@router.message(
    GenerationState.choosing_sphere,
    GenerationState.choosing_relationship_subsphere,
    GenerationState.choosing_visual_mode,
    F.text,
)
async def generation_button_menu_text_guard(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    await message.answer(_menu_choose_option_text(language))


@router.message(
    GenerationState.choosing_sphere,
    GenerationState.choosing_relationship_subsphere,
    GenerationState.choosing_visual_mode,
    F.voice,
)
async def generation_button_menu_voice_guard(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    await message.answer(_menu_choose_option_text(language))


@router.message(GenerationState.choosing_style, F.text)
async def generation_style_menu_text_guard(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    await message.answer(_menu_choose_style_text(language))


@router.message(GenerationState.choosing_style, F.voice)
async def generation_style_menu_voice_guard(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    await message.answer(_menu_choose_style_text(language))






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
    text_provider = get_text_provider_config()
    image_provider = get_image_provider_config()
    tts_provider = get_tts_provider_config()

    sphere = data.get("sphere")
    subsphere = data.get("subsphere")
    style = data.get("style") or "nature"
    visual_mode = normalize_visual_mode(data.get("visual_mode"))
    custom_style_description = data.get("custom_style_description")
    last_stt_meta = data.get("last_stt_meta") or {}
    history = list(data.get("recent_generation_history") or [])
    recent_styles = [item.get("selected_style") for item in history[-3:] if item.get("selected_style")]
    recent_scenes = [item.get("scene_preset") for item in history[-2:] if item.get("scene_preset")]

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
    if theme_text and theme_text.strip():
        focus_text = theme_text.strip()
        micro_step = focus["micro_step_en"] if language == "en" else focus["micro_step_ru"]
    else:
        focus_text = focus["en"] if language == "en" else focus["ru"]
        micro_step = focus["micro_step_en"] if language == "en" else focus["micro_step_ru"]
    image_hint = focus.get("image_hint_en")
    if is_gibberish_text(focus_text):
        if theme_text and not is_gibberish_text(theme_text):
            focus_text = theme_text.strip()
        else:
            await message.answer(_voice_unclear_text(language))
            await state.set_state(GenerationState.choosing_style)
            return
    resolved_style = resolve_style(
        style,
        sphere,
        user_id=uid,
        day=today,
        focus_key=focus["key"],
        visual_mode=visual_mode,
        recent_styles=recent_styles,
    )
    if normalize_visual_mode(visual_mode) == "photo" and style == "auto" and has_coastal_intent(theme_text):
        resolved_style = "sea_coast_photo"
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
            recent_scene_presets=recent_scenes,
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
    name = display_name_for_language((user or {}).get("name"), language)
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
            meta["text_provider"] = text_provider.provider
            meta["image_provider"] = image_provider.provider
            meta["tts_provider"] = tts_provider.provider
            meta["text_model"] = text_provider.model
            meta["image_model"] = image_provider.model
            meta["tts_model"] = tts_provider.model
            meta["voice"] = tts_provider.voice or None
            meta["stt_provider"] = last_stt_meta.get("stt_provider")
            meta["stt_model"] = last_stt_meta.get("stt_model")
            meta["stt_language"] = last_stt_meta.get("recognized_language")
            meta["recognized_language"] = last_stt_meta.get("recognized_language")
            meta["recognized_text_raw"] = last_stt_meta.get("recognized_text_raw")
            meta["recognized_text_final"] = last_stt_meta.get("recognized_text_final") or data.get("last_recognized_text")
            meta["stt_attempt_count"] = last_stt_meta.get("stt_attempt_count")
            meta["stt_language_attempts"] = last_stt_meta.get("stt_language_attempts")
            meta["theme_source"] = "custom_theme" if (theme_text and theme_text.strip()) else "sphere"
            meta["preserved_user_theme"] = bool(theme_text and theme_text.strip())
            meta["coastal_hint_detected"] = bool(has_coastal_intent(theme_text) or has_coastal_intent(custom_style_description))
            image_meta = meta
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Could not update meta file %s: %s", meta_path, e)

    if settings.show_image_debug:
        caption = f"{caption}\n\n{_build_image_debug_block(image_meta, model=settings.image_model, image_size=settings.image_size)}"

    photo = FSInputFile(image_path)
    await message.answer_photo(photo=photo, caption=caption, reply_markup=after_generation_keyboard(language))

    if limit_enabled:
        await record_interactive_generation(uid)
    log_generation_ok(uid, "interactive", prompt_trace)

    history.append(
        {
            "selected_style": resolved_style,
            "scene_preset": image_meta.get("scene_preset") or image_meta.get("photo_scene_preset"),
        }
    )
    await state.clear()
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
        },
        recent_generation_history=history[-5:],
    )


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
    again_language = (await get_user(callback.from_user.id) or {}).get("language", "ru")
    await callback.message.answer(_creating_text(again_language), reply_markup=main_reply_keyboard(again_language))
    await _run_generation(callback.message, state, theme_text=last.get("theme_text"), user_telegram_id=callback.from_user.id)


@router.callback_query(F.data == "tts:yes")
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


@router.callback_query(F.data == "new:yes")
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


@router.callback_query(F.data == "sub:open")
async def open_subscription_from_result(callback: CallbackQuery, state: FSMContext) -> None:
    """Открыть настройку подписки из результата."""
    await callback.answer()
    # Импортируем здесь, чтобы избежать циклических импортов
    from handlers.subscribe import cmd_subscribe

    await cmd_subscribe(callback.message, state)



