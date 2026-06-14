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
    "home_support",
]

LEGACY_SPHERES = ["spirituality"]

SPHERE_LABELS = {
    "inner_peace": {"ru": "🕊 Внутренний покой", "en": "🕊 Inner peace"},
    "self_worth": {"ru": "💛 Самоценность", "en": "💛 Self-worth"},
    "health": {"ru": "🌱 Энергия и тело", "en": "🌱 Energy and body"},
    "career": {"ru": "💼 Дело и карьера", "en": "💼 Work and career"},
    "money": {"ru": "💰 Деньги и устойчивость", "en": "💰 Money and stability"},
    "relationships": {"ru": "🤝 Отношения и границы", "en": "🤝 Relationships and boundaries"},
    "self_realization": {"ru": "🎨 Творчество и самореализация", "en": "🎨 Creativity and self-realization"},
    "home_support": {"ru": "🏡 Дом и опора", "en": "🏡 Home and grounding"},
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
            "image_hint_en": "quiet lake, clear morning light, breathing space",
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
            "ru": "опора на себя",
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
    "home_support": [
        {
            "key": "safe_home_base",
            "ru": "дом как тихая база",
            "en": "home as a quiet base",
            "micro_step_ru": "Сделай один маленький жест уюта или порядка вокруг себя.",
            "micro_step_en": "Make one small gesture of comfort or order around you.",
            "image_hint_en": "calm lived-in home, soft lamp light, blanket, shelf, grounded comfort",
        },
        {
            "key": "return_to_support",
            "ru": "возвращение в опору",
            "en": "returning to support",
            "micro_step_ru": "Выбери одно простое действие, которое даст телу и дому ощущение опоры.",
            "micro_step_en": "Choose one simple action that gives your body and home a sense of support.",
        },
        {
            "key": "everyday_stability",
            "ru": "бытовая устойчивость",
            "en": "everyday stability",
            "micro_step_ru": "Упростите один бытовой шаг, чтобы день ощущался мягче.",
            "micro_step_en": "Simplify one household step so the day feels gentler.",
        },
        {
            "key": "soft_recovery",
            "ru": "мягкое восстановление",
            "en": "soft recovery",
            "micro_step_ru": "Оставь себе десять минут на тёплый, восстанавливающий ритуал дома.",
            "micro_step_en": "Leave yourself ten minutes for a warm restorative ritual at home.",
        },
        {
            "key": "grounded_comfort",
            "ru": "спокойный уют",
            "en": "grounded comfort",
            "micro_step_ru": "Добавь одну деталь, которая делает пространство более тёплым и своим.",
            "micro_step_en": "Add one detail that makes your space feel warmer and more your own.",
        },
        {
            "key": "gentle_order",
            "ru": "бережный порядок",
            "en": "gentle order",
            "micro_step_ru": "Наведи порядок только в одном маленьком месте, не пытаясь охватить всё.",
            "micro_step_en": "Bring order to one small place without trying to fix everything.",
        },
        {
            "key": "restful_safety",
            "ru": "безопасность и отдых",
            "en": "safety and rest",
            "micro_step_ru": "Спроси себя, что сегодня даст ощущение защищённости и покоя.",
            "micro_step_en": "Ask yourself what would create a sense of safety and rest today.",
        },
    ],
}

VALID_VISUAL_MODES = ("photo", "illustration", "mixed", "symbolic")

PHOTO_STYLE_KEYS = [
    "sunny_morning_photo",
    "living_nature_photo",
    "urban_city_photo",
    "cafe_terrace_photo",
    "rural_calm_photo",
    "sea_coast_photo",
    "cozy_home_photo",
    "book_nook_photo",
    "calm_lifestyle_photo",
]

PHOTO_STYLE_ALIASES = {
    "bright_photo_card": "sunny_morning_photo",
    "sunny_photo_scene": "sunny_morning_photo",
    "sunny_morning_scene": "sunny_morning_photo",
    "sunny_nature_photo": "living_nature_photo",
    "cinematic_real_photo": "calm_lifestyle_photo",
    "light_interior_photo": "cozy_home_photo",
    "bright_ocean_coast_photo": "sea_coast_photo",
    "vivid_ocean_photo": "sea_coast_photo",
    "bright_ocean": "sea_coast_photo",
    # symbolic_luxe was the original single symbolic style; keep old
    # subscriptions/history pointed at its closest replacement.
    "symbolic_luxe": "mandala_harmony",
}

ILLUSTRATION_STYLE_KEYS = [
    "bright_nature_card",
    "dreamy_painterly",
    "quiet_interior",
    "minimal_botanical",
    "cinematic_light",
    "ethereal_landscape",
    "textured_collage",
]

CURATED_STYLE_KEYS = ILLUSTRATION_STYLE_KEYS

# Symbolic visual mode (🪷 Мандалы и символы): a small dedicated taxonomy of
# mandala / sacred-geometry / botanical-ornament / single-emblem styles, each
# with its own prompt contract in services/openai_image.py. These styles are
# NOT part of the regular illustration/mixed menus.
SYMBOLIC_STYLE_KEYS = [
    "mandala_harmony",
    "sacred_geometry_light",
    "botanical_mandala",
    "daily_symbol",
]

LEGACY_STYLE_KEYS = ["realistic", "nature", "cosmos", "mandala", "sacred_geometry", "abstract", "cartoon"]

STYLE_LABELS = {
    "auto": {"ru": "Автоподбор", "en": "Auto"},
    "random_suitable": {"ru": "Разные подходящие стили", "en": "Different suitable styles"},
    "sunny_morning_photo": {"ru": "Солнечное утро", "en": "Sunny morning"},
    "living_nature_photo": {"ru": "Живая природа", "en": "Living nature"},
    "urban_city_photo": {"ru": "Городской стиль", "en": "City style"},
    "cafe_terrace_photo": {"ru": "Кафе и городские веранды", "en": "Cafe & city terraces"},
    "rural_calm_photo": {"ru": "Сельское спокойствие", "en": "Rural calm"},
    "sea_coast_photo": {"ru": "Побережье моря / океана", "en": "Sea & ocean coast"},
    "cozy_home_photo": {"ru": "Уютный дом", "en": "Cozy home"},
    "book_nook_photo": {"ru": "Книжный уголок", "en": "Book nook"},
    "calm_lifestyle_photo": {"ru": "Спокойный lifestyle", "en": "Calm lifestyle"},
    "bright_photo_card": {"ru": "Солнечное утро", "en": "Sunny morning"},
    "sunny_photo_scene": {"ru": "Солнечное утро", "en": "Sunny morning"},
    "sunny_nature_photo": {"ru": "Живая природа", "en": "Living nature"},
    "light_interior_photo": {"ru": "Уютный дом", "en": "Cozy home"},
    "bright_ocean_coast_photo": {"ru": "Побережье моря / океана", "en": "Sea & ocean coast"},
    "cinematic_real_photo": {"ru": "Спокойный lifestyle", "en": "Calm lifestyle"},
    "bright_nature_card": {"ru": "Светлая открытка дня", "en": "Bright daily card"},
    "dreamy_painterly": {"ru": "Мягкая акварель", "en": "Dreamy painterly"},
    "quiet_interior": {"ru": "Тихий интерьер", "en": "Quiet interior"},
    "minimal_botanical": {"ru": "Ботанический минимализм", "en": "Minimal botanical"},
    "cinematic_light": {"ru": "Кинематографичный свет", "en": "Cinematic light"},
    "ethereal_landscape": {"ru": "Туманный пейзаж", "en": "Ethereal landscape"},
    "textured_collage": {"ru": "Текстурный коллаж", "en": "Textured collage"},
    "mandala_harmony": {"ru": "Мандальная гармония", "en": "Mandala harmony"},
    "sacred_geometry_light": {"ru": "Светлая геометрия", "en": "Light geometry"},
    "botanical_mandala": {"ru": "Ботаническая мандала", "en": "Botanical mandala"},
    "daily_symbol": {"ru": "Символ дня", "en": "Symbol of the day"},
    "realistic": {"ru": "Реалистичный", "en": "Realistic"},
    "cartoon": {"ru": "Мультяшный", "en": "Cartoon"},
    "mandala": {"ru": "Мандала", "en": "Mandala"},
    "sacred_geometry": {"ru": "Сакральная геометрия", "en": "Sacred geometry"},
    "nature": {"ru": "Природа", "en": "Nature"},
    "cosmos": {"ru": "Космос", "en": "Cosmos"},
    "abstract": {"ru": "Абстракция", "en": "Abstract"},
}

STYLE_DESCRIPTIONS = {
    "sunny_morning_photo": "warm real-life photo, fresh sunny morning atmosphere, natural daylight, realistic scene, authentic photographic textures, serene editorial photography, crisp enough to read as a photo, candid but composed, camera realism",
    "living_nature_photo": "realistic nature photography, real landscape, riverside, meadow or trees, crisp clear air, fresh daylight and readable natural detail, believable atmosphere, natural light, camera realism, nature photo not a painted landscape, real weather and sharp photographic detail, avoid visible fog, mist, murky haze or smeared pastel haze unless explicitly requested",
    "urban_city_photo": "calm realistic city photography, quiet street, courtyard, park or bridge walkway, soft natural light, believable urban atmosphere, editorial lifestyle realism, may include subtle small-scale signs of city life such as a distant pedestrian, cyclist, dog walker, parked car or an open cafe, kept small and not as the focal point, no crowd as focal point, no harsh corporate stock feeling",
    "cafe_terrace_photo": "realistic cafe terrace or city veranda photography, calm urban atmosphere, awning, planters, facade details and small seating groups, coffee or pastry hints allowed but never as mug close-up hero object, editorial cafe environment realism",
    "rural_calm_photo": "realistic rural morning photography, cottage garden, orchard, wooden porch, country road or village veranda, soft daylight, grounded countryside atmosphere, calm lived-in details, no generic wild forest default",
    "sea_coast_photo": "real coastal photograph, sea or ocean coastline photography, realistic natural light, realistic sky and cloud formations, believable wave and water behavior, natural atmospheric perspective, camera realism, editorial landscape photography feel, calm restorative airy mood",
    "cozy_home_photo": "realistic cozy home photography, lived-in domestic warmth, kitchen corner, textiles, cushions or houseplants, morning or evening home details like a warm mug, folded blanket or soft lamp light, believable textures and daylight, emotionally supportive without sterile showroom feeling",
    "book_nook_photo": "realistic reading nook or library corner photography, bookshelves, stacked books, reading chair and lamp, bookshop aisle atmosphere, calm reflective reading mood, no office feeling, no laptop-centered productivity stock look",
    "calm_lifestyle_photo": "editorial lifestyle photography, realistic everyday scene, calm warm understated mood, quiet everyday moments such as a balcony view, table detail, simple morning ritual, a calm walk, a cafe corner or hands doing a calm everyday activity, not centered on bookshelves, armchair or reading-lamp imagery, magazine lifestyle shoot, authentic photo look, lived-in but tidy details with natural materials, textured surfaces and daylight shadows, avoid generic corporate stock-photo look and showroom or catalog-furniture staging, avoid repeating the same laptop-cup-plant-notebook combination unless the scene specifically needs it",
    "bright_photo_card": "warm real-life photo, fresh sunny morning atmosphere, natural daylight, realistic scene, authentic photographic textures, serene editorial photography, crisp enough to read as a photo, candid but composed, camera realism",
    "sunny_photo_scene": "warm real-life photo, fresh sunny morning atmosphere, natural daylight, realistic scene, authentic photographic textures, serene editorial photography, crisp enough to read as a photo, candid but composed, camera realism",
    "sunny_nature_photo": "realistic nature photography, real landscape, riverside, meadow or trees, crisp clear air, fresh daylight and readable natural detail, believable atmosphere, natural light, camera realism, nature photo not a painted landscape, real weather and sharp photographic detail, avoid visible fog, mist, murky haze or smeared pastel haze unless explicitly requested",
    "light_interior_photo": "realistic cozy home photography, lived-in domestic warmth, kitchen corner, textiles, cushions or houseplants, morning or evening home details like a warm mug, folded blanket or soft lamp light, believable textures and daylight, emotionally supportive without sterile showroom feeling",
    "bright_ocean_coast_photo": "real coastal photograph, sea or ocean coastline photography, realistic natural light, realistic sky and cloud formations, believable wave and water behavior, natural atmospheric perspective, camera realism, editorial landscape photography feel, calm restorative airy mood",
    "cinematic_real_photo": "editorial lifestyle photography, realistic everyday scene, calm warm understated mood, quiet everyday moments such as a balcony view, table detail, simple morning ritual, a calm walk, a cafe corner or hands doing a calm everyday activity, not centered on bookshelves, armchair or reading-lamp imagery, magazine lifestyle shoot, authentic photo look, lived-in but tidy details with natural materials, textured surfaces and daylight shadows, avoid generic corporate stock-photo look and showroom or catalog-furniture staging, avoid repeating the same laptop-cup-plant-notebook combination unless the scene specifically needs it",
    "bright_nature_card": "bright uplifting daily card, warm natural light, beautiful nature or light airy scene, fresh atmosphere, photorealistic or soft semi-realistic quality, optimistic and emotionally supportive mood, clear composition",
    "dreamy_painterly": "light dreamy painterly artwork, airy watercolor and gouache texture, luminous pastel atmosphere, soft but clear forms, warm and hopeful mood, delicate artistic charm",
    "quiet_interior": "light-filled quiet interior, natural window light, elegant still life, notebooks, cup, fabrics, plants, soft morning or late-afternoon glow, calm and welcoming atmosphere, no dominant portrait",
    "minimal_botanical": "refined botanical composition, cream, sage, warm green, soft floral tones, elegant organic forms, bright and airy look, delicate detail, graceful negative space",
    "cinematic_light": "cinematic but luminous scene, warm or pearl natural light, elegant composition, soft realism, emotionally grounded and hopeful, focus on atmosphere, space, action or setting rather than close-up face",
    "ethereal_landscape": "light ethereal landscape, luminous mist, dawn light, soft sky, reflective water, gentle trees, quiet spacious beauty, bright readable atmosphere",
    "textured_collage": "light textured collage with paper layers, botanical or natural motifs, handmade feel, soft sunlight palette, elegant editorial balance, cheerful and refined",
    "mandala_harmony": "a single large centered visible mandala as the clear main subject filling most of the frame, strong radial symmetry and symmetrical balance, intricate geometric rosette and circular ornament with sacred geometry inspired layout, fine ornamental linework, decorative card-like composition, luminous refined colors and calm harmonious palette, purely decorative abstract motifs not tied to any specific religion, belief system or symbol set, no readable text, not a plain abstract texture, not wallpaper, not a water surface or ocean reflection, not a landscape, not a vague glowing background, not a realistic photo",
    "sacred_geometry_light": "a centered sacred-geometry-inspired ornamental composition filling most of the frame, interlocking circles, soft polygons and a geometric rosette, clear symmetry, fine luminous linework, decorative card-like composition, soft pastel palette, not occult, not religious, not a plain texture, not wallpaper, not a realistic photo",
    "botanical_mandala": "leaves, petals, flowers and branches arranged into a single large centered radial mandala ornament, clear radial symmetry and balanced botanical patterning, decorative card-like composition, soft botanical palette, a botanical ornament rather than a landscape, not a meadow or nature photo, not wallpaper, not a plain texture",
    "daily_symbol": "one simple central abstract emblem made of universal shapes such as a circle, sun, leaf, wave, path or star-like glow, placed centrally with calm balanced negative space, decorative card-like composition, luminous warm palette, a single abstract symbol rather than a mandala, not a rune, not a sigil, not an alphabet-like glyph, not wallpaper, not a plain texture",
}

ILLUSTRATION_RECOMMENDED_STYLES = {
    "inner_peace": ["bright_nature_card", "ethereal_landscape", "dreamy_painterly"],
    "self_worth": ["bright_nature_card", "minimal_botanical", "textured_collage", "quiet_interior"],
    "health": ["bright_nature_card", "minimal_botanical", "dreamy_painterly"],
    "career": ["bright_nature_card", "quiet_interior", "cinematic_light"],
    "money": ["bright_nature_card", "quiet_interior", "minimal_botanical"],
    "relationships": ["bright_nature_card", "quiet_interior", "dreamy_painterly"],
    "self_realization": ["bright_nature_card", "cinematic_light", "dreamy_painterly", "textured_collage"],
    "home_support": ["quiet_interior", "minimal_botanical", "bright_nature_card", "dreamy_painterly"],
    "spirituality": ["ethereal_landscape", "bright_nature_card"],
}

PHOTO_RECOMMENDED_STYLES = {
    "inner_peace": ["sea_coast_photo", "cozy_home_photo", "living_nature_photo", "calm_lifestyle_photo", "sunny_morning_photo"],
    "self_worth": ["cozy_home_photo", "calm_lifestyle_photo", "sea_coast_photo", "sunny_morning_photo", "book_nook_photo"],
    "health": ["living_nature_photo", "rural_calm_photo", "calm_lifestyle_photo", "sea_coast_photo", "sunny_morning_photo"],
    "career": ["urban_city_photo", "calm_lifestyle_photo", "book_nook_photo", "cafe_terrace_photo", "sea_coast_photo", "sunny_morning_photo"],
    "money": ["urban_city_photo", "cafe_terrace_photo", "book_nook_photo", "calm_lifestyle_photo", "sea_coast_photo", "sunny_morning_photo"],
    "relationships": ["cozy_home_photo", "cafe_terrace_photo", "sea_coast_photo", "calm_lifestyle_photo", "sunny_morning_photo"],
    "self_realization": ["book_nook_photo", "urban_city_photo", "calm_lifestyle_photo", "sea_coast_photo", "sunny_morning_photo"],
    "home_support": ["cozy_home_photo", "book_nook_photo", "rural_calm_photo", "living_nature_photo", "calm_lifestyle_photo"],
    "spirituality": ["sea_coast_photo", "cozy_home_photo", "living_nature_photo", "calm_lifestyle_photo", "sunny_morning_photo"],
}

RECOMMENDED_STYLES = ILLUSTRATION_RECOMMENDED_STYLES

PHOTO_SCENE_PRESETS = {
    "window_still_life": (
        "Photo scene preset: window_still_life. Realistic still life by a window, natural daylight, "
        "glass, ceramic, linen and wood, calm real home atmosphere, editorial interior photography, "
        "believable materials, perspective and shadows."
    ),
    "calm_workspace": (
        "Photo scene preset: calm_workspace. Realistic lived-in workspace with desk and daylight from a window, "
        "varying the props (e.g. notebook, pen, books, lamp, mug, plant) rather than always combining laptop, cup, "
        "plant and notebook together, with natural materials and textured surfaces, calm lifestyle/editorial photography, "
        "avoid generic corporate stock-photo look and showroom or catalog-furniture staging, "
        "real textures, daylight shadows and tasteful realistic composition."
    ),
    "botanical_corner": (
        "Photo scene preset: botanical_corner. Real plant or branches in a vase on a windowsill or table, "
        "natural daylight, close realistic photo, believable glass, leaves, water, wood and linen."
    ),
    "outdoor_path": (
        "Photo scene preset: outdoor_path. Real nature photograph of a path, park, riverside, lakeside bank "
        "or meadow edge, documentary-style natural scene, real lens rendering, crisp natural detail, "
        "believable depth and lighting, not painted and not dreamy illustration."
    ),
    "restful_daily_scene": (
        "Photo scene preset: restful_daily_scene. Water glass, tea, blanket, chair, book or soft daylight, "
        "realistic cozy recovery scene, lifestyle photography, calm but clearly photographic."
    ),
    "street_cafe_terrace": (
        "Photo scene preset: street_cafe_terrace. Realistic outdoor cafe terrace with facade details, awning, planters, "
        "small tables and visible street atmosphere, editorial urban photography, not mug close-up and not empty dining hall."
    ),
    "city_veranda_morning": (
        "Photo scene preset: city_veranda_morning. Realistic city veranda or cafe porch in the morning, soft daylight, "
        "chairs and facade details as part of the environment, calm urban openness, photographic realism."
    ),
    "courtyard_cafe": (
        "Photo scene preset: courtyard_cafe. Quiet cafe in a courtyard with greenery, tables as supporting elements, "
        "open spatial composition, realistic urban lifestyle photography, not tabletop hero shot."
    ),
    "village_veranda": (
        "Photo scene preset: village_veranda. Real rural veranda or porch, morning air, wood textures, plants and lived-in calm, "
        "realistic countryside photography with grounded home detail."
    ),
    "cottage_garden": (
        "Photo scene preset: cottage_garden. Real cottage garden with path, plants and calm home atmosphere, "
        "natural daylight, realistic rural details, editorial countryside photography."
    ),
    "warm_living_room": (
        "Photo scene preset: warm_living_room. Real calm living room with chair, blanket, shelf or lamp, "
        "soft believable daylight or warm ambient light, lived-in home feeling, not showroom styling."
    ),
    "bookshop_aisle": (
        "Photo scene preset: bookshop_aisle. Real bookstore or library aisle with shelves, reading atmosphere and warm order, "
        "realistic interior photography, calm reflective mood, not office-like."
    ),
    "relationship_table_scene": (
        "Photo scene preset: relationship_table_scene. Two cups, two chairs, table setting or shared space, "
        "realistic intimate but non-portrait scene, calm daylight, real textures, editorial lifestyle photography."
    ),
    "ocean_sunrise": (
        "Photo scene preset: ocean_sunrise. Real coastal photograph of sunrise over the ocean, soft cool-warm light, "
        "realistic sky and cloud formations, calm horizon line, believable atmospheric perspective and camera realism."
    ),
    "seaside_sunset": (
        "Photo scene preset: seaside_sunset. Real coastal photography at golden hour sunset, reflections on seawater, "
        "soft clouds, believable wave and water behavior, natural light and editorial landscape photography feel."
    ),
    "quiet_beach_morning": (
        "Photo scene preset: quiet_beach_morning. Empty beach in the morning, wave marks on sand, soft sky, "
        "light natural haze, real photo, realistic shoreline textures and calm restorative mood."
    ),
    "rocky_coast": (
        "Photo scene preset: rocky_coast. Real photograph of a rocky sea coast, waves, clouds, wet stone, "
        "real natural textures, believable water motion and realistic outdoor light."
    ),
    "dunes_and_seabirds": (
        "Photo scene preset: dunes_and_seabirds. Real photography of coastal dunes, beach grass, sand and seabirds "
        "in the sky or far distance, natural daylight, airy space, not decorative illustration."
    ),
    "coastal_path": (
        "Photo scene preset: coastal_path. Realistic outdoor photo of a path along the sea or ocean coast, "
        "water visible in the background, calm reflective mood, natural perspective and camera realism."
    ),
    "bright_ocean_sunrise": (
        "Photo scene preset: bright_ocean_sunrise. Real bright vivid ocean coastline at sunrise, open sea horizon, "
        "clear shoreline, lively waves and sea foam, expressive clouds, travel/editorial photography look."
    ),
    "vivid_seaside_sunset": (
        "Photo scene preset: vivid_seaside_sunset. Real seaside coast at vivid golden sunset with open ocean horizon, "
        "waves, sea foam and rich but natural colors."
    ),
    "sunny_beach_morning": (
        "Photo scene preset: sunny_beach_morning. Real sunny morning at ocean beach with bright sky, clear shoreline, "
        "sand or pebbles and natural lively surf."
    ),
    "turquoise_shoreline": (
        "Photo scene preset: turquoise_shoreline. Real shoreline with turquoise to deep-blue ocean water, open horizon, "
        "clear wave patterns and bright natural daylight."
    ),
    "rocky_ocean_coast": (
        "Photo scene preset: rocky_ocean_coast. Real rocky ocean coast with surf, sea foam, wet stones or cliffs, "
        "clear horizon and strong natural light."
    ),
    "seabirds_over_waves": (
        "Photo scene preset: seabirds_over_waves. Real ocean coast with seabirds over waves, open water horizon, "
        "bright sky and editorial travel coastal photography."
    ),
}

# Visual Diversity v1.1: lightweight visual archetype layer.
# Maps illustration/photo styles and photo scene presets to a small set of
# broad visual archetypes, used to avoid repeating the same "look" across
# recent generations (e.g. meadow/flowers, cozy reading corner, cafe table).
VISUAL_ARCHETYPES = [
    "meadow_or_flowers",
    "forest_path",
    "cozy_reading_corner",
    "cafe_table",
    "workspace_desk",
    "city_morning",
    "botanical_detail",
    "water_horizon",
    "architecture_detail",
    "abstract_light",
    "minimal_object",
    "open_sky",
]

STYLE_ARCHETYPES = {
    # illustration styles
    "bright_nature_card": "meadow_or_flowers",
    "dreamy_painterly": "abstract_light",
    "quiet_interior": "cozy_reading_corner",
    "minimal_botanical": "botanical_detail",
    "cinematic_light": "abstract_light",
    "ethereal_landscape": "water_horizon",
    "textured_collage": "botanical_detail",
    # symbolic mode styles
    "mandala_harmony": "minimal_object",
    "sacred_geometry_light": "minimal_object",
    "botanical_mandala": "botanical_detail",
    "daily_symbol": "minimal_object",
    # photo styles
    "sunny_morning_photo": "open_sky",
    "living_nature_photo": "forest_path",
    "urban_city_photo": "city_morning",
    "cafe_terrace_photo": "cafe_table",
    "rural_calm_photo": "architecture_detail",
    "sea_coast_photo": "water_horizon",
    "cozy_home_photo": "cozy_reading_corner",
    "book_nook_photo": "cozy_reading_corner",
    "calm_lifestyle_photo": "workspace_desk",
    "bright_photo_card": "open_sky",
    "sunny_photo_scene": "open_sky",
    "sunny_nature_photo": "forest_path",
    "light_interior_photo": "cozy_reading_corner",
    "bright_ocean_coast_photo": "water_horizon",
    "cinematic_real_photo": "workspace_desk",
}

SCENE_PRESET_ARCHETYPES = {
    "window_still_life": "minimal_object",
    "calm_workspace": "workspace_desk",
    "botanical_corner": "botanical_detail",
    "outdoor_path": "forest_path",
    "restful_daily_scene": "cozy_reading_corner",
    "street_cafe_terrace": "cafe_table",
    "city_veranda_morning": "city_morning",
    "courtyard_cafe": "cafe_table",
    "village_veranda": "architecture_detail",
    "cottage_garden": "meadow_or_flowers",
    "warm_living_room": "cozy_reading_corner",
    "bookshop_aisle": "architecture_detail",
    "relationship_table_scene": "cafe_table",
    "ocean_sunrise": "water_horizon",
    "seaside_sunset": "water_horizon",
    "quiet_beach_morning": "open_sky",
    "rocky_coast": "water_horizon",
    "dunes_and_seabirds": "open_sky",
    "coastal_path": "water_horizon",
    "bright_ocean_sunrise": "water_horizon",
    "vivid_seaside_sunset": "water_horizon",
    "sunny_beach_morning": "open_sky",
    "turquoise_shoreline": "water_horizon",
    "rocky_ocean_coast": "water_horizon",
    "seabirds_over_waves": "open_sky",
}


def get_visual_archetype(style: Optional[str] = None, scene_preset: Optional[str] = None) -> str:
    """Return a broad visual archetype label for a style/scene combination.

    Scene preset (more specific, photo mode) takes priority over style.
    Falls back to "abstract_light" for unmapped/unknown styles.
    """
    if scene_preset and scene_preset in SCENE_PRESET_ARCHETYPES:
        return SCENE_PRESET_ARCHETYPES[scene_preset]
    style_key = normalize_style_key(style)
    return STYLE_ARCHETYPES.get(style_key, "abstract_light")


def _filter_by_recent_archetypes(candidates: List[str], archetype_for, recent_archetypes: Optional[List[str]]) -> List[str]:
    """Drop candidates whose archetype was used recently; fall back to the original list if that empties it."""
    if not recent_archetypes:
        return candidates
    recent_set = set(recent_archetypes)
    filtered = [candidate for candidate in candidates if archetype_for(candidate) not in recent_set]
    return filtered or candidates


PHOTO_SCENE_ROUTING = {
    "inner_peace": ["window_still_life", "botanical_corner", "ocean_sunrise", "coastal_path", "outdoor_path", "restful_daily_scene"],
    "self_worth": ["botanical_corner", "window_still_life", "calm_workspace", "quiet_beach_morning", "restful_daily_scene"],
    "health": ["restful_daily_scene", "botanical_corner", "ocean_sunrise", "quiet_beach_morning", "outdoor_path", "window_still_life"],
    "career": ["calm_workspace", "window_still_life", "botanical_corner"],
    "money": ["calm_workspace", "window_still_life", "botanical_corner"],
    "relationships": ["relationship_table_scene", "window_still_life", "botanical_corner", "coastal_path", "quiet_beach_morning", "outdoor_path"],
    "self_realization": ["calm_workspace", "coastal_path", "botanical_corner", "window_still_life", "outdoor_path"],
    "home_support": ["warm_living_room", "bookshop_aisle", "village_veranda", "cottage_garden", "restful_daily_scene"],
    "spirituality": ["window_still_life", "botanical_corner", "ocean_sunrise", "restful_daily_scene"],
}

PHOTO_STYLE_SCENE_HINTS = {
    "sunny_morning_photo": ["outdoor_path", "restful_daily_scene", "city_veranda_morning", "window_still_life"],
    "living_nature_photo": ["outdoor_path", "botanical_corner"],
    "urban_city_photo": ["city_veranda_morning", "courtyard_cafe", "calm_workspace", "outdoor_path"],
    "cafe_terrace_photo": ["street_cafe_terrace", "city_veranda_morning", "courtyard_cafe", "bookshop_aisle"],
    "rural_calm_photo": ["village_veranda", "cottage_garden", "outdoor_path", "restful_daily_scene"],
    "sea_coast_photo": [
        "ocean_sunrise",
        "seaside_sunset",
        "quiet_beach_morning",
        "rocky_coast",
        "dunes_and_seabirds",
        "coastal_path",
    ],
    "cozy_home_photo": ["warm_living_room", "restful_daily_scene", "botanical_corner"],
    "book_nook_photo": ["bookshop_aisle", "window_still_life"],
    "calm_lifestyle_photo": ["calm_workspace", "relationship_table_scene"],
    "bright_ocean_coast_photo": [
        "bright_ocean_sunrise",
        "vivid_seaside_sunset",
        "sunny_beach_morning",
        "turquoise_shoreline",
        "rocky_ocean_coast",
        "seabirds_over_waves",
    ],
    "sunny_photo_scene": ["outdoor_path", "restful_daily_scene", "city_veranda_morning", "window_still_life"],
    "light_interior_photo": ["warm_living_room", "restful_daily_scene", "window_still_life", "botanical_corner"],
}


def get_sphere_label(sphere: str, language: str = "ru") -> str:
    return SPHERE_LABELS.get(sphere, {"ru": sphere, "en": sphere}).get(language, sphere)


def get_style_label(style: str, language: str = "ru") -> str:
    normalized = normalize_style_key(style)
    return STYLE_LABELS.get(normalized, STYLE_LABELS.get(style, {"ru": style, "en": style})).get(language, style)


def normalize_style_key(style: Optional[str]) -> str:
    if not style:
        return "auto"
    return PHOTO_STYLE_ALIASES.get(style, style)


def normalize_visual_mode(visual_mode: Optional[str]) -> str:
    if visual_mode in VALID_VISUAL_MODES:
        return visual_mode
    return "illustration"


def has_coastal_intent(text: Optional[str]) -> bool:
    if not text:
        return False
    low = text.lower()
    markers = (
        "море",
        "океан",
        "побереж",
        "берег",
        "пляж",
        "берег моря",
        "берег океана",
        "beach",
        "coast",
        "coastline",
        "shore",
        "seaside",
        "ocean",
        "sea",
        "sunset by the ocean",
    )
    return any(marker in low for marker in markers)


def get_visual_mode_label(visual_mode: str, language: str = "ru") -> str:
    labels = {
        "photo": {"ru": "📷 Фото-стиль", "en": "📷 Photo style"},
        "illustration": {"ru": "🖌 Мягкая иллюстрация", "en": "🖌 Soft illustration"},
        "mixed": {"ru": "🔀 Смешанный стиль", "en": "🔀 Mixed style"},
        "symbolic": {"ru": "🪷 Мандалы и символы", "en": "🪷 Mandalas & symbols"},
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
    if branch == "symbolic":
        return SYMBOLIC_STYLE_KEYS
    mapping = PHOTO_RECOMMENDED_STYLES if branch == "photo" else ILLUSTRATION_RECOMMENDED_STYLES
    return mapping.get(sphere, mapping["inner_peace"])


def get_photo_scene_presets(sphere: str, style: Optional[str] = None) -> List[str]:
    sphere_presets = PHOTO_SCENE_ROUTING.get(sphere, PHOTO_SCENE_ROUTING["inner_peace"])
    style_key = normalize_style_key(style)
    style_presets = PHOTO_STYLE_SCENE_HINTS.get(style_key)
    if not style_presets:
        return sphere_presets
    if style_key == "sea_coast_photo":
        return style_presets
    matched = [preset for preset in sphere_presets if preset in style_presets]
    return matched or sphere_presets


def resolve_photo_scene_preset(
    sphere: str,
    style: Optional[str] = None,
    user_id: Optional[int] = None,
    day: Optional[dt.date] = None,
    focus_key: Optional[str] = None,
    recent_scene_presets: Optional[List[str]] = None,
    recent_archetypes: Optional[List[str]] = None,
) -> str:
    presets = get_photo_scene_presets(sphere, style)
    if recent_scene_presets:
        filtered = [p for p in presets if p not in set(recent_scene_presets)]
        if filtered:
            presets = filtered
    presets = _filter_by_recent_archetypes(
        presets,
        lambda candidate: get_visual_archetype(style=style, scene_preset=candidate),
        recent_archetypes,
    )
    if len(presets) == 1:
        return presets[0]
    if user_id is not None and day is not None:
        iso_year, iso_week, weekday = day.isocalendar()
        rng = random.Random(
            f"photo-scene-{user_id}-{sphere}-{normalize_style_key(style)}-{focus_key or ''}-{iso_year}-{iso_week}-{weekday}"
        )
        return presets[rng.randrange(len(presets))]
    seed = f"photo-scene-{sphere}-{normalize_style_key(style)}-{focus_key or ''}"
    idx = sum(ord(ch) for ch in seed) % len(presets)
    return presets[idx]


def _resolve_photo_auto_style(recommended: List[str], sphere: str, weekday: int) -> str:
    if not recommended:
        return "cozy_home_photo"
    if sphere in ("money", "career"):
        # Keep work/finance grounded in interiors; coast is occasional, never dominant.
        if weekday == 7 and "sea_coast_photo" in recommended:
            return "sea_coast_photo"
        if weekday in (2, 5) and "calm_lifestyle_photo" in recommended:
            return "calm_lifestyle_photo"
        return recommended[0]
    idx = (weekday - 1) % len(recommended)
    return recommended[idx]


def visual_mode_for_style(visual_mode: Optional[str], selected_style: Optional[str] = None) -> str:
    mode = normalize_visual_mode(visual_mode)
    selected_style = normalize_style_key(selected_style)
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
    recent_styles: Optional[List[str]] = None,
    recent_archetypes: Optional[List[str]] = None,
) -> str:
    style = normalize_style_key(style)
    if style == "random":
        style = "random_suitable"
    mode = normalize_visual_mode(visual_mode)
    recommended = get_recommended_styles(sphere, mode, user_id=user_id, day=day)
    if style in ("auto", "random_suitable"):
        recent_set = set((recent_styles or []))
        if recent_set:
            filtered_recommended = [candidate for candidate in recommended if candidate not in recent_set]
            if filtered_recommended:
                recommended = filtered_recommended
        # Money/career photo-auto has a dedicated grounding rule (_resolve_photo_auto_style)
        # that keeps coast occasional; archetype anti-repeat must not remove those
        # grounded candidates and cause drift to sea_coast_photo/sunny_morning_photo.
        skip_archetype_filter_for_grounding = style == "auto" and mode == "photo" and sphere in ("money", "career")
        if not skip_archetype_filter_for_grounding:
            recommended = _filter_by_recent_archetypes(
                recommended,
                lambda candidate: get_visual_archetype(style=candidate),
                recent_archetypes,
            )
        if user_id is not None and day is not None:
            iso_year, iso_week, weekday = day.isocalendar()
            salt = "auto-style" if style == "auto" else "suitable-style"
            rng = random.Random(f"{salt}-{mode}-{user_id}-{sphere}-{focus_key or ''}-{iso_year}-{iso_week}-{weekday}")
            if mode == "photo" and style == "auto":
                return _resolve_photo_auto_style(recommended, sphere, weekday)
            if style == "auto" and recommended and recommended[0] in ("bright_nature_card", "sunny_morning_photo"):
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
