import datetime as dt

from services.ritual_config import (
    ILLUSTRATION_STYLE_KEYS,
    MAIN_SPHERES,
    PHOTO_RECOMMENDED_STYLES,
    PHOTO_SCENE_PRESETS,
    PHOTO_SCENE_ROUTING,
    PHOTO_STYLE_KEYS,
    RECOMMENDED_STYLES,
    STYLE_DESCRIPTIONS,
    VALID_VISUAL_MODES,
    get_focus_for_date,
    get_focuses,
    get_recommended_styles,
    get_weekly_balance_sphere,
    has_coastal_intent,
    is_tts_available,
    normalize_visual_mode,
    resolve_photo_scene_preset,
    resolve_style,
)


def test_main_spheres_contains_seven_and_no_spirituality():
    assert len(MAIN_SPHERES) == 7
    assert "spirituality" not in MAIN_SPHERES


def test_each_main_sphere_has_focuses_and_recommended_styles():
    for sphere in MAIN_SPHERES:
        assert len(get_focuses(sphere)) >= 7
        assert RECOMMENDED_STYLES[sphere]
        assert "bright_nature_card" in RECOMMENDED_STYLES[sphere]


def test_weekly_balance_gives_seven_unique_spheres():
    monday = dt.date.fromisocalendar(2030, 12, 1)
    spheres = [get_weekly_balance_sphere(42, monday + dt.timedelta(days=i)) for i in range(7)]
    assert len(set(spheres)) == 7


def test_weekly_balance_order_can_change_between_weeks():
    week_one = [get_weekly_balance_sphere(42, dt.date.fromisocalendar(2030, 12, i)) for i in range(1, 8)]
    week_two = [get_weekly_balance_sphere(42, dt.date.fromisocalendar(2030, 13, i)) for i in range(1, 8)]
    assert week_one != week_two


def test_sphere_focuses_do_not_repeat_within_week():
    monday = dt.date.fromisocalendar(2030, 12, 1)
    focuses = [get_focus_for_date(42, "money", monday + dt.timedelta(days=i))["key"] for i in range(7)]
    assert len(set(focuses)) == 7


def test_auto_style_uses_recommended_styles():
    assert resolve_style("auto", "money") == "bright_nature_card"
    assert resolve_style("random_suitable", "career", user_id=1, day=dt.date(2030, 1, 1)) in RECOMMENDED_STYLES["career"]


def test_visual_mode_values_and_default():
    assert set(VALID_VISUAL_MODES) == {"photo", "illustration", "mixed"}
    assert normalize_visual_mode(None) == "illustration"
    assert normalize_visual_mode("unknown") == "illustration"


def test_auto_photo_uses_only_photo_styles():
    day = dt.date(2030, 1, 1)
    style = resolve_style("auto", "money", user_id=42, day=day, visual_mode="photo")
    assert style in PHOTO_RECOMMENDED_STYLES["money"]
    assert style in PHOTO_STYLE_KEYS
    assert style not in ILLUSTRATION_STYLE_KEYS


def test_photo_auto_prefers_stable_interior_styles_for_money_and_career():
    monday = dt.date.fromisocalendar(2030, 12, 1)
    tuesday = dt.date.fromisocalendar(2030, 12, 2)
    sunday = dt.date.fromisocalendar(2030, 12, 7)
    assert resolve_style("auto", "money", user_id=42, day=monday, visual_mode="photo") == "light_interior_photo"
    assert resolve_style("auto", "career", user_id=42, day=monday, visual_mode="photo") == "light_interior_photo"
    assert resolve_style("auto", "money", user_id=42, day=tuesday, visual_mode="photo") == "calm_lifestyle_photo"
    assert resolve_style("auto", "career", user_id=42, day=sunday, visual_mode="photo") == "sea_coast_photo"


def test_auto_illustration_uses_illustration_styles():
    day = dt.date(2030, 1, 1)
    style = resolve_style("auto", "money", user_id=42, day=day, visual_mode="illustration")
    assert style in RECOMMENDED_STYLES["money"]
    assert style not in PHOTO_STYLE_KEYS


def test_mixed_mode_selects_a_supported_branch():
    day = dt.date(2030, 1, 1)
    styles = get_recommended_styles("money", visual_mode="mixed", user_id=42, day=day)
    assert styles
    assert set(styles) <= (set(PHOTO_RECOMMENDED_STYLES["money"]) | set(RECOMMENDED_STYLES["money"]))


def test_photo_style_keys_are_separate_photo_directions():
    assert PHOTO_STYLE_KEYS == [
        "sunny_photo_scene",
        "living_nature_photo",
        "sea_coast_photo",
        "bright_ocean_coast_photo",
        "light_interior_photo",
        "calm_lifestyle_photo",
    ]
    assert not (set(PHOTO_STYLE_KEYS) & set(ILLUSTRATION_STYLE_KEYS))


def test_photo_style_descriptions_avoid_illustration_language():
    banned = [
        "illustration",
        "painterly",
        "watercolor",
        "gouache",
        "collage",
        "artwork",
        "artistic render",
        "dreamy",
        "ethereal",
        "card",
    ]
    for style in PHOTO_STYLE_KEYS:
        description = STYLE_DESCRIPTIONS[style].lower()
        assert "photo" in description or "photography" in description
        for word in banned:
            assert word not in description


def test_photo_scene_presets_are_concrete_and_photographic():
    assert set(PHOTO_SCENE_PRESETS) >= {
        "window_still_life",
        "calm_workspace",
        "botanical_corner",
        "outdoor_path",
        "restful_daily_scene",
        "relationship_table_scene",
        "ocean_sunrise",
        "seaside_sunset",
        "quiet_beach_morning",
        "rocky_coast",
        "dunes_and_seabirds",
        "coastal_path",
    }
    for preset in PHOTO_SCENE_PRESETS.values():
        low = preset.lower()
        assert "photo" in low or "photography" in low
        assert "real" in low or "realistic" in low


def test_photo_scene_routing_prefers_workspace_for_money_and_career():
    for sphere in ("money", "career"):
        scenes = PHOTO_SCENE_ROUTING[sphere]
        assert scenes[0] == "calm_workspace"
        assert "outdoor_path" not in scenes


def test_photo_scene_routing_relationships_uses_concrete_table_scene():
    scenes = PHOTO_SCENE_ROUTING["relationships"]
    assert scenes[0] == "relationship_table_scene"


def test_resolve_photo_scene_uses_style_compatible_presets():
    assert resolve_photo_scene_preset("money", "light_interior_photo") in {"window_still_life", "calm_workspace", "botanical_corner"}
    assert resolve_photo_scene_preset("inner_peace", "living_nature_photo") in {"outdoor_path", "botanical_corner"}
    assert resolve_photo_scene_preset("money", "sea_coast_photo") in {
        "ocean_sunrise",
        "seaside_sunset",
        "quiet_beach_morning",
        "rocky_coast",
        "dunes_and_seabirds",
        "coastal_path",
    }


def test_photo_auto_rotates_across_categories_where_applicable():
    monday = dt.date.fromisocalendar(2030, 12, 1)
    styles = {
        resolve_style("auto", "inner_peace", user_id=42, day=monday + dt.timedelta(days=i), visual_mode="photo")
        for i in range(7)
    }
    assert {"light_interior_photo", "sea_coast_photo", "living_nature_photo", "calm_lifestyle_photo"} <= styles


def test_auto_style_rotates_across_week():
    monday = dt.date.fromisocalendar(2030, 12, 1)
    styles = {
        resolve_style("auto", "money", user_id=42, day=monday + dt.timedelta(days=i), focus_key=f"focus-{i}")
        for i in range(7)
    }
    assert len(styles) >= 2
    assert styles <= set(RECOMMENDED_STYLES["money"])


def test_tts_availability_by_language():
    assert is_tts_available("ru") is True
    assert is_tts_available("en") is False


def test_coastal_intent_keywords_detected():
    assert has_coastal_intent("walk on the ocean coast at sunset")
    assert has_coastal_intent("Хочу спокойное побережье моря")
    assert not has_coastal_intent("quiet botanical still life by a window")


def test_resolve_style_avoids_recent_photo_repetition():
    day = dt.date.fromisocalendar(2030, 12, 1)
    style = resolve_style(
        "auto",
        "inner_peace",
        user_id=42,
        day=day,
        visual_mode="photo",
        recent_styles=["light_interior_photo", "sea_coast_photo"],
    )
    assert style not in {"light_interior_photo", "sea_coast_photo"}


def test_resolve_scene_avoids_recent_scene_repetition():
    scene = resolve_photo_scene_preset(
        "inner_peace",
        "sea_coast_photo",
        recent_scene_presets=["ocean_sunrise", "seaside_sunset", "quiet_beach_morning"],
    )
    assert scene in {"rocky_coast", "dunes_and_seabirds", "coastal_path"}
