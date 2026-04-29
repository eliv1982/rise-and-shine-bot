import datetime as dt

from services.ritual_config import (
    MAIN_SPHERES,
    RECOMMENDED_STYLES,
    get_focus_for_date,
    get_focuses,
    get_weekly_balance_sphere,
    is_tts_available,
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
