import logging
from typing import Any

from database import save_generation_history, save_visual_history

logger = logging.getLogger(__name__)


def extract_telegram_photo_file_id(sent_message) -> str | None:
    if sent_message is None:
        return None
    try:
        photos = getattr(sent_message, "photo", None)
        if not photos:
            return None
        last_photo = photos[-1]
        return getattr(last_photo, "file_id", None)
    except Exception:
        return None


def build_visual_motifs(
    image_meta: dict | None = None,
    visual_mode: str | None = None,
    selected_style: str | None = None,
    color_palette: str | None = None,
    composition_hint: str | None = None,
    sphere: str | None = None,
    subsphere: str | None = None,
) -> dict:
    safe_meta = image_meta if isinstance(image_meta, dict) else {}
    scene_type = safe_meta.get("scene_preset") or safe_meta.get("photo_scene_preset")
    return {
        "source": "generation_runtime_meta",
        "scene_type": scene_type,
        "visual_mode": visual_mode,
        "selected_style": selected_style,
        "color_palette": color_palette,
        "composition_hint": composition_hint,
        "sphere": sphere,
        "subsphere": subsphere,
    }


async def record_generation_history_best_effort(
    *,
    telegram_user_id: int,
    request_type: str,
    focus_title: str | None = None,
    affirmations: list[str] | None = None,
    soft_action: str | None = None,
    text_model: str | None = None,
    image_model: str | None = None,
    image_prompt: str | None = None,
    telegram_image_file_id: str | None = None,
    scene_type: str | None = None,
    visual_motifs: dict | list | None = None,
) -> int | None:
    try:
        generation_id = await save_generation_history(
            telegram_user_id=telegram_user_id,
            request_type=request_type,
            focus_title=focus_title,
            theme_category=None,
            affirmations=affirmations,
            soft_action=soft_action,
            text_model=text_model,
            scene_model=None,
            image_model=image_model,
            image_prompt=image_prompt,
            telegram_image_file_id=telegram_image_file_id,
            status="success",
            error_message=None,
        )
        await save_visual_history(
            telegram_user_id=telegram_user_id,
            generation_id=generation_id,
            scene_type=scene_type,
            human_presence=None,
            visual_motifs=visual_motifs,
        )
        return generation_id
    except Exception:
        logger.exception("Could not record generation history for user %s", telegram_user_id)
        return None
