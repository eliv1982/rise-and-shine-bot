from services import scene_planner


def test_parse_scene_plan_response_plain_json():
    raw = '{"scene_type":"forest_path","setting":"quiet forest","human_presence":"none"}'

    parsed = scene_planner.parse_scene_plan_response(raw)

    assert parsed["scene_type"] == "forest_path"
    assert parsed["human_presence"] == "none"


def test_parse_scene_plan_response_code_fence():
    raw = '```json\n{"scene_type":"riverside","setting":"quiet river"}\n```'

    parsed = scene_planner.parse_scene_plan_response(raw)

    assert parsed == {"scene_type": "riverside", "setting": "quiet river"}


def test_parse_scene_plan_response_embedded_json():
    raw = 'Here is the plan: {"scene_type":"garden_morning","setting":"garden"} thanks'

    parsed = scene_planner.parse_scene_plan_response(raw)

    assert parsed == {"scene_type": "garden_morning", "setting": "garden"}


def test_parse_scene_plan_response_invalid():
    assert scene_planner.parse_scene_plan_response(None) is None
    assert scene_planner.parse_scene_plan_response("not json at all") is None
    assert scene_planner.parse_scene_plan_response('["not","a","dict"]') is None


def test_normalize_scene_plan_adds_missing_keys():
    plan = scene_planner.normalize_scene_plan({"scene_type": "forest_path"})

    assert set(plan.keys()) == {
        "scene_type",
        "setting",
        "human_presence",
        "main_subject",
        "visual_motifs",
        "composition",
        "lighting",
        "mood",
        "avoid",
    }


def test_normalize_scene_plan_invalid_human_presence_defaults_to_none():
    plan = scene_planner.normalize_scene_plan({"scene_type": "forest_path", "human_presence": "group"})

    assert plan["human_presence"] == "none"


def test_normalize_scene_plan_merges_avoid_from_memory():
    plan = scene_planner.normalize_scene_plan(
        {"scene_type": "forest_path", "avoid": ["fog"]},
        visual_memory_context={"hard_avoid_today": ["mug", "beach"]},
    )

    assert "fog" in plan["avoid"]
    assert "mug" in plan["avoid"]
    assert "beach" in plan["avoid"]
    assert "generic wellness stock photo" in plan["avoid"]


def test_scene_presets_include_cafe_city_and_work_scenes():
    assert "calm_cafe_corner" in scene_planner.SCENE_PRESETS
    assert "quiet_city_morning" in scene_planner.SCENE_PRESETS
    assert "office_morning_light" in scene_planner.SCENE_PRESETS


def test_scene_presets_include_new_cafe_rural_home_and_book_scenes():
    assert "street_cafe_terrace" in scene_planner.SCENE_PRESETS
    assert "village_veranda" in scene_planner.SCENE_PRESETS
    assert "warm_living_room" in scene_planner.SCENE_PRESETS
    assert "bookshop_aisle" in scene_planner.SCENE_PRESETS


def test_cafe_scene_presets_include_lived_in_cafe_markers():
    preset = scene_planner.SCENE_PRESETS["street_cafe_terrace"]
    joined = " ".join(
        [
            preset["setting"],
            preset["main_subject"],
            preset["composition"],
            " ".join(preset["visual_motifs"]),
            " ".join(preset.get("avoid", [])),
        ]
    ).lower()

    assert "terrace" in joined
    assert "coffee" in joined
    assert "menu" in joined
    assert "planters" in joined
    assert "guests" in joined
    assert "abandoned" in joined
    assert "post-apocalyptic" in joined


def test_normalize_scene_family_groups_cafe_scenes():
    assert scene_planner.normalize_scene_family("calm_cafe_corner") == "cafe_quiet"
    assert scene_planner.normalize_scene_family("quiet_cafe_window") == "cafe_quiet"
    assert scene_planner.normalize_scene_family("bookstore_cafe") == "cafe_quiet"


def test_normalize_scene_family_groups_work_scenes():
    assert scene_planner.normalize_scene_family("office_morning_light") == "work_quiet"
    assert scene_planner.normalize_scene_family("coworking_quiet_corner") == "work_quiet"


def test_normalize_scene_family_groups_new_cafe_terrace_rural_cozy_and_book_scenes():
    assert scene_planner.normalize_scene_family("street_cafe_terrace") == "cafe_terrace"
    assert scene_planner.normalize_scene_family("village_veranda") == "rural_quiet"
    assert scene_planner.normalize_scene_family("warm_living_room") == "cozy_home"
    assert scene_planner.normalize_scene_family("library_corner") == "book_nook"


def test_build_fallback_scene_plan_uses_preferred_scene_type():
    plan = scene_planner.build_fallback_scene_plan(
        focus_title="Inner trust",
        visual_memory_context={"prefer_scene_types": ["riverside"], "hard_avoid_today": ["mug"]},
    )

    assert plan["scene_type"] == "riverside"
    assert "Inner trust" in plan["mood"]
    assert "mug" in plan["avoid"]


def test_build_fallback_scene_plan_uses_default_when_no_preference():
    plan = scene_planner.build_fallback_scene_plan(
        focus_title=None,
        visual_memory_context={"prefer_scene_types": []},
    )

    assert plan["scene_type"] in {"forest_path", "open_meadow", "garden_morning"}


def test_build_fallback_scene_plan_avoids_recent_exact_scene_type():
    plan = scene_planner.build_fallback_scene_plan(
        focus_title="Fresh start",
        visual_memory_context={
            "recent_scene_types": ["forest_path"],
            "recent_scene_families": ["nature_path"],
            "overused_scene_families": [],
        },
        selected_style="living_nature_photo",
        resolved_style="living_nature_photo",
        visual_mode="photo",
    )

    assert plan["scene_type"] != "forest_path"


def test_build_fallback_scene_plan_avoids_same_scene_family_if_alternatives_exist():
    plan = scene_planner.build_fallback_scene_plan(
        focus_title="Fresh start",
        visual_memory_context={
            "recent_scene_types": ["forest_path", "outdoor_path"],
            "recent_scene_families": ["nature_path", "nature_path", "nature_path"],
            "overused_scene_families": ["nature_path"],
        },
        selected_style="living_nature_photo",
        resolved_style="living_nature_photo",
        visual_mode="photo",
    )

    assert scene_planner.normalize_scene_family(plan["scene_type"]) != "nature_path"


def test_get_scene_candidates_for_style_living_nature_has_multiple_outdoor_scenes():
    candidates = scene_planner.get_scene_candidates_for_style(
        selected_style="living_nature_photo",
        resolved_style="living_nature_photo",
        visual_mode="photo",
    )
    assert "forest_path" in candidates
    assert "open_meadow" in candidates
    assert "riverside" in candidates
    assert len(candidates) >= 6


def test_get_scene_candidates_for_style_coastal_has_multiple_coastal_scenes():
    candidates = scene_planner.get_scene_candidates_for_style(
        selected_style="sea_coast_photo",
        resolved_style="sea_coast_photo",
        visual_mode="photo",
    )
    assert "sea_horizon" in candidates
    assert "coastal_morning" in candidates
    assert "rocky_shore" in candidates
    assert len(candidates) >= 4


def test_get_scene_candidates_for_style_interior_is_not_only_table_mug():
    candidates = scene_planner.get_scene_candidates_for_style(
        selected_style="light_interior_photo",
        resolved_style="light_interior_photo",
        visual_mode="photo",
    )
    assert "library_corner" in candidates
    assert "reading_corner" in candidates
    assert len(candidates) >= 4


def test_get_scene_candidates_for_style_cafe_contains_terrace_and_cafe_scenes():
    candidates = scene_planner.get_scene_candidates_for_style(
        selected_style="cafe_terrace_photo",
        resolved_style="cafe_terrace_photo",
        visual_mode="photo",
    )
    assert "street_cafe_terrace" in candidates
    assert "city_veranda_morning" in candidates
    assert "courtyard_cafe" in candidates
    assert "bookstore_cafe" in candidates


def test_get_scene_candidates_for_style_rural_contains_rural_scenes():
    candidates = scene_planner.get_scene_candidates_for_style(
        selected_style="rural_calm_photo",
        resolved_style="rural_calm_photo",
        visual_mode="photo",
    )
    assert "village_veranda" in candidates
    assert "cottage_garden" in candidates
    assert "country_road" in candidates
    assert "bench_under_tree_near_cottage" in candidates


def test_get_scene_candidates_for_style_cozy_home_contains_home_scenes():
    candidates = scene_planner.get_scene_candidates_for_style(
        selected_style="cozy_home_photo",
        resolved_style="cozy_home_photo",
        visual_mode="photo",
    )
    assert "warm_living_room" in candidates
    assert "fireplace_reading_chair" in candidates
    assert "calm_room_wide" in candidates


def test_get_scene_candidates_for_style_book_nook_contains_library_and_bookshop_scenes():
    candidates = scene_planner.get_scene_candidates_for_style(
        selected_style="book_nook_photo",
        resolved_style="book_nook_photo",
        visual_mode="photo",
    )
    assert "library_corner" in candidates
    assert "fireplace_library" in candidates
    assert "bookshop_aisle" in candidates


def test_get_scene_candidates_for_style_money_career_work_pool_contains_city_cafe_and_work():
    candidates = scene_planner.get_scene_candidates_for_style(
        sphere="money",
        focus_title="спокойная карьера и устойчивость",
    )
    assert "quiet_city_morning" in candidates
    assert "calm_cafe_corner" in candidates
    assert "office_morning_light" in candidates
    assert "library_corner" in candidates


def test_build_fallback_scene_plan_can_choose_professional_scene_for_money_context():
    plan = scene_planner.build_fallback_scene_plan(
        focus_title="спокойная работа и достаточность",
        visual_memory_context={"recent_scene_types": [], "recent_scene_families": [], "overused_scene_families": []},
        sphere="money",
    )
    assert plan["scene_type"] in {
        "quiet_city_morning",
        "calm_cafe_corner",
        "bookstore_cafe",
        "city_park_before_work",
        "courtyard_morning",
        "office_morning_light",
        "coworking_quiet_corner",
        "bridge_walkway",
        "street_after_rain",
        "tram_stop_morning",
        "library_corner",
    }


def test_build_fallback_scene_plan_avoids_repeated_cafe_family_for_professional_context():
    plan = scene_planner.build_fallback_scene_plan(
        focus_title="career stability",
        visual_memory_context={
            "recent_scene_types": ["calm_cafe_corner", "quiet_cafe_window"],
            "recent_scene_families": ["cafe_quiet", "cafe_quiet"],
            "overused_scene_families": ["cafe_quiet"],
        },
        sphere="career",
    )
    assert scene_planner.normalize_scene_family(plan["scene_type"]) != "cafe_quiet"


def test_build_fallback_scene_plan_can_choose_cafe_scene_for_cafe_style():
    plan = scene_planner.build_fallback_scene_plan(
        focus_title="soft professional reset",
        visual_memory_context={"recent_scene_types": [], "recent_scene_families": [], "overused_scene_families": []},
        selected_style="cafe_terrace_photo",
        resolved_style="cafe_terrace_photo",
        visual_mode="photo",
    )
    assert plan["scene_type"] in {
        "street_cafe_terrace",
        "city_veranda_morning",
        "courtyard_cafe",
        "sidewalk_cafe_after_rain",
        "quiet_cafe_window",
        "bookstore_cafe",
        "calm_cafe_corner",
    }


def test_build_fallback_scene_plan_uses_limited_background_human_presence_for_cafe_scenes():
    plan = scene_planner.build_fallback_scene_plan(
        focus_title="quiet morning reset",
        visual_memory_context={"recent_scene_types": [], "recent_scene_families": [], "overused_scene_families": []},
        selected_style="cafe_terrace_photo",
        resolved_style="cafe_terrace_photo",
        visual_mode="photo",
    )
    if scene_planner.normalize_scene_family(plan["scene_type"]) in {"cafe_terrace", "cafe_quiet"}:
        assert plan["human_presence"] == "distant_figure"


def test_build_fallback_scene_plan_avoids_repeated_cafe_terrace_family():
    plan = scene_planner.build_fallback_scene_plan(
        focus_title="urban pause",
        visual_memory_context={
            "recent_scene_types": ["street_cafe_terrace", "city_veranda_morning"],
            "recent_scene_families": ["cafe_terrace", "cafe_terrace"],
            "overused_scene_families": ["cafe_terrace"],
        },
        selected_style="cafe_terrace_photo",
        resolved_style="cafe_terrace_photo",
        visual_mode="photo",
    )
    assert scene_planner.normalize_scene_family(plan["scene_type"]) != "cafe_terrace"


def test_build_scene_image_prompt_includes_avoid_constraints():
    prompt = scene_planner.build_scene_image_prompt(
        {
            "scene_type": "forest_path",
            "avoid": ["mug", "window"],
        }
    )

    assert "Avoid: " in prompt
    assert "mug" in prompt
    assert "window" in prompt
    assert "No crowd. No extra people." in prompt


def test_build_scene_planner_prompt_includes_focus_and_memory():
    prompt = scene_planner.build_scene_planner_prompt(
        focus_title="Quiet self-trust",
        affirmations=["I move gently", "I trust my pace"],
        soft_action="Take one small calm step",
        visual_memory_context={
            "hard_avoid_today": ["mug", "beach"],
            "recent_scene_types": ["window_still_life"],
            "recent_motifs": ["mug", "window"],
            "overused_motifs": ["mug"],
            "prefer_scene_types": ["forest_path", "riverside"],
        },
        language="ru",
    )

    assert "Quiet self-trust" in prompt
    assert "hard_avoid_today" in prompt
    assert "window_still_life" in prompt
    assert "mug, beach" in prompt
