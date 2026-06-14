from services.orchestrator_shadow import (
    attach_orchestrator_shadow_to_metadata,
    build_orchestrator_shadow_best_effort,
    build_orchestrator_shadow_payload,
    is_orchestrator_shadow_enabled,
)


class _Settings:
    def __init__(self, enabled):
        self.orchestrator_shadow_enabled = enabled


def test_is_orchestrator_shadow_enabled_false_from_settings():
    assert is_orchestrator_shadow_enabled(_Settings(False)) is False


def test_is_orchestrator_shadow_enabled_true_from_settings():
    assert is_orchestrator_shadow_enabled(_Settings(True)) is True


def test_build_orchestrator_shadow_payload_returns_compact_payload():
    payload = build_orchestrator_shadow_payload(
        language="ru",
        sphere="money",
        subsphere=None,
        focus_title="деньги и устойчивость",
        selected_style="living_nature_photo",
        visual_mode="photo",
        text_plan_shadow={"text_plan": {"theme_category": "money_stability"}},
        text_prompt_controlled={"guidance_used": True},
        text_memory_context={
            "overused_text_patterns": ["я позволяю", "спокойствие"],
            "overused_soft_action_patterns": ["name_three_things"],
        },
        text_reviewer_shadow={"score": 0.85, "warnings": ["repeated_openings"]},
        scene_plan_shadow={"scene_plan": {"scene_type": "forest_path"}},
        scene_prompt_controlled={"used_scene_type": "forest_path"},
        profile_guidance_meta={
            "profile_used": True,
            "profile_preferences_count": 4,
            "profile_current_focus_used": True,
            "profile_avoid_constraints_count": 3,
        },
    )

    assert payload["enabled"] is True
    assert payload["mode"] == "shadow"
    assert payload["route"]["text_planner"] is True
    assert payload["route"]["text_memory"] is True
    assert payload["route"]["text_reviewer"] is True
    assert payload["route"]["scene_planner"] is True
    assert payload["route"]["scene_prompt_controlled"] is True
    assert payload["route"]["profile_preferences"] is True
    assert payload["quality"]["text_reviewer_score"] == 0.85
    assert payload["quality"]["text_warnings_count"] == 1
    assert payload["quality"]["text_memory_overused_count"] == 3
    assert payload["quality"]["profile_preferences_count"] == 4
    assert payload["quality"]["profile_avoid_constraints_count"] == 3
    assert payload["inputs"]["profile_used"] is True
    assert payload["inputs"]["profile_current_focus_used"] is True
    assert "text planner guidance used" in payload["decisions"]
    assert "profile preferences guidance used" in payload["decisions"]
    assert "scene controlled prompt used" in payload["decisions"]


def test_build_orchestrator_shadow_best_effort_returns_none_when_disabled():
    payload = build_orchestrator_shadow_best_effort(
        settings=_Settings(False),
        language="ru",
        focus_title="мягкая опора",
    )

    assert payload is None


def test_build_orchestrator_shadow_best_effort_returns_payload_when_enabled():
    payload = build_orchestrator_shadow_best_effort(
        settings=_Settings(True),
        language="ru",
        focus_title="мягкая опора",
        text_prompt_controlled={"guidance_used": True},
        text_reviewer_shadow={"score": 1.0, "warnings": []},
    )

    assert payload is not None
    assert payload["enabled"] is True
    assert payload["route"]["text_planner"] is True


def test_build_orchestrator_shadow_best_effort_swallows_exceptions(monkeypatch):
    def _boom(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "services.orchestrator_shadow.build_orchestrator_shadow_payload",
        _boom,
    )

    payload = build_orchestrator_shadow_best_effort(
        settings=_Settings(True),
        language="ru",
        focus_title="мягкая опора",
    )

    assert payload is None


def test_build_orchestrator_shadow_payload_does_not_include_full_prompt_or_caption_fields():
    payload = build_orchestrator_shadow_payload(
        language="ru",
        focus_title="мягкая опора",
    )

    payload_str = str(payload)
    assert "final_caption" not in payload
    assert "prompt_final" not in payload
    assert "image_prompt" not in payload
    assert "caption" not in payload_str.lower()


def test_attach_orchestrator_shadow_to_metadata_adds_payload():
    payload = {"enabled": True, "mode": "shadow"}
    result = attach_orchestrator_shadow_to_metadata({"existing": 1}, payload)

    assert result["existing"] == 1
    assert result["orchestrator_shadow"] == payload


def test_attach_orchestrator_shadow_to_metadata_noop_for_none():
    result = attach_orchestrator_shadow_to_metadata({"existing": 1}, None)

    assert result == {"existing": 1}
