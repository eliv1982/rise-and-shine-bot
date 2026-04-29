from handlers.start import build_subscription_summary
from services.ritual_config import (
    ILLUSTRATION_STYLE_KEYS,
    PHOTO_STYLE_KEYS,
    get_sphere_label,
    get_style_label,
)


def test_profile_summary_no_subscriptions_ru():
    summary = build_subscription_summary(None, "ru")
    assert "Пока нет активных подписок" in summary
    assert "/subscribe" in summary


def test_profile_summary_subscription_with_visual_mode_ru():
    summary = build_subscription_summary(
        {
            "sphere": "random",
            "image_style": "auto",
            "hour": 9,
            "minute": 0,
            "subscription_mode": "weekly_balance",
            "subscription_style_mode": "auto",
            "visual_mode": "photo",
        },
        "ru",
    )
    assert "🌿 Баланс недели" in summary
    assert "Время: 09:00" in summary
    assert "Визуал: 📷 Фотореализм" in summary
    assert "Стиль: 🎨 Автоподбор" in summary


def test_profile_summary_missing_visual_mode_defaults_to_illustration():
    summary = build_subscription_summary(
        {
            "sphere": "money",
            "image_style": "bright_nature_card",
            "hour": 8,
            "minute": 30,
            "subscription_mode": "sphere_focus",
            "subscription_sphere": "money",
        },
        "ru",
    )
    assert "Визуал: 🖌 Мягкая иллюстрация" in summary


def test_sphere_labels_do_not_use_inner_support_as_sphere():
    labels = {get_sphere_label(sphere, "ru") for sphere in ("inner_peace", "self_worth", "health", "career", "money", "relationships", "self_realization")}
    assert "внутренняя опора" not in {label.lower() for label in labels}


def test_style_labels_are_non_empty():
    for style in PHOTO_STYLE_KEYS + ILLUSTRATION_STYLE_KEYS + ["auto", "random_suitable"]:
        assert get_style_label(style, "ru")
        assert get_style_label(style, "en")
