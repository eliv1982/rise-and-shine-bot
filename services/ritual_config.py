import datetime as dt
import random
from typing import Dict, List, Optional


MAIN_SPHERES = [
    "inner_peace",
    "self_worth",
    "health",
    "career",
    "money",
    "relationships",
    "self_realization",
]

LEGACY_SPHERES = ["spirituality"]

SPHERE_LABELS = {
    "inner_peace": {"ru": "🕊 Внутренний покой", "en": "🕊 Inner peace"},
    "self_worth": {"ru": "💛 Самоценность", "en": "💛 Self-worth"},
    "health": {"ru": "🌱 Энергия и тело", "en": "🌱 Energy and body"},
    "career": {"ru": "💼 Дело и карьера", "en": "💼 Work and career"},
    "money": {"ru": "💰 Деньги и устойчивость", "en": "💰 Money and stability"},
    "relationships": {"ru": "🤝 Отношения и границы", "en": "🤝 Relationships and boundaries"},
    "self_realization": {"ru": "🎨 Самореализация и творчество", "en": "🎨 Self-realization and creativity"},
    "spirituality": {"ru": "Духовный рост", "en": "Spiritual growth"},
}

FOCUSES = {
    "inner_peace": [
        {
            "key": "inner_stillness",
            "ru": "тишина внутри",
            "en": "inner stillness",
            "micro_step_ru": "Сделай одну короткую паузу на дыхание перед важным делом.",
            "micro_step_en": "Take one short breathing pause before an important task.",
            "image_hint_en": "quiet lake, mist, soft morning light, breathing space",
        },
        {
            "key": "gentle_clarity",
            "ru": "мягкая ясность",
            "en": "gentle clarity",
            "micro_step_ru": "Запиши одну мысль, которую хочешь сегодня упростить.",
            "micro_step_en": "Write down one thought you want to simplify today.",
        },
        {
            "key": "returning_to_myself",
            "ru": "спокойное возвращение к себе",
            "en": "returning to myself calmly",
            "micro_step_ru": "Выбери один момент дня, где ты вернёшь внимание к себе.",
            "micro_step_en": "Choose one moment today to bring attention back to yourself.",
        },
        {
            "key": "less_pressure",
            "ru": "меньше давления",
            "en": "less inner pressure",
            "micro_step_ru": "Сними одно необязательное требование к себе на сегодня.",
            "micro_step_en": "Release one unnecessary demand you placed on yourself today.",
        },
        {
            "key": "steadiness",
            "ru": "устойчивость в моменте",
            "en": "steadiness in the moment",
            "micro_step_ru": "Назови три простые вещи, на которые можно опереться сейчас.",
            "micro_step_en": "Name three simple things you can rely on right now.",
        },
        {
            "key": "space_to_breathe",
            "ru": "пространство для дыхания",
            "en": "space to breathe",
            "micro_step_ru": "Оставь десять минут без задач и уведомлений.",
            "micro_step_en": "Leave ten minutes free from tasks and notifications.",
        },
        {
            "key": "own_pace",
            "ru": "доверие своему темпу",
            "en": "trust in my own pace",
            "micro_step_ru": "Сделай следующее действие чуть медленнее, чем обычно.",
            "micro_step_en": "Do your next action a little slower than usual.",
        },
    ],
    "self_worth": [
        {
            "key": "right_to_be_myself",
            "ru": "право быть собой",
            "en": "the right to be myself",
            "micro_step_ru": "Заметь одно место, где сегодня можно не подстраиваться.",
            "micro_step_en": "Notice one place where you do not need to over-adapt today.",
        },
        {
            "key": "dignity_without_proof",
            "ru": "достоинство без доказательств",
            "en": "dignity without proof",
            "micro_step_ru": "Сделай паузу перед тем, как начать оправдываться.",
            "micro_step_en": "Pause before you start explaining or proving yourself.",
        },
        {
            "key": "soft_confidence",
            "ru": "мягкая уверенность",
            "en": "soft confidence",
            "micro_step_ru": "Скажи одну честную фразу без лишнего смягчения.",
            "micro_step_en": "Say one honest sentence without over-softening it.",
        },
        {
            "key": "self_acceptance",
            "ru": "принятие себя",
            "en": "self-acceptance",
            "micro_step_ru": "Отнесись к одной своей ошибке как к человеческому опыту.",
            "micro_step_en": "Treat one mistake as a human experience, not a verdict.",
        },
        {
            "key": "inner_support",
            "ru": "внутренняя опора",
            "en": "inner support",
            "micro_step_ru": "Напомни себе, что твоя ценность не зависит от результата дня.",
            "micro_step_en": "Remind yourself that your worth is not decided by today's outcome.",
        },
        {
            "key": "value_without_hurry",
            "ru": "ценность без суеты",
            "en": "worth without hurry",
            "micro_step_ru": "Сделай одно дело в спокойном темпе, не доказывая свою полезность.",
            "micro_step_en": "Do one task calmly without trying to prove your usefulness.",
        },
        {
            "key": "loyalty_to_myself",
            "ru": "верность себе",
            "en": "loyalty to myself",
            "micro_step_ru": "Выбери один маленький поступок в поддержку себя.",
            "micro_step_en": "Choose one small action that supports your own side.",
        },
    ],
    "health": [
        {
            "key": "gentle_restoration",
            "ru": "бережное восстановление",
            "en": "gentle restoration",
            "micro_step_ru": "Выбери один способ восстановиться без давления на себя.",
            "micro_step_en": "Choose one way to restore yourself without pressure.",
            "image_hint_en": "morning air, water, linen, green leaves, restorative atmosphere",
        },
        {
            "key": "soft_energy",
            "ru": "мягкая энергия",
            "en": "soft energy",
            "micro_step_ru": "Сделай короткое движение, которое приятно телу.",
            "micro_step_en": "Do one brief movement that feels kind to your body.",
        },
        {
            "key": "care_without_pressure",
            "ru": "забота без давления",
            "en": "care without pressure",
            "micro_step_ru": "Выбери одну форму заботы, которая не требует идеальности.",
            "micro_step_en": "Choose one form of care that does not require perfection.",
        },
        {
            "key": "body_contact",
            "ru": "контакт с телом",
            "en": "connection with my body",
            "micro_step_ru": "На минуту прислушайся к телу без оценки.",
            "micro_step_en": "Listen to your body for one minute without judging it.",
        },
        {
            "key": "calm_rhythm",
            "ru": "спокойный ритм дня",
            "en": "a calm rhythm for the day",
            "micro_step_ru": "Поставь одно дело в более реалистичное время.",
            "micro_step_en": "Move one task into a more realistic time slot.",
        },
        {
            "key": "right_to_rest",
            "ru": "право на отдых",
            "en": "the right to rest",
            "micro_step_ru": "Разреши себе один короткий отдых без чувства вины.",
            "micro_step_en": "Allow yourself one short rest without guilt.",
        },
        {
            "key": "attention_to_myself",
            "ru": "внимание к себе",
            "en": "attention to myself",
            "micro_step_ru": "Спроси себя, что сейчас действительно поддержит твоё состояние.",
            "micro_step_en": "Ask what would genuinely support your state right now.",
        },
    ],
    "career": [
        {
            "key": "clear_movement",
            "ru": "ясное движение вперёд",
            "en": "clear movement forward",
            "micro_step_ru": "Выбери одно дело, которое реально продвинет тебя вперёд без суеты.",
            "micro_step_en": "Choose one small action that moves you forward without pressure.",
            "image_hint_en": "quiet workspace, morning light, open notebook, calm professional dignity",
        },
        {
            "key": "professional_dignity",
            "ru": "профессиональное достоинство",
            "en": "professional dignity",
            "micro_step_ru": "Сделай один рабочий выбор из уважения к своему времени.",
            "micro_step_en": "Make one work choice that respects your time.",
        },
        {
            "key": "calm_focus",
            "ru": "спокойная собранность",
            "en": "calm focus",
            "micro_step_ru": "Закрой один лишний отвлекающий канал на время важной задачи.",
            "micro_step_en": "Close one distracting channel while you do an important task.",
        },
        {
            "key": "mature_decisions",
            "ru": "зрелые решения",
            "en": "mature decisions",
            "micro_step_ru": "Перед решением уточни один факт вместо догадок.",
            "micro_step_en": "Clarify one fact before deciding instead of guessing.",
        },
        {
            "key": "growth_without_strain",
            "ru": "рост без надрыва",
            "en": "growth without strain",
            "micro_step_ru": "Сделай шаг развития, который не требует от тебя истощения.",
            "micro_step_en": "Take one growth step that does not require exhaustion.",
        },
        {
            "key": "one_important_step",
            "ru": "один важный шаг",
            "en": "one important step",
            "micro_step_ru": "Назови главный шаг дня и начни с первых десяти минут.",
            "micro_step_en": "Name today's main step and begin with the first ten minutes.",
        },
        {
            "key": "trust_the_process",
            "ru": "уверенность в процессе",
            "en": "confidence in the process",
            "micro_step_ru": "Отметь один признак прогресса, который уже есть.",
            "micro_step_en": "Notice one sign of progress that is already present.",
        },
    ],
    "money": [
        {
            "key": "financial_ground",
            "ru": "спокойная финансовая опора",
            "en": "calm financial ground",
            "micro_step_ru": "Посмотри на один финансовый вопрос спокойно и без самокритики.",
            "micro_step_en": "Look at one financial question calmly and without self-criticism.",
            "image_hint_en": "refined interior, warm light, calm order, open notebook, enoughness and dignity",
        },
        {
            "key": "mature_money_relation",
            "ru": "зрелое отношение к деньгам",
            "en": "a mature relationship with money",
            "micro_step_ru": "Прими одно денежное решение из ясности, а не из страха.",
            "micro_step_en": "Make one money decision from clarity rather than fear.",
        },
        {
            "key": "stability_enoughness",
            "ru": "устойчивость и достаточность",
            "en": "stability and enoughness",
            "micro_step_ru": "Заметь один ресурс, который уже поддерживает твою устойчивость.",
            "micro_step_en": "Notice one resource that already supports your stability.",
        },
        {
            "key": "value_of_my_work",
            "ru": "ценность моего труда",
            "en": "the value of my work",
            "micro_step_ru": "Назови одну конкретную ценность, которую создаёт твой труд.",
            "micro_step_en": "Name one concrete value your work creates.",
        },
        {
            "key": "decisions_without_fear",
            "ru": "решения без страха",
            "en": "decisions without fear",
            "micro_step_ru": "Сделай один маленький финансовый шаг без спешки.",
            "micro_step_en": "Take one small financial step without rushing.",
        },
        {
            "key": "order_and_clarity",
            "ru": "порядок и ясность",
            "en": "order and clarity",
            "micro_step_ru": "Упорядочи один маленький денежный список или заметку.",
            "micro_step_en": "Bring order to one small money list or note.",
        },
        {
            "key": "receiving_more",
            "ru": "право принимать больше",
            "en": "permission to receive more",
            "micro_step_ru": "Заметь, где ты можешь принять поддержку без оправданий.",
            "micro_step_en": "Notice where you can receive support without explaining it away.",
        },
    ],
    "relationships": [
        {
            "key": "warmth_boundaries",
            "ru": "тепло и границы",
            "en": "warmth and boundaries",
            "micro_step_ru": "Скажи одно ясное «да» или «нет» мягко и честно.",
            "micro_step_en": "Say one clear yes or no with kindness and honesty.",
            "image_hint_en": "tea table, two chairs, warm domestic light, respectful closeness",
        },
        {
            "key": "honest_closeness",
            "ru": "честная близость",
            "en": "honest closeness",
            "micro_step_ru": "Назови одно чувство без обвинений и драматизации.",
            "micro_step_en": "Name one feeling without blame or drama.",
        },
        {
            "key": "mutual_respect",
            "ru": "уважение к себе и другому",
            "en": "respect for myself and another",
            "micro_step_ru": "Выбери фразу, которая сохраняет уважение к обеим сторонам.",
            "micro_step_en": "Choose a phrase that keeps respect for both sides.",
        },
        {
            "key": "soft_openness",
            "ru": "мягкая открытость",
            "en": "soft openness",
            "micro_step_ru": "Откройся ровно настолько, насколько сейчас безопасно.",
            "micro_step_en": "Open up only as much as feels safe right now.",
        },
        {
            "key": "safe_contact",
            "ru": "безопасный контакт",
            "en": "safe contact",
            "micro_step_ru": "Заметь, с кем тебе сегодня спокойно быть собой.",
            "micro_step_en": "Notice who lets you feel calm being yourself today.",
        },
        {
            "key": "clear_yes_no",
            "ru": "ясное «да» и ясное «нет»",
            "en": "a clear yes and a clear no",
            "micro_step_ru": "Перед ответом спроси себя, чего ты правда хочешь.",
            "micro_step_en": "Before answering, ask yourself what you truly want.",
        },
        {
            "key": "trust_without_losing_self",
            "ru": "доверие без потери себя",
            "en": "trust without losing myself",
            "micro_step_ru": "Оставь себе право на собственное мнение в близком контакте.",
            "micro_step_en": "Keep your right to your own view inside closeness.",
        },
    ],
    "self_realization": [
        {
            "key": "own_voice",
            "ru": "свой голос",
            "en": "my own voice",
            "micro_step_ru": "Запиши одну мысль своим языком, не делая её идеальной.",
            "micro_step_en": "Write one thought in your own words without making it perfect.",
            "image_hint_en": "creative studio, open window, sketchbook, warm light, artistic process",
        },
        {
            "key": "courage_to_show_up",
            "ru": "смелость проявляться",
            "en": "courage to be visible",
            "micro_step_ru": "Покажи один маленький результат тому, кому доверяешь.",
            "micro_step_en": "Show one small result to someone you trust.",
        },
        {
            "key": "creativity_without_perfection",
            "ru": "творчество без идеальности",
            "en": "creativity without perfection",
            "micro_step_ru": "Сделай черновик и не исправляй его первые десять минут.",
            "micro_step_en": "Make a draft and do not edit it for the first ten minutes.",
        },
        {
            "key": "living_interest",
            "ru": "живой интерес",
            "en": "living interest",
            "micro_step_ru": "Выбери одно действие из любопытства, а не из обязанности.",
            "micro_step_en": "Choose one action from curiosity rather than obligation.",
        },
        {
            "key": "permission_to_try",
            "ru": "право пробовать",
            "en": "permission to try",
            "micro_step_ru": "Разреши себе один маленький эксперимент без гарантии результата.",
            "micro_step_en": "Allow yourself one small experiment without guaranteed results.",
        },
        {
            "key": "small_creative_step",
            "ru": "маленький творческий шаг",
            "en": "a small creative step",
            "micro_step_ru": "Выдели пятнадцать минут на творческое действие без оценки.",
            "micro_step_en": "Give fifteen minutes to a creative action without judging it.",
        },
        {
            "key": "visibility_without_strain",
            "ru": "видимость без надрыва",
            "en": "visibility without strain",
            "micro_step_ru": "Выбери мягкий способ обозначить своё присутствие.",
            "micro_step_en": "Choose a gentle way to make your presence visible.",
        },
    ],
    "spirituality": [
        {
            "key": "grounded_intuition",
            "ru": "заземлённая интуиция",
            "en": "grounded intuition",
            "micro_step_ru": "Проверь внутреннее ощущение через один реальный факт.",
            "micro_step_en": "Check an inner feeling against one real fact.",
        }
    ],
}

VALID_VISUAL_MODES = ("photo", "illustration", "mixed")

PHOTO_STYLE_KEYS = [
    "bright_photo_card",
    "sunny_nature_photo",
    "light_interior_photo",
    "cinematic_real_photo",
]

ILLUSTRATION_STYLE_KEYS = [
    "bright_nature_card",
    "dreamy_painterly",
    "quiet_interior",
    "minimal_botanical",
    "cinematic_light",
    "ethereal_landscape",
    "symbolic_luxe",
    "textured_collage",
]

CURATED_STYLE_KEYS = ILLUSTRATION_STYLE_KEYS

LEGACY_STYLE_KEYS = ["realistic", "nature", "cosmos", "mandala", "sacred_geometry", "abstract", "cartoon"]

STYLE_LABELS = {
    "auto": {"ru": "Автоподбор", "en": "Auto"},
    "random_suitable": {"ru": "Разные подходящие стили", "en": "Different suitable styles"},
    "bright_photo_card": {"ru": "Солнечная фотокарточка", "en": "Sunny photo card"},
    "sunny_nature_photo": {"ru": "Солнечная природа", "en": "Sunny nature"},
    "light_interior_photo": {"ru": "Светлый интерьер", "en": "Light interior"},
    "cinematic_real_photo": {"ru": "Кинематографичное фото", "en": "Cinematic photo"},
    "bright_nature_card": {"ru": "Светлая открытка дня", "en": "Bright daily card"},
    "dreamy_painterly": {"ru": "Мягкая акварель", "en": "Dreamy painterly"},
    "quiet_interior": {"ru": "Тихий интерьер", "en": "Quiet interior"},
    "minimal_botanical": {"ru": "Ботанический минимализм", "en": "Minimal botanical"},
    "cinematic_light": {"ru": "Кинематографичный свет", "en": "Cinematic light"},
    "ethereal_landscape": {"ru": "Туманный пейзаж", "en": "Ethereal landscape"},
    "symbolic_luxe": {"ru": "Абстрактная гармония", "en": "Abstract harmony"},
    "textured_collage": {"ru": "Текстурный коллаж", "en": "Textured collage"},
    "realistic": {"ru": "Реалистичный", "en": "Realistic"},
    "cartoon": {"ru": "Мультяшный", "en": "Cartoon"},
    "mandala": {"ru": "Мандала", "en": "Mandala"},
    "sacred_geometry": {"ru": "Сакральная геометрия", "en": "Sacred geometry"},
    "nature": {"ru": "Природа", "en": "Nature"},
    "cosmos": {"ru": "Космос", "en": "Cosmos"},
    "abstract": {"ru": "Абстракция", "en": "Abstract"},
}

STYLE_DESCRIPTIONS = {
    "bright_photo_card": "bright photorealistic daily image, natural photography look, realistic sunlight, realistic colors, clear details, fresh optimistic atmosphere, beautiful natural or lifestyle scene, pleasant and readable on a phone screen",
    "sunny_nature_photo": "photorealistic sunny nature photography, clear sky, warm sunlight, fresh air, trees, flowers, meadow, sea, lake or gentle landscape, vibrant but natural colors, uplifting morning mood",
    "light_interior_photo": "photorealistic light interior photography, natural window light, cozy elegant room, flowers, cup, notebook without visible text, soft fabrics, plants, warm realistic shadows, calm welcoming atmosphere",
    "cinematic_real_photo": "cinematic photorealistic scene, realistic natural light, shallow depth of field, elegant composition, warm hopeful mood, realistic textures, no posing, no direct eye contact portrait",
    "bright_nature_card": "bright uplifting daily card, warm natural light, beautiful nature or light airy scene, fresh atmosphere, photorealistic or soft semi-realistic quality, optimistic and emotionally supportive mood, clear composition",
    "dreamy_painterly": "light dreamy painterly artwork, airy watercolor and gouache texture, luminous pastel atmosphere, soft but clear forms, warm and hopeful mood, delicate artistic charm",
    "quiet_interior": "light-filled quiet interior, natural window light, elegant still life, notebooks, cup, fabrics, plants, soft morning or late-afternoon glow, calm and welcoming atmosphere, no dominant portrait",
    "minimal_botanical": "refined botanical composition, cream, sage, warm green, soft floral tones, elegant organic forms, bright and airy look, delicate detail, graceful negative space",
    "cinematic_light": "cinematic but luminous scene, warm or pearl natural light, elegant composition, soft realism, emotionally grounded and hopeful, focus on atmosphere, space, action or setting rather than close-up face",
    "ethereal_landscape": "light ethereal landscape, luminous mist, dawn light, soft sky, reflective water, gentle trees, quiet spacious beauty, bright readable atmosphere",
    "symbolic_luxe": "elegant symbolic visual with soft light, clean refined textures, subtle metaphor, warm luminous palette, graceful and clear composition, emotionally uplifting rather than mysterious",
    "textured_collage": "light textured collage with paper layers, botanical or natural motifs, handmade feel, soft sunlight palette, elegant editorial balance, cheerful and refined",
}

ILLUSTRATION_RECOMMENDED_STYLES = {
    "inner_peace": ["bright_nature_card", "ethereal_landscape", "dreamy_painterly"],
    "self_worth": ["bright_nature_card", "minimal_botanical", "textured_collage", "quiet_interior"],
    "health": ["bright_nature_card", "minimal_botanical", "dreamy_painterly"],
    "career": ["bright_nature_card", "quiet_interior", "cinematic_light"],
    "money": ["bright_nature_card", "quiet_interior", "minimal_botanical"],
    "relationships": ["bright_nature_card", "quiet_interior", "dreamy_painterly"],
    "self_realization": ["bright_nature_card", "cinematic_light", "dreamy_painterly", "textured_collage"],
    "spirituality": ["ethereal_landscape", "bright_nature_card", "symbolic_luxe"],
}

PHOTO_RECOMMENDED_STYLES = {
    "inner_peace": ["sunny_nature_photo", "bright_photo_card", "cinematic_real_photo"],
    "self_worth": ["bright_photo_card", "light_interior_photo", "sunny_nature_photo"],
    "health": ["sunny_nature_photo", "bright_photo_card", "light_interior_photo"],
    "career": ["light_interior_photo", "cinematic_real_photo", "bright_photo_card"],
    "money": ["light_interior_photo", "bright_photo_card", "sunny_nature_photo"],
    "relationships": ["light_interior_photo", "sunny_nature_photo", "cinematic_real_photo"],
    "self_realization": ["bright_photo_card", "light_interior_photo", "cinematic_real_photo", "sunny_nature_photo"],
    "spirituality": ["sunny_nature_photo", "bright_photo_card", "cinematic_real_photo"],
}

RECOMMENDED_STYLES = ILLUSTRATION_RECOMMENDED_STYLES


def get_sphere_label(sphere: str, language: str = "ru") -> str:
    return SPHERE_LABELS.get(sphere, {"ru": sphere, "en": sphere}).get(language, sphere)


def get_style_label(style: str, language: str = "ru") -> str:
    return STYLE_LABELS.get(style, {"ru": style, "en": style}).get(language, style)


def normalize_visual_mode(visual_mode: Optional[str]) -> str:
    if visual_mode in VALID_VISUAL_MODES:
        return visual_mode
    return "illustration"


def get_visual_mode_label(visual_mode: str, language: str = "ru") -> str:
    labels = {
        "photo": {"ru": "📷 Фотореализм", "en": "📷 Photo realism"},
        "illustration": {"ru": "🖌 Мягкая иллюстрация", "en": "🖌 Soft illustration"},
        "mixed": {"ru": "🔀 Смешивать стили", "en": "🔀 Mix styles"},
    }
    mode = normalize_visual_mode(visual_mode)
    return labels[mode][language if language == "en" else "ru"]


def get_focuses(sphere: str) -> List[Dict[str, str]]:
    return FOCUSES.get(sphere, FOCUSES["inner_peace"])


def get_focus_by_key(sphere: str, focus_key: Optional[str]) -> Dict[str, str]:
    focuses = get_focuses(sphere)
    for focus in focuses:
        if focus["key"] == focus_key:
            return focus
    return focuses[0]


def get_focus_for_date(user_id: int, sphere: str, day: dt.date) -> Dict[str, str]:
    focuses = list(get_focuses(sphere))
    iso_year, iso_week, weekday = day.isocalendar()
    rng = random.Random(f"{user_id}-{sphere}-{iso_year}-{iso_week}")
    rng.shuffle(focuses)
    return focuses[(weekday - 1) % len(focuses)]


def get_weekly_balance_sphere(user_id: int, day: dt.date) -> str:
    spheres = list(MAIN_SPHERES)
    iso_year, iso_week, weekday = day.isocalendar()
    rng = random.Random(f"{user_id}-{iso_year}-{iso_week}")
    rng.shuffle(spheres)
    return spheres[(weekday - 1) % len(spheres)]


def _visual_branch(visual_mode: str, user_id: Optional[int], day: Optional[dt.date], sphere: str) -> str:
    mode = normalize_visual_mode(visual_mode)
    if mode != "mixed":
        return mode
    if user_id is not None and day is not None:
        iso_year, iso_week, weekday = day.isocalendar()
        rng = random.Random(f"visual-branch-{user_id}-{sphere}-{iso_year}-{iso_week}-{weekday}")
        return "photo" if rng.randrange(2) == 0 else "illustration"
    return random.choice(("photo", "illustration"))


def get_recommended_styles(
    sphere: str,
    visual_mode: Optional[str] = None,
    user_id: Optional[int] = None,
    day: Optional[dt.date] = None,
) -> List[str]:
    branch = _visual_branch(normalize_visual_mode(visual_mode), user_id, day, sphere)
    mapping = PHOTO_RECOMMENDED_STYLES if branch == "photo" else ILLUSTRATION_RECOMMENDED_STYLES
    return mapping.get(sphere, mapping["inner_peace"])


def visual_mode_for_style(visual_mode: Optional[str], selected_style: Optional[str] = None) -> str:
    mode = normalize_visual_mode(visual_mode)
    if mode == "mixed":
        if selected_style in PHOTO_STYLE_KEYS:
            return "photo"
        if selected_style in ILLUSTRATION_STYLE_KEYS or selected_style in LEGACY_STYLE_KEYS:
            return "illustration"
        return "illustration"
    return mode


def resolve_style(
    style: str,
    sphere: str,
    user_id: Optional[int] = None,
    day: Optional[dt.date] = None,
    focus_key: Optional[str] = None,
    visual_mode: Optional[str] = None,
) -> str:
    if style == "random":
        style = "random_suitable"
    mode = normalize_visual_mode(visual_mode)
    recommended = get_recommended_styles(sphere, mode, user_id=user_id, day=day)
    if style in ("auto", "random_suitable"):
        if user_id is not None and day is not None:
            iso_year, iso_week, weekday = day.isocalendar()
            salt = "auto-style" if style == "auto" else "suitable-style"
            rng = random.Random(f"{salt}-{mode}-{user_id}-{sphere}-{focus_key or ''}-{iso_year}-{iso_week}-{weekday}")
            if style == "auto" and recommended and recommended[0] in ("bright_nature_card", "bright_photo_card"):
                if weekday in (1, 3, 5, 7):
                    return recommended[0]
                return rng.choice(recommended[1:] or recommended)
            idx = (rng.randrange(len(recommended)) + weekday - 1) % len(recommended)
            return recommended[idx]
        if style == "auto":
            return recommended[0]
        return random.choice(recommended)
    return style


def is_tts_available(language: str) -> bool:
    return language == "ru"
