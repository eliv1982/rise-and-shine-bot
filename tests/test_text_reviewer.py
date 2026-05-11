from services.text_reviewer import review_generated_text


def test_review_generated_text_female_gender_mismatch_catches_masculine_first_person():
    report = review_generated_text(
        affirmations=["Я открыт новым возможностям", "Я выбираю спокойствие"],
        soft_action="Сделай один мягкий шаг",
        language="ru",
        gender_hint="для женщины",
    )

    assert report["checks"]["gender_mismatch"] is True


def test_review_generated_text_female_does_not_flag_feminine_first_person():
    report = review_generated_text(
        affirmations=["Я открыта новым возможностям", "Я выбираю спокойствие"],
        language="ru",
        gender_hint="она",
    )

    assert report["checks"]["gender_mismatch"] is False


def test_review_generated_text_unknown_gender_does_not_flag_gender_mismatch():
    report = review_generated_text(
        affirmations=["Я открыт новым возможностям"],
        language="ru",
        gender_hint="для пользователя",
    )

    assert report["checks"]["gender_mismatch"] is False


def test_review_generated_text_detects_repeated_openings():
    report = review_generated_text(
        affirmations=["Я выбираю спокойствие", "Я выбираю ясность", "Я нахожу опору"],
        language="ru",
    )

    assert report["checks"]["repeated_openings"] is True


def test_review_generated_text_detects_overused_affirmation_openings_from_memory():
    report = review_generated_text(
        affirmations=["Я выбираю спокойствие", "Я нахожу опору"],
        language="ru",
        text_memory_context={
            "avoid_affirmation_openings": ["я выбираю"],
            "overused_affirmation_openings": ["я выбираю"],
        },
    )

    assert report["checks"]["overused_affirmation_openings"] is True


def test_review_generated_text_detects_language_mismatch_for_russian_output():
    report = review_generated_text(
        affirmations=["I choose calm clarity", "Я нахожу опору"],
        language="ru",
    )

    assert report["checks"]["language_mismatch"] is True


def test_review_generated_text_detects_repeated_soft_action_structure_from_memory():
    report = review_generated_text(
        affirmations=["Я замечаю, что мне можно действовать мягче."],
        soft_action="Прими одно денежное решение из ясности, а не из страха.",
        language="ru",
        text_memory_context={
            "avoid_soft_action_structures": ["contrast_from_not_from"],
            "overused_soft_action_structures": ["contrast_from_not_from"],
        },
    )

    assert report["checks"]["repeated_soft_action_structure"] is True


def test_review_generated_text_detects_abstract_contrast_formula():
    report = review_generated_text(
        affirmations=["Я выбираю более живой ритм дня."],
        soft_action="Выбери одно действие из любопытства, а не из страха.",
        language="ru",
    )

    assert report["checks"]["abstract_contrast_formula"] is True


def test_review_generated_text_softly_flags_too_generic_text():
    report = review_generated_text(
        affirmations=[
            "Я выбираю спокойствие и ясность.",
            "Я принимаю устойчивость и достаточность.",
            "Я создаю гармонию внутри себя.",
        ],
        language="ru",
    )

    assert report["checks"]["too_generic"] is True


def test_review_generated_text_detects_pressure_language():
    report = review_generated_text(
        affirmations=["Я должна срочно собраться", "Я выбираю ясность"],
        language="ru",
    )

    assert report["checks"]["pressure_language"] is True


def test_review_generated_text_detects_productivity_framing():
    report = review_generated_text(
        affirmations=["Я выжму максимум из этого дня", "Я выбираю эффективность"],
        language="ru",
    )

    assert report["checks"]["too_productivity_framed"] is True


def test_review_generated_text_detects_soft_action_repeated_from_memory_context():
    report = review_generated_text(
        affirmations=["Я выбираю спокойствие"],
        soft_action="Назови три вещи, которые уже помогают",
        language="ru",
        text_memory_context={
            "avoid_soft_actions": [
                "назови три вещи, которые уже помогают",
                "сделай один маленький шаг",
            ],
            "avoid_soft_action_patterns": ["name_three_things"],
        },
    )

    assert report["checks"]["soft_action_repeated"] is True


def test_review_generated_text_flags_soft_action_repeated_by_family_pattern():
    report = review_generated_text(
        affirmations=["Я выбираю спокойствие"],
        soft_action="Назови три простые вещи, на которые можно опереться сейчас",
        language="ru",
        text_memory_context={
            "avoid_soft_action_patterns": ["name_three_things"],
            "overused_soft_action_patterns": ["name_three_things"],
        },
    )

    assert report["checks"]["soft_action_repeated"] is True


def test_review_generated_text_does_not_flag_unrelated_soft_action_family():
    report = review_generated_text(
        affirmations=["Я выбираю спокойствие"],
        soft_action="Запиши одну тихую мысль перед сном",
        language="ru",
        text_memory_context={
            "avoid_soft_action_patterns": ["name_three_things"],
            "overused_soft_action_patterns": ["name_three_things"],
        },
    )

    assert report["checks"]["soft_action_repeated"] is False


def test_review_generated_text_does_not_flag_unrelated_openings_or_language():
    report = review_generated_text(
        affirmations=["Я замечаю живое тепло утра", "Сегодня я иду мягче и яснее"],
        soft_action="Запиши одну тихую мысль перед сном",
        language="ru",
        text_memory_context={
            "avoid_affirmation_openings": ["я выбираю"],
            "overused_affirmation_openings": ["я выбираю"],
        },
    )

    assert report["checks"]["overused_affirmation_openings"] is False
    assert report["checks"]["language_mismatch"] is False


def test_review_generated_text_does_not_flag_unrelated_soft_action_structure():
    report = review_generated_text(
        affirmations=["Я замечаю живое тепло утра."],
        soft_action="Запиши одну мысль, которую хочется проверить на практике.",
        language="ru",
        text_memory_context={
            "avoid_soft_action_structures": ["contrast_from_not_from"],
            "overused_soft_action_structures": ["contrast_from_not_from"],
        },
    )

    assert report["checks"]["repeated_soft_action_structure"] is False
    assert report["checks"]["abstract_contrast_formula"] is False


def test_review_generated_text_score_decreases_when_warnings_exist():
    report = review_generated_text(
        affirmations=["Я открыт новому", "Я выбираю ясность", "Я выбираю покой"],
        soft_action="Назови три вещи, которые уже помогают",
        language="ru",
        gender_hint="для женщины",
        text_memory_context={"avoid_soft_actions": ["назови три вещи, которые уже помогают"]},
    )

    assert report["warnings"]
    assert report["score"] < 1.0


def test_review_generated_text_empty_input_is_safe():
    report = review_generated_text(
        affirmations=None,
        soft_action=None,
        language="ru",
    )

    assert report["enabled"] is True
    assert report["checks"]["gender_mismatch"] is False
    assert report["score"] <= 1.0
