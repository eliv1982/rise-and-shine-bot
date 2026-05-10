import json

VALID_HUMAN_PRESENCE = [
    "none",
    "single_person",
    "hands_only",
    "distant_figure",
]

DEFAULT_CLICHE_AVOID = [
    "mug",
    "notebook",
    "table",
    "window",
    "beach",
    "human",
    "crowd",
    "extra people",
    "generic wellness stock photo",
]

DEFAULT_SCENE_FALLBACK_ORDER = [
    "forest_path",
    "open_meadow",
    "garden_morning",
]

SCENE_PRESETS = {
    "forest_path": {
        "setting": "quiet forest path with soft morning light",
        "main_subject": "narrow path between trees and tall grasses",
        "visual_motifs": ["forest", "path", "morning_light"],
        "composition": "wide natural landscape, open depth, not table-centered",
        "lighting": "soft morning light",
        "mood": "quiet self-trust and spaciousness",
    },
    "open_meadow": {
        "setting": "open meadow with airy horizon and gentle daylight",
        "main_subject": "grasses and wildflowers moving in light wind",
        "visual_motifs": ["meadow", "field", "open_space"],
        "composition": "wide open landscape with breathing space",
        "lighting": "clear soft daylight",
        "mood": "freedom, lightness and inner steadiness",
    },
    "garden_morning": {
        "setting": "calm garden in the morning with dew and soft light",
        "main_subject": "garden path and flowering plants in fresh air",
        "visual_motifs": ["garden", "flowers", "morning_light"],
        "composition": "balanced garden scene with natural depth",
        "lighting": "fresh morning light",
        "mood": "gentle renewal and calm optimism",
    },
    "quiet_city_morning": {
        "setting": "quiet city street in the early morning",
        "main_subject": "empty urban street with soft reflections and stillness",
        "visual_motifs": ["city", "street", "morning_light"],
        "composition": "clean urban perspective with open foreground",
        "lighting": "soft cool morning light",
        "mood": "clarity, dignity and calm forward movement",
    },
    "botanical_still_life": {
        "setting": "refined botanical still life in natural daylight",
        "main_subject": "plant forms and flowers arranged with calm simplicity",
        "visual_motifs": ["flowers", "plant", "botanical"],
        "composition": "minimal still life with elegant negative space",
        "lighting": "soft window-adjacent daylight",
        "mood": "quiet care and grounded beauty",
    },
    "hands_detail": {
        "setting": "close lifestyle scene focused on hands and meaningful detail",
        "main_subject": "hands interacting with natural objects or fabric",
        "visual_motifs": ["hands", "detail", "presence"],
        "composition": "close but uncluttered detail shot",
        "lighting": "soft directional daylight",
        "mood": "intimacy, tenderness and grounded attention",
    },
    "mountain_view": {
        "setting": "clear mountain view with expansive air and distance",
        "main_subject": "mountain ridges and open horizon",
        "visual_motifs": ["mountain", "horizon", "open_space"],
        "composition": "wide landscape with layered depth",
        "lighting": "clean natural daylight",
        "mood": "perspective, resilience and calm strength",
    },
    "riverside": {
        "setting": "quiet riverside with gentle current and soft greenery",
        "main_subject": "water edge with grasses and calm reflections",
        "visual_motifs": ["riverside", "water", "greenery"],
        "composition": "grounded riverside scene with gentle leading lines",
        "lighting": "soft daylight with light reflections on water",
        "mood": "flow, calm trust and restoration",
    },
    "library_corner": {
        "setting": "peaceful library corner with soft ambient light",
        "main_subject": "shelves, chair and quiet reading atmosphere",
        "visual_motifs": ["library", "books", "quiet_interior"],
        "composition": "intimate interior corner with depth and order",
        "lighting": "warm diffused interior light",
        "mood": "reflection, clarity and inward calm",
    },
    "abstract_light": {
        "setting": "abstract light-filled scene with atmospheric softness",
        "main_subject": "shapes of light, shadow and luminous texture",
        "visual_motifs": ["abstract_light", "glow", "air"],
        "composition": "open abstract composition with spacious balance",
        "lighting": "luminous diffused light",
        "mood": "subtle hope and emotional spaciousness",
    },
    "balcony_garden": {
        "setting": "small balcony garden with fresh air and city quietness",
        "main_subject": "plants, railing light and morning openness",
        "visual_motifs": ["garden", "balcony", "plants"],
        "composition": "layered small-space scene with outward view",
        "lighting": "fresh morning daylight",
        "mood": "small daily joy and grounded optimism",
    },
    "rain_window": {
        "setting": "quiet rain-lit window scene with reflective calm",
        "main_subject": "rain traces, soft glass reflections and light",
        "visual_motifs": ["window", "rain", "light"],
        "composition": "simple reflective composition with soft depth",
        "lighting": "muted rainy daylight",
        "mood": "introspection and emotional softness",
    },
    "autumn_park": {
        "setting": "autumn park with warm leaves and calm pathways",
        "main_subject": "park path framed by autumn trees",
        "visual_motifs": ["path", "trees", "seasonal_leaves"],
        "composition": "gentle park perspective with warm texture",
        "lighting": "soft autumn daylight",
        "mood": "maturity, grounding and peaceful change",
    },
    "sunrise_field": {
        "setting": "sunrise field with open sky and first warm light",
        "main_subject": "field grasses glowing in early sun",
        "visual_motifs": ["sunrise", "field", "open_light"],
        "composition": "wide field scene with clean horizon",
        "lighting": "golden sunrise light",
        "mood": "renewal, hope and quiet beginning",
    },
}


def _safe_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _safe_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return []


def _clean_str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dedupe_stable(items: list) -> list[str]:
    seen = set()
    result = []
    for item in items:
        text = _clean_str(item)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _normalize_human_presence(value) -> str:
    text = _clean_str(value)
    if text in VALID_HUMAN_PRESENCE:
        return text
    return "none"


def build_scene_planner_prompt(
    *,
    focus_title: str | None,
    affirmations: list[str] | None,
    soft_action: str | None,
    visual_memory_context: dict | None,
    language: str = "ru",
) -> str:
    memory = _safe_dict(visual_memory_context)
    aff_list = _dedupe_stable(_safe_list(affirmations))
    focus = _clean_str(focus_title) or "—"
    soft = _clean_str(soft_action) or "—"
    recent_scene_types = ", ".join(_dedupe_stable(_safe_list(memory.get("recent_scene_types")))) or "—"
    recent_motifs = ", ".join(_dedupe_stable(_safe_list(memory.get("recent_motifs")))) or "—"
    overused_motifs = ", ".join(_dedupe_stable(_safe_list(memory.get("overused_motifs")))) or "—"
    hard_avoid = ", ".join(_dedupe_stable(_safe_list(memory.get("hard_avoid_today")))) or "—"
    prefer_scene_types = ", ".join(_dedupe_stable(_safe_list(memory.get("prefer_scene_types")))) or "—"
    affirmations_block = "\n".join(f"- {item}" for item in aff_list) if aff_list else "- —"

    return (
        "You are a Scene Planner for a daily Telegram mood image.\n"
        "Return JSON only.\n"
        "Design one concrete and photographable visual scene that expresses the emotional meaning of the input.\n"
        "Avoid repeats from visual memory context.\n"
        "Avoid hard_avoid_today and recent_scene_types whenever a good alternative exists.\n"
        "Do not use mug, notebook, table, window, beach, or human unless semantically necessary.\n"
        "No crowd. No extra people. No generic wellness stock photo.\n"
        "Prefer nature, garden, forest, meadow, quiet city, hands detail, abstract light, mountain, riverside.\n"
        "Use the emotional meaning from focus_title, affirmations, and soft_action.\n\n"
        f"Interface language: {language}\n"
        f"focus_title: {focus}\n"
        f"soft_action: {soft}\n"
        "affirmations:\n"
        f"{affirmations_block}\n\n"
        "visual_memory_context:\n"
        f"- recent_scene_types: {recent_scene_types}\n"
        f"- recent_motifs: {recent_motifs}\n"
        f"- overused_motifs: {overused_motifs}\n"
        f"- hard_avoid_today: {hard_avoid}\n"
        f"- prefer_scene_types: {prefer_scene_types}\n\n"
        "Expected JSON schema:\n"
        "{\n"
        '  "scene_type": "forest_path",\n'
        '  "setting": "...",\n'
        '  "human_presence": "none",\n'
        '  "main_subject": "...",\n'
        '  "visual_motifs": ["forest", "path", "morning_light"],\n'
        '  "composition": "...",\n'
        '  "lighting": "...",\n'
        '  "mood": "...",\n'
        '  "avoid": ["mug", "notebook", "beach"]\n'
        "}\n"
    )


def parse_scene_plan_response(raw_text: str | None) -> dict | None:
    text = _clean_str(raw_text)
    if not text:
        return None

    candidates = [text]
    if "```" in text:
        chunks = text.split("```")
        for chunk in chunks:
            cleaned = chunk.strip()
            if not cleaned:
                continue
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
            candidates.append(cleaned)

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidates.append(text[first_brace:last_brace + 1].strip())

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def normalize_scene_plan(
    plan: dict | None,
    visual_memory_context: dict | None = None,
) -> dict:
    safe_plan = _safe_dict(plan)
    memory = _safe_dict(visual_memory_context)
    prefer_scene_types = _dedupe_stable(_safe_list(memory.get("prefer_scene_types")))
    scene_type = _clean_str(safe_plan.get("scene_type")) or (prefer_scene_types[0] if prefer_scene_types else "forest_path")
    preset = _safe_dict(SCENE_PRESETS.get(scene_type))

    setting = _clean_str(safe_plan.get("setting")) or _clean_str(preset.get("setting")) or "quiet natural scene with soft light"
    main_subject = _clean_str(safe_plan.get("main_subject")) or _clean_str(preset.get("main_subject")) or "calm visual focal point with open space"
    composition = _clean_str(safe_plan.get("composition")) or _clean_str(preset.get("composition")) or "balanced open composition"
    lighting = _clean_str(safe_plan.get("lighting")) or _clean_str(preset.get("lighting")) or "soft natural light"
    mood = _clean_str(safe_plan.get("mood")) or _clean_str(preset.get("mood")) or "calm, grounded, emotionally spacious"
    human_presence = _normalize_human_presence(safe_plan.get("human_presence"))

    visual_motifs = _dedupe_stable(
        _safe_list(safe_plan.get("visual_motifs")) + _safe_list(preset.get("visual_motifs"))
    )
    avoid = _dedupe_stable(
        _safe_list(safe_plan.get("avoid"))
        + _safe_list(memory.get("hard_avoid_today"))
        + DEFAULT_CLICHE_AVOID
    )

    return {
        "scene_type": scene_type,
        "setting": setting,
        "human_presence": human_presence,
        "main_subject": main_subject,
        "visual_motifs": visual_motifs,
        "composition": composition,
        "lighting": lighting,
        "mood": mood,
        "avoid": avoid,
    }


def build_fallback_scene_plan(
    *,
    focus_title: str | None,
    visual_memory_context: dict | None = None,
) -> dict:
    memory = _safe_dict(visual_memory_context)
    prefer_scene_types = _dedupe_stable(_safe_list(memory.get("prefer_scene_types")))
    scene_type = prefer_scene_types[0] if prefer_scene_types else DEFAULT_SCENE_FALLBACK_ORDER[0]
    preset = _safe_dict(SCENE_PRESETS.get(scene_type))
    focus = _clean_str(focus_title)
    mood = preset.get("mood") or "calm, grounded, emotionally spacious"
    if focus:
        mood = f"calm, grounded atmosphere for: {focus}"

    raw_plan = {
        "scene_type": scene_type,
        "setting": preset.get("setting"),
        "human_presence": "none",
        "main_subject": preset.get("main_subject"),
        "visual_motifs": preset.get("visual_motifs"),
        "composition": preset.get("composition"),
        "lighting": preset.get("lighting"),
        "mood": mood,
        "avoid": _safe_list(memory.get("hard_avoid_today")) + DEFAULT_CLICHE_AVOID,
    }
    return normalize_scene_plan(raw_plan, visual_memory_context=memory)


def build_scene_image_prompt(scene_plan: dict, language: str = "ru") -> str:
    normalized = normalize_scene_plan(scene_plan)
    motifs = ", ".join(normalized["visual_motifs"]) or "quiet natural motifs"
    avoid = ", ".join(normalized["avoid"])
    return (
        f"Scene type: {normalized['scene_type']}. "
        f"Setting: {normalized['setting']}. "
        f"Human presence: {normalized['human_presence']}. "
        f"Main subject: {normalized['main_subject']}. "
        f"Visual motifs: {motifs}. "
        f"Composition: {normalized['composition']}. "
        f"Lighting: {normalized['lighting']}. "
        f"Mood: {normalized['mood']}. "
        f"Avoid: {avoid}. "
        "No crowd. No extra people. Avoid generic wellness stock photo."
    )
