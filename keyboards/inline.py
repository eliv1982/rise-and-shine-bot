from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
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
        b.button(text=_t(language, "✍️ Своя тема", "✍️ Custom theme"), callback_data="sphere:custom_theme")
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
    b.button(text=_t(language, "📷 Фото-стиль", "📷 Photo style"), callback_data="visual:photo")
    b.button(text=_t(language, "🖌 Мягкая иллюстрация", "🖌 Soft illustration"), callback_data="visual:illustration")
    b.button(text=_t(language, "🔀 Смешивать стили", "🔀 Mix styles"), callback_data="visual:mixed")
    b.adjust(1)
    return b.as_markup()


def relationships_subsphere_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "❤️ С партнёром", "❤️ With partner"), callback_data="subsphere:partner")
    b.button(text=_t(language, "💼 С коллегами", "💼 With colleagues"), callback_data="subsphere:colleagues")
    b.button(text=_t(language, "🫶 С друзьями", "🫶 With friends"), callback_data="subsphere:friends")
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
        "sunny_photo_scene": "☀️",
        "living_nature_photo": "🌿",
        "sea_coast_photo": "🌊",
        "calm_lifestyle_photo": "📸",
        "bright_photo_card": "☀️",
        "sunny_nature_photo": "🌿",
        "light_interior_photo": "🪟",
        "cinematic_real_photo": "📸",
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
    if label and label[0] in "🌊☀️🌿📸🪟🌸🖌🌱🎬🌫✨🧩":
        return label
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
    b.button(text=_t(language, "❌ Отмена", "❌ Cancel"), callback_data="theme:cancel")
    b.adjust(1)
    return b.as_markup()


def theme_early_cancel_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "❌ Отмена", "❌ Cancel"), callback_data="theme_early:cancel")
    b.adjust(1)
    return b.as_markup()


def style_cancel_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "❌ Отмена", "❌ Cancel"), callback_data="style:cancel")
    b.adjust(1)
    return b.as_markup()


def voice_recovery_keyboard(language: str, *, scope: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(
        text=_t(language, "🔁 Повторить голосом", "🔁 Try voice again"),
        callback_data=f"{scope}:retry_voice",
    )
    b.button(
        text=_t(language, "✍️ Ввести текстом", "✍️ Type text"),
        callback_data=f"{scope}:type_text",
    )
    b.button(
        text=_t(language, "↩️ Назад", "↩️ Back"),
        callback_data=f"{scope}:back",
    )
    b.button(
        text=_t(language, "🏠 В меню", "🏠 Menu"),
        callback_data=f"{scope}:menu",
    )
    b.adjust(1)
    return b.as_markup()


def voice_confirm_keyboard(language: str, *, scope: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(
        text=_t(language, "✅ Использовать", "✅ Use this"),
        callback_data=f"{scope}:use",
    )
    b.button(
        text=_t(language, "🔁 Повторить голосом", "🔁 Try voice again"),
        callback_data=f"{scope}:retry_voice",
    )
    b.button(
        text=_t(language, "✍️ Ввести текстом", "✍️ Type text"),
        callback_data=f"{scope}:type_text",
    )
    b.button(
        text=_t(language, "↩️ Назад", "↩️ Back"),
        callback_data=f"{scope}:back",
    )
    b.button(
        text=_t(language, "🏠 В меню", "🏠 Menu"),
        callback_data=f"{scope}:menu",
    )
    b.adjust(1)
    return b.as_markup()


def gender_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "👩 Она", "👩 She"), callback_data="gender:female")
    b.button(text=_t(language, "👨 Он", "👨 He"), callback_data="gender:male")
    b.adjust(2)
    return b.as_markup()


def language_keyboard() -> InlineKeyboardMarkup:
    """Выбор языка: русский / English (для /language и для подписки)."""
    b = InlineKeyboardBuilder()
    b.button(text="🇷🇺 Русский", callback_data="lang:ru")
    b.button(text="🇬🇧 English", callback_data="lang:en")
    b.adjust(2)
    return b.as_markup()


def start_menu_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "🌿 Создать настрой", "🌿 Create focus"), callback_data="cmd:new")
    b.button(text=_t(language, "⚙️ Подписки", "⚙️ Subscriptions"), callback_data="sub:dash")
    b.button(text=_t(language, "👤 Профиль", "👤 Profile"), callback_data="profile:open")
    b.adjust(1)
    return b.as_markup()


def main_reply_keyboard(language: str) -> ReplyKeyboardMarkup:
    """Persistent нижнее меню для основных действий."""
    if language == "en":
        keyboard = [
            [KeyboardButton(text="🌿 Create mood")],
            [KeyboardButton(text="⚙️ Subscriptions"), KeyboardButton(text="👤 Profile")],
        ]
    else:
        keyboard = [
            [KeyboardButton(text="🌿 Создать настрой")],
            [KeyboardButton(text="⚙️ Подписки"), KeyboardButton(text="👤 Профиль")],
        ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder=_t(language, "Выбери действие", "Choose an action"),
    )


def new_affirmation_keyboard(language: str) -> InlineKeyboardMarkup:
    """Кнопка создания нового настроя дня после регистрации."""
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "🌿 Создать настрой", "🌿 Create focus"), callback_data="cmd:new")
    b.adjust(1)
    return b.as_markup()


def after_generation_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if is_tts_available(language):
        b.button(text="🔊 Озвучить", callback_data="tts:yes")
    b.button(text=_t(language, "✨ Ещё настрой", "✨ More"), callback_data="again:yes")
    b.button(text=_t(language, "🔁 Создать новый", "🔁 Create new"), callback_data="new:yes")
    b.button(text=_t(language, "⚙️ Настроить подписки", "⚙️ Manage subscriptions"), callback_data="sub:open")
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
    b.button(text=_t(language, "✅ Подтвердить", "✅ Confirm"), callback_data="sub:confirm")
    b.button(text=_t(language, "❌ Отмена", "❌ Cancel"), callback_data="sub:cancel")
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
        text=_t(language, "🔁 Создать новый", "🔁 Create new"),
        callback_data="sub_new:yes",
    )
    b.button(
        text=_t(language, "⚙️ Настроить подписки", "⚙️ Manage subscriptions"),
        callback_data="sub:change",
    )
    b.adjust(1)
    return b.as_markup()


def profile_keyboard(language: str, has_subscription: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "⚙️ Настроить подписки", "⚙️ Manage subscriptions"), callback_data="sub:dash")
    b.button(text=_t(language, "👩 Она", "👩 She"), callback_data="gender:female")
    b.button(text=_t(language, "👨 Он", "👨 He"), callback_data="gender:male")
    b.adjust(1)
    return b.as_markup()


def subscription_dashboard_keyboard(language: str, count: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if count < 3:
        b.button(text=_t(language, "➕ Добавить подписку", "➕ Add subscription"), callback_data="sub:add")
    if count > 0:
        b.button(text=_t(language, "✏️ Изменить подписку", "✏️ Edit subscription"), callback_data="sub:edit")
        b.button(text=_t(language, "🗑 Удалить подписку", "🗑 Delete subscription"), callback_data="sub:delete")
    b.button(text=_t(language, "❌ Отмена", "❌ Cancel"), callback_data="sub:cancel_dash")
    b.adjust(1)
    return b.as_markup()


def subscription_saved_keyboard(language: str, count: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if count < 3:
        b.button(text=_t(language, "➕ Добавить ещё", "➕ Add another"), callback_data="sub:add")
    b.button(text=_t(language, "🧾 Мои подписки", "🧾 My subscriptions"), callback_data="sub:dash")
    b.button(text=_t(language, "🌿 Создать настрой", "🌿 Create focus"), callback_data="sub_new:yes")
    b.adjust(1)
    return b.as_markup()


def subscription_select_keyboard(subscriptions: list[dict], language: str, action: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    prefix = "subedit" if action == "edit" else "subdel"
    for idx, sub in enumerate(subscriptions, start=1):
        mode = sub.get("subscription_mode") or ("weekly_balance" if sub.get("sphere") == "random" else "sphere_focus")
        if mode == "weekly_balance":
            title = _t(language, "🌿 Баланс недели", "🌿 Weekly balance")
        else:
            title = get_sphere_label(sub.get("subscription_sphere") or sub.get("sphere") or "inner_peace", language)
        time_str = f"{int(sub.get('hour', 0)):02d}:{int(sub.get('minute', 0)):02d}"
        visual = sub.get("visual_mode") or "illustration"
        visual_icon = {"photo": "📷", "illustration": "🖌", "mixed": "🔀"}.get(visual, "🖌")
        b.button(text=f"{idx}. {title} — {time_str} — {visual_icon}", callback_data=f"{prefix}:{sub['id']}")
    b.button(text=_t(language, "↩️ Назад", "↩️ Back"), callback_data="sub:dash")
    b.adjust(1)
    return b.as_markup()


def subscription_edit_keyboard(language: str, subscription_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "⏰ Время", "⏰ Time"), callback_data=f"subfield:{subscription_id}:time")
    b.button(text=_t(language, "🌿 Режим", "🌿 Mode"), callback_data=f"subfield:{subscription_id}:mode")
    b.button(text=_t(language, "🧭 Сферу", "🧭 Sphere"), callback_data=f"subfield:{subscription_id}:sphere")
    b.button(text=_t(language, "🎨 Визуальный режим", "🎨 Visual mode"), callback_data=f"subfield:{subscription_id}:visual")
    b.button(text=_t(language, "✨ Стиль", "✨ Style"), callback_data=f"subfield:{subscription_id}:style")
    b.button(text=_t(language, "🌍 Язык", "🌍 Language"), callback_data=f"subfield:{subscription_id}:language")
    b.button(text=_t(language, "🗑 Удалить эту подписку", "🗑 Delete this subscription"), callback_data=f"subdel:{subscription_id}")
    b.button(text=_t(language, "↩️ Назад", "↩️ Back"), callback_data="sub:edit")
    b.adjust(1)
    return b.as_markup()


def subscription_delete_confirm_keyboard(language: str, subscription_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "🗑 Да, удалить", "🗑 Yes, delete"), callback_data=f"subdelok:{subscription_id}")
    b.button(text=_t(language, "↩️ Назад", "↩️ Back"), callback_data="sub:dash")
    b.adjust(1)
    return b.as_markup()


def subscription_edit_done_keyboard(language: str, subscription_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "✏️ Изменить ещё", "✏️ Edit more"), callback_data=f"subedit:{subscription_id}")
    b.button(text=_t(language, "🧾 К подпискам", "🧾 Back to subscriptions"), callback_data="sub:dash")
    b.button(text=_t(language, "🌿 Создать настрой", "🌿 Create focus"), callback_data="sub_new:yes")
    b.adjust(1)
    return b.as_markup()


def subscription_language_edit_keyboard(language: str, subscription_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🇷🇺 Русский", callback_data=f"sublangedit:{subscription_id}:ru")
    b.button(text="🇬🇧 English", callback_data=f"sublangedit:{subscription_id}:en")
    b.button(text=_t(language, "↩️ Назад", "↩️ Back"), callback_data=f"subedit:{subscription_id}")
    b.adjust(1)
    return b.as_markup()


def subscription_visual_style_followup_keyboard(language: str, subscription_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "✨ Да, выбрать стиль", "✨ Yes, choose style"), callback_data=f"substylepick:{subscription_id}:yes")
    b.button(text=_t(language, "✅ Оставить автоподбор", "✅ Keep auto"), callback_data=f"substylepick:{subscription_id}:auto")
    b.adjust(1)
    return b.as_markup()


def subscription_mode_sphere_info_keyboard(language: str, subscription_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "🌿 Изменить режим", "🌿 Change mode"), callback_data=f"subfield:{subscription_id}:mode")
    b.button(text=_t(language, "↩️ Назад", "↩️ Back"), callback_data=f"subedit:{subscription_id}")
    b.adjust(1)
    return b.as_markup()

