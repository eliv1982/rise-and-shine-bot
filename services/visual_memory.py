from collections import Counter

from database import get_recent_generation_history, get_recent_visual_history
from services.scene_planner import normalize_scene_family

MOTIF_KEYWORDS = {
    "beach": ["beach", "sea", "coast", "shore", "shoreline", "ocean", "waves", "surf"],
    "mug": ["mug", "cup", "tea", "coffee", "ceramic cup"],
    "notebook": ["notebook", "journal", "book", "sketchbook"],
    "table": ["table", "desk", "workspace"],
    "window": ["window"],
    "human": ["human", "woman", "man", "person", "figure", "portrait"],
    "forest": ["forest", "woods", "trees"],
    "garden": ["garden"],
    "meadow": ["meadow", "field"],
    "city": ["city", "urban", "street"],
    "path": ["path", "road", "trail"],
    "flowers": ["flower", "flowers", "vase", "plant", "botanical"],
    "sunrise": ["sunrise", "dawn", "sunset", "golden hour"],
}

CLICHE_MOTIFS = ["beach", "mug", "notebook", "table", "window", "human"]

PREFERRED_SCENE_TYPES = [
    "forest_path",
    "garden_morning",
    "open_meadow",
    "quiet_city_morning",
    "botanical_still_life",
    "hands_detail",
    "mountain_view",
    "riverside",
    "library_corner",
    "abstract_light",
    "balcony_garden",
    "rain_window",
    "autumn_park",
    "sunrise_field",
]


def _safe_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value) -> list:
    return value if isinstance(value, list) else []


def _dedupe_stable(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _count_items(items: list[str]) -> dict[str, int]:
    return dict(Counter(items))


def _extract_scene_types_from_visual(visual_dict: dict, visual_motifs: dict) -> list[str]:
    scene_types = []
    for candidate in (
        visual_dict.get("scene_type"),
        visual_motifs.get("scene_type"),
        _safe_dict(_safe_dict(visual_motifs.get("scene_plan_shadow")).get("scene_plan")).get("scene_type"),
        _safe_dict(visual_motifs.get("scene_prompt_controlled")).get("used_scene_type"),
        _safe_dict(visual_motifs.get("scene_prompt_controlled")).get("scene_type"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            scene_types.append(candidate.strip())
    return _dedupe_stable(scene_types)


def extract_visual_motifs_from_prompt(prompt: str | None) -> list[str]:
    if not isinstance(prompt, str) or not prompt.strip():
        return []

    lowered = prompt.lower()
    motifs = []
    for motif, keywords in MOTIF_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            motifs.append(motif)
    return motifs


def build_visual_memory_context(
    recent_generations: list[dict],
    recent_visuals: list[dict],
    limit: int = 10,
) -> dict:
    safe_generations = _as_list(recent_generations)[:limit]
    safe_visuals = _as_list(recent_visuals)[:limit]

    recent_scene_types_raw = []
    recent_selected_styles_raw = []
    recent_visual_modes_raw = []
    all_prompt_motifs = []
    last_three_cliche_hits = []
    scene_type_counter_items = []
    scene_family_counter_items = []

    for idx, generation in enumerate(safe_generations):
        generation_dict = _safe_dict(generation)
        prompt_motifs = extract_visual_motifs_from_prompt(generation_dict.get("image_prompt"))
        all_prompt_motifs.extend(prompt_motifs)
        if idx < 3:
            last_three_cliche_hits.extend([motif for motif in prompt_motifs if motif in CLICHE_MOTIFS])

    for visual in safe_visuals:
        visual_dict = _safe_dict(visual)
        visual_motifs = _safe_dict(visual_dict.get("visual_motifs"))

        scene_types = _extract_scene_types_from_visual(visual_dict, visual_motifs)
        for scene_type in scene_types:
            recent_scene_types_raw.append(scene_type)
            scene_type_counter_items.append(scene_type)
            family = normalize_scene_family(scene_type)
            if family:
                scene_family_counter_items.append(family)

        selected_style = visual_motifs.get("selected_style")
        if selected_style:
            recent_selected_styles_raw.append(selected_style)

        visual_mode = visual_motifs.get("visual_mode")
        if visual_mode:
            recent_visual_modes_raw.append(visual_mode)

        for motif_key in MOTIF_KEYWORDS:
            value = visual_motifs.get(motif_key)
            if value == motif_key or value is True:
                all_prompt_motifs.append(motif_key)

    motif_counts = _count_items(all_prompt_motifs)
    scene_type_counts = _count_items(scene_type_counter_items)
    scene_family_counts = _count_items(scene_family_counter_items)
    overused_motifs = [motif for motif in MOTIF_KEYWORDS if motif_counts.get(motif, 0) >= 2]
    overused_scene_families = [
        family for family in _dedupe_stable(scene_family_counter_items) if scene_family_counts.get(family, 0) >= 2
    ]
    hard_avoid_today = _dedupe_stable(overused_motifs + last_three_cliche_hits)
    recent_scene_types = _dedupe_stable(recent_scene_types_raw)
    recent_scene_families = _dedupe_stable([normalize_scene_family(scene) for scene in recent_scene_types_raw if normalize_scene_family(scene)])
    recent_selected_styles = _dedupe_stable(recent_selected_styles_raw)
    recent_visual_modes = _dedupe_stable(recent_visual_modes_raw)
    recent_motifs = _dedupe_stable(all_prompt_motifs)
    prefer_scene_types = [scene for scene in PREFERRED_SCENE_TYPES if scene not in recent_scene_types][:8]

    return {
        "limit": limit,
        "recent_scene_types": recent_scene_types,
        "recent_scene_families": recent_scene_families,
        "recent_selected_styles": recent_selected_styles,
        "recent_visual_modes": recent_visual_modes,
        "recent_motifs": recent_motifs,
        "overused_motifs": overused_motifs,
        "overused_scene_families": overused_scene_families,
        "hard_avoid_today": hard_avoid_today,
        "prefer_scene_types": prefer_scene_types,
        "motif_counts": motif_counts,
        "scene_type_counts": scene_type_counts,
        "scene_family_counts": scene_family_counts,
    }


async def get_visual_memory_context(telegram_user_id: int, limit: int = 10) -> dict:
    recent_generations = await get_recent_generation_history(telegram_user_id, limit=limit)
    recent_visuals = await get_recent_visual_history(telegram_user_id, limit=limit)
    return build_visual_memory_context(
        recent_generations=recent_generations,
        recent_visuals=recent_visuals,
        limit=limit,
    )
