from services.yandex_gpt import _build_prompt


def test_affirmation_prompt_contains_anti_cliche_instructions():
    prompt = _build_prompt(
        sphere="career",
        subsphere=None,
        language="ru",
        user_text=None,
        gender_hint="для женщины",
        gender="female",
    )
    assert "ровно 4" in prompt
    assert "JSON-массив" in prompt
    assert "Не начинай все пункты одинаково" in prompt
    assert "Я открыта" in prompt
    assert "Я спокойна и уверена" in prompt
    assert "Я благодарна" in prompt
    assert "Я готова" in prompt
    assert "фокусом дня" in prompt
    assert "мотивационный плакат" in prompt


def test_affirmation_prompt_contains_focus_context_and_json_contract():
    prompt = _build_prompt(
        sphere="money",
        subsphere=None,
        language="en",
        user_text=None,
        focus="calm financial ground",
        micro_theme="Look at one financial question calmly.",
    )
    assert "Focus of the day: calm financial ground" in prompt
    assert "JSON array of strings only" in prompt
    assert "exactly 4" in prompt


def test_money_affirmation_prompt_discourages_cliches_and_magic_abundance():
    prompt = _build_prompt(
        sphere="money",
        subsphere=None,
        language="ru",
        user_text=None,
        focus="порядок без тревоги",
        micro_theme="Посмотри на один денежный вопрос спокойно.",
        gender="female",
    )
    assert "правильные финансовые решения" in prompt
    assert "финансовая независимость" in prompt
    assert "деньги легко приходят" in prompt
    assert "я притягиваю деньги" in prompt
    assert "изобилие приходит ко мне" in prompt
    assert "гарантий богатства" in prompt
    assert "порядок без тревоги" in prompt
