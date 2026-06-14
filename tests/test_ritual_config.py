import datetime as dt

from keyboards.inline import sphere_keyboard, style_keyboard, visual_mode_keyboard
from services.ritual_config import (
    ILLUSTRATION_RECOMMENDED_STYLES,
    ILLUSTRATION_STYLE_KEYS,
    MAIN_SPHERES,
    PHOTO_RECOMMENDED_STYLES,
    PHOTO_SCENE_PRESETS,
    PHOTO_SCENE_ROUTING,
    PHOTO_STYLE_KEYS,
    PHOTO_STYLE_SCENE_HINTS,
    RECOMMENDED_STYLES,
    STYLE_DESCRIPTIONS,
    SYMBOLIC_STYLE_KEYS,
    VALID_VISUAL_MODES,
    get_sphere_label,
    get_style_label,
    get_focus_for_date,
    get_focuses,
    get_recommended_styles,
    get_weekly_balance_sphere,
    has_coastal_intent,
    is_tts_available,
    normalize_style_key,
    normalize_visual_mode,
    resolve_photo_scene_preset,
    resolve_style,
)


def test_main_spheres_contains_home_support_and_no_spirituality():
    assert len(MAIN_SPHERES) == 8
    assert "home_support" in MAIN_SPHERES
    assert "spirituality" not in MAIN_SPHERES


def test_each_main_sphere_has_focuses_and_recommended_styles():
    for sphere in MAIN_SPHERES:
        assert len(get_focuses(sphere)) >= 7
        assert RECOMMENDED_STYLES[sphere]
        if sphere != "home_support":
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
    assert set(VALID_VISUAL_MODES) == {"photo", "illustration", "mixed", "symbolic"}
    assert normalize_visual_mode(None) == "illustration"
    assert normalize_visual_mode("unknown") == "illustration"
    assert normalize_visual_mode("symbolic") == "symbolic"


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
    assert resolve_style("auto", "money", user_id=42, day=monday, visual_mode="photo") == "urban_city_photo"
    assert resolve_style("auto", "career", user_id=42, day=monday, visual_mode="photo") == "urban_city_photo"
    assert resolve_style("auto", "money", user_id=42, day=tuesday, visual_mode="photo") == "calm_lifestyle_photo"
    assert resolve_style("auto", "career", user_id=42, day=sunday, visual_mode="photo") == "sea_coast_photo"


def test_auto_illustration_uses_illustration_styles():
    day = dt.date(2030, 1, 1)
    style = resolve_style("auto", "money", user_id=42, day=day, visual_mode="illustration")
    assert style in RECOMMENDED_STYLES["money"]
    assert style not in PHOTO_STYLE_KEYS


def test_symbolic_styles_exist_and_are_not_illustration_styles():
    # The symbolic visual mode (🪷 Мандалы и символы) has its own small
    # taxonomy of styles, each with its own prompt contract. None of them are
    # part of the regular illustration menu.
    for key in SYMBOLIC_STYLE_KEYS:
        assert key in STYLE_DESCRIPTIONS
        assert key not in ILLUSTRATION_STYLE_KEYS
        assert resolve_style(key, "inner_peace", visual_mode="symbolic") == key

    # symbolic_luxe is kept as a backward-compatible alias for old subscriptions.
    assert normalize_style_key("symbolic_luxe") == "mandala_harmony"
    assert "symbolic_luxe" not in ILLUSTRATION_STYLE_KEYS


def test_symbolic_auto_selection_can_choose_any_symbolic_style():
    # "Автоподбор" inside visual_mode="symbolic" must be able to pick any of
    # the symbolic styles (not always mandala_harmony), while never picking
    # a photo/illustration style.
    chosen = set()
    for user_id in range(20):
        for day_offset in range(7):
            day = dt.date(2030, 1, 1) + dt.timedelta(days=day_offset)
            style = resolve_style("auto", "inner_peace", user_id=user_id, day=day, visual_mode="symbolic")
            assert style in SYMBOLIC_STYLE_KEYS
            chosen.add(style)
    assert chosen == set(SYMBOLIC_STYLE_KEYS)


def test_symbolic_styles_are_not_recommended_for_illustration():
    for sphere in MAIN_SPHERES:
        recommended = get_recommended_styles(sphere, visual_mode="illustration")
        for key in SYMBOLIC_STYLE_KEYS:
            assert key not in recommended
            assert key not in ILLUSTRATION_RECOMMENDED_STYLES.get(sphere, [])


def test_cozy_home_and_book_nook_photo_scene_hints_reduce_overlap():
    cozy_home_scenes = set(PHOTO_STYLE_SCENE_HINTS["cozy_home_photo"])
    book_nook_scenes = set(PHOTO_STYLE_SCENE_HINTS["book_nook_photo"])

    assert len(cozy_home_scenes) >= 2
    assert len(book_nook_scenes) >= 2
    assert "warm_living_room" in cozy_home_scenes
    assert "bookshop_aisle" in book_nook_scenes
    assert "warm_living_room" not in book_nook_scenes
    assert "window_still_life" not in cozy_home_scenes


def test_calm_lifestyle_photo_scene_hints_differ_from_cozy_and_book_nook():
    cozy_home_scenes = set(PHOTO_STYLE_SCENE_HINTS["cozy_home_photo"])
    book_nook_scenes = set(PHOTO_STYLE_SCENE_HINTS["book_nook_photo"])
    calm_lifestyle_scenes = set(PHOTO_STYLE_SCENE_HINTS["calm_lifestyle_photo"])

    assert len(calm_lifestyle_scenes) >= 2
    assert not (calm_lifestyle_scenes & cozy_home_scenes)
    assert not (calm_lifestyle_scenes & book_nook_scenes)
    assert "window_still_life" not in calm_lifestyle_scenes


def test_mixed_mode_selects_a_supported_branch():
    day = dt.date(2030, 1, 1)
    styles = get_recommended_styles("money", visual_mode="mixed", user_id=42, day=day)
    assert styles
    assert set(styles) <= (set(PHOTO_RECOMMENDED_STYLES["money"]) | set(RECOMMENDED_STYLES["money"]))


def test_photo_style_keys_are_separate_photo_directions():
    assert PHOTO_STYLE_KEYS == [
        "sunny_morning_photo",
        "living_nature_photo",
        "urban_city_photo",
        "cafe_terrace_photo",
        "rural_calm_photo",
        "sea_coast_photo",
        "cozy_home_photo",
        "book_nook_photo",
        "calm_lifestyle_photo",
    ]
    assert not (set(PHOTO_STYLE_KEYS) & set(ILLUSTRATION_STYLE_KEYS))


def test_home_support_sphere_and_self_realization_label_are_updated():
    assert get_sphere_label("home_support", "ru") == "🏡 Дом и опора"
    assert get_sphere_label("self_realization", "ru") == "🎨 Творчество и самореализация"


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
    assert {"cozy_home_photo", "sea_coast_photo", "living_nature_photo", "calm_lifestyle_photo"} <= styles


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


def test_legacy_style_aliases_are_recognized():
    assert normalize_style_key("sunny_photo_scene") == "sunny_morning_photo"
    assert normalize_style_key("light_interior_photo") == "cozy_home_photo"
    assert normalize_style_key("bright_ocean_coast_photo") == "sea_coast_photo"
    assert normalize_style_key("sunny_nature_photo") == "living_nature_photo"


def test_photo_style_labels_are_updated_for_new_menu():
    assert get_style_label("sunny_morning_photo", "ru") == "Солнечное утро"
    assert get_style_label("cozy_home_photo", "ru") == "Уютный дом"
    assert get_style_label("book_nook_photo", "ru") == "Книжный уголок"
    assert get_style_label("light_interior_photo", "ru") == "Уютный дом"


def test_sphere_keyboard_includes_home_support():
    keyboard = sphere_keyboard("ru")
    texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "🏡 Дом и опора" in texts
    assert "🎨 Творчество и самореализация" in texts


def test_photo_style_keyboard_shows_new_styles_and_hides_bright_ocean_duplicate():
    keyboard = style_keyboard("ru", visual_mode="photo")
    texts = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "🏙 Городской стиль" in texts
    assert "☕ Кафе и городские веранды" in texts
    assert "🌾 Сельское спокойствие" in texts
    assert "🏡 Уютный дом" in texts
    assert "📚 Книжный уголок" in texts
    assert not any("Яркое океанское побережье" in text for text in texts)


def test_mandala_harmony_is_not_in_illustration_and_mixed_style_menus():
    # Mandalas and symbolic ornaments are a separate visual mode, not ordinary
    # illustration styles, so "Мандальная гармония" must not appear in the
    # regular illustration or mixed style menus.
    for visual_mode in ("illustration", "mixed", "photo"):
        keyboard = style_keyboard("ru", visual_mode=visual_mode)
        entries = [(button.text, button.callback_data) for row in keyboard.inline_keyboard for button in row]
        assert ("🪷 Мандальная гармония", "style:mandala_harmony") not in entries
        assert ("🪷 Мандальная гармония", "style:symbolic_luxe") not in entries
        callbacks = [callback for _, callback in entries]
        assert "style:symbolic_luxe" not in callbacks
        for key in SYMBOLIC_STYLE_KEYS:
            assert f"style:{key}" not in callbacks


def test_visual_mode_keyboard_includes_symbolic_mode():
    keyboard = visual_mode_keyboard("ru")
    entries = [(button.text, button.callback_data) for row in keyboard.inline_keyboard for button in row]
    assert ("🪷 Мандалы и символы", "visual:symbolic") in entries

    # Existing visual modes remain unchanged.
    assert ("📷 Фото-стиль", "visual:photo") in entries
    assert ("🖌 Мягкая иллюстрация", "visual:illustration") in entries
    assert ("🔀 Смешанный стиль", "visual:mixed") in entries


def test_sphere_keyboard_has_main_menu_escape():
    keyboard = sphere_keyboard("ru")
    entries = [(button.text, button.callback_data) for row in keyboard.inline_keyboard for button in row]
    assert ("🏠 Главное меню", "nav:main_menu") in entries


def test_visual_mode_keyboard_has_back_and_main_menu_navigation():
    keyboard = visual_mode_keyboard("ru")
    entries = [(button.text, button.callback_data) for row in keyboard.inline_keyboard for button in row]
    assert ("⬅️ Назад", "nav:back_to_sphere") in entries
    assert ("🏠 Главное меню", "nav:main_menu") in entries

    # The shared subscription keyboard must keep its existing layout untouched.
    sub_keyboard = visual_mode_keyboard("ru", for_subscription=True)
    sub_callbacks = [button.callback_data for row in sub_keyboard.inline_keyboard for button in row]
    assert "nav:back_to_sphere" not in sub_callbacks
    assert "nav:main_menu" not in sub_callbacks


def test_style_keyboard_has_back_and_main_menu_navigation_for_all_visual_modes():
    for visual_mode in ("photo", "illustration", "mixed", "symbolic"):
        keyboard = style_keyboard("ru", visual_mode=visual_mode)
        entries = [(button.text, button.callback_data) for row in keyboard.inline_keyboard for button in row]
        assert ("⬅️ Назад", "nav:back_to_visual") in entries
        assert ("🏠 Главное меню", "nav:main_menu") in entries


def test_symbolic_visual_mode_style_keyboard_shows_only_symbolic_styles():
    keyboard = style_keyboard("ru", visual_mode="symbolic")
    entries = [(button.text, button.callback_data) for row in keyboard.inline_keyboard for button in row]
    assert ("🪷 Мандальная гармония", "style:mandala_harmony") in entries
    assert ("🔷 Светлая геометрия", "style:sacred_geometry_light") in entries
    assert ("🌿 Ботаническая мандала", "style:botanical_mandala") in entries
    assert ("✨ Символ дня", "style:daily_symbol") in entries

    # Only symbolic styles are offered in this mode (plus auto/custom).
    style_callbacks = {
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data.startswith("style:") and button.callback_data not in ("style:auto", "style:custom")
    }
    assert style_callbacks == {f"style:{key}" for key in SYMBOLIC_STYLE_KEYS}


def test_symbolic_visual_mode_auto_resolves_to_symbolic_style():
    assert resolve_style("auto", "inner_peace", visual_mode="symbolic") in SYMBOLIC_STYLE_KEYS
    for key in SYMBOLIC_STYLE_KEYS:
        assert resolve_style(key, "inner_peace", visual_mode="symbolic") == key
    assert resolve_style("symbolic_luxe", "inner_peace", visual_mode="symbolic") == "mandala_harmony"
