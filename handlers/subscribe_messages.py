def new_flow_text(language: str) -> str:
    if language == "ru":
        return "🌿 Что создаём?\n\nВыбери сферу, для которой собрать настрой дня:"
    return "🌿 What shall we create?\n\nChoose an area for your daily focus:"


def visual_mode_text(language: str) -> str:
    return "🎨 Какой визуал тебе ближе?" if language == "ru" else "🎨 Which visual style feels closer to you?"


def style_choice_text(language: str) -> str:
    return "✨ Выбери стиль изображения:" if language == "ru" else "✨ Choose image style:"


def creating_text(language: str) -> str:
    return "🌿 Создаю твой настрой дня..." if language == "ru" else "🌿 Creating your daily focus..."


def limit_text(language: str) -> str:
    if language == "en":
        return "You already have 3 active subscriptions. Please edit or delete one first."
    return "У тебя уже 3 активные подписки. Сначала измени или удали одну из них."


def setup_intro(language: str, action: str = "add") -> str:
    if action == "edit":
        if language == "en":
            return "✏️ Edit subscription\n\nChoose subscription language:"
        return "✏️ Изменить подписку\n\nВыбери язык подписки:"
    if language == "en":
        return "➕ Add subscription\n\nChoose subscription language:"
    return "➕ Добавить подписку\n\nВыбери язык подписки:"
