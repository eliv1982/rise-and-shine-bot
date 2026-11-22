"""Neutral SG-01 semantic data; no configuration, consumers or provider I/O.

Only interpretation vocabulary and existing FIX-03A style identity/compatibility
are registered in Stage 1A. Prompt fragments/capabilities are deferred.
"""
import re

REGISTRY_VERSION = "sg01-stage1a-v1"
VOCABULARY_VERSION = "ar01-sg01-v1"
POLICY_VERSION = "D1-A_SG-D1_SG-D2_FIX-03A-v1"

_OBJECT = re.compile(
    r"\b(?:"
    r"(?P<mug>mugs?|cups?|кружек|чашек|кружк(?:а|и|у|ой|е|ами|ах)|чашк(?:а|и|у|ой|е|ами|ах))"
    r"|(?P<table>tables?|стол(?:ы|а|у|ом|е|ов|ами|ах)?)"
    r"|(?P<notebook>notebooks?|блокнот(?:ы|а|у|ом|е|ов|ами|ах)?|тетрад(?:ь|и|ью|ей|ями|ях))"
    r"|(?P<window>windows?|окн(?:о|а|у|ом|е|ами|ах)|окон)"
    r"|(?P<body>(?:human\s+)?body\s+parts?|arms?|legs?|feet|foot|faces?|ног(?:а|и|у|ой|е|ами|ах)|лиц(?:о|а|у|ом|е))"
    r"|(?P<human>human\s+presence|persons?|people|humans?|guests?|(?:distant|seated)\s+figures?|pedestrians?|человек(?:а|у|ом|е)?|люд(?:и|ей|ям|ьми|ях)|гост(?:и|ей|ям|ями|ях))"
    r"|(?P<hands>hands?|рук(?:а|и|у|ой|е|ами|ах))"
    r")\b", re.I,
)
_SHORE = r"берег(?:а|ом|е|ов|ам|ами|ах)?"
_COASTAL = re.compile(
    r"\b(?:"
    r"(?P<sandy>sandy\s+beach(?:es)?|песчан\w*\s+пляж(?:а|и|ей|ем|е)?)"
    r"|(?P<rocky>rocky\s+(?:coast(?:line)?|shore)s?|скалист\w*\s+(?:" + _SHORE + r"|побереж(?:ье|ья|ью|ьем)))"
    r"|(?P<beach>beach(?:es)?|пляж(?:а|и|ей|ем|е)?)"
    r"|(?P<water>oceans?|seas?|мор(?:е|я|ю|ем)|океан(?:а|у|ом|е|ы|ов)?)"
    r"|(?P<lagoon>lagoons?|bays?|лагун(?:а|ы|е|у|ой)?|бухт(?:а|ы|е|у|ой)?)"
    r"|(?P<coast>coast(?:s|al|line|lines)?|shore(?:s|line|lines)?|seaside|побереж(?:ье|ья|ью|ьем)|" + _SHORE + r"|tropical\s+islands?)"
    r")\b", re.I,
)


COASTAL_STYLES = {"sea_coast_photo", "bright_ocean_coast_photo"}
COASTAL_SCENES = {
    "sea_horizon", "coastal_morning", "beach_path", "dune_grass",
    "rocky_shore", "quiet_pier", "ocean_sunrise", "seaside_sunset",
    "quiet_beach_morning", "rocky_coast", "dunes_and_seabirds", "coastal_path",
    "bright_ocean_sunrise", "vivid_seaside_sunset", "sunny_beach_morning",
    "turquoise_shoreline", "rocky_ocean_coast", "seabirds_over_waves",
}


COASTAL_STYLE_DIRECTIONS = {
    "urban_city_photo": "realistic urban waterfront photography, coastal city promenade overlooking the sea, believable city details supporting the water view",
    "cafe_terrace_photo": "realistic seaside cafe terrace overlooking the ocean, cafe seating as supporting details, editorial cafe photography, water clearly visible",
    "rural_calm_photo": "realistic coastal village photography, village veranda or cottage garden overlooking the sea, grounded rural details supporting the water view",
    "calm_lifestyle_photo": "editorial coastal lifestyle photography, quiet coastal walk or balcony sea view, calm understated mood, authentic natural textures",
}


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

COAST_INCOMPATIBLE_STYLES = frozenset({
    "cozy_home_photo", "light_interior_photo", "book_nook_photo", "quiet_interior",
    "minimal_botanical", "mandala_harmony", "sacred_geometry_light", "botanical_mandala", "daily_symbol",
})
DEDICATED_BEACH_INCOMPATIBLE_STYLES = frozenset({
    "urban_city_photo", "cafe_terrace_photo", "rural_calm_photo",
})
# Exact contextual exception in coastal_intent.user_coastal_intent (FIX-03A).
# The isolated resolver applies it only to structurally positive context.
COASTAL_CONTEXT = re.compile(
    r"\b(?:caf[eé]|terrace|veranda|village|urban|city|waterfront|кафе|террас\w*|веранд\w*|деревн\w*|город\w*)\b",
    re.I,
)
ARTIFACT = re.compile(r"\b(?P<poster>posters?|постер(?:а|ы|у|ом|е)?|плакат(?:а|ы|у|ом|е)?)\b", re.I)
SCENE = re.compile(r"\b(?P<mountain>mountains?|гор(?:а|ы|у|ой|е|ами|ах))\b", re.I)
QUALIFIER = re.compile(
    r"\b(?:(?P<sunrise>sunrise|dawn|рассвет\w*|восход\w*)"
    r"|(?P<sunset>sunset|закат\w*)|(?P<morning>morning|утр\w*)"
    r"|(?P<evening>evening|dusk|вечер\w*|сумерк\w*)"
    r"|(?P<tropical>tropical|тропическ\w*)|(?P<palms>palms?|пальм\w*))\b", re.I,
)
NARRATIVE_HEADS = frozenset({
    "story", "stories", "report", "reports", "discussion", "discussions",
    "история", "историю", "истории", "рассказ", "рассказа", "отчет", "отчёт",
})
NONVISUAL_HEADS = frozenset({"time", "время", "времени"})


def normalize_style_key(style: str | None) -> str:
    return PHOTO_STYLE_ALIASES.get(style, style) if style else "auto"
