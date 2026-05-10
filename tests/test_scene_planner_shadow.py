import asyncio

from services import scene_planner_shadow


class _Settings:
    def __init__(self, enabled: bool):
        self.scene_planner_shadow_enabled = enabled


def test_shadow_disabled_returns_none(monkeypatch):
    called = {"visual_memory": False}

    async def _fake_get_visual_memory_context(*_args, **_kwargs):
        called["visual_memory"] = True
        return {}

    monkeypatch.setattr(scene_planner_shadow, "get_visual_memory_context", _fake_get_visual_memory_context)

    result = asyncio.run(
        scene_planner_shadow.build_scene_plan_shadow_best_effort(
            telegram_user_id=1,
            focus_title="Focus",
            affirmations=["A"],
            soft_action="Step",
            settings=_Settings(False),
        )
    )

    assert result is None
    assert called["visual_memory"] is False


def test_shadow_best_effort_returns_payload_when_enabled(monkeypatch):
    async def _fake_get_visual_memory_context(*_args, **_kwargs):
        return {
            "recent_scene_types": ["window_still_life"],
            "hard_avoid_today": ["mug", "window"],
            "prefer_scene_types": ["riverside"],
            "overused_motifs": ["mug"],
        }

    monkeypatch.setattr(scene_planner_shadow, "get_visual_memory_context", _fake_get_visual_memory_context)

    result = asyncio.run(
        scene_planner_shadow.build_scene_plan_shadow_best_effort(
            telegram_user_id=1,
            focus_title="Calm trust",
            affirmations=["I move gently"],
            soft_action="Take one calm step",
            settings=_Settings(True),
        )
    )

    assert result["enabled"] is True
    assert result["mode"] == "local_fallback"
    assert result["llm_used"] is False
    assert "scene_plan" in result
    assert "visual_memory_summary" in result
    assert result["scene_plan"]["scene_type"] == "riverside"


def test_shadow_best_effort_swallows_visual_memory_errors(monkeypatch):
    async def _boom(*_args, **_kwargs):
        raise RuntimeError("visual memory down")

    monkeypatch.setattr(scene_planner_shadow, "get_visual_memory_context", _boom)

    result = asyncio.run(
        scene_planner_shadow.build_scene_plan_shadow_best_effort(
            telegram_user_id=1,
            focus_title="Calm trust",
            affirmations=["I move gently"],
            soft_action="Take one calm step",
            settings=_Settings(True),
        )
    )

    assert result is None


def test_attach_scene_plan_shadow_to_visual_motifs_adds_payload():
    payload = {"enabled": True, "scene_plan": {"scene_type": "forest_path"}}

    result = scene_planner_shadow.attach_scene_plan_shadow_to_visual_motifs(
        {"selected_style": "soft_editorial"},
        payload,
    )

    assert result["selected_style"] == "soft_editorial"
    assert result["scene_plan_shadow"] == payload


def test_attach_scene_plan_shadow_to_visual_motifs_without_payload_keeps_existing():
    original = {"selected_style": "soft_editorial"}

    result = scene_planner_shadow.attach_scene_plan_shadow_to_visual_motifs(original, None)

    assert result == original


def test_payload_does_not_include_full_planner_prompt():
    payload = scene_planner_shadow.build_scene_plan_shadow_payload(
        scene_plan={"scene_type": "forest_path"},
        visual_memory_context={"hard_avoid_today": ["mug"]},
        scene_image_brief="brief",
    )

    assert "planner_prompt" not in payload
    assert payload["scene_image_brief"] == "brief"
    assert "scene_plan" in payload
