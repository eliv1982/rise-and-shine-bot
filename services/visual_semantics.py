"""Neutral SG-01 semantic data; no configuration, consumers or provider I/O.

Stage 1A data is unchanged. Stage 1B adds immutable registry contract TYPES only;
no production fragment, route policy or model capability is registered here.
"""
from dataclasses import dataclass
import re

from services.visual_safety_types import (
    FragmentRole, HumanPresence, PromptCapacity, SemanticKey,
    immutable_tuple, invalid_evidence, semantic_keys,
)

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


def _records(items, record_type):
    immutable_tuple(items)
    if any(type(item) is not record_type for item in items):
        invalid_evidence()


def _strings(*values):
    if any(not isinstance(value, str) or not value for value in values):
        invalid_evidence()


@dataclass(frozen=True, slots=True)
class ClosedSlotValue:
    value_id: str
    text: str
    positive_keys: frozenset[SemanticKey] = frozenset()
    excluded_keys: frozenset[SemanticKey] = frozenset()
    conditional_keys: frozenset[SemanticKey] = frozenset()

    def __post_init__(self):
        _strings(self.value_id, self.text)
        for keys in (self.positive_keys, self.excluded_keys, self.conditional_keys):
            semantic_keys(keys)


@dataclass(frozen=True, slots=True)
class RegisteredFragment:
    registry_id: str
    role: FragmentRole
    text: str
    positive_keys: frozenset[SemanticKey] = frozenset()
    excluded_keys: frozenset[SemanticKey] = frozenset()
    conditional_keys: frozenset[SemanticKey] = frozenset()
    slot_values: tuple[ClosedSlotValue, ...] = ()

    def __post_init__(self):
        _strings(self.registry_id, self.text)
        _records(self.slot_values, ClosedSlotValue)
        for keys in (self.positive_keys, self.excluded_keys, self.conditional_keys):
            semantic_keys(keys)
        if (self.role not in FragmentRole.__args__ or self.role == 'untrusted_prose'
                or len({s.value_id for s in self.slot_values}) != len(self.slot_values)
                or (bool(self.slot_values) != (self.text.count('{value}') == 1))
                or '{' in self.text.replace('{value}', '') or '}' in self.text.replace('{value}', '')):
            invalid_evidence()


@dataclass(frozen=True, slots=True)
class FragmentSelection:
    registry_id: str
    slot_value: str | None = None

    def __post_init__(self):
        _strings(self.registry_id)
        if self.slot_value is not None:
            _strings(self.slot_value)


@dataclass(frozen=True, slots=True)
class ProjectionBinding:
    key: SemanticKey
    selection: FragmentSelection

    def __post_init__(self):
        if type(self.key) is not tuple or len(self.key) != 2 or any(not isinstance(k, str) for k in self.key):
            invalid_evidence()
        semantic_keys(frozenset((self.key,)))
        if type(self.selection) is not FragmentSelection:
            invalid_evidence()


@dataclass(frozen=True, slots=True)
class PresenceBinding:
    presence: HumanPresence
    fragments: tuple[FragmentSelection, ...]

    def __post_init__(self):
        _records(self.fragments, FragmentSelection)
        if self.presence not in HumanPresence.__args__:
            invalid_evidence()


@dataclass(frozen=True, slots=True)
class ControlledContext:
    context_id: str
    requested_style: str
    resolved_style: str
    mode: str
    scene_type: str
    base_fragments: tuple[FragmentSelection, ...]
    presence_bindings: tuple[PresenceBinding, ...]
    default_human_presence: HumanPresence = 'none'
    required_keys: frozenset[SemanticKey] = frozenset()
    forbidden_keys: frozenset[SemanticKey] = frozenset()

    def __post_init__(self):
        _strings(self.context_id, self.requested_style, self.resolved_style, self.mode, self.scene_type)
        _records(self.base_fragments, FragmentSelection)
        _records(self.presence_bindings, PresenceBinding)
        semantic_keys(self.required_keys)
        semantic_keys(self.forbidden_keys)
        if (self.default_human_presence not in HumanPresence.__args__
                or len({p.presence for p in self.presence_bindings}) != len(self.presence_bindings)):
            invalid_evidence()


@dataclass(frozen=True, slots=True)
class SyntheticCapability:
    """Fake, offline evidence. It never verifies an actual provider contract."""
    capacity: PromptCapacity
    sizes: tuple[str, ...]

    def __post_init__(self):
        immutable_tuple(self.sizes)
        if type(self.capacity) is not PromptCapacity:
            invalid_evidence()
        _strings(*self.sizes)


@dataclass(frozen=True, slots=True)
class SyntheticRegistry:
    """Explicit synthetic authority, with no production counterpart/loader."""
    version: str
    fragments: tuple[RegisteredFragment, ...]
    positive_bindings: tuple[ProjectionBinding, ...]
    exclusion_bindings: tuple[ProjectionBinding, ...]
    contexts: tuple[ControlledContext, ...]
    capabilities: tuple[SyntheticCapability, ...]

    def __post_init__(self):
        _strings(self.version)
        for items, cls in ((self.fragments, RegisteredFragment), (self.positive_bindings, ProjectionBinding),
                           (self.exclusion_bindings, ProjectionBinding), (self.contexts, ControlledContext),
                           (self.capabilities, SyntheticCapability)):
            _records(items, cls)
        for values in (tuple(f.registry_id for f in self.fragments),
                       tuple(c.context_id for c in self.contexts),
                       tuple(b.key for b in self.positive_bindings),
                       tuple(b.key for b in self.exclusion_bindings),
                       tuple((c.capacity.adapter_id, c.capacity.model) for c in self.capabilities)):
            if len(set(values)) != len(values):
                invalid_evidence()


@dataclass(frozen=True, slots=True)
class SyntheticPolicy:
    policy_version: str
    selection_rule_id: str
    registry_version: str
    context_ids: tuple[str, ...]
    covered_keys: frozenset[SemanticKey]

    def __post_init__(self):
        _strings(self.policy_version, self.selection_rule_id, self.registry_version)
        immutable_tuple(self.context_ids)
        _strings(*self.context_ids)
        semantic_keys(self.covered_keys)
