import asyncio

import services.yandex_gpt as yandex_gpt
from services.yandex_gpt import (
    _build_prompt,
    generate_affirmations,
    normalize_russian_first_person_gender,
    normalize_russian_user_facing_text_fields,
)


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


def test_prompt_preserves_theme_across_input_language():
    prompt = _build_prompt(
        sphere="inner_peace",
        subsphere=None,
        language="en",
        user_text="Достоинство и вера в себя",
        focus="dignity and self-trust",
        micro_theme="one honest confident step",
    )
    assert "Language: English." in prompt
    assert "Interpret user-provided theme in its original language" in prompt
    assert "Preserve semantic closeness to user theme" in prompt


def test_custom_theme_kept_as_primary_anchor():
    prompt = _build_prompt(
        sphere="inner_peace",
        subsphere=None,
        language="ru",
        user_text="Достоинство и вера в себя",
        focus="достоинство и вера в себя",
        micro_theme="мягкий шаг",
    )
    assert "Достоинство и вера в себя" in prompt
    assert "не подменяй её нерелевантными встроенными категориями" in prompt
    assert "Тема задаёт смысл карточки" in prompt or "Theme controls the meaning of the card" in prompt


def test_theme_style_separation_rule_present_for_dignity_theme():
    prompt = _build_prompt(
        sphere="self_worth",
        subsphere=None,
        language="en",
        user_text="Dignity and self-trust",
        focus="Dignity and self-trust",
        micro_theme="One grounded confident step",
    )
    assert "The user theme is the main meaning of the card" in prompt
    assert "Do not replace or reinterpret the theme because of the style" in prompt


def test_affirmation_prompt_keeps_old_path_without_text_plan_guidance():
    prompt = _build_prompt(
        sphere="inner_peace",
        subsphere=None,
        language="ru",
        user_text="мягкая ясность",
        focus="мягкая ясность",
        micro_theme="один спокойный шаг",
        text_plan_guidance=None,
    )

    assert "Text planner guidance:" not in prompt
    assert "тёплое неформальное обращение на «ты»" in prompt
    assert "Запрещены формальные или множественные формы" in prompt
    assert "«Выберите»" in prompt
    assert "«Выбери»" in prompt


def test_affirmation_prompt_includes_text_plan_guidance_when_provided():
    prompt = _build_prompt(
        sphere="money",
        subsphere=None,
        language="ru",
        user_text="спокойная устойчивость",
        focus="спокойная устойчивость",
        micro_theme="один небольшой шаг",
        text_plan_guidance=(
            "Text planner guidance:\n"
            "- theme_category: money_stability\n"
            "- tone: gentle_practical\n"
            "- avoid: toxic positivity, pressure, productivity framing\n"
        ),
    )

    assert "Text planner guidance:" in prompt
    assert "theme_category: money_stability" in prompt
    assert "tone: gentle_practical" in prompt
    assert "avoid: toxic positivity, pressure, productivity framing" in prompt
    assert "тёплое неформальное обращение на «ты»" in prompt
    assert "«Вы/вы»" in prompt


def test_affirmation_prompt_with_text_plan_guidance_keeps_feminine_gender_instruction():
    prompt = _build_prompt(
        sphere="inner_peace",
        subsphere=None,
        language="ru",
        user_text="мягкая опора",
        focus="мягкая опора",
        micro_theme="один спокойный шаг",
        gender_hint="для женщины",
        gender="female",
        text_plan_guidance=(
            "Text planner guidance:\n"
            "- tone: soft_grounded\n"
            "Respect the user's Russian grammatical gender: feminine.\n"
            "Use feminine forms when needed: готова, выбрала, уверена, открыта.\n"
        ),
    )

    assert "Пол пользователя (из регистрации): женский" in prompt
    assert "женском роде" in prompt
    assert "Я готова" in prompt
    assert "Я уверена в себе" in prompt
    assert "Russian grammatical gender: feminine" in prompt
    assert "Я готов" in prompt
    assert "Я выбрал" in prompt
    assert "Я уверен" in prompt
    assert "Я открыт" in prompt


def test_affirmation_prompt_with_text_plan_guidance_keeps_masculine_gender_instruction():
    prompt = _build_prompt(
        sphere="work_career",
        subsphere=None,
        language="ru",
        user_text="спокойный рост",
        focus="спокойный рост",
        micro_theme="один рабочий шаг",
        gender_hint="для мужчины",
        gender="male",
        text_plan_guidance=(
            "Text planner guidance:\n"
            "- tone: calm_clear\n"
            "Respect the user's Russian grammatical gender: masculine.\n"
            "Use masculine forms when needed: готов, выбрал, уверен, открыт.\n"
        ),
    )

    assert "Пол пользователя (из регистрации): мужской" in prompt
    assert "мужском роде" in prompt
    assert "Я готов" in prompt
    assert "Я уверен в себе" in prompt
    assert "Russian grammatical gender: masculine" in prompt


def test_normalize_russian_first_person_gender_female_fixes_safe_first_person_forms():
    assert (
        normalize_russian_first_person_gender("Я открыт новым возможностям", gender_hint="для женщины")
        == "Я открыта новым возможностям"
    )
    assert (
        normalize_russian_first_person_gender("Я готов развиваться", gender_hint="она")
        == "Я готова развиваться"
    )
    assert (
        normalize_russian_first_person_gender("Я уверен в себе", gender_hint="женский")
        == "Я уверена в себе"
    )


def test_normalize_russian_first_person_gender_does_not_change_non_first_person_text():
    assert (
        normalize_russian_first_person_gender("Путь открыт новым возможностям", gender_hint="для женщины")
        == "Путь открыт новым возможностям"
    )


def test_normalize_russian_first_person_gender_male_reverse_and_unknown_noop():
    assert (
        normalize_russian_first_person_gender("Я открыта новому", gender_hint="для мужчины")
        == "Я открыт новому"
    )
    assert (
        normalize_russian_first_person_gender("Я готова двигаться дальше", gender_hint="он")
        == "Я готов двигаться дальше"
    )
    assert (
        normalize_russian_first_person_gender("Я открыта новому", gender_hint="для пользователя")
        == "Я открыта новому"
    )


def test_generate_affirmations_applies_gender_cleanup_for_russian_female(monkeypatch):
    class _FakeResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": '[\"Я открыт новым возможностям\", \"Я готов развиваться\", \"Путь открыт\", \"Я уверен в себе\"]'
                        }
                    }
                ]
            }

        async def text(self):
            return ""

    class _FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return _FakeResponse()

    monkeypatch.setattr(
        yandex_gpt,
        "get_text_provider_config",
        lambda: yandex_gpt.TextProviderConfig(
            provider="openai",
            base_url="https://api.openai.com/v1",
            api_key="test",
            model="gpt-4o-mini",
            timeout_seconds=5,
            options={},
        ),
    )
    monkeypatch.setattr(yandex_gpt.aiohttp, "ClientSession", _FakeSession)

    result = asyncio.run(
        generate_affirmations(
            sphere="inner_peace",
            language="ru",
            user_text="мягкая опора",
            gender_hint="для женщины",
            gender="female",
        )
    )

    assert result[0] == "Я открыта новым возможностям"
    assert result[1] == "Я готова развиваться"
    assert result[2] == "Путь открыт"
    assert result[3] == "Я уверена в себе"


def test_normalize_russian_user_facing_text_fields_fixes_soft_action_and_micro_step_for_female():
    payload = {
        "affirmations": ["Я открыт новым возможностям", "Путь открыт"],
        "soft_action": "Я готов сделать один спокойный шаг",
        "micro_step": "Я уверен в своём следующем шаге",
    }

    normalized = normalize_russian_user_facing_text_fields(payload, gender_hint="для женщины")

    assert normalized["affirmations"][0] == "Я открыта новым возможностям"
    assert normalized["affirmations"][1] == "Путь открыт"
    assert normalized["soft_action"] == "Я готова сделать один спокойный шаг"
    assert normalized["micro_step"] == "Я уверена в своём следующем шаге"


def test_normalize_russian_user_facing_text_fields_keeps_non_first_person_and_unknown_gender():
    payload = {
        "soft_action": "Путь открыт новым возможностям",
        "micro_step": "Я открыта новым возможностям",
    }

    female_normalized = normalize_russian_user_facing_text_fields(payload, gender_hint="для женщины")
    unknown_normalized = normalize_russian_user_facing_text_fields(
        {"soft_action": "Я готов сделать один спокойный шаг"},
        gender_hint="для пользователя",
    )

    assert female_normalized["soft_action"] == "Путь открыт новым возможностям"
    assert female_normalized["micro_step"] == "Я открыта новым возможностям"
    assert unknown_normalized["soft_action"] == "Я готов сделать один спокойный шаг"


def test_normalize_russian_user_facing_text_fields_converts_formal_soft_action_phrases():
    payload = {
        "soft_action": "Упростите один бытовой шаг, чтобы день ощущался мягче.",
        "micro_step": "Выберите одно действие, которое даст телу ощущение опоры.",
    }

    normalized = normalize_russian_user_facing_text_fields(payload, gender_hint="для женщины")

    assert normalized["soft_action"] == "Упрости один бытовой шаг, чтобы день ощущался мягче."
    assert normalized["micro_step"] == "Выбери одно действие, которое даст телу ощущение опоры."


def test_normalize_russian_user_facing_text_fields_converts_name_three_and_keeps_correct_imperatives():
    payload = {
        "soft_action": "Назовите три вещи, на которые можно опереться сейчас.",
        "micro_step": "Прими одно решение из ясности, а не из страха.",
        "affirmations": ["Выбери одно действие из любопытства."],
    }

    normalized = normalize_russian_user_facing_text_fields(payload, gender_hint="для пользователя")

    assert normalized["soft_action"] == "Назови три вещи, на которые можно опереться сейчас."
    assert normalized["micro_step"] == "Прими одно решение из ясности, а не из страха."
    assert normalized["affirmations"][0] == "Выбери одно действие из любопытства."
