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
from services.ritual_config import STYLE_DESCRIPTIONS, resolve_style

logger = logging.getLogger(__name__)

# Варианты цветовой гаммы и атмосферы для разнообразия картинок
_COLOR_MOODS = [
    "warm sunrise gold, soft blue, sea light",
    "spring green, blossom white, clear sky blue",
    "pearl daylight, ivory, pale sage",
    "honey sunlight, cream, gentle terracotta",
    "pale turquoise, sand, warm white",
    "fresh meadow green, daisy white, sunlight yellow",
    "soft peach dawn, warm cloud grey, light gold",
    "morning blue, silver light, white mist",
    "blossom pink, pale green, warm ivory",
    "dawn pearl, misty blue, pale gold",
    "clear aqua, sunlit cream, tender green",
    "fresh mint, white linen, warm daylight",
    "soft lavender, pearl white, pale gold",
    "bright sage, cream, apricot light",
    "warm walnut, parchment, soft sage",
    "sea glass, fog, linen white",
]

# Варианты композиции
_COMPOSITION_HINTS = [
    "open airy composition with breathable space and clear subject separation",
    "bright nature scene with foreground detail and visible depth",
    "sunlit landscape with sky, water or meadow as the main visual",
    "flowering branches or trees in sunlight with a clean background",
    "warm still life by a window, no visible text",
    "light workspace with morning light and no visible writing",
    "gentle symbolic nature metaphor, clear on a phone screen",
    "balanced daily card composition with optimistic open space",
    "intimate still life with symbolic objects, no text",
    "quiet interior scene with natural window light",
    "soft landscape with readable focal point and bright exposure",
]


def _build_default_image_theme(sphere: str, subsphere: Optional[str]) -> str:
    """
    Англоязычное описание сцены по умолчанию для генерации изображений.
    """
    sphere_key = sphere.lower()
    subsphere_key = (subsphere or "").lower()

    if sphere_key == "career":
        return "light workspace, open window, desk with notebook but no visible text, morning light, clear path or forward movement metaphor, no lonely dark interior portrait"
    if sphere_key == "self_worth":
        return "blooming branch, graceful flower in morning light, warm airy interior, clean uplifting natural metaphor, gentle beauty without drama"
    if sphere_key == "self_realization":
        return "creative desk in daylight, open notebook without text, flowering field, birds, sky, movement, sunlight, expression and openness"
    if sphere_key == "inner_peace":
        return "lake at dawn, gentle river, light mist with sunrise, calm open sky, quiet water reflections"
    if sphere_key == "relationships":
        if subsphere_key == "partner":
            return "a shared tea table and two chairs in warm domestic light, subtle closeness with respectful distance"
        if subsphere_key == "colleagues":
            return "a calm shared workspace with warm light, clear surfaces and a respectful sense of collaboration"
        if subsphere_key == "friends":
            return "a cozy table with cups, linen and soft light, suggesting friendship, support and honest presence"
        return "two cups on a bright table, two birds in open sky, shared warm space, light and closeness without melodrama"
    if sphere_key == "health":
        return "fresh greenery, sunlight through leaves, water, air, morning freshness, soft movement in nature, bright restorative mood"
    if sphere_key == "money":
        return "calm abundance through light and order, warm sunlight, organized peaceful setting, natural prosperity metaphors, no dark room and no literal finance symbols"
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
        "bright_nature_card": STYLE_DESCRIPTIONS["bright_nature_card"],
        "quiet_interior": STYLE_DESCRIPTIONS["quiet_interior"],
        "textured_collage": STYLE_DESCRIPTIONS["textured_collage"],
        "soft_editorial": (
            "soft editorial illustration, premium wellness aesthetic, muted colors, "
            "elegant composition, gentle natural light"
        ),
        "dreamy_painterly": STYLE_DESCRIPTIONS["dreamy_painterly"],
        "minimal_botanical": STYLE_DESCRIPTIONS["minimal_botanical"],
        "cinematic_light": STYLE_DESCRIPTIONS["cinematic_light"],
        "ethereal_landscape": STYLE_DESCRIPTIONS["ethereal_landscape"],
        "symbolic_luxe": STYLE_DESCRIPTIONS["symbolic_luxe"],
    }
    return mapping.get(style, "soft, inspiring, visually harmonious style")


def _avoid_literal_symbols_clause(sphere: str) -> str:
    base = (
        "Avoid: stock photo vibe, corporate illustration vibe, clipart icons, infographic elements, "
        "typography, logos, watermarks, dollar signs, coins, piggy banks, charts, arrows, currency symbols, "
        "generic business success icons, generic silhouette with arms wide open at sunset unless explicitly requested, "
        "cheap AI fantasy poster look, oversaturated colors, cluttered composition, flat minimal icon art, "
        "simplistic poster, generic centered portrait, direct eye contact portrait by default, "
        "centered face dominating the composition, gloomy mood, depressive mood, muddy colors, underexposed dark image, "
        "low-contrast scene, abstract spiritual fog as the main visual, close-up portrait by default, "
        "sad lonely human figure as the default motif, solitary person in a vast landscape unless explicitly intended, "
        "heavy painterly blur, oversimplified beige flower unless the chosen style is minimal_botanical."
    )
    sphere_key = sphere.lower()
    if sphere_key == "money":
        return (
            base
            + " For money, do not use dollar signs, coins, stacks of money, charts, arrows or piggy banks; "
            "use bright order, warm sunlight, organized peaceful setting, natural prosperity metaphors and calm enoughness."
        )
    if sphere_key == "career":
        return (
            base
            + " For career, avoid a lonely person on a mountain peak; prefer light workspace, morning light, open window, clear path and calm professional dignity."
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
    image_hint: Optional[str] = None,
) -> str:
    """
    Формирует англоязычный промпт для генерации изображения.
    Случайные color_mood и composition_hint добавляют разнообразие при каждой генерации.
    """
    style = resolve_style(style, sphere)
    base_theme = _build_default_image_theme(sphere, subsphere)
    if image_hint:
        base_theme = f"{base_theme}; focus visual hint: {image_hint}"

    if style.lower() == "custom" and custom_style_description:
        style_phrase = f"in the style: {custom_style_description}"
    else:
        style_phrase = _style_to_phrase(style)
        if custom_style_description:
            style_phrase = f"{style_phrase}. Additional: {custom_style_description}"

    extra = ""
    if user_text:
        extra = f" The scene subtly reflects the idea: \"{user_text}\"."

    color_part = f" Color palette and lighting: {color_mood}." if color_mood else ""
    comp_part = f" Composition: {composition_hint}." if composition_hint else ""

    avoid_clause = _avoid_literal_symbols_clause(sphere)

    return (
        f"{base_theme}.{extra} "
        "Create a beautiful bright daily affirmation image for a Telegram card. "
        "The image should feel uplifting, calming, warm, clear and emotionally encouraging. "
        "Prefer luminous natural light, open air, fresh morning or golden-hour atmosphere, visible depth, clean composition, natural beauty and a hopeful mood. "
        "The image must look clear and pleasant on a phone screen, with bright exposure, readable subject separation, natural detail and elegant simplicity. "
        "Use a photorealistic or high-quality soft semi-realistic look. "
        "Prefer nature scenes, lake, sea, sky, soft landscape, flowering branches, trees in sunlight, meadow, garden, morning light, bright still life with window light, light workspace without visible text, two cups or warm table for relationships, and gentle symbolic nature metaphors. "
        "If a person appears, keep them small, from behind or side view, not a dominant portrait, with no direct eye contact. "
        f"Atmosphere: bright daily card, elegant, simple, warm and hopeful, suitable for affirmation practice about {sphere}. "
        f"Visual style: {style_phrase}.{color_part}{comp_part} "
        "No text, no words, no letters, no numbers, no typography, no logos, no watermarks. "
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
    image_hint: Optional[str] = None,
    resolved_style_override: Optional[str] = None,
    focus_key: Optional[str] = None,
    color_mood: Optional[str] = None,
    composition_hint: Optional[str] = None,
) -> str:
    """
    Асинхронно вызывает OpenAI-совместимый image API через ProxiAPI и сохраняет PNG.
    Случайные цвет и композиция добавляют разнообразие при каждой генерации.
    Возвращает путь к файлу.
    """
    settings = get_settings()
    resolved_style = resolved_style_override or resolve_style(style, sphere, focus_key=focus_key)
    if output_dir is None:
        output_dir = get_outputs_dir()

    base_url = settings.proxi_base_url.rstrip("/")
    url = f"{base_url}/images/generations"

    color_mood = color_mood or random.choice(_COLOR_MOODS)
    composition_hint = composition_hint or random.choice(_COMPOSITION_HINTS)
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
            image_hint=image_hint,
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
        safe_style = resolved_style.replace(" ", "_").lower()
        unique = uuid.uuid4().hex[:8]
        file_basename = f"affirmation_{safe_sphere}_{safe_style}_{unique}"

    filename = f"{file_basename}.png"
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "wb") as f:
        f.write(image_bytes)

    meta = {
        "prompt": prompt,
        "prompt_source": trace,
        "requested_style": style,
        "selected_style": resolved_style,
        "style": style,
        "resolved_style": resolved_style,
        "sphere": sphere,
        "subsphere": subsphere,
        "focus_key": focus_key,
        "color_palette": color_mood,
        "composition_hint": composition_hint,
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

