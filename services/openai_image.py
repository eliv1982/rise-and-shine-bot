import asyncio
import base64
import json
import logging
import os
from typing import Optional

import aiohttp

from config import get_outputs_dir, get_settings

logger = logging.getLogger(__name__)


def _build_default_image_theme(sphere: str, subsphere: Optional[str]) -> str:
    """
    Англоязычное описание сцены по умолчанию для генерации изображений.
    """
    sphere_key = sphere.lower()
    subsphere_key = (subsphere or "").lower()

    if sphere_key == "career":
        return "a peaceful yet inspiring scene symbolizing professional growth and confidence"
    if sphere_key == "self_realization":
        return "a creative, expressive scene symbolizing self-realization, talent and inspiration"
    if sphere_key == "inner_peace":
        return "a serene, meditative scene symbolizing inner peace and tranquility"
    if sphere_key == "relationships":
        if subsphere_key == "partner":
            return "a warm, intimate atmosphere symbolizing deep trust and romantic connection"
        if subsphere_key == "colleagues":
            return "a friendly, collaborative workspace symbolizing respectful teamwork"
        if subsphere_key == "friends":
            return "a cozy gathering of friends symbolizing support and joy"
        return "soft, kind human connections and trust between people"
    if sphere_key == "health":
        return "a gentle wellness scene symbolizing balance, vitality and self-care"
    if sphere_key == "money":
        return "a calm, abundant atmosphere symbolizing stability, prosperity and wise decisions"
    if sphere_key == "spirituality":
        return "a serene, luminous scene symbolizing inner peace, intuition and spiritual growth"
    return "a harmonious, uplifting scene symbolizing inner balance and hope"


def _style_to_phrase(style: str) -> str:
    """
    Преобразует выбранный стиль в фразу для промпта.
    """
    style = style.lower()
    mapping = {
        "realistic": "realistic style, detailed, soft natural light",
        "cartoon": "soft cartoon style, friendly lines, gentle colors",
        "mandala": "intricate mandala, symmetric, meditative patterns",
        "sacred_geometry": "sacred geometry patterns, harmonious proportions, glowing lines",
        "nature": "lush nature scene, trees, sky, soft sun rays",
        "cosmos": "cosmic scene with stars, galaxies, soft glowing nebulae",
        "abstract": "abstract art, flowing shapes, harmonious colors",
    }
    return mapping.get(style, "soft, inspiring, visually harmonious style")


def _build_image_prompt(
    style: str,
    sphere: str,
    subsphere: Optional[str],
    user_text: Optional[str],
    custom_style_description: Optional[str] = None,
) -> str:
    """
    Формирует англоязычный промпт для генерации изображения.
    """
    base_theme = _build_default_image_theme(sphere, subsphere)

    if style == "custom" and custom_style_description:
        style_phrase = f"in the style: {custom_style_description}"
    else:
        style_phrase = _style_to_phrase(style)
        if custom_style_description:
            style_phrase = f"{style_phrase}. Additional: {custom_style_description}"

    extra = ""
    if user_text:
        extra = f" The scene subtly reflects the idea: \"{user_text}\"."

    return (
        f"{base_theme}.{extra} "
        f"Atmosphere: uplifting, calm, hopeful, suitable for affirmation practice about {sphere}. "
        f"Visual style: {style_phrase}. No text, no words on the image."
    )


async def generate_image(
    style: str,
    sphere: str,
    user_text: Optional[str] = None,
    subsphere: Optional[str] = None,
    custom_style_description: Optional[str] = None,
    output_dir: Optional[str] = None,
    file_basename: Optional[str] = None,
) -> str:
    """
    Асинхронно вызывает OpenAI-совместимый image API через ProxiAPI и сохраняет PNG.
    Возвращает путь к файлу.
    """
    settings = get_settings()
    if output_dir is None:
        output_dir = get_outputs_dir()

    base_url = settings.proxi_base_url.rstrip("/")
    url = f"{base_url}/images/generations"

    prompt = _build_image_prompt(
        style=style, sphere=sphere, subsphere=subsphere,
        user_text=user_text, custom_style_description=custom_style_description,
    )

    payload = {
        "model": "gpt-image-1-mini",
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "response_format": "b64_json",
    }

    headers = {
        "Authorization": f"Bearer {settings.proxi_api_key}",
        "Content-Type": "application/json",
    }

    os.makedirs(output_dir, exist_ok=True)

    # Генерация изображения может занимать 2–3 минуты, таймаут 4 мин
    timeout = aiohttp.ClientTimeout(total=240)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=timeout) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error("Image API error: status=%s, body=%s", resp.status, text)
                    raise RuntimeError(f"Image generation failed with status {resp.status}")
                data = await resp.json()
    except asyncio.TimeoutError as exc:
        logger.warning("Image API timeout after 240s")
        raise RuntimeError(
            "Генерация изображения заняла слишком много времени. Сервер перегружен — попробуй через минуту."
        ) from exc
    except Exception as exc:
        logger.exception("Error calling image generation API: %s", exc)
        raise RuntimeError(f"Error calling image generation API: {exc}") from exc

    try:
        b64 = data["data"][0]["b64_json"]
    except Exception as exc:
        logger.exception("Unexpected image API response format: %s", exc)
        raise RuntimeError("Unexpected image API response format") from exc

    image_bytes = base64.b64decode(b64)

    if not file_basename:
        safe_sphere = sphere.replace(" ", "_").lower()
        safe_style = style.replace(" ", "_").lower()
        file_basename = f"affirmation_{safe_sphere}_{safe_style}"

    filename = f"{file_basename}.png"
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "wb") as f:
        f.write(image_bytes)

    meta = {
        "prompt": prompt,
        "style": style,
        "sphere": sphere,
        "subsphere": subsphere,
        "user_text": user_text,
        "custom_style_description": custom_style_description,
        "model": "gpt-image-1-mini",
        "size": "1024x1024",
    }
    meta_path = os.path.join(output_dir, f"{file_basename}_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    logger.info("Image saved to %s", output_path)
    return output_path

