from services.subscription_ui import build_dashboard_text, build_subscription_summary, build_subscriptions_summary
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
    assert "⏰ Время: 09:00" in summary
    assert "🎨 Визуал: 📷 Фотореализм" in summary
    assert "✨ Стиль: 🎨 Автоподбор" in summary


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
    assert "🎨 Визуал: 🖌 Мягкая иллюстрация" in summary


def test_profile_summary_lists_multiple_subscriptions():
    summary = build_subscriptions_summary(
        [
            {"sphere": "random", "image_style": "auto", "hour": 9, "minute": 0, "subscription_mode": "weekly_balance"},
            {
                "sphere": "money",
                "image_style": "bright_nature_card",
                "hour": 15,
                "minute": 0,
                "subscription_mode": "sphere_focus",
                "subscription_sphere": "money",
                "visual_mode": "illustration",
            },
        ],
        "ru",
    )
    assert "1. 🌿 Баланс недели" in summary
    assert "2. 🎯 Фокус на сфере" in summary
    assert "Сфера: 💰 Деньги и устойчивость" in summary


def test_dashboard_summary_contains_count_and_emojis():
    text = build_dashboard_text(
        [{"sphere": "random", "image_style": "auto", "hour": 9, "minute": 0, "subscription_mode": "weekly_balance"}],
        "ru",
    )
    assert "🧾 Твои подписки" in text
    assert "Активных подписок: 1/3" in text
    assert "🌿 Баланс недели" in text


def test_sphere_labels_do_not_use_inner_support_as_sphere():
    labels = {get_sphere_label(sphere, "ru") for sphere in ("inner_peace", "self_worth", "health", "career", "money", "relationships", "self_realization")}
    assert "внутренняя опора" not in {label.lower() for label in labels}


def test_style_labels_are_non_empty():
    for style in PHOTO_STYLE_KEYS + ILLUSTRATION_STYLE_KEYS + ["auto", "random_suitable"]:
        assert get_style_label(style, "ru")
        assert get_style_label(style, "en")
