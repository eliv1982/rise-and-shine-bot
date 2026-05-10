import logging

from config import get_settings
from services.scene_planner import build_scene_image_prompt, normalize_scene_plan

logger = logging.getLogger(__name__)

_LIVING_NATURE_MARKERS = (
    "living_nature_photo",
    "sunny_nature_photo",
    "living_nature",
    "living nature",
    "живая природа",
)

_OUTDOOR_SCENE_TYPES = {
    "forest_path",
    "open_meadow",
    "garden_morning",
    "mountain_view",
    "riverside",
    "autumn_park",
    "sunrise_field",
}


def _safe_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


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
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(text)
    return result


def _coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off", ""):
            return False
    return bool(value)


def is_scene_planner_image_prompt_enabled(settings: object | None = None) -> bool:
    try:
        effective_settings = settings or get_settings()
        return _coerce_bool(getattr(effective_settings, "scene_planner_image_prompt_enabled", False))
    except Exception:
        return False


def should_use_llm_image_prompt_for_fallback(
    *,
    scene_planner_image_prompt_enabled: bool,
    llm_image_prompt_enabled: bool,
) -> bool:
    if scene_planner_image_prompt_enabled:
        return False
    return bool(llm_image_prompt_enabled)


def is_living_nature_style(
    *,
    selected_style: str | None = None,
    resolved_style: str | None = None,
    visual_mode: str | None = None,
    style_mode: str | None = None,
) -> bool:
    values = [selected_style, resolved_style, visual_mode, style_mode]
    for value in values:
        text = _clean_str(value)
        if not text:
            continue
        normalized = text.lower().replace("-", "_")
        normalized = normalized.replace("  ", " ")
        for marker in _LIVING_NATURE_MARKERS:
            if marker in normalized:
                return True
    return False


def build_living_nature_constraints() -> list[str]:
    return [
        "no indoor scene",
        "no interior",
        "no room",
        "no table",
        "no desk",
        "no mug",
        "no cup",
        "no notebook",
        "no book",
        "no window",
        "no windowsill",
        "no furniture",
        "no chair",
        "no laptop",
        "no still life props",
        "outdoor nature scene only",
    ]


def build_controlled_scene_prompt(
    *,
    scene_plan: dict,
    focus_title: str | None = None,
    visual_mode: str | None = None,
    selected_style: str | None = None,
    resolved_style: str | None = None,
    color_palette: str | None = None,
    composition_hint: str | None = None,
    sphere: str | None = None,
    subsphere: str | None = None,
    language: str = "ru",
) -> str:
    normalized = normalize_scene_plan(scene_plan)
    prompt = build_scene_image_prompt(normalized, language=language).strip()

    extras = []
    focus = _clean_str(focus_title)
    if focus:
        extras.append(f"Emotional focus: {focus}.")
    if _clean_str(sphere):
        sphere_part = f"Sphere: {_clean_str(sphere)}."
        if _clean_str(subsphere):
            sphere_part = f"Sphere: {_clean_str(sphere)}. Subsphere: {_clean_str(subsphere)}."
        extras.append(sphere_part)
    if _clean_str(color_palette):
        extras.append(f"Color direction: {_clean_str(color_palette)}.")
    if _clean_str(composition_hint):
        extras.append(f"Composition preference: {_clean_str(composition_hint)}.")
    if _clean_str(visual_mode):
        extras.append(f"Visual mode: {_clean_str(visual_mode)}.")
    if _clean_str(resolved_style):
        extras.append(f"Style direction: {_clean_str(resolved_style)}.")
    elif _clean_str(selected_style):
        extras.append(f"Style direction: {_clean_str(selected_style)}.")

    if is_living_nature_style(
        selected_style=selected_style,
        resolved_style=resolved_style,
        visual_mode=visual_mode,
    ):
        nature_constraints = build_living_nature_constraints()
        extras.append(
            "Positive direction: outdoor nature scene, forest, meadow, garden, riverside, mountain path, field, trees, grass, plants in a natural outdoor setting."
        )
        extras.append(
            "Living nature constraints: " + ", ".join(nature_constraints) + "."
        )

    return " ".join([prompt] + extras).strip()


def select_photo_scene_preset_override(
    *,
    scene_plan: dict | None,
    selected_style: str | None = None,
    resolved_style: str | None = None,
    visual_mode: str | None = None,
) -> str | None:
    if is_living_nature_style(
        selected_style=selected_style,
        resolved_style=resolved_style,
        visual_mode=visual_mode,
    ):
        return "outdoor_path"

    safe_plan = _safe_dict(scene_plan)
    scene_type = _clean_str(safe_plan.get("scene_type"))
    if scene_type in _OUTDOOR_SCENE_TYPES:
        return "outdoor_path"
    return None
