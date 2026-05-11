from services.text_reviewer_shadow import (
    attach_text_reviewer_shadow_to_metadata,
    build_text_reviewer_shadow_best_effort,
)


class _Settings:
    def __init__(self, enabled):
        self.text_reviewer_shadow_enabled = enabled


def test_text_reviewer_shadow_disabled_returns_none():
    payload = build_text_reviewer_shadow_best_effort(
        affirmations=["Я выбираю спокойствие"],
        soft_action="Сделай один спокойный шаг",
        focus_title="спокойствие",
        language="ru",
        settings=_Settings(False),
    )

    assert payload is None


def test_text_reviewer_shadow_enabled_returns_compact_payload():
    payload = build_text_reviewer_shadow_best_effort(
        affirmations=["Я открыт новому", "Я выбираю спокойствие"],
        soft_action="Назови три вещи, которые уже помогают",
        focus_title="спокойствие и опора",
        language="ru",
        gender_hint="для женщины",
        text_memory_context={"avoid_soft_actions": ["назови три вещи, которые уже помогают"]},
        settings=_Settings(True),
    )

    assert payload["enabled"] is True
    assert payload["language"] == "ru"
    assert "checks" in payload
    assert "warnings" in payload
    assert "score" in payload


def test_attach_text_reviewer_shadow_to_metadata_adds_payload():
    payload = {"enabled": True, "score": 0.8}
    result = attach_text_reviewer_shadow_to_metadata({"existing": 1}, payload)

    assert result["existing"] == 1
    assert result["text_reviewer_shadow"] == payload


def test_attach_text_reviewer_shadow_to_metadata_noop_for_none():
    result = attach_text_reviewer_shadow_to_metadata({"existing": 1}, None)

    assert result == {"existing": 1}
