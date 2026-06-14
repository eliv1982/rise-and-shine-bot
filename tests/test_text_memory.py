import asyncio

from services import text_memory


def test_extract_text_patterns_finds_common_russian_patterns():
    patterns = text_memory.extract_text_patterns(
        "Я позволяю себе маленький шаг без чувства вины и выбираю спокойствие и ясность."
    )

    assert "я позволяю" in patterns
    assert "я выбираю" in patterns
    assert "маленький шаг" in patterns
    assert "без чувства вины" in patterns
    assert "спокойствие" in patterns
    assert "ясность" in patterns


def test_build_text_memory_context_dedupes_and_counts_patterns():
    context = text_memory.build_text_memory_context(
        [
            {
                "focus_title": "спокойствие и опора",
                "soft_action": "назови три вещи, которые уже помогают",
                "affirmations": [
                    "Я позволяю себе паузу без чувства вины.",
                    "Я выбираю ясность и устойчивость.",
                ],
            },
            {
                "focus_title": "деньги и устойчивость",
                "soft_action": "сделай один маленький шаг к финансовой ясности",
                "affirmations": [
                    "Я позволяю себе двигаться маленькими шагами.",
                    "Я выбираю устойчивость без давления.",
                ],
            },
        ],
        limit=10,
    )

    assert context["recent_focus_titles"] == ["спокойствие и опора", "деньги и устойчивость"]
    assert context["pattern_counts"]["я позволяю"] == 2
    assert context["pattern_counts"]["я выбираю"] == 2
    assert "я позволяю" in context["overused_text_patterns"]
    assert "я выбираю" in context["overused_text_patterns"]


def test_build_text_memory_context_includes_recent_soft_actions_and_safe_empty_context():
    context = text_memory.build_text_memory_context(
        [
            {"soft_action": "назови три вещи, которые уже помогают", "affirmations": ["Я нахожу опору."]},
            {"soft_action": "сделай один маленький шаг к покою", "affirmations": ["Я выбираю спокойствие."]},
        ],
        limit=10,
    )

    assert context["avoid_soft_actions"] == [
        "назови три вещи, которые уже помогают",
        "сделай один маленький шаг к покою",
    ]
    assert context["recent_soft_action_patterns"] == ["name_three_things", "take_short_step"]

    empty = text_memory.build_text_memory_context(None, limit=10)
    assert empty["recent_focus_titles"] == []
    assert empty["pattern_counts"] == {}


def test_build_text_memory_context_detects_repeated_soft_action_families_across_wording_variants():
    context = text_memory.build_text_memory_context(
        [
            {"soft_action": "Назови три вещи, которые уже помогают", "affirmations": []},
            {"soft_action": "Найди три маленькие опоры рядом с собой", "affirmations": []},
            {"soft_action": "Заметь три спокойных сигнала в теле", "affirmations": []},
        ],
        limit=10,
    )

    assert "name_three_things" in context["recent_soft_action_patterns"]
    assert "name_three_things" in context["overused_soft_action_patterns"]
    assert "name_three_things" in context["avoid_soft_action_patterns"]
    assert len(context["avoid_soft_action_patterns"]) <= 3


def test_build_text_memory_context_tracks_affirmation_openings_and_variation_guidance():
    context = text_memory.build_text_memory_context(
        [
            {
                "affirmations": [
                    "Я выбираю спокойствие и мягкость.",
                    "Я выбираю ясность без спешки.",
                    "Сегодня я дышу свободнее.",
                ]
            },
            {
                "affirmations": [
                    "Я принимаю свой ритм.",
                    "Я выбираю устойчивость без давления.",
                ]
            },
        ],
        limit=10,
    )

    assert "я выбираю" in context["recent_affirmation_openings"]
    assert "сегодня я" in context["recent_affirmation_openings"]
    assert "я выбираю" in context["overused_affirmation_openings"]
    assert "я выбираю" in context["avoid_affirmation_openings"]
    assert "vary affirmation openings" in context["variation_guidance"]
    assert len(context["avoid_affirmation_openings"]) <= 4


def test_build_text_memory_context_tracks_repeated_soft_action_structures_and_abstract_words():
    context = text_memory.build_text_memory_context(
        [
            {
                "soft_action": "Прими одно денежное решение из ясности, а не из страха.",
                "affirmations": ["Я выбираю спокойствие и ясность."],
            },
            {
                "soft_action": "Выбери одно действие из любопытства, а не из обязанности.",
                "affirmations": ["Я принимаю устойчивость и достаточность."],
            },
        ],
        limit=10,
    )

    assert "contrast_from_not_from" in context["recent_soft_action_structures"]
    assert "contrast_from_not_from" in context["overused_soft_action_structures"]
    assert "contrast_from_not_from" in context["avoid_soft_action_structures"]
    assert "ясность" in context["overused_abstract_words"]
    assert "avoid repeating the same soft action structure" in context["variation_guidance"]
    assert "avoid repeating the 'из X, а не из Y' contrast formula" in context["variation_guidance"]


def test_get_text_memory_context_swallows_database_errors(monkeypatch):
    async def _boom(*_args, **_kwargs):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(text_memory, "get_recent_generation_history", _boom)

    context = asyncio.run(text_memory.get_text_memory_context(123, limit=10))

    assert context["recent_focus_titles"] == []
    assert context["overused_text_patterns"] == []
