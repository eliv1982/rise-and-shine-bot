"""Dry-run inspection of image prompts.

Generates a batch of sample image prompts using the same prompt-building
functions as the real generation flow, WITHOUT making any network/API calls
(no OpenAI, no image API, no YandexGPT). Useful for reviewing prompt text,
length and motif diversity after changes to services/openai_image.py.

Usage:
    python scripts/dry_run_image_prompts.py
    python scripts/dry_run_image_prompts.py --seed 7 --output dry_run_prompts.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys

# Минимальные переменные окружения, чтобы безопасно импортировать config/services
# (значения тестовые, реальные API не вызываются).
os.environ.setdefault("OPENAI_API_KEY", "dry-run-key")
os.environ.setdefault("BOT_TOKEN", "dry-run-token")
os.environ.setdefault("OPENAI_BASE_URL", "https://api.openai.com/v1")
os.environ.setdefault("OPENAI_TEXT_MODEL", "gpt-4o-mini")
os.environ.setdefault("OPENAI_IMAGE_MODEL", "gpt-image-1")
os.environ.setdefault("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
os.environ.setdefault("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
os.environ.setdefault("YANDEX_API_KEY", "dry-run-key")
os.environ.setdefault("YANDEX_FOLDER_ID", "dry-run-folder")
os.environ.setdefault("PROXI_API_KEY", "dry-run-key")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from services.openai_image import (  # noqa: E402
    _COLOR_MOODS,
    _COMPOSITION_HINTS,
    _build_image_prompt,
)
from services.ritual_config import get_visual_archetype, resolve_photo_scene_preset, resolve_style  # noqa: E402
from services.visual_memory import extract_visual_motifs_from_prompt  # noqa: E402

# Набор сэмплов: (sphere, subsphere, style, visual_mode, user_text)
SAMPLES: list[tuple[str, str | None, str, str, str | None]] = [
    ("inner_peace", None, "ethereal_landscape", "illustration", "хочу больше спокойствия"),
    ("inner_peace", None, "auto", "photo", None),
    ("money", None, "quiet_interior", "illustration", "финансовая стабильность"),
    ("money", None, "auto", "photo", "порядок в делах"),
    ("career", None, "cinematic_light", "illustration", None),
    ("career", None, "urban_city_photo", "photo", "новый проект"),
    ("self_realization", None, "dreamy_painterly", "illustration", "творческое самовыражение"),
    ("self_realization", None, "book_nook_photo", "photo", None),
    ("relationships", "partner", "bright_nature_card", "illustration", None),
    ("relationships", "partner", "cafe_terrace_photo", "photo", "тепло в отношениях"),
    ("health", None, "minimal_botanical", "illustration", None),
    ("health", None, "living_nature_photo", "photo", "энергия и свежесть"),
    ("self_worth", None, "textured_collage", "illustration", None),
    ("self_worth", None, "cozy_home_photo", "photo", "уверенность в себе"),
    ("spirituality", None, "symbolic_luxe", "illustration", None),
    ("spirituality", None, "sea_coast_photo", "photo", "тихий ритуал по утрам"),
    ("home_support", None, "quiet_interior", "illustration", None),
    ("home_support", None, "rural_calm_photo", "photo", "уют и забота о доме"),
]


def build_prompts(seed: int) -> list[dict]:
    rng = random.Random(seed)
    results = []
    for sphere, subsphere, style, visual_mode, user_text in SAMPLES:
        resolved_style = resolve_style(style, sphere, visual_mode=visual_mode)
        photo_scene_preset = None
        if visual_mode == "photo":
            photo_scene_preset = resolve_photo_scene_preset(sphere, resolved_style)

        color_mood = rng.choice(_COLOR_MOODS)
        composition_hint = rng.choice(_COMPOSITION_HINTS)

        prompt = _build_image_prompt(
            style=style,
            sphere=sphere,
            subsphere=subsphere,
            user_text=user_text,
            color_mood=color_mood,
            composition_hint=composition_hint,
            visual_mode=visual_mode,
            photo_scene_preset=photo_scene_preset,
        )

        motifs = extract_visual_motifs_from_prompt(prompt)
        visual_archetype = get_visual_archetype(style=resolved_style, scene_preset=photo_scene_preset)

        results.append(
            {
                "sphere": sphere,
                "subsphere": subsphere,
                "requested_style": style,
                "resolved_style": resolved_style,
                "visual_mode": visual_mode,
                "photo_scene_preset": photo_scene_preset,
                "visual_archetype": visual_archetype,
                "color_mood": color_mood,
                "composition_hint": composition_hint,
                "user_text": user_text,
                "prompt_length": len(prompt),
                "motifs": motifs,
                "prompt": prompt,
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42, help="Seed for color/composition selection (default: 42)")
    parser.add_argument("--output", type=str, default=None, help="Optional path to save full results as JSON")
    args = parser.parse_args()

    results = build_prompts(args.seed)

    motif_totals: dict[str, int] = {}
    lengths = []
    for item in results:
        lengths.append(item["prompt_length"])
        for motif in item["motifs"]:
            motif_totals[motif] = motif_totals.get(motif, 0) + 1

    print(f"Generated {len(results)} prompts (seed={args.seed})\n")
    for item in results:
        print(
            f"[{item['sphere']}/{item['subsphere'] or '-'}] "
            f"style={item['resolved_style']} mode={item['visual_mode']} "
            f"scene={item['photo_scene_preset'] or '-'} "
            f"archetype={item['visual_archetype']} "
            f"len={item['prompt_length']} motifs={item['motifs']}"
        )
        print(f"    color: {item['color_mood']}")
        print(f"    composition: {item['composition_hint']}")
        print(f"    prompt: {item['prompt'][:220]}...")
        print()

    print("--- Stats ---")
    print(f"Prompt length: min={min(lengths)}, max={max(lengths)}, avg={sum(lengths) / len(lengths):.0f}")
    print(f"Motif frequency across {len(results)} prompts: {motif_totals}")
    repeated_motifs = {motif: count for motif, count in motif_totals.items() if count >= len(results) // 2}
    if repeated_motifs:
        print(f"Motifs present in >= half of prompts (possible repetition): {repeated_motifs}")
    else:
        print("No motif present in >= half of prompts.")

    archetype_totals: dict[str, int] = {}
    for item in results:
        archetype_totals[item["visual_archetype"]] = archetype_totals.get(item["visual_archetype"], 0) + 1
    print(f"\nVisual archetype frequency across {len(results)} samples: {archetype_totals}")

    consecutive_repeats = [
        (i, results[i - 1]["visual_archetype"])
        for i in range(1, len(results))
        if results[i]["visual_archetype"] == results[i - 1]["visual_archetype"]
    ]
    if consecutive_repeats:
        print(f"Consecutive archetype repeats (sample index, archetype): {consecutive_repeats}")
    else:
        print("No consecutive archetype repeats in this sample sequence.")

    overused_archetypes = {arch: count for arch, count in archetype_totals.items() if count >= len(results) // 2}
    if overused_archetypes:
        print(f"Archetypes present in >= half of samples (possible repetition): {overused_archetypes}")
    else:
        print("No archetype present in >= half of samples.")

    print("\n--- Anti-repeat demo (auto style, illustration, sphere=inner_peace) ---")
    history_window: list[str] = []
    for step in range(6):
        recent = history_window[-5:]
        step_style = resolve_style("auto", "inner_peace", visual_mode="illustration", recent_archetypes=recent)
        step_archetype = get_visual_archetype(style=step_style)
        print(f"step {step + 1}: recent_archetypes={recent} -> style={step_style} archetype={step_archetype}")
        history_window.append(step_archetype)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nFull results saved to {args.output}")


if __name__ == "__main__":
    main()
