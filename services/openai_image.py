import asyncio
import base64
import json
import logging
import os
import random
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


# Варианты сцен для разнообразия (подписка): один стиль — разные места и мотивы
SCENE_VARIANTS: dict[str, list[str]] = {
    "nature": [
        "misty forest with sunlight through trees",
        "peaceful lake surrounded by mountains",
        "gentle coast with sea and rocks",
        "flower meadow at golden hour",
        "desert dunes at sunset",
        "waterfall in a green canyon",
        "autumn forest path",
        "winter landscape with snow and soft light",
        "bamboo grove with soft shadows",
        "lavender or poppy field",
        "tropical beach with palm trees",
        "mountain valley with a stream",
        "cherry blossom or garden in bloom",
        "northern lights over a quiet lake",
        "vineyard or olive grove on a hill",
    ],
    "realistic": [
        "soft window light in a minimal interior",
        "morning mist over a landscape",
        "detail of water or stone in natural light",
        "portrait-style still life with plants",
        "architectural detail with soft shadows",
        "coastal cliff at dawn",
        "forest clearing with rays of light",
        "urban park in autumn",
        "mountain peak at sunrise",
        "field of wheat or grass in the wind",
        "ice or snow crystals in sunlight",
        "old garden with climbing plants",
        "sea horizon at dusk",
        "rocks and moss by a stream",
        "balcony or terrace with view",
    ],
    "cosmos": [
        "nebula in blue and purple tones",
        "galaxy with golden core",
        "starfield over a planet silhouette",
        "aurora in space",
        "comet or meteor shower",
        "moon and stars over a minimal landscape",
        "deep space with distant galaxies",
        "planetary ring in soft light",
        "constellation pattern in night sky",
        "nebula in warm pink and orange",
    ],
    "abstract": [
        "flowing gradients in warm tones",
        "geometric shapes in soft pastels",
        "organic forms in blue and green",
        "layers of translucent color",
        "minimal composition with one accent",
        "fluid shapes in sunset colors",
        "soft circles and waves",
        "earthy tones with gold accent",
        "cool blues and silvers",
        "warm amber and cream",
    ],
    "mandala": [
        "floral motifs in pastel tones",
        "geometric with gold and deep blue",
        "nature-inspired (leaves, petals) in green and earth",
        "radial pattern in warm sunset palette",
        "minimal lines in monochrome",
        "layered circles in soft pink and mint",
    ],
    "sacred_geometry": [
        "golden ratio spiral in warm light",
        "crystalline pattern in cool tones",
        "overlapping circles in pastels",
        "hexagonal grid in nature colors",
        "luminous lines on dark background",
    ],
    "cartoon": [
        "friendly landscape with rolling hills",
        "cozy house by a lake",
        "magical forest with glowing elements",
        "sunny meadow with butterflies",
        "mountain village at dusk",
        "garden with birds and flowers",
        "seaside town with boats",
        "autumn park scene",
    ],
}

# Цветовые палитры для разнообразия
COLOR_PALETTES: list[str] = [
    "warm golden hour, soft yellows and oranges",
    "cool blue and green, peaceful and fresh",
    "pastel tones, soft pink mint and lavender",
    "earthy, terracotta and olive",
    "sunset colors, coral and deep blue",
    "morning mist, silver and pale green",
    "rich jewel tones, deep blue and emerald",
    "minimal, cream and soft grey",
    "autumn palette, amber and burgundy",
    "spring palette, fresh green and white",
    "nocturne, deep blue and purple",
    "warm neutrals, sand and stone",
]


def _pick_scene_and_palette(style: str) -> tuple[str, str]:
    """Случайный выбор сцены и палитры для разнообразия (подписка)."""
    style_key = style.lower() if style else "nature"
    variants = SCENE_VARIANTS.get(style_key) or SCENE_VARIANTS["nature"]
    scene = random.choice(variants)
    palette = random.choice(COLOR_PALETTES)
    return scene, palette


def _build_image_prompt(
    style: str,
    sphere: str,
    subsphere: Optional[str],
    user_text: Optional[str],
    custom_style_description: Optional[str] = None,
    scene_variant: Optional[str] = None,
    color_palette: Optional[str] = None,
) -> str:
    """
    Формирует англоязычный промпт для генерации изображения.
    scene_variant и color_palette — для разнообразия (подписка).
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

    scene_part = ""
    if scene_variant:
        scene_part = f" Scene: {scene_variant}."
    if color_palette:
        scene_part = f"{scene_part} Color palette: {color_palette}."

    return (
        f"{base_theme}.{extra}{scene_part} "
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
    add_variety: bool = False,
) -> str:
    """
    Асинхронно вызывает OpenAI-совместимый image API через ProxiAPI и сохраняет PNG.
    add_variety=True — случайная сцена и палитра (для подписки, чтобы картинки не повторялись).
    Возвращает путь к файлу.
    """
    settings = get_settings()
    if output_dir is None:
        output_dir = get_outputs_dir()

    base_url = settings.proxi_base_url.rstrip("/")
    url = f"{base_url}/images/generations"

    scene_variant: Optional[str] = None
    color_palette: Optional[str] = None
    if add_variety and style != "custom":
        scene_variant, color_palette = _pick_scene_and_palette(style)

    prompt = _build_image_prompt(
        style=style, sphere=sphere, subsphere=subsphere,
        user_text=user_text, custom_style_description=custom_style_description,
        scene_variant=scene_variant, color_palette=color_palette,
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
    if scene_variant is not None:
        meta["scene_variant"] = scene_variant
    if color_palette is not None:
        meta["color_palette"] = color_palette
    meta_path = os.path.join(output_dir, f"{file_basename}_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    logger.info("Image saved to %s", output_path)
    return output_path

