import asyncio

from services import text_planner_shadow


class _Settings:
    def __init__(self, enabled: bool):
        self.text_planner_shadow_enabled = enabled


def test_shadow_disabled_returns_none():
    result = asyncio.run(
        text_planner_shadow.build_text_plan_shadow_best_effort(
            sphere="home_support",
            focus_title="дом и опора",
            settings=_Settings(False),
        )
    )
    assert result is None


def test_shadow_best_effort_returns_payload_when_enabled():
    result = asyncio.run(
        text_planner_shadow.build_text_plan_shadow_best_effort(
            sphere="home_support",
            focus_title="дом и опора",
            language="ru",
            settings=_Settings(True),
        )
    )
    assert result["enabled"] is True
    assert result["mode"] == "local_fallback"
    assert result["llm_used"] is False
    assert "text_plan" in result
    assert "text_plan_summary" in result
    assert result["text_plan"]["theme_category"] == "home_support"


def test_shadow_best_effort_swallows_exceptions(monkeypatch):
    def _boom(**_kwargs):
        raise RuntimeError("planner failed")

    monkeypatch.setattr(text_planner_shadow, "build_fallback_text_plan", _boom)

    result = asyncio.run(
        text_planner_shadow.build_text_plan_shadow_best_effort(
            sphere="money",
            focus_title="деньги и устойчивость",
            settings=_Settings(True),
        )
    )
    assert result is None


def test_attach_text_plan_shadow_to_metadata_adds_payload():
    payload = {"enabled": True, "text_plan": {"theme_category": "home_support"}}
    result = text_planner_shadow.attach_text_plan_shadow_to_metadata(
        {"selected_style": "soft_editorial"},
        payload,
    )
    assert result["selected_style"] == "soft_editorial"
    assert result["text_plan_shadow"] == payload


def test_attach_text_plan_shadow_to_metadata_with_none_keeps_existing():
    original = {"selected_style": "soft_editorial"}
    result = text_planner_shadow.attach_text_plan_shadow_to_metadata(original, None)
    assert result == original


def test_payload_does_not_include_full_planner_prompt():
    payload = text_planner_shadow.build_text_plan_shadow_payload(
        text_plan={"theme_category": "home_support", "focus_title": "дом и опора"},
        text_plan_summary="summary",
    )
    assert "planner_prompt" not in payload
    assert payload["text_plan_summary"] == "summary"
    assert "text_plan" in payload
