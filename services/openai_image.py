import asyncio
import base64
import json
import logging
import os
import random
import uuid
from typing import Optional

import aiohttp

from config import get_image_provider_config, get_outputs_dir
from services.ritual_config import (
    PHOTO_SCENE_PRESETS,
    STYLE_DESCRIPTIONS,
    has_coastal_intent,
    normalize_style_key,
    normalize_visual_mode,
    resolve_photo_scene_preset,
    resolve_style,
    visual_mode_for_style,
)

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
        return (
            "calm order, morning light, clarity, dignity, enoughness and stability; "
            "bright organized desk without financial props, sunlight on a clean table, notebook without readable text, "
            "ceramic cup, plant, open window, calm interior and peaceful natural light"
        )
    if sphere_key == "spirituality":
        return "a grounded luminous scene with candles, soft geometry, quiet ritual and subtle light, without exaggerated mysticism"
    return "an atmospheric, elegant scene suggesting inner balance, dignity and quiet hope through poetic visual metaphor"


def _build_photo_image_theme(sphere: str, subsphere: Optional[str]) -> str:
    """
    Photo mode converts abstract themes into concrete scenes that can plausibly be photographed.
    """
    sphere_key = sphere.lower()
    subsphere_key = (subsphere or "").lower()

    if sphere_key == "career":
        return "realistic editorial photo of a bright workspace, open window, real desk, notebook without readable text, cup, plant, morning daylight, clean perspective and calm professional order"
    if sphere_key == "self_worth":
        return "real-life photo of a sunlit room corner, real flowers or botanical branch, linen, ceramic cup, window light, quiet dignity and enough space around the subject"
    if sphere_key == "self_realization":
        return "realistic lifestyle photo of a creative desk or studio corner, sketchbook without readable text, pencils, paper, natural daylight, window, plants, signs of active creative work"
    if sphere_key == "inner_peace":
        return "realistic nature photo of a riverside, quiet lake edge, morning park path, meadow or room corner with window light, clear real-world subject and natural daylight"
    if sphere_key == "relationships":
        if subsphere_key == "partner":
            return "realistic interior photo of a shared tea table with two cups, two chairs, warm window light, real ceramics and linen, respectful closeness without greeting-card romance"
        if subsphere_key == "colleagues":
            return "realistic editorial photo of a calm shared workspace, two notebooks without readable text, cups, plants, natural daylight, clean surfaces and collaborative atmosphere"
        if subsphere_key == "friends":
            return "realistic lifestyle photo of a cozy table with cups, linen, fruit or flowers, soft daylight, real materials and friendly presence without drawn symbols"
        return "realistic interior photo of two cups on a bright table, real chairs, window light, plants and warm domestic atmosphere"
    if sphere_key == "health":
        return "realistic nature or lifestyle photo with fresh greenery, glass of water, linen, sunlight through leaves, morning air, real botanical corner or park path"
    if sphere_key == "money":
        return (
            "realistic interior still life photo of calm order and stability, bright organized desk without financial props, "
            "sunlight on a clean table, notebook without readable text, ceramic cup, plant, open window, real wood, linen and glass"
        )
    if sphere_key == "spirituality":
        return "realistic still life photo of a quiet grounded ritual corner, candle, ceramic bowl, linen, plant, natural window light, physically real objects and believable shadows"
    return "realistic lifestyle photo of a real table, window light, plant, ceramic cup, linen and calm everyday scene with a clear photographed subject"


def _style_to_phrase(style: str) -> str:
    """
    Преобразует выбранный стиль в фразу для промпта.
    """
    style = normalize_style_key(style.lower())
    mapping = {
        "realistic": "realistic style, detailed, soft natural light",
        "cartoon": "soft cartoon style, friendly lines, gentle colors",
        "mandala": "intricate mandala, symmetric, meditative patterns",
        "sacred_geometry": "sacred geometry patterns, harmonious proportions, glowing lines",
        "nature": "lush nature scene, trees, sky, soft sun rays",
        "cosmos": "cosmic scene with stars, galaxies, soft glowing nebulae",
        "abstract": "abstract art, flowing shapes, harmonious colors",
        "sunny_photo_scene": STYLE_DESCRIPTIONS["sunny_photo_scene"],
        "living_nature_photo": STYLE_DESCRIPTIONS["living_nature_photo"],
        "sea_coast_photo": STYLE_DESCRIPTIONS["sea_coast_photo"],
        "light_interior_photo": STYLE_DESCRIPTIONS["light_interior_photo"],
        "calm_lifestyle_photo": STYLE_DESCRIPTIONS["calm_lifestyle_photo"],
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


def _avoid_literal_symbols_clause(sphere: str, visual_mode: str = "illustration") -> str:
    if visual_mode == "photo":
        base = _build_photo_negative_prompt()
    else:
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
            + " For money and stability, do not show money literally. Do not include coins, stacks of coins, money, "
            "banknotes, cash, wallets, piggy banks, dollar signs, euro signs, currency symbols, charts, arrows, "
            "financial icons, payment cards, calculators as the main symbol, or business success props. "
            "Use visual metaphors of calm order, morning light, clarity, dignity, enoughness and stability instead. "
            "Prefer a bright organized desk without financial props, sunlight on a clean table, notebook without readable text, "
            "ceramic cup, plant, open window, calm interior, natural light and a peaceful sense of order and stability."
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


def _build_photo_negative_prompt() -> str:
    return (
        "Photo negative prompt: no text, no letters, no numbers, no typography, no logos, no watermarks, "
        "no charts, no arrows, no currency symbols, no coins, no piggy banks, "
        "no illustration, no painting, no watercolor, no gouache, no oil painting, no canvas texture, "
        "no painterly, no brush strokes, no brushstrokes, no drawn image, no digital art, no digital painting, no digital illustration, "
        "no stylized artwork, no pastel illustration, no poster art, no poster look, no poster-like image, no poster illustration, "
        "no greeting card art, no greeting card illustration, no greeting-card illustration, no decorative illustration, no storybook look, "
        "no dreamy painterly haze, no dreamy painted haze, no soft painterly haze, no soft painterly look, no overly soft art look, "
        "no flat vector, no fantasy art, no 3D render, no CGI, no cartoon, no vector art, no flat art, "
        "no overly smooth AI art look, not an art print, not a drawn scene, not stylized artwork, not a painting-like scene, "
        "no gloomy mood, no underexposed image, no low-contrast scene, no cheap stock-business vibe."
    )


def _build_photo_prompt(
    *,
    base_theme: str,
    photo_scene: str,
    extra: str,
    style_phrase: str,
    color_part: str,
    comp_part: str,
    avoid_clause: str,
    coastal_clause: str = "",
) -> str:
    return (
        f"{base_theme}.{extra} "
        f"{photo_scene} "
        "PHOTO BRANCH ONLY. Create a genuine realistic photo, not artwork. "
        "The final image must read immediately as a real photograph and a real photographic scene. "
        "Use realistic photography, lifestyle or editorial photo aesthetic, camera-like realism, "
        "natural daylight or believable indoor daylight, physically plausible lighting, realistic lens optics, "
        "believable depth of field, authentic photographic detail, realistic textures and materials, "
        "realistic composition, subtle imperfections of real photography, clean but real composition, "
        "candid but composed framing, and serene but real atmosphere. "
        "Translate abstract emotions into concrete real-world scenes: room corner with natural light, "
        "table still life that looks photographed, realistic desk with notebook and cup, real botanical corner, "
        "riverside or meadow photo, park path, morning field, or believable interior lifestyle scene. "
        "If nature appears, it must be realistic nature photography or a believable landscape photo. "
        "If an interior appears, it must be a realistic interior photo with real ceramics, wood, linen, glass, paper or plants. "
        "If the scene is symbolic still life, it must look physically photographed, with real objects and believable shadows. "
        "Do not create a greeting card image, decorative art print, drawn scene or stylized AI illustration. "
        f"{coastal_clause}"
        f"Photo style direction: {style_phrase}.{color_part}{comp_part} "
        f"{avoid_clause}"
    )


def _augment_photo_override_prompt(prompt: str, photo_scene: str, avoid_clause: str) -> str:
    p = _ensure_no_text_clause(prompt)
    return (
        f"{p} "
        f"{photo_scene} "
        "Strict photo branch: realistic photograph, real scene, editorial lifestyle photography, "
        "camera-like image, believable lens optics, realistic materials and textures, "
        "physically plausible natural light, authentic photographic detail, subtle imperfections of real photography. "
        f"{avoid_clause}"
    )


def _coastal_photo_clause() -> str:
    return (
        "Coastal realism is mandatory: clearly visible sea or ocean coastline, open horizon over water, visible shoreline, "
        "waves, surf or sea foam, and at least one explicit coastal element such as sand beach, dunes, rocky shore, driftwood, "
        "seashells, cliffs, coastal path, boardwalk or seabirds. "
        "Avoid inland lakes, rivers, generic botanical still life, landlocked meadow scenes, and interior window scenes unless explicitly requested. "
        "If user intent implies a walk at sunset by the ocean, allow subtle human presence only (footprints, distant solitary figure from behind, "
        "walking path, or edge of dress), calm contemplative mood, no dominant portrait."
    )


def _build_image_prompt(
    style: str,
    sphere: str,
    subsphere: Optional[str],
    user_text: Optional[str],
    custom_style_description: Optional[str] = None,
    color_mood: Optional[str] = None,
    composition_hint: Optional[str] = None,
    image_hint: Optional[str] = None,
    visual_mode: Optional[str] = None,
    focus_key: Optional[str] = None,
    photo_scene_preset: Optional[str] = None,
) -> str:
    """
    Формирует англоязычный промпт для генерации изображения.
    Случайные color_mood и composition_hint добавляют разнообразие при каждой генерации.
    """
    requested_style = style
    style = resolve_style(style, sphere, visual_mode=visual_mode)
    coastal_intent = has_coastal_intent(user_text) or has_coastal_intent(image_hint)
    if normalize_visual_mode(visual_mode) == "photo" and requested_style == "auto" and coastal_intent:
        style = "sea_coast_photo"
    effective_visual_mode = visual_mode_for_style(normalize_visual_mode(visual_mode), style)
    base_theme = (
        _build_photo_image_theme(sphere, subsphere)
        if effective_visual_mode == "photo"
        else _build_default_image_theme(sphere, subsphere)
    )
    if image_hint:
        base_theme = f"{base_theme}; focus visual hint: {image_hint}"
    photo_scene = ""
    if effective_visual_mode == "photo":
        if coastal_intent and style == "sea_coast_photo":
            scene_key = photo_scene_preset or resolve_photo_scene_preset(sphere, "sea_coast_photo", focus_key=focus_key)
        else:
            scene_key = photo_scene_preset or resolve_photo_scene_preset(sphere, style, focus_key=focus_key)
        photo_scene = PHOTO_SCENE_PRESETS.get(scene_key, PHOTO_SCENE_PRESETS["window_still_life"])

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

    avoid_clause = _avoid_literal_symbols_clause(sphere, effective_visual_mode)

    if effective_visual_mode == "photo":
        coastal_clause = _coastal_photo_clause() if (style == "sea_coast_photo" or coastal_intent) else ""
        return _build_photo_prompt(
            base_theme=base_theme,
            photo_scene=photo_scene,
            extra=extra,
            style_phrase=style_phrase,
            color_part=color_part,
            comp_part=comp_part,
            avoid_clause=avoid_clause,
            coastal_clause=coastal_clause,
        )

    return (
        f"{base_theme}.{extra} "
        "Create a beautiful bright daily affirmation image for a Telegram card. "
        "The image should feel uplifting, calming, warm, clear and emotionally encouraging. "
        "Prefer luminous natural light, open air, fresh morning or golden-hour atmosphere, visible depth, clean composition, natural beauty and a hopeful mood. "
        "The image must look clear and pleasant on a phone screen, with bright exposure, readable subject separation, natural detail and elegant simplicity. "
        "Use a high-quality soft semi-realistic or gentle illustration look. "
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
    visual_mode: Optional[str] = None,
    focus_key: Optional[str] = None,
    color_mood: Optional[str] = None,
    composition_hint: Optional[str] = None,
    recent_scene_presets: Optional[list[str]] = None,
) -> str:
    """
    Асинхронно вызывает OpenAI-совместимый image API через ProxiAPI и сохраняет PNG.
    Случайные цвет и композиция добавляют разнообразие при каждой генерации.
    Возвращает путь к файлу.
    """
    resolved_style = resolved_style_override or resolve_style(style, sphere, focus_key=focus_key, visual_mode=visual_mode)
    effective_visual_mode = visual_mode_for_style(normalize_visual_mode(visual_mode), resolved_style)
    photo_scene_preset = None
    if effective_visual_mode == "photo":
        photo_scene_preset = resolve_photo_scene_preset(
            sphere,
            resolved_style,
            focus_key=focus_key,
            recent_scene_presets=recent_scene_presets,
        )
    if output_dir is None:
        output_dir = get_outputs_dir()

    image_provider = get_image_provider_config()
    base_url = image_provider.base_url.rstrip("/")
    url = f"{base_url}/images/generations"

    color_mood = color_mood or random.choice(_COLOR_MOODS)
    composition_hint = composition_hint or random.choice(_COMPOSITION_HINTS)
    if prompt_override:
        if effective_visual_mode == "photo":
            scene_text = PHOTO_SCENE_PRESETS.get(photo_scene_preset or "", PHOTO_SCENE_PRESETS["window_still_life"])
            prompt = _augment_photo_override_prompt(
                prompt_override,
                scene_text,
                _avoid_literal_symbols_clause(sphere, effective_visual_mode),
            )
        else:
            prompt = _ensure_no_text_clause(prompt_override)
    else:
        prompt = _build_image_prompt(
            style=resolved_style,
            sphere=sphere,
            subsphere=subsphere,
            user_text=user_text,
            custom_style_description=custom_style_description,
            color_mood=color_mood,
            composition_hint=composition_hint,
            image_hint=image_hint,
            visual_mode=effective_visual_mode,
            focus_key=focus_key,
            photo_scene_preset=photo_scene_preset,
        )
    trace = image_prompt_trace or ("override" if prompt_override else "template")

    payload = {
        "model": image_provider.model,
        "prompt": prompt,
        "n": 1,
        "size": image_provider.size,
        "response_format": "b64_json",
    }

    headers = {
        "Authorization": f"Bearer {image_provider.api_key}",
        "Content-Type": "application/json",
    }

    os.makedirs(output_dir, exist_ok=True)

    timeout_sec = max(30, image_provider.timeout_seconds)
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
        "final_prompt": prompt,
        "prompt_branch": effective_visual_mode,
        "photo_scene_preset": photo_scene_preset,
        "scene_preset": photo_scene_preset,
        "prompt_source": trace,
        "requested_style": style,
        "selected_style": resolved_style,
        "visual_mode": effective_visual_mode,
        "style": style,
        "resolved_style": resolved_style,
        "sphere": sphere,
        "subsphere": subsphere,
        "focus_key": focus_key,
        "color_palette": color_mood,
        "composition_hint": composition_hint,
        "image_size": image_provider.size,
        "user_text": user_text,
        "custom_style_description": custom_style_description,
        "model": image_provider.model,
        "size": image_provider.size,
        "image_provider": image_provider.provider,
    }
    meta_path = os.path.join(output_dir, f"{file_basename}_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    logger.info("Image saved to %s", output_path)
    return output_path

