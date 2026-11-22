"""Small RU/EN coastal vocabulary and exclusions, not a general language parser.

Only current user scene text (and notes for a selected custom style) belongs in
user_coastal_intent. Generated hints, prompts and avoid lists are not user intent.
"""

import re
from dataclasses import dataclass

from services.visual_semantics import (
    COASTAL_STYLES, COASTAL_SCENES, COASTAL_STYLE_DIRECTIONS,
    COAST_INCOMPATIBLE_STYLES, DEDICATED_BEACH_INCOMPATIBLE_STYLES,
    COASTAL_CONTEXT,
)
from services.visual_constraints import (
    _continues_exclusion_list, _nominal_list_fragment, compatible_custom_style_prose,
)



# Longest phrases first; shoreline noun endings exclude the verbs «берегу»,
# «береги», «берегите». Word boundaries exclude research, seasonal and seated.
_SHORE = r"берег(?:а|ом|е|ов|ам|ами|ах)?"
_SUBJECT = re.compile(
    r"\b(?P<sandy>sandy\s+beach(?:es)?|песчан\w*\s+пляж(?:а|и|ей|ем|е)?)\b"
    r"|\b(?P<rocky>rocky\s+(?:coast(?:line)?|shore)(?:s)?|скалист\w*\s+(?:" + _SHORE + r"|берегу|побереж(?:ье|ья|ью|ьем)))\b"
    r"|\b(?P<beach>beach(?:es)?|пляж(?:а|и|ей|ем|е)?)\b"
    r"|\b(?P<water>ocean(?:s)?|sea(?:s)?|мор(?:е|я|ю|ем)|океан(?:а|у|ом|е|ы|ов)?)\b"
    r"|\b(?P<lagoon>lagoon(?:s)?|bay(?:s)?|лагун(?:а|ы|е|у|ой)|бухт(?:а|ы|е|у|ой))\b"
    r"|\b(?P<coast>coast(?:s|al|line|lines)?|shore(?:s|line|lines)?|seaside|"
    r"побереж(?:ье|ья|ью|ьем)|" + _SHORE + r"|(?:на|к|по)\s+берегу|tropical\s+island(?:s)?)\b",
    re.IGNORECASE,
)
_NEGATION = re.compile(
    r"\b(?:avoid|no|without|exclude|excluding|not|(?:do\s+not|don['’]t)(?:\s+(?:show|include))?|"
    r"без|не\s+хочу|не\s+показыва(?:й(?:те)?|ть)|избега(?:й(?:те)?|ть)|исключи(?:те|ть)?|нет)\b",
    re.IGNORECASE,
)
# Negation wins at the same position (e.g. "do not show", «не хочу»).
# Coordinating conjunctions alone do not end an exclusion list.
_SCOPE_MARKER = re.compile(
    r"(?P<negative>" + _NEGATION.pattern + r")"
    r"|(?P<positive>\b(?:show|include|i\s+want|хочу|покажи|покажите)\b)"
    r"|(?P<comma>,)|(?P<reset>[.;!?\n]+|\b(?:but|но)\b)",
    re.IGNORECASE,
)
_LIST_NEGATION = re.compile(r"^\s*(?:avoid|exclude|excluding|избега(?:й(?:те)?|ть)|исключи(?:те|ть)?)\b", re.IGNORECASE)

# Only explicit coastal requests use these small lighting/setting qualifiers.
# They do not add coastal vocabulary or infer scenes from generated prompts.
_COASTAL_TIMES = {
    "sunrise": r"\b(?:sunrise|dawn|рассвет\w*|восход\w*)\b",
    "sunset": r"\b(?:sunset|закат\w*)\b",
    "morning": r"\b(?:morning|утр\w*)\b",
    "evening": r"\b(?:evening|dusk|вечер\w*|сумерк\w*)\b",
}


def _scoped_fragments(text: str | None):
    """Yield positive/exclusion spans using a deliberately small RU/EN grammar.

    No/without/без coastal scope ends at a comma. Noncoastal nominal exclusions
    retain the shared object-list scope so they cannot become positive prose.
    Avoid/exclude can introduce a coastal list across commas, but an unrelated
    exclusion ("Avoid crowds") cannot.
    An explicit positive directive always ends that list, including after and/и.
    """
    text = text or ""
    start, negative, coastal_list = 0, False, False
    for marker in _SCOPE_MARKER.finditer(text):
        fragment = text[start:marker.start()].strip(" ,;\t")
        if marker.lastgroup in {"negative", "positive"}:
            if fragment:
                yield fragment, negative
            negative = marker.lastgroup == "negative"
            coastal_list = negative and bool(_LIST_NEGATION.match(marker.group()))
            start = marker.start()
        else:
            if fragment:
                yield fragment, negative
            next_marker = _SCOPE_MARKER.search(text, marker.end())
            continuation = text[marker.end():next_marker.start() if next_marker else len(text)]
            nominal_list = (
                _nominal_list_fragment(fragment)
                and not _SUBJECT.search(continuation)
                and _continues_exclusion_list(text, marker.end())
            )
            negative = bool(marker.lastgroup == "comma" and negative and (
                (coastal_list and _SUBJECT.search(fragment)) or nominal_list
            ))
            coastal_list = coastal_list and negative
            start = marker.end()
    if tail := text[start:].strip(" ,;\t"):
        yield tail, negative


@dataclass(frozen=True)
class CoastalIntent:
    positive: frozenset[str] = frozenset()
    excluded: frozenset[str] = frozenset()
    time_of_day: str | None = None
    dedicated_beach: bool = False

    @property
    def blocks_coast(self) -> bool:
        return bool(self.excluded & {"water", "coast"})

    @property
    def wants_coast(self) -> bool:
        return not self.blocks_coast and bool(self.positive - self.excluded - (
            {"sandy"} if "beach" in self.excluded else set()
        ))

    @property
    def subtype(self) -> str:
        if "lagoon" in self.positive and "lagoon" not in self.excluded:
            return "lagoon"
        if self.positive & {"sandy", "beach"} and not self.excluded & {"sandy", "beach"}:
            return "beach"
        if "rocky" in self.positive and "rocky" not in self.excluded:
            return "rocky"
        if self.excluded & {"beach", "sandy", "rocky"}:
            # An ocean request with an excluded shore subtype is still water;
            # the exclusion is not evidence for another positive shore subtype.
            return "water"
        return "coast"

    def exclusion_clause(self) -> str:
        labels = {"water": "ocean or sea", "coast": "coastline or shoreline",
                  "beach": "beach", "sandy": "sandy beach", "rocky": "rocky coast",
                  "lagoon": "lagoon or bay"}
        parts = [f"no {labels[key]}" for key in sorted(self.excluded)]
        return "Scene exclusions: " + ", ".join(parts) + "." if parts else ""


def parse_coastal_text(text: str | None) -> CoastalIntent:
    """Classify coastal mentions; callers retain ownership of the text's source."""
    positive, excluded = set(), set()
    for fragment, negative in _scoped_fragments(text):
        for match in _SUBJECT.finditer(fragment):
            target = excluded if negative else positive
            target.add(match.lastgroup)
    return CoastalIntent(frozenset(positive), frozenset(excluded))


def user_coastal_intent(
    user_text: str | None, *, style: str | None = None,
    custom_style_description: str | None = None,
) -> CoastalIntent:
    request = parse_coastal_text(user_text)
    notes = parse_coastal_text(custom_style_description if style == "custom" else None)
    intent = CoastalIntent(request.positive | notes.positive, request.excluded | notes.excluded)
    positive, _ = user_scene_prompt_parts(
        user_text, style=style, custom_style_description=custom_style_description, intent=intent,
    )
    time_of_day = next((key for key, pattern in _COASTAL_TIMES.items() if re.search(pattern, positive, re.IGNORECASE)), None)
    dedicated_beach = bool(
        intent.subtype == "beach"
        and re.search(r"\b(?:tropical|palms?|palm\s+trees|тропическ\w*|пальм\w*)\b", positive, re.IGNORECASE)
        and not COASTAL_CONTEXT.search(positive)
    )
    return CoastalIntent(intent.positive, intent.excluded, time_of_day, dedicated_beach)


def coastal_request_text(
    user_text: str | None, *, style: str | None = None,
    custom_style_description: str | None = None,
) -> str:
    positive, _ = user_scene_prompt_parts(
        user_text, style=style, custom_style_description=custom_style_description,
        coastal_only=True,
    )
    return positive


def user_scene_prompt_parts(
    user_text: str | None, *, style: str | None = None,
    custom_style_description: str | None = None, coastal_only: bool = False,
    intent: CoastalIntent | None = None,
) -> tuple[str, str]:
    """Keep mixed user expressions out of unconditional positive directives."""
    intent = intent or user_coastal_intent(user_text, style=style, custom_style_description=custom_style_description)
    forbidden = set(intent.excluded)
    if "beach" in forbidden:
        forbidden.add("sandy")
    if intent.blocks_coast:
        forbidden.update({"water", "coast", "beach", "sandy", "rocky", "lagoon"})
    sources = [user_text, custom_style_description if style == "custom" else None]
    positive, negative = [], []
    for source in sources:
        for fragment, excluded in _scoped_fragments(source):
            subjects = parse_coastal_text(fragment).positive
            if excluded:
                # Joining list members with semicolons must not erase the
                # negative scope carried by their original comma boundaries.
                negative.append(fragment if _NEGATION.match(fragment) else
                                "Avoid " + compatible_custom_style_prose(fragment, ()))
            elif not subjects & forbidden and (subjects or not coastal_only):
                positive.append(fragment)
    if coastal_only and not positive and intent.wants_coast:
        # Conflicting coordinated requests may share one fragment. Keep only
        # the supported categories instead of reintroducing an excluded noun.
        labels = {"water": "ocean or sea view", "coast": "coastline", "beach": "beach",
                  "sandy": "sandy beach", "rocky": "rocky coast", "lagoon": "lagoon or bay"}
        positive = [labels[key] for key in sorted(intent.positive - forbidden)]
    return "; ".join(positive), "; ".join(negative)


def coastal_style_conflict(requested_style: str, intent: CoastalIntent, *, visual_mode: str = "photo") -> bool:
    """Clearly incompatible explicit scene families; auto styles stay flexible."""
    from services.ritual_config import normalize_style_key
    if visual_mode == "symbolic":
        return False
    requested_style = normalize_style_key(requested_style)
    return bool(
        (requested_style in COASTAL_STYLES and intent.blocks_coast)
        or (intent.wants_coast and requested_style in COAST_INCOMPATIBLE_STYLES)
        or (intent.wants_coast and intent.dedicated_beach and requested_style in DEDICATED_BEACH_INCOMPATIBLE_STYLES)
    )


def coastal_style_direction(style: str | None, intent: CoastalIntent) -> str | None:
    direction = COASTAL_STYLE_DIRECTIONS.get(style) if intent.wants_coast else None
    if direction and intent.subtype == "lagoon":
        direction = direction.replace("the ocean", "the requested lagoon or bay").replace(
            "the sea", "the requested lagoon or bay",
        ).replace("sea view", "lagoon or bay view")
    return direction


def coastal_time_hint(hint: str | None, intent: CoastalIntent) -> str | None:
    """Keep automatic palette/framing prose consistent with explicit lighting."""
    if hint and intent.time_of_day:
        for pattern in _COASTAL_TIMES.values():
            hint = re.sub(pattern, intent.time_of_day, hint, flags=re.IGNORECASE)
    return hint


def coastal_time_conflict(text: str, intent: CoastalIntent) -> bool:
    if not intent.time_of_day:
        return False
    opposite = {"sunset", "evening"} if intent.time_of_day in {"sunrise", "morning"} else {"sunrise", "morning"}
    return any(
        re.search(_COASTAL_TIMES[key], fragment, re.IGNORECASE)
        for fragment, negative in _scoped_fragments(text) if not negative
        for key in opposite
    )


def coastal_composition_hint(hint: str | None) -> str | None:
    """Discard clearly indoor automatic framing when a coast already owns the scene."""
    if hint and re.search(r"\b(?:interior|workspace|desk|still life|window|doorway|table)\b", hint, re.IGNORECASE):
        return "open coastal composition with clear depth and a readable horizon"
    return hint


def coastal_photo_style(
    requested_style: str, resolved_style: str, intent: CoastalIntent, *, visual_mode: str = "photo",
) -> str:
    if coastal_style_conflict(requested_style, intent, visual_mode=visual_mode):
        raise ValueError("Selected style conflicts with the explicit coastal exclusion or scene request")
    if intent.blocks_coast and resolved_style in COASTAL_STYLES:
        return "living_nature_photo"
    if requested_style in {"auto", "random_suitable", "random"} and resolved_style in COASTAL_STYLES and intent.excluded and not intent.wants_coast:
        return "living_nature_photo"
    if intent.wants_coast and requested_style in {"auto", "random_suitable", "random"}:
        if visual_mode == "photo":
            return "sea_coast_photo"
        if coastal_style_conflict(resolved_style, intent, visual_mode=visual_mode):
            return "bright_nature_card"
    return resolved_style
