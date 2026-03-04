from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def _t(language: str, ru: str, en: str) -> str:
    return ru if language == "ru" else en


def _sphere_buttons(b: InlineKeyboardBuilder, language: str, include_custom_theme: bool = True) -> None:
    b.button(text=_t(language, "Карьера и успех", "Career & success"), callback_data="sphere:career")
    b.button(text=_t(language, "Здоровье и энергия", "Health & energy"), callback_data="sphere:health")
    b.button(text=_t(language, "Финансовое благополучие", "Financial well-being"), callback_data="sphere:money")
    b.button(text=_t(language, "Отношения", "Relationships"), callback_data="sphere:relationships")
    b.button(text=_t(language, "Самореализация и творчество", "Self-realization & creativity"), callback_data="sphere:self_realization")
    b.button(text=_t(language, "Духовный рост", "Spiritual growth"), callback_data="sphere:spirituality")
    b.button(text=_t(language, "Внутренний покой", "Inner peace"), callback_data="sphere:inner_peace")
    if include_custom_theme:
        b.button(text=_t(language, "Своя тема", "Custom theme"), callback_data="sphere:custom_theme")
    b.adjust(1)


def sphere_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    _sphere_buttons(b, language, include_custom_theme=True)
    return b.as_markup()


def sphere_keyboard_for_subscription(language: str) -> InlineKeyboardMarkup:
    """Сферы для подписки (без «Своя тема»)."""
    b = InlineKeyboardBuilder()
    _sphere_buttons(b, language, include_custom_theme=False)
    return b.as_markup()


def relationships_subsphere_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "С партнёром", "With partner"), callback_data="subsphere:partner")
    b.button(text=_t(language, "С коллегами", "With colleagues"), callback_data="subsphere:colleagues")
    b.button(text=_t(language, "С друзьями", "With friends"), callback_data="subsphere:friends")
    b.adjust(1)
    return b.as_markup()


def style_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "Реалистичный", "Realistic"), callback_data="style:realistic")
    b.button(text=_t(language, "Мультяшный", "Cartoon"), callback_data="style:cartoon")
    b.button(text=_t(language, "Мандала", "Mandala"), callback_data="style:mandala")
    b.button(text=_t(language, "Сакральная геометрия", "Sacred geometry"), callback_data="style:sacred_geometry")
    b.button(text=_t(language, "Природа", "Nature"), callback_data="style:nature")
    b.button(text=_t(language, "Космос", "Cosmos"), callback_data="style:cosmos")
    b.button(text=_t(language, "Абстракция", "Abstract"), callback_data="style:abstract")
    b.button(text=_t(language, "Свой стиль", "Custom style"), callback_data="style:custom")
    b.adjust(1)
    return b.as_markup()


def style_keyboard_for_subscription(language: str) -> InlineKeyboardMarkup:
    """Стили для подписки (без «Свой стиль»)."""
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "Реалистичный", "Realistic"), callback_data="style:realistic")
    b.button(text=_t(language, "Мультяшный", "Cartoon"), callback_data="style:cartoon")
    b.button(text=_t(language, "Мандала", "Mandala"), callback_data="style:mandala")
    b.button(text=_t(language, "Сакральная геометрия", "Sacred geometry"), callback_data="style:sacred_geometry")
    b.button(text=_t(language, "Природа", "Nature"), callback_data="style:nature")
    b.button(text=_t(language, "Космос", "Cosmos"), callback_data="style:cosmos")
    b.button(text=_t(language, "Абстракция", "Abstract"), callback_data="style:abstract")
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


def style_extra_keyboard(language: str) -> InlineKeyboardMarkup:
    """После выбора пресетного стиля: добавить описание или продолжить."""
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "Добавить описание", "Add description"), callback_data="style_extra:add")
    b.button(text=_t(language, "Продолжить", "Continue"), callback_data="style_extra:continue")
    b.adjust(1)
    return b.as_markup()


def gender_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "Мужской", "Male"), callback_data="gender:male")
    b.button(text=_t(language, "Женский", "Female"), callback_data="gender:female")
    b.adjust(2)
    return b.as_markup()


def new_affirmation_keyboard(language: str) -> InlineKeyboardMarkup:
    """Кнопка «Новая аффирмация» после регистрации."""
    b = InlineKeyboardBuilder()
    b.button(text=_t(language, "Новая аффирмация", "New affirmation"), callback_data="cmd:new")
    b.adjust(1)
    return b.as_markup()


def after_generation_keyboard(language: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="🔊 Озвучить", callback_data="tts:yes")
    b.button(text=_t(language, "Ещё аффирмацию", "More"), callback_data="again:yes")
    b.button(text=_t(language, "Создать новую (другая сфера/стиль)", "Create new (different sphere/style)"), callback_data="new:yes")
    b.button(text=_t(language, "Настроить подписку", "Subscribe"), callback_data="sub:open")
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

