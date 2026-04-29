import asyncio
import base64
import json
import logging
import os
import random
import uuid
from typing import Optional

import aiohttp

from config import get_outputs_dir, get_settings

logger = logging.getLogger(__name__)

# Варианты цветовой гаммы и атмосферы для разнообразия картинок
_COLOR_MOODS = [
    "warm golden hour lighting, soft amber and honey tones",
    "cool blue and soft lavender tones, peaceful morning light",
    "earthy greens and soft browns, natural forest atmosphere",
    "pastel soft colors, gentle pink and peach hues",
    "misty morning atmosphere, soft grey and pale green",
    "deep twilight, indigo and silver accents",
    "warm terracotta and sand tones, mediterranean feel",
    "fresh mint and sage green palette, spring feeling",
    "rich burgundy and gold accents, cozy and warm",
    "soft aqua and white, clean and airy",
    "warm candlelight glow, ochre and soft yellow",
    "muted sage, cream and warm beige",
    "dusty rose and soft clay",
    "champagne gold and ivory",
    "misty blue grey and pearl",
    "olive green and linen white",
    "cocoa, amber and candlelight",
    "muted terracotta and pale peach",
    "deep indigo and warm moonlight",
]

# Варианты композиции
_COMPOSITION_HINTS = [
    "wide open space, horizon in the distance",
    "intimate close-up, soft focus background",
    "symmetrical balance, centered subject",
    "layered depth, foreground and distant elements",
    "minimalist composition, lots of negative space",
    "dynamic angle, gentle movement in the scene",
    "editorial card composition with calm negative space",
    "intimate still life with symbolic objects, no text",
    "quiet interior scene with natural window light",
    "poetic landscape with layered depth",
    "minimal centered composition with soft atmosphere",
    "cinematic close-up with gentle depth of field",
]


def _build_default_image_theme(sphere: str, subsphere: Optional[str]) -> str:
    """
    Англоязычное описание сцены по умолчанию для генерации изображений.
    """
    sphere_key = sphere.lower()
    subsphere_key = (subsphere or "").lower()

    if sphere_key == "career":
        return "a refined workspace in calm natural light, suggesting clarity, professional dignity and sustainable progress"
    if sphere_key == "self_realization":
        return "a creative studio with an open window, sketchbook, warm light and flowing curtains, suggesting personal voice and imperfect artistic process"
    if sphere_key == "inner_peace":
        return "a quiet lake with mist, soft morning light and breathing space, suggesting emotional steadiness"
    if sphere_key == "relationships":
        if subsphere_key == "partner":
            return "a shared tea table and two chairs in warm domestic light, subtle closeness with respectful distance"
        if subsphere_key == "colleagues":
            return "a calm shared workspace with warm light, clear surfaces and a respectful sense of collaboration"
        if subsphere_key == "friends":
            return "a cozy table with cups, linen and soft light, suggesting friendship, support and honest presence"
        return "a shared tea table, two chairs, warm domestic light, hands and subtle closeness without romantic clichés"
    if sphere_key == "health":
        return "morning air, clear water, linen, green leaves and gentle movement, creating a restorative atmosphere"
    if sphere_key == "money":
        return "a refined interior with warm light, calm order, a beautiful desk, open notebook and sunlight, suggesting enoughness, stability and dignity"
    if sphere_key == "spirituality":
        return "a grounded luminous scene with candles, soft geometry, quiet ritual and subtle light, without exaggerated mysticism"
    return "an atmospheric, elegant scene suggesting inner balance, dignity and quiet hope through poetic visual metaphor"


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
        "soft_editorial": (
            "soft editorial illustration, premium wellness aesthetic, muted colors, "
            "elegant composition, gentle natural light"
        ),
        "dreamy_painterly": (
            "dreamy painterly illustration, visible soft brushwork, poetic atmosphere, "
            "warm depth, refined color palette"
        ),
        "minimal_botanical": (
            "minimal botanical composition, sage green, cream and beige palette, "
            "clean meditative design, organic shapes"
        ),
        "cinematic_light": (
            "cinematic natural light, emotional realism, soft shadows, quiet storytelling, refined composition"
        ),
        "ethereal_landscape": (
            "ethereal misty landscape, contemplative stillness, atmospheric depth, quiet beauty, soft morning light"
        ),
        "symbolic_luxe": (
            "refined abstract symbolic art, subtle luxury mood, harmonious textures, soft glow, no literal icons"
        ),
    }
    return mapping.get(style, "soft, inspiring, visually harmonious style")


def _avoid_literal_symbols_clause(sphere: str) -> str:
    base = (
        "Avoid: stock photo vibe, corporate illustration vibe, clipart icons, infographic elements, "
        "typography, dollar signs, coins, piggy banks, charts, arrows, currency symbols, "
        "generic business success icons, generic silhouette with arms wide open at sunset unless explicitly requested, "
        "cheap AI fantasy poster look, oversaturated colors, cluttered composition."
    )
    sphere_key = sphere.lower()
    if sphere_key == "money":
        return (
            base
            + " For money, do not use dollar signs, coins, stacks of money, charts, arrows or piggy banks; "
            "use refined interior, warm light, calm order, beautiful desk, open notebook, sunlight, stable grounded atmosphere, subtle enoughness and dignity."
        )
    if sphere_key == "self_realization":
        return (
            base
            + " For self-realization, avoid the cliché of a person at sunset with arms wide open; "
            "prefer creative studio, open window, sketchbook, warm light, flowing curtains and artistic process."
        )
    if sphere_key == "relationships":
        return (
            base
            + " For relationships, avoid hearts and romantic greeting-card clichés; "
            "prefer shared tea table, two chairs, warm domestic light, subtle closeness, respectful distance, hands and soft atmosphere."
        )
    if sphere_key == "spirituality":
        return base + " For spirituality, avoid exaggerated mysticism and glowing third-eye imagery."
    return base


def _build_image_prompt(
    style: str,
    sphere: str,
    subsphere: Optional[str],
    user_text: Optional[str],
    custom_style_description: Optional[str] = None,
    color_mood: Optional[str] = None,
    composition_hint: Optional[str] = None,
) -> str:
    """
    Формирует англоязычный промпт для генерации изображения.
    Случайные color_mood и composition_hint добавляют разнообразие при каждой генерации.
    """
    base_theme = _build_default_image_theme(sphere, subsphere)

    if style.lower() == "custom" and custom_style_description:
        style_phrase = f"in the style: {custom_style_description}"
    else:
        style_phrase = _style_to_phrase(style)
        if custom_style_description:
            style_phrase = f"{style_phrase}. Additional: {custom_style_description}"

    extra = ""
    if user_text:
        extra = f" The scene subtly reflects the idea: \"{user_text}\"."

    color_part = f" Color and lighting: {color_mood}." if color_mood else ""
    comp_part = f" Composition: {composition_hint}." if composition_hint else ""

    avoid_clause = _avoid_literal_symbols_clause(sphere)

    return (
        f"{base_theme}.{extra} "
        "Create an atmospheric, elegant, emotionally resonant illustration for a daily affirmation card. "
        "Use a refined, calm, artistic and visually cohesive scene with poetic visual metaphor instead of literal symbols. "
        f"Atmosphere: premium wellness, editorial, painterly, calm and hopeful, suitable for affirmation practice about {sphere}. "
        f"Visual style: {style_phrase}.{color_part}{comp_part} "
        "No text, no words, no letters, no numbers. "
        f"{avoid_clause}"
    )


def _ensure_no_text_clause(prompt: str) -> str:
    p = prompt.strip()
    low = p.lower()
    if "no text" in low or "no words" in low or "without text" in low:
        return p
    return p.rstrip(" .") + ". No text, no words on the image."


async def generate_image(
    style: str,
    sphere: str,
    user_text: Optional[str] = None,
    subsphere: Optional[str] = None,
    custom_style_description: Optional[str] = None,
    output_dir: Optional[str] = None,
    file_basename: Optional[str] = None,
    prompt_override: Optional[str] = None,
    image_prompt_trace: Optional[str] = None,
) -> str:
    """
    Асинхронно вызывает OpenAI-совместимый image API через ProxiAPI и сохраняет PNG.
    Случайные цвет и композиция добавляют разнообразие при каждой генерации.
    Возвращает путь к файлу.
    """
    settings = get_settings()
    if output_dir is None:
        output_dir = get_outputs_dir()

    base_url = settings.proxi_base_url.rstrip("/")
    url = f"{base_url}/images/generations"

    color_mood = random.choice(_COLOR_MOODS)
    composition_hint = random.choice(_COMPOSITION_HINTS)
    if prompt_override:
        prompt = _ensure_no_text_clause(prompt_override)
    else:
        prompt = _build_image_prompt(
            style=style,
            sphere=sphere,
            subsphere=subsphere,
            user_text=user_text,
            custom_style_description=custom_style_description,
            color_mood=color_mood,
            composition_hint=composition_hint,
        )
    trace = image_prompt_trace or ("override" if prompt_override else "template")

    payload = {
        "model": settings.image_model,
        "prompt": prompt,
        "n": 1,
        "size": settings.image_size,
        "response_format": "b64_json",
    }

    headers = {
        "Authorization": f"Bearer {settings.proxi_api_key}",
        "Content-Type": "application/json",
    }

    os.makedirs(output_dir, exist_ok=True)

    timeout_sec = max(30, settings.image_api_timeout_seconds)
    timeout = aiohttp.ClientTimeout(total=timeout_sec)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=timeout) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error("Image API error: status=%s, body=%s", resp.status, text)
                    raise RuntimeError(f"Image generation failed with status {resp.status}")
                data = await resp.json()
    except asyncio.TimeoutError as exc:
        logger.warning("Image API timeout after %ss", timeout_sec)
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
        unique = uuid.uuid4().hex[:8]
        file_basename = f"affirmation_{safe_sphere}_{safe_style}_{unique}"

    filename = f"{file_basename}.png"
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "wb") as f:
        f.write(image_bytes)

    meta = {
        "prompt": prompt,
        "prompt_source": trace,
        "style": style,
        "sphere": sphere,
        "subsphere": subsphere,
        "user_text": user_text,
        "custom_style_description": custom_style_description,
        "model": settings.image_model,
        "size": settings.image_size,
    }
    meta_path = os.path.join(output_dir, f"{file_basename}_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    logger.info("Image saved to %s", output_path)
    return output_path

