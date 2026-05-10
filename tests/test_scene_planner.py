from services import scene_planner


def test_parse_scene_plan_response_plain_json():
    raw = '{"scene_type":"forest_path","setting":"quiet forest","human_presence":"none"}'

    parsed = scene_planner.parse_scene_plan_response(raw)

    assert parsed["scene_type"] == "forest_path"
    assert parsed["human_presence"] == "none"


def test_parse_scene_plan_response_code_fence():
    raw = '```json\n{"scene_type":"riverside","setting":"quiet river"}\n```'

    parsed = scene_planner.parse_scene_plan_response(raw)

    assert parsed == {"scene_type": "riverside", "setting": "quiet river"}


def test_parse_scene_plan_response_embedded_json():
    raw = 'Here is the plan: {"scene_type":"garden_morning","setting":"garden"} thanks'

    parsed = scene_planner.parse_scene_plan_response(raw)

    assert parsed == {"scene_type": "garden_morning", "setting": "garden"}


def test_parse_scene_plan_response_invalid():
    assert scene_planner.parse_scene_plan_response(None) is None
    assert scene_planner.parse_scene_plan_response("not json at all") is None
    assert scene_planner.parse_scene_plan_response('["not","a","dict"]') is None


def test_normalize_scene_plan_adds_missing_keys():
    plan = scene_planner.normalize_scene_plan({"scene_type": "forest_path"})

    assert set(plan.keys()) == {
        "scene_type",
        "setting",
        "human_presence",
        "main_subject",
        "visual_motifs",
        "composition",
        "lighting",
        "mood",
        "avoid",
    }


def test_normalize_scene_plan_invalid_human_presence_defaults_to_none():
    plan = scene_planner.normalize_scene_plan({"scene_type": "forest_path", "human_presence": "group"})

    assert plan["human_presence"] == "none"


def test_normalize_scene_plan_merges_avoid_from_memory():
    plan = scene_planner.normalize_scene_plan(
        {"scene_type": "forest_path", "avoid": ["fog"]},
        visual_memory_context={"hard_avoid_today": ["mug", "beach"]},
    )

    assert "fog" in plan["avoid"]
    assert "mug" in plan["avoid"]
    assert "beach" in plan["avoid"]
    assert "generic wellness stock photo" in plan["avoid"]


def test_build_fallback_scene_plan_uses_preferred_scene_type():
    plan = scene_planner.build_fallback_scene_plan(
        focus_title="Inner trust",
        visual_memory_context={"prefer_scene_types": ["riverside"], "hard_avoid_today": ["mug"]},
    )

    assert plan["scene_type"] == "riverside"
    assert "Inner trust" in plan["mood"]
    assert "mug" in plan["avoid"]


def test_build_fallback_scene_plan_uses_default_when_no_preference():
    plan = scene_planner.build_fallback_scene_plan(
        focus_title=None,
        visual_memory_context={"prefer_scene_types": []},
    )

    assert plan["scene_type"] in {"forest_path", "open_meadow", "garden_morning"}


def test_build_scene_image_prompt_includes_avoid_constraints():
    prompt = scene_planner.build_scene_image_prompt(
        {
            "scene_type": "forest_path",
            "avoid": ["mug", "window"],
        }
    )

    assert "Avoid: " in prompt
    assert "mug" in prompt
    assert "window" in prompt
    assert "No crowd. No extra people." in prompt


def test_build_scene_planner_prompt_includes_focus_and_memory():
    prompt = scene_planner.build_scene_planner_prompt(
        focus_title="Quiet self-trust",
        affirmations=["I move gently", "I trust my pace"],
        soft_action="Take one small calm step",
        visual_memory_context={
            "hard_avoid_today": ["mug", "beach"],
            "recent_scene_types": ["window_still_life"],
            "recent_motifs": ["mug", "window"],
            "overused_motifs": ["mug"],
            "prefer_scene_types": ["forest_path", "riverside"],
        },
        language="ru",
    )

    assert "Quiet self-trust" in prompt
    assert "hard_avoid_today" in prompt
    assert "window_still_life" in prompt
    assert "mug, beach" in prompt
