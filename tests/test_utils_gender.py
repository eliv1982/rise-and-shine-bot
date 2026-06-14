from services.ritual_config import get_focuses
from utils import (
    build_focus_of_day,
    display_name_for_language,
    gender_display,
    infer_gender_from_hint,
    is_gibberish_text,
    normalize_gender,
    normalize_russian_informal_address,
)


def test_normalize_gender_basic():
    assert normalize_gender("female") == "female"
    assert normalize_gender("male") == "male"
    assert normalize_gender("Female") == "female"
    assert normalize_gender("MALE") == "male"
    assert normalize_gender(None) is None
    assert normalize_gender("") is None
    assert normalize_gender("unknown") is None
    assert normalize_gender("женщина") == "female"
    assert normalize_gender("мужчина") == "male"
    assert normalize_gender("она") == "female"
    assert normalize_gender("он") == "male"


def test_gender_display_never_empty():
    assert gender_display(None, "ru")
    assert "нейтраль" in gender_display(None, "ru").lower()
    assert gender_display("female", "ru") == "для женщины"


def test_infer_gender_from_hint_supports_runtime_values():
    assert infer_gender_from_hint("для женщины") == "female"
    assert infer_gender_from_hint("женский") == "female"
    assert infer_gender_from_hint("она") == "female"
    assert infer_gender_from_hint("feminine") == "female"
    assert infer_gender_from_hint("для мужчины") == "male"
    assert infer_gender_from_hint("мужской") == "male"
    assert infer_gender_from_hint("он") == "male"
    assert infer_gender_from_hint("masculine") == "male"
    assert infer_gender_from_hint("для пользователя") is None


def test_focus_of_day_is_localized_and_non_empty():
    assert build_focus_of_day("money", "ru") in {focus["ru"] for focus in get_focuses("money")}
    assert build_focus_of_day("money", "en") in {focus["en"] for focus in get_focuses("money")}


def test_display_name_transliterates_for_english_ui():
    assert display_name_for_language("Лена", "en") == "Lena"
    assert display_name_for_language("Лена", "ru") == "Лена"


def test_is_gibberish_text_detects_repeated_nonsense():
    assert is_gibberish_text("Do stoint weh weh weh")
    assert not is_gibberish_text("Достоинство и вера в себя")


def test_normalize_russian_informal_address_handles_common_formal_imperatives():
    assert normalize_russian_informal_address("Упростите один бытовой шаг.") == "Упрости один бытовой шаг."
    assert normalize_russian_informal_address("Выберите одно действие.") == "Выбери одно действие."
    assert normalize_russian_informal_address("Назовите три вещи.") == "Назови три вещи."
    assert normalize_russian_informal_address("Позвольте себе паузу.") == "Позволь себе паузу."


def test_normalize_russian_informal_address_leaves_unrelated_or_correct_words_untouched():
    assert normalize_russian_informal_address("Прими одно решение из ясности.") == "Прими одно решение из ясности."
    assert normalize_russian_informal_address("Выбери одно действие из любопытства.") == "Выбери одно действие из любопытства."
    assert normalize_russian_informal_address("Это уже упрощённый шаг.") == "Это уже упрощённый шаг."
