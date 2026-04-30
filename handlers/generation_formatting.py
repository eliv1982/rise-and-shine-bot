import json
import os
from typing import Optional

from services.ritual_config import has_coastal_intent
from utils import display_name_for_language


def build_image_debug_block(meta: dict, *, model: str, image_size: str) -> str:
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


def build_generation_caption(
    *,
    user: Optional[dict],
    language: str,
    focus_text: str,
    affirmations: list[str],
    micro_step: str,
) -> str:
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

    return "\n\n".join(text_lines)


def update_image_meta(
    *,
    image_path: str,
    affirmations: list[str],
    theme_text: Optional[str],
    gender: Optional[str],
    focus: dict,
    micro_step: str,
    effective_visual_mode: str,
    style: str,
    resolved_style: str,
    color_mood: str,
    composition_hint: str,
    text_provider,
    image_provider,
    tts_provider,
    last_stt_meta: dict,
    data: dict,
    custom_style_description: Optional[str],
    logger,
) -> dict:
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
    return image_meta
