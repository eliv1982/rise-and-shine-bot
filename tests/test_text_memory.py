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

    empty = text_memory.build_text_memory_context(None, limit=10)
    assert empty["recent_focus_titles"] == []
    assert empty["pattern_counts"] == {}


def test_get_text_memory_context_swallows_database_errors(monkeypatch):
    async def _boom(*_args, **_kwargs):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(text_memory, "get_recent_generation_history", _boom)

    context = asyncio.run(text_memory.get_text_memory_context(123, limit=10))

    assert context["recent_focus_titles"] == []
    assert context["overused_text_patterns"] == []
