from services import text_planner


def test_parse_text_plan_response_parses_clean_json():
    parsed = text_planner.parse_text_plan_response('{"theme_category":"inner_peace","focus_title":"покой"}')
    assert parsed == {"theme_category": "inner_peace", "focus_title": "покой"}


def test_parse_text_plan_response_extracts_json_from_markdown_fence():
    parsed = text_planner.parse_text_plan_response('```json\n{"theme_category":"money_stability"}\n```')
    assert parsed == {"theme_category": "money_stability"}


def test_parse_text_plan_response_returns_none_for_invalid_json():
    assert text_planner.parse_text_plan_response(None) is None
    assert text_planner.parse_text_plan_response("not json") is None


def test_normalize_text_plan_fills_missing_keys():
    plan = text_planner.normalize_text_plan({"theme_category": "inner_peace"})
    assert set(plan.keys()) == {
        "theme_category",
        "focus_title",
        "tone",
        "emotional_direction",
        "affirmation_intent",
        "affirmation_angles",
        "soft_action_intent",
        "soft_action_style",
        "avoid",
        "language",
    }


def test_normalize_text_plan_normalizes_invalid_tone_to_soft_grounded():
    plan = text_planner.normalize_text_plan({"theme_category": "custom", "tone": "aggressive"})
    assert plan["tone"] == "soft_grounded"


def test_normalize_text_plan_keeps_lists_and_removes_empty_values():
    plan = text_planner.normalize_text_plan(
        {
            "theme_category": "custom",
            "affirmation_angles": ["body care", "", "body care", None, "permission to pause"],
            "avoid": ["pressure", "", "pressure"],
        }
    )
    assert plan["affirmation_angles"] == ["body care", "permission to pause"]
    assert "pressure" in plan["avoid"]


def test_build_fallback_text_plan_supports_inner_peace():
    plan = text_planner.build_fallback_text_plan(sphere="inner_peace", language="ru")
    assert plan["theme_category"] == "inner_peace"
    assert plan["tone"] == "soft_grounded"


def test_build_fallback_text_plan_supports_money_stability():
    plan = text_planner.build_fallback_text_plan(sphere="money", language="ru")
    assert plan["theme_category"] == "money_stability"


def test_build_fallback_text_plan_supports_work_career():
    plan = text_planner.build_fallback_text_plan(sphere="career", language="ru")
    assert plan["theme_category"] == "work_career"


def test_build_fallback_text_plan_supports_home_support():
    plan = text_planner.build_fallback_text_plan(sphere="home_support", language="ru")
    assert plan["theme_category"] == "home_support"
    assert plan["focus_title"] == "дом и опора"


def test_build_fallback_text_plan_supports_custom_topic():
    plan = text_planner.build_fallback_text_plan(user_custom_topic="мягкое возвращение к себе", language="ru")
    assert plan["theme_category"] == "custom"
    assert plan["focus_title"] == "мягкое возвращение к себе"


def test_infer_theme_category_detects_money_career_home_relationships_creativity():
    assert text_planner.infer_theme_category(user_custom_topic="финансы и устойчивость") == "money_stability"
    assert text_planner.infer_theme_category(user_custom_topic="money and stability") == "money_stability"
    assert text_planner.infer_theme_category(user_custom_topic="career growth") == "work_career"
    assert text_planner.infer_theme_category(user_custom_topic="дом и уют") == "home_support"
    assert text_planner.infer_theme_category(user_custom_topic="home comfort and safety") == "home_support"
    assert text_planner.infer_theme_category(user_custom_topic="отношения и границы") == "relationships_boundaries"
    assert text_planner.infer_theme_category(user_custom_topic="relationships and boundaries") == "relationships_boundaries"
    assert text_planner.infer_theme_category(user_custom_topic="творчество и проявленность") == "creativity_self_expression"
    assert text_planner.infer_theme_category(user_custom_topic="creative self-expression") == "creativity_self_expression"


def test_build_text_planner_prompt_includes_sphere_focus_language_and_json_only_instruction():
    prompt = text_planner.build_text_planner_prompt(
        sphere="home_support",
        focus_title="дом и опора",
        language="ru",
        recent_text_context={"recent_focus_titles": ["внутренний покой"]},
    )
    assert "sphere: home_support" in prompt
    assert "focus_title: дом и опора" in prompt
    assert "language: ru" in prompt
    assert "Return JSON only." in prompt


def test_build_text_plan_summary_returns_compact_string():
    summary = text_planner.build_text_plan_summary(
        {
            "theme_category": "home_support",
            "focus_title": "дом и опора",
            "affirmation_angles": ["comfort", "safety"],
            "avoid": ["pressure"],
        }
    )
    assert "theme_category: home_support" in summary
    assert "focus_title: дом и опора" in summary
