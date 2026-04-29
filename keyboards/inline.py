from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.ritual_config import (
    ILLUSTRATION_STYLE_KEYS,
    MAIN_SPHERES,
    PHOTO_STYLE_KEYS,
    get_sphere_label,
    get_style_label,
    is_tts_available,
    normalize_visual_mode,
)


def _t(language: str, ru: str, en: str) -> str:
    return ru if language == "ru" else en


def _sphere_buttons(b: InlineKeyboardBuilder, language: str, include_custom_theme: bool = True) -> None:
    for sphere in MAIN_SPHERES:
        b.button(text=get_sphere_label(sphere, language), callback_data=f"sphere:{sphere}")
    if include_custom_theme:
        b.button(text=_t(language, "Своя тема", "Custom theme"), callback_data="sphere:custom_theme")
    b.adjust(1)


def sphere_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    _sphere_buttons(b, language, include_custom_theme=True)
    return b.as_markup()


def sphere_keyboard_for_subscription(language: str) -> InlineKeyboardMarkup:
    """Основные сферы для режима фокуса на одной сфере."""
    b = InlineKeyboardBuilder()
    for sphere in MAIN_SPHERES:
        b.button(text=get_sphere_label(sphere, language), callback_data=f"sphere:{sphere}")
    b.adjust(1)
    return b.as_markup()


def subscription_mode_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "🌿 Баланс недели", "🌿 Weekly balance"), callback_data="submode:weekly_balance")
    b.button(text=_t(language, "🎯 Фокус на сфере", "🎯 Focus on one area"), callback_data="submode:sphere_focus")
    b.adjust(1)
    return b.as_markup()


def visual_mode_keyboard(language: str, *, for_subscription: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "📷 Фотореализм", "📷 Photo realism"), callback_data="visual:photo")
    b.button(text=_t(language, "🖌 Мягкая иллюстрация", "🖌 Soft illustration"), callback_data="visual:illustration")
    b.button(text=_t(language, "🔀 Смешивать стили", "🔀 Mix styles"), callback_data="visual:mixed")
    b.adjust(1)
    return b.as_markup()


def relationships_subsphere_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "С партнёром", "With partner"), callback_data="subsphere:partner")
    b.button(text=_t(language, "С коллегами", "With colleagues"), callback_data="subsphere:colleagues")
    b.button(text=_t(language, "С друзьями", "With friends"), callback_data="subsphere:friends")
    b.adjust(1)
    return b.as_markup()


def _style_keys_for_visual_mode(visual_mode: str) -> list[str]:
    mode = normalize_visual_mode(visual_mode)
    if mode == "photo":
        return PHOTO_STYLE_KEYS
    if mode == "mixed":
        return PHOTO_STYLE_KEYS + ILLUSTRATION_STYLE_KEYS
    return ILLUSTRATION_STYLE_KEYS


def _style_button_label(style: str, language: str) -> str:
    icons = {
        "bright_photo_card": "🌞",
        "sunny_nature_photo": "🌿",
        "light_interior_photo": "🪟",
        "cinematic_real_photo": "🎬",
        "bright_nature_card": "🌸",
        "dreamy_painterly": "🖌",
        "quiet_interior": "🪟",
        "minimal_botanical": "🌱",
        "cinematic_light": "🎬",
        "ethereal_landscape": "🌫",
        "symbolic_luxe": "✨",
        "textured_collage": "🧩",
    }
    label = get_style_label(style, language)
    icon = icons.get(style)
    return f"{icon} {label}" if icon else label


def style_keyboard(language: str, visual_mode: str = "illustration") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "🎨 Автоподбор", "🎨 Auto"), callback_data="style:auto")
    for style in _style_keys_for_visual_mode(visual_mode):
        b.button(text=_style_button_label(style, language), callback_data=f"style:{style}")
    b.button(text=_t(language, "Свой стиль", "Custom style"), callback_data="style:custom")
    b.adjust(1)
    return b.as_markup()


def style_keyboard_for_subscription(language: str, visual_mode: str = "illustration") -> InlineKeyboardMarkup:
    """Curated стили для подписки."""
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "🎨 Автоподбор", "🎨 Auto"), callback_data="style:auto")
    b.button(text=_t(language, "🔀 Разные подходящие стили", "🔀 Different suitable styles"), callback_data="style:random_suitable")
    for style in _style_keys_for_visual_mode(visual_mode):
        b.button(text=_style_button_label(style, language), callback_data=f"style:{style}")
    b.adjust(1)
    return b.as_markup()


def theme_choice_keyboard(language: str) -> InlineKeyboardMarkup:
    """Продолжить — без своей темы, Своя тема — опционально добавить (текст/голос)."""
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "Продолжить", "Continue"), callback_data="theme:continue")
    b.button(text=_t(language, "Своя тема", "Custom theme"), callback_data="theme:custom")
    b.adjust(2)
    return b.as_markup()


def theme_cancel_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "Отмена", "Cancel"), callback_data="theme:cancel")
    b.adjust(1)
    return b.as_markup()


def theme_early_cancel_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "Отмена", "Cancel"), callback_data="theme_early:cancel")
    b.adjust(1)
    return b.as_markup()


def style_cancel_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "Отмена", "Cancel"), callback_data="style:cancel")
    b.adjust(1)
    return b.as_markup()


def gender_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "Мужской", "Male"), callback_data="gender:male")
    b.button(text=_t(language, "Женский", "Female"), callback_data="gender:female")
    b.adjust(2)
    return b.as_markup()


def language_keyboard() -> InlineKeyboardMarkup:
    """Выбор языка: русский / English (для /language и для подписки)."""
    b = InlineKeyboardBuilder()
    b.button(text="Русский", callback_data="lang:ru")
    b.button(text="English", callback_data="lang:en")
    b.adjust(2)
    return b.as_markup()


def new_affirmation_keyboard(language: str) -> InlineKeyboardMarkup:
    """Кнопка создания нового настроя дня после регистрации."""
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "🌿 Создать настрой дня", "🌿 Create daily focus"), callback_data="cmd:new")
    b.adjust(1)
    return b.as_markup()


def after_generation_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if is_tts_available(language):
        b.button(text="🔊 Озвучить", callback_data="tts:yes")
    b.button(text=_t(language, "✨ Ещё настрой", "✨ More"), callback_data="again:yes")
    b.button(text=_t(language, "🔁 Создать новый", "🔁 Create new"), callback_data="new:yes")
    b.button(text=_t(language, "⚙️ Настроить подписку", "⚙️ Subscription settings"), callback_data="sub:open")
    b.adjust(1)
    return b.as_markup()


def subscription_time_keyboard_hours(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for hour in range(0, 24):
        b.button(text=f"{hour:02d}", callback_data=f"hour:{hour}")
    b.adjust(6)
    return b.as_markup()


def subscription_time_keyboard_minutes(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for minute in range(0, 60, 15):
        b.button(text=f"{minute:02d}", callback_data=f"minute:{minute}")
    b.adjust(4)
    return b.as_markup()


def subscription_confirm_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "Подтвердить", "Confirm"), callback_data="sub:confirm")
    b.button(text=_t(language, "Отмена", "Cancel"), callback_data="sub:cancel")
    b.adjust(2)
    return b.as_markup()


def subscription_after_keyboard(language: str) -> InlineKeyboardMarkup:
    """Клавиатура под сообщением по подписке."""
    b = InlineKeyboardBuilder()
    if is_tts_available(language):
        b.button(text="🔊 Озвучить", callback_data="sub_tts:yes")
    b.button(
        text=_t(language, "✨ Ещё настрой", "✨ More"),
        callback_data="sub_more:yes",
    )
    b.button(
        text=_t(language, "🔁 Создать новую", "Create new"),
        callback_data="sub_new:yes",
    )
    b.button(
        text=_t(language, "⚙️ Настроить подписку", "Subscription settings"),
        callback_data="sub:change",
    )
    b.adjust(1)
    return b.as_markup()


def profile_keyboard(language: str, has_subscription: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "⚙️ Настроить подписку", "⚙️ Subscription settings"), callback_data="sub:change")
    if has_subscription:
        b.button(text=_t(language, "🗑 Отменить подписку", "🗑 Cancel subscription"), callback_data="sub:unsubscribe")
    b.button(text=_t(language, "Мужской", "Male"), callback_data="gender:male")
    b.button(text=_t(language, "Женский", "Female"), callback_data="gender:female")
    b.adjust(1)
    return b.as_markup()

