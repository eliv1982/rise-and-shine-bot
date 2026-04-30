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


def missing_previous_generation_text(language: str) -> str:
    return (
        "Не нашла параметры предыдущего настроя. Давай начнём заново с /new."
        if language == "ru"
        else "Could not find previous parameters. Please start again with /new."
    )
