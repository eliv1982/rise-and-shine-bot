import inspect

from handlers import start
from keyboards.inline import gender_keyboard, main_reply_keyboard, relationships_subsphere_keyboard, style_keyboard
from services.subscription_ui import (
    build_dashboard_text,
    build_subscription_summary,
    build_subscriptions_summary,
    gender_profile_label,
)
from services.ritual_config import (
    ILLUSTRATION_STYLE_KEYS,
    PHOTO_STYLE_KEYS,
    get_focuses,
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
    assert "🎨 Визуал: 📷 Фото-стиль" in summary
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


def test_self_worth_focus_no_longer_uses_inner_support_phrase():
    labels = {focus["ru"] for focus in get_focuses("self_worth")}
    assert "внутренняя опора" not in labels
    assert "опора на себя" in labels


def test_style_labels_are_non_empty():
    for style in PHOTO_STYLE_KEYS + ILLUSTRATION_STYLE_KEYS + ["auto", "random_suitable"]:
        assert get_style_label(style, "ru")
        assert get_style_label(style, "en")


def test_photo_style_labels_are_photographic():
    assert get_style_label("sunny_photo_scene", "ru") == "Солнечная фотосцена"
    assert get_style_label("living_nature_photo", "en") == "Living nature"
    assert get_style_label("sea_coast_photo", "ru") == "Побережье моря / океана"
    assert get_style_label("sea_coast_photo", "en") == "Sea & ocean coast"
    assert get_style_label("calm_lifestyle_photo", "ru") == "Спокойный lifestyle"
    assert get_style_label("bright_photo_card", "ru") == "Солнечная фотосцена"


def test_sea_coast_photo_is_selectable_with_emoji():
    buttons = [button.text for row in style_keyboard("ru", visual_mode="photo").inline_keyboard for button in row]
    assert "🌊 Побережье моря / океана" in buttons


def test_main_reply_keyboard_labels_ru_en():
    ru = main_reply_keyboard("ru").keyboard
    en = main_reply_keyboard("en").keyboard
    assert [button.text for row in ru for button in row] == ["🌿 Создать настрой", "⚙️ Подписки", "👤 Профиль"]
    assert [button.text for row in en for button in row] == ["🌿 Create mood", "⚙️ Subscriptions", "👤 Profile"]


def test_relationships_keyboard_contains_emojis():
    buttons = [button.text for row in relationships_subsphere_keyboard("ru").inline_keyboard for button in row]
    assert "❤️ С партнёром" in buttons
    assert "💼 С коллегами" in buttons
    assert "🫶 С друзьями" in buttons


def test_pronoun_labels_are_natural():
    buttons = [button.text for row in gender_keyboard("ru").inline_keyboard for button in row]
    en_buttons = [button.text for row in gender_keyboard("en").inline_keyboard for button in row]
    assert buttons == ["👩 Она", "👨 Он"]
    assert en_buttons == ["👩 She", "👨 He"]
    assert gender_profile_label("female", "ru") == "👩 Она"
    assert gender_profile_label("male", "en") == "👨 He"


def test_start_flow_does_not_send_bare_done_message():
    source = inspect.getsource(start)
    assert '"Готово."' not in source
    assert '"Done."' not in source
