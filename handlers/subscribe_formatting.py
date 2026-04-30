from typing import Optional

from services.ritual_config import get_sphere_label, get_style_label, normalize_visual_mode


def sphere_display(sphere: str, language: str) -> str:
    """Человекочитаемое название сферы для подтверждения подписки."""
    if sphere == "random":
        return "Баланс недели" if language == "ru" else "Weekly balance"
    return get_sphere_label(sphere, language)


def style_display(style: str, language: str) -> str:
    """Человекочитаемое название стиля для подтверждения подписки."""
    if style == "random":
        style = "random_suitable"
    return get_style_label(style, language)


def sub_language(state_data: dict, user: Optional[dict]) -> str:
    """Язык в потоке подписки: из state или из профиля."""
    return (state_data or {}).get("language") or (user or {}).get("language", "ru")


def subscription_update_kwargs(subscription: dict, **overrides) -> dict:
    data = {
        "sphere": subscription.get("sphere") or "random",
        "subsphere": subscription.get("subsphere"),
        "image_style": subscription.get("image_style") or "auto",
        "language": subscription.get("language") or "ru",
        "hour": int(subscription.get("hour", 0)),
        "minute": int(subscription.get("minute", 0)),
        "subscription_mode": subscription.get("subscription_mode")
        or ("weekly_balance" if subscription.get("sphere") == "random" else "sphere_focus"),
        "subscription_sphere": subscription.get("subscription_sphere"),
        "subscription_style_mode": subscription.get("subscription_style_mode") or subscription.get("image_style") or "auto",
        "visual_mode": normalize_visual_mode(subscription.get("visual_mode")),
    }
    data.update(overrides)
    return data
