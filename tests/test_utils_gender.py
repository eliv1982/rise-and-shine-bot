from services.ritual_config import get_focuses
from utils import build_focus_of_day, gender_display, normalize_gender


def test_normalize_gender_basic():
    assert normalize_gender("female") == "female"
    assert normalize_gender("male") == "male"
    assert normalize_gender("Female") == "female"
    assert normalize_gender("MALE") == "male"
    assert normalize_gender(None) is None
    assert normalize_gender("") is None
    assert normalize_gender("unknown") is None


def test_gender_display_never_empty():
    assert gender_display(None, "ru")
    assert "мужч" in gender_display(None, "ru").lower() or "для" in gender_display(None, "ru")
    assert gender_display("female", "ru") == "для женщины"


def test_focus_of_day_is_localized_and_non_empty():
    assert build_focus_of_day("money", "ru") in {focus["ru"] for focus in get_focuses("money")}
    assert build_focus_of_day("money", "en") in {focus["en"] for focus in get_focuses("money")}
