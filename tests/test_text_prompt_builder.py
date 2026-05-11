from services.text_prompt_builder import (
    build_text_generation_guidance,
    is_text_planner_controlled_enabled,
)


class _Settings:
    def __init__(self, enabled):
        self.text_planner_controlled_enabled = enabled


def test_is_text_planner_controlled_enabled_false_by_default_from_settings():
    assert is_text_planner_controlled_enabled(_Settings(False)) is False


def test_is_text_planner_controlled_enabled_true_from_settings():
    assert is_text_planner_controlled_enabled(_Settings(True)) is True


def test_build_text_generation_guidance_returns_none_for_missing_plan():
    assert build_text_generation_guidance(text_plan=None, language="ru") is None
    assert build_text_generation_guidance(text_plan={}, language="ru") is None


def test_build_text_generation_guidance_includes_tone_theme_avoid_and_affirmation_intent():
    guidance = build_text_generation_guidance(
        text_plan={
            "theme_category": "money_stability",
            "focus_title": "деньги и устойчивость",
            "tone": "gentle_practical",
            "emotional_direction": "financial steadiness without fear or shame",
            "affirmation_intent": "reduce anxiety around money and support grounded clarity",
            "affirmation_angles": ["enoughness", "financial clarity"],
            "soft_action_intent": "one small calm step",
            "soft_action_style": "small_concrete_step",
            "avoid": ["toxic positivity", "pressure", "productivity framing"],
            "language": "ru",
        },
        language="ru",
    )

    assert "theme_category: money_stability" in guidance
    assert "tone: gentle_practical" in guidance
    assert "affirmation_intent: reduce anxiety around money and support grounded clarity" in guidance
    assert "avoid: toxic positivity, pressure, productivity framing" in guidance


def test_build_text_generation_guidance_mentions_russian_output_for_ru():
    guidance = build_text_generation_guidance(
        text_plan={
            "theme_category": "home_support",
            "focus_title": "дом и опора",
            "tone": "soft_grounded",
            "emotional_direction": "return to safety",
            "affirmation_intent": "support recovery",
            "affirmation_angles": ["comfort"],
            "soft_action_intent": "one small home step",
            "soft_action_style": "small_concrete_step",
            "avoid": ["toxic positivity"],
            "language": "ru",
        },
        language="ru",
    )

    assert "Output language: Russian" in guidance


def test_build_text_generation_guidance_does_not_dump_full_raw_json():
    guidance = build_text_generation_guidance(
        text_plan={
            "theme_category": "work_career",
            "focus_title": "дело и карьера",
            "tone": "calm_clear",
            "emotional_direction": "calm professional dignity",
            "affirmation_intent": "support steady focus",
            "affirmation_angles": ["clarity", "dignity"],
            "soft_action_intent": "one clear work step",
            "soft_action_style": "small_concrete_step",
            "avoid": ["pressure", "moralizing"],
            "language": "ru",
        },
        language="ru",
    )

    assert '"theme_category"' not in guidance
    assert "{" not in guidance
    assert "}" not in guidance
