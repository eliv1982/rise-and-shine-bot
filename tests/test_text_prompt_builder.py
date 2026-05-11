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
    assert "keep all user-facing text strictly in Russian" in guidance
    assert "Do not leave English words or English action phrases" in guidance


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


def test_build_text_generation_guidance_includes_feminine_gender_instruction_for_ru():
    guidance = build_text_generation_guidance(
        text_plan={
            "theme_category": "self_worth",
            "focus_title": "достоинство",
            "tone": "soft_grounded",
            "emotional_direction": "quiet confidence",
            "affirmation_intent": "support self-trust",
            "affirmation_angles": ["dignity"],
            "soft_action_intent": "one calm step",
            "soft_action_style": "small_concrete_step",
            "avoid": ["pressure"],
            "language": "ru",
        },
        language="ru",
        gender_hint="для женщины",
    )

    assert "Russian grammatical gender: feminine" in guidance
    assert "готова, выбрала, уверена, открыта" in guidance
    assert "готов, выбрал, уверен, открыт" in guidance


def test_build_text_generation_guidance_includes_masculine_gender_instruction_for_ru():
    guidance = build_text_generation_guidance(
        text_plan={
            "theme_category": "work_career",
            "focus_title": "дело и карьера",
            "tone": "calm_clear",
            "emotional_direction": "steady progress",
            "affirmation_intent": "support focus",
            "affirmation_angles": ["clarity"],
            "soft_action_intent": "one work step",
            "soft_action_style": "small_concrete_step",
            "avoid": ["pressure"],
            "language": "ru",
        },
        language="ru",
        gender_hint="для мужчины",
    )

    assert "Russian grammatical gender: masculine" in guidance
    assert "готов, выбрал, уверен, открыт" in guidance
    assert "готова, выбрала, уверена, открыта" in guidance


def test_build_text_generation_guidance_prefers_gender_neutral_wording_for_unknown_hint():
    guidance = build_text_generation_guidance(
        text_plan={
            "theme_category": "inner_peace",
            "focus_title": "мягкая опора",
            "tone": "soft_grounded",
            "emotional_direction": "calm support",
            "affirmation_intent": "support steadiness",
            "affirmation_angles": ["calm"],
            "soft_action_intent": "one quiet pause",
            "soft_action_style": "small_concrete_step",
            "avoid": ["pressure"],
            "language": "ru",
        },
        language="ru",
        gender_hint="для пользователя",
    )

    assert "Prefer gender-neutral Russian wording where possible." in guidance


def test_build_text_generation_guidance_detects_real_runtime_gender_hint_values():
    female_guidance = build_text_generation_guidance(
        text_plan={
            "theme_category": "self_worth",
            "focus_title": "достоинство",
            "tone": "soft_grounded",
            "emotional_direction": "quiet confidence",
            "affirmation_intent": "support self-trust",
            "affirmation_angles": ["dignity"],
            "soft_action_intent": "one calm step",
            "soft_action_style": "small_concrete_step",
            "avoid": ["pressure"],
            "language": "ru",
        },
        language="ru",
        gender_hint="она",
    )
    male_guidance = build_text_generation_guidance(
        text_plan={
            "theme_category": "work_career",
            "focus_title": "дело и карьера",
            "tone": "calm_clear",
            "emotional_direction": "steady progress",
            "affirmation_intent": "support focus",
            "affirmation_angles": ["clarity"],
            "soft_action_intent": "one work step",
            "soft_action_style": "small_concrete_step",
            "avoid": ["pressure"],
            "language": "ru",
        },
        language="ru",
        gender_hint="для мужчины",
    )

    assert "Russian grammatical gender: feminine" in female_guidance
    assert "Russian grammatical gender: masculine" in male_guidance


def test_build_text_generation_guidance_includes_anti_repeat_block_when_text_memory_context_present():
    guidance = build_text_generation_guidance(
        text_plan={
            "theme_category": "inner_peace",
            "focus_title": "право на отдых",
            "tone": "soft_grounded",
            "emotional_direction": "permission to rest without guilt",
            "affirmation_intent": "support recovery",
            "affirmation_angles": ["rest", "self-worth"],
            "soft_action_intent": "one guilt-free pause",
            "soft_action_style": "small_concrete_step",
            "avoid": ["toxic positivity", "pressure", "moralizing"],
            "language": "ru",
        },
        language="ru",
        text_memory_context={
            "recent_focus_titles": ["право на отдых", "спокойствие и опора"],
            "recent_affirmation_openings": ["я позволяю", "сегодня я"],
            "overused_text_patterns": ["я позволяю", "спокойствие"],
            "overused_affirmation_openings": ["я позволяю"],
            "avoid_affirmation_openings": ["я позволяю", "сегодня я"],
            "avoid_soft_actions": ["назови три вещи, которые уже помогают"],
            "avoid_soft_action_patterns": ["name_three_things"],
            "avoid_soft_action_structures": ["contrast_from_not_from"],
            "overused_soft_action_structures": ["contrast_from_not_from"],
            "overused_abstract_words": ["ясность", "спокойствие"],
            "avoid_phrases": ["Я позволяю себе отдых без чувства вины."],
            "style_guidance": ["avoid repeating recent affirmation openings", "vary sentence rhythm"],
            "variation_guidance": [
                "vary affirmation openings",
                "avoid repeating the same first-person verb structure",
                "avoid repeating the same soft action structure",
            ],
        },
    )

    assert "Text memory / anti-repeat guidance:" in guidance
    assert "recent_affirmation_openings: я позволяю, сегодня я" in guidance
    assert "overused_text_patterns: я позволяю, спокойствие" in guidance
    assert "overused_affirmation_openings: я позволяю" in guidance
    assert "avoid_affirmation_openings: я позволяю, сегодня я" in guidance
    assert "avoid_soft_actions: назови три вещи, которые уже помогают" in guidance
    assert "avoid_soft_action_patterns: name_three_things" in guidance
    assert "avoid_soft_action_structures: contrast_from_not_from" in guidance
    assert "overused_soft_action_structures: contrast_from_not_from" in guidance
    assert "overused_abstract_words: ясность, спокойствие" in guidance
    assert "variation_guidance: vary affirmation openings; avoid repeating the same first-person verb structure; avoid repeating the same soft action structure" in guidance
    assert "Do not reuse recent soft action structure." in guidance
    assert "Do not make every affirmation start with the same 'I + verb' pattern." in guidance
    assert "Avoid overusing the 'из X, а не из Y' contrast formula." in guidance
    assert "Prefer a concrete, grounded, small real-life action" in guidance
    assert "If recent actions asked the user to name three things, choose a different action type." in guidance
    assert "Vary the soft action verb and structure." in guidance
    assert "Output language: Russian" in guidance
    assert '{"recent_focus_titles"' not in guidance
