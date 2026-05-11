from services.scene_prompt_builder import (
    build_controlled_scene_prompt,
    build_cafe_scene_constraints,
    build_living_nature_constraints,
    is_living_nature_style,
    select_photo_scene_preset_override,
    should_use_llm_image_prompt_for_fallback,
)
from services.scene_planner import get_scene_candidates_for_style


def test_build_controlled_scene_prompt_includes_scene_and_avoid_constraints():
    prompt = build_controlled_scene_prompt(
        scene_plan={
            "scene_type": "forest_path",
            "setting": "quiet forest path with soft morning light",
            "human_presence": "none",
            "main_subject": "narrow path between trees and tall grasses",
            "visual_motifs": ["forest", "path", "morning_light"],
            "composition": "wide natural landscape, open depth, not table-centered",
            "lighting": "soft morning light",
            "mood": "quiet self-trust and spaciousness",
            "avoid": ["mug", "notebook", "table", "window", "beach"],
        },
        focus_title="спокойствие и опора",
        visual_mode="photo",
        selected_style="living_nature_photo",
        resolved_style="living_nature_photo",
        color_palette="fresh greens and soft gold",
        composition_hint="wide landscape with visible depth",
        sphere="inner_peace",
        language="ru",
    ).lower()

    assert "scene type: forest_path" in prompt
    assert "forest path" in prompt
    assert "wide natural landscape" in prompt
    assert "avoid: mug, notebook, table, window, beach" in prompt
    assert "no crowd" in prompt
    assert "no extra people" in prompt


def test_build_living_nature_constraints_include_hard_outdoor_rules():
    constraints = [item.lower() for item in build_living_nature_constraints()]
    assert "no indoor scene" in constraints
    assert "no interior" in constraints
    assert "no room" in constraints
    assert "no table" in constraints
    assert "no mug" in constraints
    assert "no notebook" in constraints
    assert "no window" in constraints
    assert "no furniture" in constraints
    assert "outdoor nature scene only" in constraints


def test_build_cafe_scene_constraints_include_lived_in_cafe_and_avoid_guardrails():
    constraints = [item.lower() for item in build_cafe_scene_constraints()]
    assert "a few calm guests seated at distant tables" in constraints
    assert "one or two coffee cups on tables as small supporting details" in constraints
    assert "small dessert or pastry hint" in constraints
    assert "menu card" in constraints
    assert "avoid empty abandoned cafe" in constraints
    assert "avoid post-apocalyptic street" in constraints
    assert "avoid deserted showroom" in constraints
    assert "avoid sterile dining room" in constraints
    assert "avoid empty classroom feeling" in constraints
    assert "avoid crowded noisy scene" in constraints


def test_is_living_nature_style_detects_runtime_values():
    assert is_living_nature_style(
        selected_style="living_nature_photo",
        resolved_style="living_nature_photo",
        visual_mode="photo",
    )
    assert is_living_nature_style(
        selected_style="Живая природа",
        resolved_style=None,
        visual_mode="photo",
    )
    assert not is_living_nature_style(
        selected_style="quiet_interior",
        resolved_style="quiet_interior",
        visual_mode="illustration",
    )


def test_select_photo_scene_preset_override_returns_outdoor_path_for_living_nature():
    assert (
        select_photo_scene_preset_override(
            scene_plan={"scene_type": "botanical_still_life"},
            selected_style="living_nature_photo",
            resolved_style="living_nature_photo",
            visual_mode="photo",
        )
        == "outdoor_path"
    )


def test_select_photo_scene_preset_override_returns_outdoor_path_for_outdoor_scene_types():
    for scene_type in ("forest_path", "open_meadow", "riverside"):
        assert (
            select_photo_scene_preset_override(
                scene_plan={"scene_type": scene_type},
                selected_style="quiet_interior",
                resolved_style="quiet_interior",
                visual_mode="photo",
            )
            == "outdoor_path"
        )


def test_select_photo_scene_preset_override_supports_new_cafe_rural_and_book_scenes():
    assert (
        select_photo_scene_preset_override(
            scene_plan={"scene_type": "street_cafe_terrace"},
            selected_style="cafe_terrace_photo",
            resolved_style="cafe_terrace_photo",
            visual_mode="photo",
        )
        == "street_cafe_terrace"
    )
    assert (
        select_photo_scene_preset_override(
            scene_plan={"scene_type": "village_veranda"},
            selected_style="rural_calm_photo",
            resolved_style="rural_calm_photo",
            visual_mode="photo",
        )
        == "village_veranda"
    )
    assert (
        select_photo_scene_preset_override(
            scene_plan={"scene_type": "library_corner"},
            selected_style="book_nook_photo",
            resolved_style="book_nook_photo",
            visual_mode="photo",
        )
        == "bookshop_aisle"
    )


def test_select_photo_scene_preset_override_does_not_use_botanical_corner_for_living_nature():
    override = select_photo_scene_preset_override(
        scene_plan={"scene_type": "botanical_still_life"},
        selected_style="sunny_nature_photo",
        resolved_style="living_nature_photo",
        visual_mode="photo",
    )
    assert override == "outdoor_path"
    assert override != "botanical_corner"


def test_should_use_llm_image_prompt_for_fallback_disables_llm_in_controlled_mode():
    assert (
        should_use_llm_image_prompt_for_fallback(
            scene_planner_image_prompt_enabled=True,
            llm_image_prompt_enabled=True,
        )
        is False
    )
    assert (
        should_use_llm_image_prompt_for_fallback(
            scene_planner_image_prompt_enabled=True,
            llm_image_prompt_enabled=False,
        )
        is False
    )


def test_should_use_llm_image_prompt_for_fallback_preserves_old_disabled_path():
    assert (
        should_use_llm_image_prompt_for_fallback(
            scene_planner_image_prompt_enabled=False,
            llm_image_prompt_enabled=True,
        )
        is True
    )
    assert (
        should_use_llm_image_prompt_for_fallback(
            scene_planner_image_prompt_enabled=False,
            llm_image_prompt_enabled=False,
        )
        is False
    )


def test_selected_style_and_visual_mode_affect_candidate_pool():
    nature_candidates = get_scene_candidates_for_style(
        selected_style="living_nature_photo",
        resolved_style="living_nature_photo",
        visual_mode="photo",
    )
    coastal_candidates = get_scene_candidates_for_style(
        selected_style="sea_coast_photo",
        resolved_style="sea_coast_photo",
        visual_mode="photo",
    )
    assert "forest_path" in nature_candidates
    assert "sea_horizon" not in nature_candidates
    assert "sea_horizon" in coastal_candidates
    assert "forest_path" not in coastal_candidates


def test_professional_context_candidate_pool_contains_multiple_city_cafe_work_scenes():
    candidates = get_scene_candidates_for_style(
        sphere="career",
        focus_title="professional growth and stability",
    )
    assert "quiet_city_morning" in candidates
    assert "calm_cafe_corner" in candidates
    assert "office_morning_light" in candidates
    assert "coworking_quiet_corner" in candidates


def test_new_photo_style_candidate_pools_are_specialized():
    cafe_candidates = get_scene_candidates_for_style(
        selected_style="cafe_terrace_photo",
        resolved_style="cafe_terrace_photo",
        visual_mode="photo",
    )
    rural_candidates = get_scene_candidates_for_style(
        selected_style="rural_calm_photo",
        resolved_style="rural_calm_photo",
        visual_mode="photo",
    )
    home_candidates = get_scene_candidates_for_style(
        selected_style="cozy_home_photo",
        resolved_style="cozy_home_photo",
        visual_mode="photo",
    )
    assert "street_cafe_terrace" in cafe_candidates
    assert "village_veranda" in rural_candidates
    assert "warm_living_room" in home_candidates


def test_build_controlled_scene_prompt_for_cafe_scene_includes_cafe_markers_and_limited_people():
    prompt = build_controlled_scene_prompt(
        scene_plan={
            "scene_type": "street_cafe_terrace",
            "setting": "street cafe terrace with awning shade, planters, menu card, one or two coffee cups and a few calm guests at distant tables",
            "human_presence": "distant_figure",
            "main_subject": "terrace seating, facade details and quiet city street life rather than a cup close-up or empty dining hall",
            "visual_motifs": ["cafe", "terrace", "city_morning", "planters", "background_guests"],
            "composition": "wide terrace scene with small tables as supporting details, city street view and no tabletop hero framing",
            "lighting": "soft morning daylight with gentle facade reflections",
            "mood": "social ease, composure and light urban openness",
            "avoid": ["empty abandoned cafe", "post-apocalyptic street", "crowded noisy scene"],
        },
        selected_style="cafe_terrace_photo",
        resolved_style="cafe_terrace_photo",
        visual_mode="photo",
        language="ru",
    ).lower()

    assert "terrace" in prompt
    assert "coffee cups" in prompt
    assert "menu card" in prompt
    assert "background" in prompt
    assert "one to three calm people" in prompt
    assert "avoid empty abandoned cafe" in prompt
    assert "avoid post-apocalyptic street" in prompt
    assert "avoid crowded noisy scene" in prompt
