from dataclasses import dataclass
from typing import Any, Optional

from services.ritual_config import normalize_visual_mode


@dataclass(frozen=True)
class GenerationContextSnapshot:
    sphere: Optional[str]
    subsphere: Optional[str]
    theme_text: Optional[str]
    style: str
    custom_style_description: Optional[str]
    visual_mode: str
    last_stt_meta: Optional[dict[str, Any]]
    recent_generation_history: list[dict[str, Any]]


def build_generation_context_snapshot(
    data: dict[str, Any],
    *,
    theme_text: Optional[str],
) -> GenerationContextSnapshot:
    return GenerationContextSnapshot(
        sphere=data.get("sphere"),
        subsphere=data.get("subsphere"),
        theme_text=theme_text,
        style=data.get("style") or "nature",
        custom_style_description=data.get("custom_style_description"),
        visual_mode=normalize_visual_mode(data.get("visual_mode")),
        last_stt_meta=data.get("last_stt_meta"),
        recent_generation_history=list(data.get("recent_generation_history") or []),
    )
