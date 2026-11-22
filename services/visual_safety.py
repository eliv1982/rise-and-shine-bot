"""SG-01 Stage 1A: pure interpretation resolution, NOT provider certification.

There is deliberately no preflight/assembly/dispatch validator, renderer or
route selector here. An allowed interpretation cannot authorize generation.
"""
from dataclasses import dataclass, fields, is_dataclass, replace
from enum import Enum
import hashlib
import json
from typing import Literal

from services.directive_segments import Polarity, SourceKind
from services.visual_intent import FactDomain, VisualInterpretation, validate_interpretation
from services.visual_semantics import (
    COASTAL_STYLES, COAST_INCOMPATIBLE_STYLES, DEDICATED_BEACH_INCOMPATIBLE_STYLES,
    POLICY_VERSION, VOCABULARY_VERSION, REGISTRY_VERSION, normalize_style_key,
    COASTAL_CONTEXT, NARRATIVE_HEADS, NONVISUAL_HEADS,
)
from services.visual_safety_types import (
    DirectiveRef, SafetyFailureData, ValidationIssue, ValidationResult,
    VisualSafetyFailure, immutable_tuple, invalid_evidence,
)

ConstraintDomain = FactDomain | Literal['system']
FactKey = tuple[ConstraintDomain, str]
RequestDisposition = Literal['none', 'eligible', 'unsupported', 'mixed']


@dataclass(frozen=True, slots=True)
class ResolvedFact:
    domain: FactDomain
    key: str
    polarity: Literal[Polarity.POSITIVE, Polarity.NEGATIVE]
    fact_indices: tuple[int, ...]

    def __post_init__(self):
        immutable_tuple(self.fact_indices)


@dataclass(frozen=True, slots=True)
class VisualConflict:
    kind: Literal['object', 'coastal', 'style', 'human_presence', 'scene']
    keys: frozenset[FactKey]
    evidence_refs: tuple[DirectiveRef, ...]
    candidate_field: str | None
    resolution: Literal['blocked', 'exclusion_wins', 'soft_default_removed']

    def __post_init__(self):
        immutable_tuple(self.evidence_refs)
        if not isinstance(self.keys, frozenset):
            invalid_evidence()


@dataclass(frozen=True, slots=True)
class MandatoryBan:
    domain: ConstraintDomain
    key: str
    evidence_refs: tuple[DirectiveRef, ...]
    causes: tuple[str, ...]

    def __post_init__(self):
        immutable_tuple(self.evidence_refs)
        immutable_tuple(self.causes)
        if not self.causes or any(c not in {'USER_EXCLUSION', 'HUMAN_EXCLUSION_CASCADE',
                'COASTAL_EXCLUSION_CASCADE', 'SCENE_HUMAN_NONE', 'SELECTED_STYLE_CONSTRAINT', 'SYSTEM_NO_TEXT'} for c in self.causes):
            invalid_evidence()


@dataclass(frozen=True, slots=True)
class EnforcementRoute:
    kind: Literal['fully_controlled', 'bounded_untrusted']
    source_snapshot_digest: str
    selection_rule_id: str
    policy_version: str
    bounded_standard_ids: tuple[str, ...]
    selected_before_enrichment: Literal[True]

    def __post_init__(self):
        immutable_tuple(self.bounded_standard_ids)
        if self.kind not in {'fully_controlled', 'bounded_untrusted'} or self.selected_before_enrichment is not True:
            invalid_evidence()


@dataclass(frozen=True, slots=True)
class ResolvedVisualIntent:
    interpretation: VisualInterpretation
    requested_style: str
    requested_mode: str
    disposition: RequestDisposition
    effective_facts: tuple[ResolvedFact, ...]
    mandatory_bans: tuple[MandatoryBan, ...]
    conflicts: tuple[VisualConflict, ...]
    enforcement_route: EnforcementRoute | None
    resolution_digest: str
    policy_version: str
    vocabulary_version: str
    registry_version: str

    def __post_init__(self):
        for items in (self.effective_facts, self.mandatory_bans, self.conflicts):
            immutable_tuple(items)
        for fact in self.effective_facts:
            immutable_tuple(fact.fact_indices)
        for ban in self.mandatory_bans:
            immutable_tuple(ban.evidence_refs)
            immutable_tuple(ban.causes)
        for conflict in self.conflicts:
            immutable_tuple(conflict.evidence_refs)
            if not isinstance(conflict.keys, frozenset):
                invalid_evidence()

    def _keys(self, domain, polarity):
        return frozenset(f.key for f in self.effective_facts if f.domain == domain and f.polarity == polarity)

    @property
    def required_objects(self):
        return self._keys(FactDomain.OBJECT, Polarity.POSITIVE)

    @property
    def excluded_objects(self):
        return frozenset(b.key for b in self.mandatory_bans if b.domain == FactDomain.OBJECT)

    @property
    def positive_coastal(self):
        return self._keys(FactDomain.COASTAL, Polarity.POSITIVE)

    @property
    def excluded_coastal(self):
        return frozenset(b.key for b in self.mandatory_bans if b.domain == FactDomain.COASTAL)

    @property
    def time_of_day(self):
        return next((key for key in ('sunrise', 'sunset', 'morning', 'evening')
                     if key in self._keys(FactDomain.QUALIFIER, Polarity.POSITIVE)), None)

    @property
    def dedicated_beach(self):
        return _dedicated_beach(self.interpretation, self.positive_coastal,
                               self._keys(FactDomain.QUALIFIER, Polarity.POSITIVE), self.excluded_coastal)


def _canonical(value):
    if is_dataclass(value):
        return {f.name: _canonical(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (tuple, list)):
        return [_canonical(v) for v in value]
    if isinstance(value, frozenset):
        return sorted((_canonical(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True))
    return value


def _digest(resolution):
    data = _canonical(resolution)
    data.pop('resolution_digest')
    # Views are derived, but bind their exact contents too, as specified.
    data['unresolved_negatives'] = _canonical(resolution.interpretation.unresolved_negatives)
    data['unsupported_requests'] = _canonical(resolution.interpretation.unsupported_requests)
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def _refs(interpretation, indices):
    return tuple(sorted({(interpretation.facts[i].source_id, interpretation.facts[i].directive_id) for i in indices}))


def _closure(domain, key):
    """The single closure definition for the new layer (legacy runtime isolated)."""
    if domain == FactDomain.OBJECT and key == 'human':
        return ('human', 'hands', 'body'), 'HUMAN_EXCLUSION_CASCADE'
    if domain == FactDomain.COASTAL:
        if key in {'water', 'coast'}:
            return ('water', 'coast', 'beach', 'sandy', 'rocky', 'lagoon'), 'COASTAL_EXCLUSION_CASCADE'
        if key == 'beach':
            return ('beach', 'sandy'), 'COASTAL_EXCLUSION_CASCADE'
    return (key,), None


def _dedicated_beach(interpretation, coastal, qualifiers, excluded):
    # Preserve the production beach-subtype predicate, including lagoon priority.
    if not (coastal & {'beach', 'sandy'} and not coastal & {'lagoon'}
            and not excluded & {'beach', 'sandy'} and qualifiers & {'tropical', 'palms'}):
        return False
    classifications = {c.ref: c for c in interpretation.classifications}
    for segmented in interpretation.segmentations:
        source = segmented.source
        if not source.active or source.kind not in {SourceKind.USER_TEXT, SourceKind.CUSTOM_NOTES}:
            continue
        for directive, structure in zip(segmented.directives, segmented.structure):
            classification = classifications[(source.source_id, directive.directive_id)]
            if (classification.request_class not in {'eligible', 'nonvisual'}
                    or directive.polarity == Polarity.NEGATIVE
                    or (directive.polarity == Polarity.UNSPECIFIED
                        and segmented.scopes[directive.scope_id].polarity == Polarity.NEGATIVE)
                    or structure.uncertain or structure.frame not in {'nominal', 'render_complement'}
                    or structure.nominal_span is None):
                continue
            head = structure.head_span.extract(source.text).casefold() if structure.head_span else ''
            if head in NARRATIVE_HEADS | NONVISUAL_HEADS | {'read', 'discuss'}:
                continue
            governor = structure.governing_directive_id
            if (classification.request_class == 'nonvisual' and governor is not None
                    and segmented.structure[governor].relations):
                continue  # an owned mention is not independent contextual intent
            if COASTAL_CONTEXT.search(structure.nominal_span.extract(source.text)):
                return False
    return True


def resolve_visual_intent(
    interpretation: VisualInterpretation, *, requested_style: str = 'auto',
    requested_mode: str = 'illustration', policy_version: str = POLICY_VERSION,
    vocabulary_version: str = VOCABULARY_VERSION, enforcement_policy=None,
) -> ResolvedVisualIntent:
    """Resolve only interpretation policy. Route/capacity enforcement is deferred."""
    validate_interpretation(interpretation)
    if (policy_version != POLICY_VERSION or vocabulary_version != VOCABULARY_VERSION
            or enforcement_policy is not None or not isinstance(requested_style, str)
            or not isinstance(requested_mode, str)):
        invalid_evidence()
    # Activity belongs to the requested style, never an automatically chosen one.
    if any(s.source.kind == SourceKind.CUSTOM_NOTES and s.source.active != (requested_style == 'custom')
           for s in interpretation.segmentations):
        invalid_evidence()
    grouped = {}
    resolved_negatives = {i for n in interpretation.negatives if n.classification == 'resolved' for i in n.fact_indices}
    for i, fact in enumerate(interpretation.facts):
        if fact.eligible and (fact.polarity == Polarity.POSITIVE or i in resolved_negatives):
            grouped.setdefault((fact.domain, fact.key, fact.polarity), []).append(i)
    bans = {}
    for (domain, key, polarity), indices in grouped.items():
        if polarity != Polarity.NEGATIVE:
            continue
        keys, cascade = _closure(domain, key)
        for ban_key in keys:
            refs, causes = bans.setdefault((domain, ban_key), (set(), set()))
            refs.update(_refs(interpretation, indices))
            causes.add('USER_EXCLUSION')
            if cascade and ban_key != key:
                causes.add(cascade)
    mandatory = tuple(MandatoryBan(domain, key, tuple(sorted(refs)), tuple(sorted(causes)))
                      for (domain, key), (refs, causes) in sorted(bans.items()))
    conflicts, suppressed = [], set()
    for (domain, key, polarity), indices in grouped.items():
        if polarity != Polarity.POSITIVE or (domain, key) not in bans:
            continue
        refs = tuple(sorted(set(_refs(interpretation, indices)) | bans[(domain, key)][0]))
        coastal = domain == FactDomain.COASTAL
        conflicts.append(VisualConflict('coastal' if coastal else 'object', frozenset({(domain, key)}),
                                        refs, None, 'exclusion_wins' if coastal else 'blocked'))
        if coastal:
            suppressed.add((domain, key, polarity))
    effective = [ResolvedFact(domain, key, polarity, tuple(indices))
                 for (domain, key, polarity), indices in sorted(grouped.items())
                 if (domain, key, polarity) not in suppressed]
    # A lighting/palm qualifier cannot survive the suppression of its subject.
    subject_refs = {ref for f in effective if f.polarity == Polarity.POSITIVE
                    and f.domain in {FactDomain.COASTAL, FactDomain.SCENE, FactDomain.ARTIFACT, FactDomain.OBJECT}
                    for ref in _refs(interpretation, f.fact_indices)}
    def qualifier_has_subject(fact):
        for i in fact.fact_indices:
            evidence = interpretation.facts[i]
            segmentation = next(s for s in interpretation.segmentations if s.source.source_id == evidence.source_id)
            structure = segmentation.structure[evidence.directive_id]
            if (evidence.source_id, evidence.directive_id) in subject_refs:
                return True
            if (evidence.source_id, structure.governing_directive_id) in subject_refs:
                return True
        return False
    effective = tuple(f for f in effective if f.domain != FactDomain.QUALIFIER or qualifier_has_subject(f))
    coastal = {f.key for f in effective if f.domain == FactDomain.COASTAL and f.polarity == Polarity.POSITIVE}
    qualifiers = {f.key for f in effective if f.domain == FactDomain.QUALIFIER and f.polarity == Polarity.POSITIVE}
    style = normalize_style_key(requested_style)
    style_conflict = requested_mode != 'symbolic' and (
        style in COASTAL_STYLES and any((FactDomain.COASTAL, key) in bans for key in ('water', 'coast'))
        or bool(coastal) and style in COAST_INCOMPATIBLE_STYLES
        or _dedicated_beach(interpretation, coastal, qualifiers,
                            {b.key for b in mandatory if b.domain == FactDomain.COASTAL})
        and style in DEDICATED_BEACH_INCOMPATIBLE_STYLES)
    if style_conflict:
        indices = [i for i, f in enumerate(interpretation.facts) if f.eligible and f.domain == FactDomain.COASTAL]
        conflicts.append(VisualConflict('style', frozenset((FactDomain.COASTAL, k) for k in coastal | {
            b.key for b in mandatory if b.domain == FactDomain.COASTAL}), _refs(interpretation, indices),
            'selected_style', 'blocked'))
    eligible = any(c.request_class == 'eligible' and any(interpretation.facts[i].eligible
                   and interpretation.facts[i].polarity == Polarity.POSITIVE for i in c.fact_indices)
                   for c in interpretation.classifications)
    unsupported = bool(interpretation.unsupported_requests)
    disposition = 'mixed' if eligible and unsupported else 'eligible' if eligible else 'unsupported' if unsupported else 'none'
    result = ResolvedVisualIntent(interpretation, requested_style, requested_mode, disposition,
                                  effective, mandatory, tuple(sorted(conflicts, key=lambda c: (c.kind, c.evidence_refs))),
                                  None, '', policy_version, vocabulary_version, REGISTRY_VERSION)
    return replace(result, resolution_digest=_digest(result))


def check_interpretation(resolution: ResolvedVisualIntent) -> ValidationResult:
    """Stage 1A verdict only. It is never a V1 preflight or a dispatch seal."""
    validate_interpretation(resolution.interpretation)
    if resolution.enforcement_route is not None or resolution.resolution_digest != _digest(resolution):
        invalid_evidence()
    issues = [ValidationIssue('UNRESOLVED_EXCLUSION', 'interpretation', (n.ref,), (), n.detail)
              for n in resolution.interpretation.unresolved_negatives]
    if resolution.disposition == 'unsupported':
        issues.append(ValidationIssue('UNSUPPORTED_VISUAL_REQUEST', 'interpretation',
                                      tuple(r.ref for r in resolution.interpretation.unsupported_requests)))
    codes = {'object': 'OBJECT_CONFLICT', 'coastal': 'COASTAL_CONFLICT', 'style': 'STYLE_CONFLICT',
             'human_presence': 'HUMAN_PRESENCE_CONFLICT', 'scene': 'SCENE_CONFLICT'}
    issues.extend(ValidationIssue(codes[c.kind], 'interpretation', c.evidence_refs)
                  for c in resolution.conflicts if c.resolution == 'blocked')
    issues = tuple(sorted(issues, key=lambda i: (i.stage, i.code, i.evidence_refs, i.fragment_indices)))
    return ValidationResult('blocked' if issues else 'allowed', 'interpretation', issues, resolution.resolution_digest)


def require_valid_interpretation(resolution: ResolvedVisualIntent) -> ResolvedVisualIntent:
    result = check_interpretation(resolution)
    if result.outcome == 'blocked':
        codes = {i.code for i in result.issues}
        key = ('visual_exclusion_unresolved' if 'UNRESOLVED_EXCLUSION' in codes else
               'visual_request_unsupported' if 'UNSUPPORTED_VISUAL_REQUEST' in codes else 'visual_constraints_conflict')
        raise VisualSafetyFailure(SafetyFailureData(result, key))
    return resolution
