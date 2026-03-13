import asyncio
import json
import logging
import os
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message, PhotoSize

from config import get_outputs_dir
from database import get_user
from keyboards.inline import (
    after_generation_keyboard,
    relationships_subsphere_keyboard,
    sphere_keyboard,
    style_cancel_keyboard,
    style_extra_keyboard,
    style_keyboard,
    theme_early_cancel_keyboard,
)
from services.openai_image import generate_image
from services.speechkit import transcribe_audio
from services.speechkit_tts import synthesize_affirmations_with_pauses
from services.yandex_gpt import generate_affirmations
from states import GenerationState
from utils import gender_display

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "cmd:new")
async def cb_new_affirmation(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка кнопки «Новая аффирмация» после регистрации."""
    await callback.answer()
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    await state.update_data(theme_text=None)
    await state.set_state(GenerationState.choosing_sphere)
    current = await state.get_state()
    # Если уже в сценарии генерации — редактируем текущее сообщение, чтобы не слать лишний блок
    if current and current.startswith("GenerationState:"):
        await callback.message.edit_text(
            "Выбери сферу жизни:" if language == "ru" else "Choose a life area:",
            reply_markup=sphere_keyboard(language),
        )
    else:
        await callback.message.answer(
            "Выбери сферу жизни:" if language == "ru" else "Choose a life area:",
            reply_markup=sphere_keyboard(language),
        )


@router.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    current = await state.get_state()
    # Уже в сценарии генерации — не слать второй блок «Выбери сферу», чтобы не дублировать
    if current and current.startswith("GenerationState:"):
        if language == "ru":
            await message.answer("Продолжи выбор выше: выбери стиль или сферу в предыдущем сообщении.")
        else:
            await message.answer("Continue above: choose style or sphere in the previous message.")
        return
    await state.update_data(theme_text=None)
    await state.set_state(GenerationState.choosing_sphere)
    await message.answer(
        "Выбери сферу жизни:" if language == "ru" else "Choose a life area:",
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
        "Выбери сферу жизни:" if language == "ru" else "Choose a life area:",
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
    await state.set_state(GenerationState.choosing_style)
    await message.answer(
        (f"Тема: «{recognized}». Выбери стиль изображения:" if language == "ru" else f"Theme: “{recognized}”. Choose image style:"),
        reply_markup=style_keyboard(language),
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
    await state.set_state(GenerationState.choosing_style)
    await message.answer(
        (f"Тема: «{text}». Выбери стиль изображения:" if language == "ru" else f"Theme: “{text}”. Choose image style:"),
        reply_markup=style_keyboard(language),
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
        await state.set_state(GenerationState.choosing_style)
        await callback.message.edit_text(
            "Выбери стиль изображения:" if language == "ru" else "Choose image style:",
            reply_markup=style_keyboard(language),
        )
    await callback.answer()


@router.callback_query(GenerationState.choosing_relationship_subsphere, F.data.startswith("subsphere:"))
async def choose_relationship_subsphere(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    subsphere = callback.data.split(":", maxsplit=1)[1]

    await state.update_data(subsphere=subsphere)
    await state.set_state(GenerationState.choosing_style)
    await callback.message.edit_text(
        "Выбери стиль изображения:" if language == "ru" else "Choose image style:",
        reply_markup=style_keyboard(language),
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
    await state.set_state(GenerationState.confirm_style_extra)
    await callback.message.edit_text(
        "Добавить описание к стилю картинки или продолжить без него?" if language == "ru" else "Add a description to the image style or continue without?",
        reply_markup=style_extra_keyboard(language),
    )
    await callback.answer()


@router.callback_query(GenerationState.confirm_style_extra, F.data == "style_extra:continue")
async def style_extra_continue(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    data = await state.get_data()
    theme_text = data.get("theme_text")
    await callback.message.edit_text(
        "Генерирую аффирмацию и изображение…" if language == "ru" else "Generating affirmation and image…"
    )
    await callback.answer()
    await _run_generation(callback.message, state, theme_text=theme_text)


@router.callback_query(GenerationState.confirm_style_extra, F.data == "style_extra:add")
async def style_extra_add(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    await state.set_state(GenerationState.waiting_for_custom_style)
    await callback.message.edit_text(
        "Опиши желаемый стиль изображения текстом или отправь голосовое сообщение."
        if language == "ru"
        else "Describe the desired image style in text or send a voice message.",
        reply_markup=style_cancel_keyboard(language),
    )
    await callback.answer()


@router.message(GenerationState.confirm_style_extra, F.voice)
async def handle_voice_style_extra(message: Message, state: FSMContext) -> None:
    """Голос прямо на «Добавить описание или продолжить?» — распознаём и запускаем генерацию."""
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
        logger.exception("STT failed (style extra): %s", exc)
        await message.answer(
            "Не удалось распознать голос. Напиши текстом или нажми «Продолжить»." if language == "ru" else "Could not recognize. Type or press Continue."
        )
        return
    await state.update_data(custom_style_description=recognized)
    data = await state.get_data()
    await message.answer("Генерирую аффирмацию и изображение…" if language == "ru" else "Generating affirmation and image…")
    await _run_generation(message, state, theme_text=data.get("theme_text"))


@router.message(GenerationState.confirm_style_extra, F.text)
async def handle_text_style_extra(message: Message, state: FSMContext) -> None:
    """Текст прямо на «Добавить описание или продолжить?» — используем как описание и запускаем генерацию."""
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    text = (message.text or "").strip()
    if not text:
        return
    await state.update_data(custom_style_description=text)
    data = await state.get_data()
    await message.answer("Генерирую аффирмацию и изображение…" if language == "ru" else "Generating affirmation and image…")
    await _run_generation(message, state, theme_text=data.get("theme_text"))


@router.callback_query(GenerationState.waiting_for_custom_style, F.data == "style:cancel")
async def cancel_custom_style(callback: CallbackQuery, state: FSMContext) -> None:
    user = await get_user(callback.from_user.id)
    language = (user or {}).get("language", "ru")
    data = await state.get_data()
    # Если пришли из «Добавить описание» (пресет уже выбран) — вернуть к двум кнопкам
    if data.get("style") and data.get("style") != "custom":
        await state.set_state(GenerationState.confirm_style_extra)
        await callback.message.edit_text(
            "Добавить описание к стилю картинки или продолжить без него?" if language == "ru" else "Add a description or continue without?",
            reply_markup=style_extra_keyboard(language),
        )
    else:
        await state.set_state(GenerationState.choosing_style)
        await callback.message.edit_text(
            "Выбери стиль изображения:" if language == "ru" else "Choose image style:",
            reply_markup=style_keyboard(language),
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
    await message.answer("Генерирую аффирмацию и изображение…" if language == "ru" else "Generating affirmation and image…")
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
    await message.answer("Генерирую аффирмацию и изображение…" if language == "ru" else "Generating affirmation and image…")
    await _run_generation(message, state, theme_text=data.get("theme_text"))






async def _run_generation(message: Message, state: FSMContext, theme_text: Optional[str]) -> None:
    user = await get_user(message.from_user.id)
    language = (user or {}).get("language", "ru")
    gender = (user or {}).get("gender")
    data = await state.get_data()

    sphere = data.get("sphere")
    subsphere = data.get("subsphere")
    style = data.get("style") or "nature"
    custom_style_description = data.get("custom_style_description")

    if not sphere:
        await message.answer("Что-то пошло не так, попробуй начать заново с /new.")
        await state.clear()
        return

    gender_hint = gender_display(gender, language=language)

    try:
        affirmations_task = generate_affirmations(
            sphere=sphere,
            language=language,
            user_text=theme_text,
            subsphere=subsphere,
            gender_hint=gender_hint,
            gender=gender,
        )
        image_task = generate_image(
            style=style,
            sphere=sphere,
            user_text=theme_text,
            subsphere=subsphere,
            custom_style_description=custom_style_description,
        )
        results = await asyncio.gather(affirmations_task, image_task, return_exceptions=True)
    except Exception as exc:
        logger.exception("Generation failed: %s", exc)
        await message.answer(
            "Не удалось сгенерировать аффирмации. Попробуй ещё раз — выбери стиль ниже или /new для нового запроса.",
            reply_markup=style_keyboard(language),
        )
        await state.set_state(GenerationState.choosing_style)
        return

    affirmations_err = results[0]
    image_err = results[1]
    if isinstance(affirmations_err, Exception):
        logger.exception("Affirmations generation failed: %s", affirmations_err)
        await message.answer(
            "Не удалось сгенерировать текст аффирмаций. Попробуй ещё раз — выбери стиль ниже или /new.",
            reply_markup=style_keyboard(language),
        )
        await state.set_state(GenerationState.choosing_style)
        return
    if isinstance(image_err, Exception):
        logger.exception("Image generation failed: %s", image_err)
        err_text = str(image_err)
        if "Генерация изображения" in err_text or "времени" in err_text:
            msg = err_text + " Попробуй ещё раз — выбери стиль ниже или /new."
        else:
            msg = "Не удалось сгенерировать изображение. Попробуй ещё раз — выбери стиль ниже или /new."
        await message.answer(msg, reply_markup=style_keyboard(language))
        await state.set_state(GenerationState.choosing_style)
        return

    affirmations = affirmations_err
    image_path = image_err

    text_lines = []
    name = (user or {}).get("name")
    if language == "ru":
        if name:
            text_lines.append(f"{name}, твои аффирмации:")
        else:
            text_lines.append("Твои аффирмации:")
    else:
        if name:
            text_lines.append(f"{name}, here are your affirmations:")
        else:
            text_lines.append("Here are your affirmations:")

    for a in affirmations:
        text_lines.append(f"• {a}")

    caption = "\n\n".join(text_lines)

    meta_path = image_path.replace(".png", "_meta.json")
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["affirmations"] = affirmations
            meta["theme_text"] = theme_text
            meta["gender"] = gender
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Could not update meta file %s: %s", meta_path, e)

    photo = FSInputFile(image_path)
    await message.answer_photo(photo=photo, caption=caption, reply_markup=after_generation_keyboard(language))

    await state.update_data(
        last_generation={
            "sphere": sphere,
            "subsphere": subsphere,
            "style": style,
            "theme_text": theme_text,
            "custom_style_description": custom_style_description,
            "affirmations": affirmations,
        }
    )
    await state.set_state(GenerationState.after_result)


@router.callback_query(GenerationState.after_result, F.data == "again:yes")
async def again_affirmation(callback: CallbackQuery, state: FSMContext) -> None:
    """Повторная генерация с теми же параметрами."""
    await callback.answer()
    data = await state.get_data()
    last = data.get("last_generation")
    if not last:
        user = await get_user(callback.from_user.id)
        language = (user or {}).get("language", "ru")
        await state.clear()
        await callback.message.answer(
            "Не нашла параметры предыдущей аффирмации. Давай начнём заново с /new."
            if language == "ru"
            else "Could not find previous parameters. Please start again with /new."
        )
        return

    await state.update_data(
        sphere=last.get("sphere"),
        subsphere=last.get("subsphere"),
        style=last.get("style") or "nature",
        custom_style_description=last.get("custom_style_description"),
    )
    await callback.message.answer("Генерирую ещё..." if (await get_user(callback.from_user.id) or {}).get("language", "ru") == "ru" else "Generating more...")
    await _run_generation(callback.message, state, theme_text=last.get("theme_text"))


@router.callback_query(GenerationState.after_result, F.data == "tts:yes")
async def tts_affirmations(callback: CallbackQuery, state: FSMContext) -> None:
    """Озвучить последние аффирмации через SpeechKit TTS и отправить голосовым сообщением."""
    await callback.answer()
    data = await state.get_data()
    last = data.get("last_generation")
    raw = (last or {}).get("affirmations") if last else None
    if not raw:
        await callback.message.answer(
            "Нет текста для озвучки. Сначала получи аффирмацию, затем нажми «🔊 Озвучить»."
        )
        return
    # Всегда приводим к списку строк (на случай если FSM сохранил иначе или одна строка с переносами)
    if isinstance(raw, list):
        affirmations = [str(a).strip() for a in raw if a and str(a).strip()]
    else:
        affirmations = [s.strip() for s in str(raw).splitlines() if s.strip()]
    if not affirmations:
        await callback.message.answer(
            "Нет текста для озвучки. Сначала получи аффирмацию, затем нажми «🔊 Озвучить»."
        )
        return
    user = await get_user(callback.from_user.id)
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
    await state.update_data(theme_text=None)
    await state.set_state(GenerationState.choosing_sphere)
    await callback.message.answer(
        "Выбери сферу жизни:" if language == "ru" else "Choose a life area:",
        reply_markup=sphere_keyboard(language),
    )


@router.callback_query(GenerationState.after_result, F.data == "sub:open")
async def open_subscription_from_result(callback: CallbackQuery, state: FSMContext) -> None:
    """Открыть настройку подписки из результата."""
    await callback.answer()
    # Импортируем здесь, чтобы избежать циклических импортов
    from handlers.subscribe import cmd_subscribe

    await cmd_subscribe(callback.message, state)

