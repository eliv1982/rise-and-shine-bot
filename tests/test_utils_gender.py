from utils import gender_display, normalize_gender


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
