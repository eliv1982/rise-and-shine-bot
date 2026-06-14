from typing import Optional

from database import MAX_ACTIVE_SUBSCRIPTIONS
from services.ritual_config import (
    get_allowed_visual_modes,
    get_sphere_label,
    get_style_label,
    get_visual_mix_preset_label,
    get_visual_mode_label,
    visual_mix_preset_for_modes,
)


def visual_mix_summary_label(allowed_visual_modes: list[str], language: str) -> str:
    if len(allowed_visual_modes) == 1:
        return get_visual_mode_label(allowed_visual_modes[0], language)
    preset_key = visual_mix_preset_for_modes(allowed_visual_modes)
    if preset_key:
        return get_visual_mix_preset_label(preset_key, language)
    return " + ".join(get_visual_mode_label(mode, language) for mode in allowed_visual_modes)


def gender_profile_label(gender: Optional[str], language: str) -> str:
    if language == "en":
        if gender == "female":
            return "👩 She"
        if gender == "male":
            return "👨 He"
        return "not specified"
    if gender == "female":
        return "👩 Она"
    if gender == "male":
        return "👨 Он"
    return "не указано"


def subscription_mode_label(mode: str, language: str) -> str:
    if mode == "sphere_focus":
        return "🎯 Фокус на сфере" if language == "ru" else "🎯 Focus on one area"
    return "🌿 Баланс недели" if language == "ru" else "🌿 Weekly balance"


def subscription_style_label(style: Optional[str], language: str) -> str:
    style = style or "auto"
    if style in ("auto", "random"):
        return "🎨 Автоподбор" if language == "ru" else "🎨 Auto"
    if style == "random_suitable":
        return "🔀 Разные подходящие стили" if language == "ru" else "🔀 Different suitable styles"
    return get_style_label(style, language)


def format_subscription_summary(sub: dict, language: str = "ru", index: int = 1) -> str:
    mode = sub.get("subscription_mode") or ("weekly_balance" if sub.get("sphere") == "random" else "sphere_focus")
    allowed_visual_modes = get_allowed_visual_modes(sub)
    style = sub.get("subscription_style_mode") or sub.get("image_style") or "auto"
    time_str = f"{int(sub.get('hour', 0)):02d}:{int(sub.get('minute', 0)):02d}"

    lines = [f"{index}. {subscription_mode_label(mode, language)}"]
    if mode == "sphere_focus":
        sphere = sub.get("subscription_sphere") or sub.get("sphere") or "inner_peace"
        label = get_sphere_label(sphere, language)
        lines.append(f"   Сфера: {label}" if language == "ru" else f"   Area: {label}")
    lines.append(f"   ⏰ Время: {time_str}" if language == "ru" else f"   ⏰ Time: {time_str}")
    visual_label = visual_mix_summary_label(allowed_visual_modes, language)
    lines.append(
        f"   🎨 Визуал: {visual_label}"
        if language == "ru"
        else f"   🎨 Visual: {visual_label}"
    )
    lines.append(
        f"   ✨ Стиль: {subscription_style_label(style, language)}"
        if language == "ru"
        else f"   ✨ Style: {subscription_style_label(style, language)}"
    )
    return "\n".join(lines)


def build_subscriptions_summary(subscriptions: list[dict], language: str = "ru") -> str:
    if not subscriptions:
        if language == "en":
            return "No active subscriptions yet.\nYou can set up your daily ritual with /subscribe."
        return "Пока нет активных подписок.\nНастроить ежедневный ритуал можно командой /subscribe."
    return "\n\n".join(format_subscription_summary(sub, language, idx) for idx, sub in enumerate(subscriptions, start=1))


def build_subscription_summary(subscription: Optional[dict], language: str = "ru") -> str:
    return build_subscriptions_summary([subscription] if subscription else [], language)


def build_dashboard_text(subscriptions: list[dict], language: str = "ru") -> str:
    count = len(subscriptions)
    if not subscriptions:
        if language == "en":
            return (
                "🧾 Your subscriptions\n\n"
                "No active subscriptions yet.\n\n"
                "You can add up to 3 daily rituals: for example, weekly balance in the morning and inner peace in the evening."
            )
        return (
            "🧾 Твои подписки\n\n"
            "Пока нет активных подписок.\n\n"
            "Можно добавить до 3 ежедневных ритуалов: например, утром — баланс недели, вечером — внутренний покой."
        )

    summary = build_subscriptions_summary(subscriptions, language)
    if language == "en":
        return (
            "🧾 Your subscriptions\n\n"
            f"Active subscriptions: {count}/{MAX_ACTIVE_SUBSCRIPTIONS}\n\n"
            f"{summary}\n\n"
            "What would you like to do?"
        )
    return (
        "🧾 Твои подписки\n\n"
        f"Активных подписок: {count}/{MAX_ACTIVE_SUBSCRIPTIONS}\n\n"
        f"{summary}\n\n"
        "Что хочешь сделать?"
    )
