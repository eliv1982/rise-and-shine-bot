def voice_recognition_failed_text(language: str) -> str:
    if language == "ru":
        return "Не получилось распознать голос 😕\nПопробуй ещё раз или отправь текстом."
    return "I couldn’t recognize the voice message 😕\nPlease try again or send it as text."


def voice_recognized_echo_text(language: str, recognized_text: str) -> str:
    clipped = recognized_text.strip()
    if len(clipped) > 140:
        clipped = clipped[:137] + "..."
    if language == "ru":
        return f"🎙 Распознано: \"{clipped}\""
    return f"🎙 Recognized: \"{clipped}\""


def voice_unclear_text(language: str) -> str:
    if language == "ru":
        return "Я распознала голос, но текст получился неразборчивым 😕\nПопробуй ещё раз или отправь словами."
    return "I recognized the voice message, but the text looks unclear 😕\nPlease try again or send it as text."


def voice_language_mismatch_text(language: str) -> str:
    if language == "ru":
        return "Похоже, голос распознан на другом языке 🌿\nОтправь голосовое или текст на русском."
    return "I recognized speech in another language 🌿\nPlease send voice or text in English."


def main_menu_mismatch_text(language: str) -> str:
    if language == "ru":
        return "Я сейчас работаю на русском 🌿\nВыбери действие в меню или отправь сообщение на русском."
    return "I’m currently working in English 🌿\nPlease choose an option from the menu or send a message in English."


def text_language_mismatch_text(language: str) -> str:
    if language == "ru":
        return "В этом режиме я жду текст на русском 🌿\nНапиши тему или стиль по-русски."
    return "I can work with this flow in English 🌿\nPlease send the theme or style in English."


def menu_choose_option_text(language: str) -> str:
    if language == "ru":
        return "Выбери вариант в меню выше 🌿\nЕсли хочешь написать свою тему — нажми «Своя тема»."
    return "Please choose an option from the menu above 🌿\nIf you want to write your own theme, choose “Custom theme”."


def menu_choose_style_text(language: str) -> str:
    if language == "ru":
        return "Выбери стиль кнопкой выше 🎨\nЕсли хочешь описать стиль своими словами — выбери «Свой стиль»."
    return "Please choose an image style from the buttons above 🎨\nIf you want to describe your own style, choose “Custom style”."
