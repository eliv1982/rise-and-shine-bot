"""Isolated SG-01 interpretation and synthetic offline assembly validation.

No production registry, route approval, capability or dispatch authority exists
here. Stage 1A's public interpretation contract retains enforcement_route=None.
"""
from dataclasses import dataclass, fields, is_dataclass, replace
from enum import Enum
import hashlib
import json
from typing import Literal

from services.directive_segments import Polarity, SourceKind, Span
from services.visual_intent import FactDomain, VisualInterpretation, validate_interpretation
from services.visual_semantics import (
    COASTAL_STYLES, COAST_INCOMPATIBLE_STYLES, DEDICATED_BEACH_INCOMPATIBLE_STYLES,
    POLICY_VERSION, VOCABULARY_VERSION, REGISTRY_VERSION, normalize_style_key,
    COASTAL_CONTEXT, NARRATIVE_HEADS, NONVISUAL_HEADS,
    SyntheticRegistry, SyntheticPolicy, FragmentSelection,
)
from services.visual_safety_types import (
    DirectiveRef, SafetyFailureData, ValidationIssue, ValidationResult,
    VisualSafetyFailure, immutable_tuple, invalid_evidence,
    PromptCapacity, FragmentProvenance, PromptFragment, HumanPresence, safety_failure,
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
        if (any(type(f) is not ResolvedFact for f in self.effective_facts)
                or any(type(b) is not MandatoryBan for b in self.mandatory_bans)
                or any(type(c) is not VisualConflict for c in self.conflicts)):
            invalid_evidence()
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
    return _hash_record(data)


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
    if type(resolution) is not ResolvedVisualIntent:
        invalid_evidence()
    expected = resolve_visual_intent(
        resolution.interpretation, requested_style=resolution.requested_style,
        requested_mode=resolution.requested_mode, policy_version=resolution.policy_version,
        vocabulary_version=resolution.vocabulary_version,
    )
    if resolution != expected:
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


@dataclass(frozen=True, slots=True)
class PreflightEvidence:
    """Only the issuing gate's exact receipt can bind its candidate."""
    validation: ValidationResult
    authority_digest: str
    capacity: PromptCapacity
    adapter_id: str
    model: str
    size: str

    def __post_init__(self):
        if (type(self.validation) is not ValidationResult or self.validation.outcome != 'allowed'
                or self.validation.stage != 'preflight' or type(self.capacity) is not PromptCapacity
                or any(not isinstance(s, str) or not s for s in (
                    self.authority_digest, self.adapter_id, self.model, self.size))):
            invalid_evidence('preflight')


@dataclass(frozen=True, slots=True)
class PromptCandidate:
    resolution: ResolvedVisualIntent
    fragments: tuple[PromptFragment, ...]
    scene_type: str
    human_presence: HumanPresence
    resolved_style: str
    effective_mode: str
    trace: str
    preflight: PreflightEvidence
    optional_selections: tuple[FragmentSelection, ...] = ()

    def __post_init__(self):
        immutable_tuple(self.fragments)
        immutable_tuple(self.optional_selections)
        if (type(self.resolution) is not ResolvedVisualIntent
                or type(self.preflight) is not PreflightEvidence
                or any(type(f) is not PromptFragment for f in self.fragments)
                or any(type(s) is not FragmentSelection for s in self.optional_selections)
                or self.human_presence not in HumanPresence.__args__
                or any(not isinstance(s, str) for s in (
                    self.scene_type, self.resolved_style, self.effective_mode, self.trace))):
            invalid_evidence('candidate')


@dataclass(frozen=True, slots=True)
class FinalAssembly:
    candidate: PromptCandidate
    enforcement_route: EnforcementRoute
    prompt: str
    fragment_spans: tuple[Span, ...]
    mandatory_bans: tuple[MandatoryBan, ...]
    capacity: PromptCapacity
    model: str
    adapter_id: str
    size: str
    policy_version: str
    registry_version: str
    authority_digest: str

    def __post_init__(self):
        immutable_tuple(self.fragment_spans)
        immutable_tuple(self.mandatory_bans)
        if (type(self.candidate) is not PromptCandidate
                or type(self.enforcement_route) is not EnforcementRoute
                or type(self.capacity) is not PromptCapacity
                or any(type(s) is not Span for s in self.fragment_spans)
                or any(type(b) is not MandatoryBan for b in self.mandatory_bans)
                or any(not isinstance(s, str) for s in (
                    self.prompt, self.model, self.adapter_id, self.size,
                    self.policy_version, self.registry_version, self.authority_digest))):
            invalid_evidence('final')


_FACTORY_KEY = object()


@dataclass(frozen=True, slots=True, init=False)
class SyntheticValidatedAssembly:
    """Offline-only result, deliberately distinct from future dispatch authority.

    Private construction/identity checks are internal API boundaries, not a
    sandbox against malicious Python code with access to this module's internals.
    """
    assembly: FinalAssembly
    validation: ValidationResult
    assembly_digest: str

    def __init__(self, assembly, validation, *, _key=None):
        if _key is not _FACTORY_KEY:
            invalid_evidence('final')
        object.__setattr__(self, 'assembly', assembly)
        object.__setattr__(self, 'validation', validation)
        object.__setattr__(self, 'assembly_digest', validation.assembly_digest)

    @property
    def authority(self) -> Literal['synthetic_offline']:
        return 'synthetic_offline'

    @property
    def production_authorized(self) -> Literal[False]:
        return False


def _hash_record(value):
    try:
        encoded = json.dumps(_canonical(value), ensure_ascii=False, sort_keys=True,
                             separators=(',', ':')).encode('utf-8')
    except UnicodeEncodeError:
        invalid_evidence()
    return hashlib.sha256(encoded).hexdigest()


def _result(stage, digest, issues=(), assembly_digest=None):
    ordered = tuple(sorted(set(issues), key=lambda i: (
        i.stage, i.code, i.evidence_refs, i.fragment_indices, i.detail or '')))
    return ValidationResult('blocked' if ordered else 'allowed', stage, ordered, digest, assembly_digest)


def _veto(code, stage, digest='', refs=()):
    safety_failure(_result(stage, digest, (ValidationIssue(code, stage, refs),)))


def _serialize(fragments):
    """The entire offline wire format: exact fragments separated by one LF."""
    spans, position = [], 0
    for fragment in fragments:
        spans.append(Span(position, position + len(fragment.text)))
        position += len(fragment.text) + 1
    return '\n'.join(f.text for f in fragments), tuple(spans)


def _measure(prompt, capacity):
    if capacity.unit == 'unicode_codepoints' and capacity.counter_version == 'python-len-v1':
        return len(prompt)
    if capacity.unit == 'utf8_bytes' and capacity.counter_version == 'utf8-v1':
        try:
            return len(prompt.encode('utf-8'))
        except UnicodeEncodeError:
            invalid_evidence()
    return None  # No tokenizer or unverified counter is invented here.


def _assembly_bans(resolution, context, human_presence):
    """One constraint owner, reusing the SAME closure as interpretation."""
    entries = {}
    for ban in resolution.mandatory_bans:
        entries[(ban.domain, ban.key)] = (set(ban.evidence_refs), set(ban.causes))
    seeds = [(domain, key, 'SELECTED_STYLE_CONSTRAINT') for domain, key in context.forbidden_keys]
    if human_presence == 'none':
        seeds.append((FactDomain.OBJECT, 'human', 'SCENE_HUMAN_NONE'))
    seeds.append(('system', 'text_marks', 'SYSTEM_NO_TEXT'))
    for domain, key, cause in seeds:
        keys, _ = _closure(domain, key)
        for closed_key in keys:
            _, causes = entries.setdefault((domain, closed_key), (set(), set()))
            causes.add(cause)
    return tuple(MandatoryBan(domain, key, tuple(sorted(refs)), tuple(sorted(causes)))
                 for (domain, key), (refs, causes) in sorted(entries.items()))


class SyntheticAssemblyGate:
    """One offline attempt; route selection is single-shot and a veto is terminal.

    Registry/policy/capability fixture DATA belongs in tests. This explicit API
    can only produce SyntheticValidatedAssembly, never production authorization.
    There is no production registry injection API, environment switch or dispatch.
    """

    def __init__(self, resolution, registry, policy, *, context_id, adapter_id, model, size, _key=None):
        if _key is not _FACTORY_KEY:
            _veto('UNTRUSTED_AUTHORITY', 'preflight')
        # No route is selected for a blocked or forged interpretation.
        try:
            verdict = check_interpretation(resolution)
        except VisualSafetyFailure as error:
            safety_failure(_result('preflight', '', tuple(
                replace(i, stage='preflight') for i in error.failure.result.issues)))
        safety_failure(_result('preflight', resolution.resolution_digest, tuple(
            replace(i, stage='preflight') for i in verdict.issues)))
        if type(registry) is not SyntheticRegistry or type(policy) is not SyntheticPolicy:
            _veto('UNTRUSTED_AUTHORITY', 'preflight', resolution.resolution_digest)
        if any(not isinstance(s, str) or not s for s in (context_id, adapter_id, model, size)):
            invalid_evidence('preflight')
        self._base = resolution
        self._registry, self._policy = registry, policy
        self._adapter_id, self._model, self._size = adapter_id, model, size
        self._context = next((c for c in registry.contexts if c.context_id == context_id), None)
        self._capability = next((c for c in registry.capabilities
                                 if (c.capacity.adapter_id, c.capacity.model) == (adapter_id, model)), None)
        self._authority_digest = _hash_record((registry, policy))
        snapshot = _hash_record((resolution, self._authority_digest, context_id, adapter_id, model, size))
        self._route = EnforcementRoute('fully_controlled', snapshot, policy.selection_rule_id,
                                       policy.policy_version, (), True)
        routed = replace(resolution, enforcement_route=self._route, resolution_digest='')
        self._resolution = replace(routed, resolution_digest=_digest(routed))
        self._receipt = None
        self._issued = None
        self._failed = False

    @property
    def resolution(self):
        return self._resolution

    def _run(self, stage, operation):
        if self._failed:
            return _result(stage, self.resolution.resolution_digest,
                           (ValidationIssue('STALE_VALIDATION', stage),))
        try:
            result = operation()
        except VisualSafetyFailure as error:
            result = _result(stage, self.resolution.resolution_digest, tuple(
                replace(i, stage=stage) for i in error.failure.result.issues))
        if result.outcome == 'blocked':
            self._failed = True
        return result

    def _verify_resolution(self, resolution, route, stage):
        check_interpretation(self._base)  # Complete structural/semantic/resolution derivation.
        if (type(resolution) is not ResolvedVisualIntent or resolution != self.resolution
                or resolution.resolution_digest != _digest(resolution)
                or route is not self._route or resolution.enforcement_route is not self._route):
            _veto('STALE_VALIDATION', stage, self.resolution.resolution_digest)

    def _verify_context(self, capacity, stage):
        context, policy, registry = self._context, self._policy, self._registry
        if (context is None or context.context_id not in policy.context_ids
                or policy.registry_version != registry.version):
            _veto('UNTRUSTED_ENFORCEMENT_UNPROVEN', stage, self.resolution.resolution_digest)
        if (normalize_style_key(self.resolution.requested_style) != context.requested_style
                or self.resolution.requested_mode != context.mode
                or (context.requested_style != 'auto' and context.resolved_style != context.requested_style)):
            _veto('STYLE_CONFLICT', stage, self.resolution.resolution_digest)
        # No approved Custom Style renderer/subset or symbolic nuance policy exists.
        if (self.resolution.requested_style == 'custom' or (self.resolution.requested_mode == 'symbolic'
                and any(s.source.kind == SourceKind.CUSTOM_NOTES and s.source.text.strip()
                        for s in self.resolution.interpretation.segmentations))):
            _veto('UNTRUSTED_ENFORCEMENT_UNPROVEN', stage, self.resolution.resolution_digest)
        if (self._capability is None or type(capacity) is not PromptCapacity
                or capacity != self._capability.capacity or self._size not in self._capability.sizes
                or _measure('', capacity) is None):
            _veto('CAPACITY_UNVERIFIED', stage, self.resolution.resolution_digest)

    def _fragment(self, selection, origin='curated', refs=()):
        if type(selection) is not FragmentSelection:
            _veto('UNTRUSTED_AUTHORITY', 'candidate')
        entry = next((f for f in self._registry.fragments if f.registry_id == selection.registry_id), None)
        if entry is None:
            _veto('UNTRUSTED_AUTHORITY', 'candidate')
        text, positive, excluded, conditional = entry.text, entry.positive_keys, entry.excluded_keys, entry.conditional_keys
        if entry.slot_values:
            value = next((v for v in entry.slot_values if v.value_id == selection.slot_value), None)
            if value is None:
                _veto('UNTRUSTED_AUTHORITY', 'candidate')
            text = text.replace('{value}', value.text)
            positive, excluded, conditional = (positive | value.positive_keys,
                                               excluded | value.excluded_keys,
                                               conditional | value.conditional_keys)
        elif selection.slot_value is not None:
            _veto('UNTRUSTED_AUTHORITY', 'candidate')
        return PromptFragment(text, entry.role, FragmentProvenance(
            origin, refs, entry.registry_id, self._registry.version, selection.slot_value),
            positive, excluded, conditional)

    def _make_candidate(self, receipt, optional_selections=(), trace=''):
        immutable_tuple(optional_selections)
        if any(type(s) is not FragmentSelection for s in optional_selections) or not isinstance(trace, str):
            _veto('UNTRUSTED_AUTHORITY', 'candidate')
        resolution, context = self.resolution, self._context
        positive = {(f.domain, f.key): _refs(resolution.interpretation, f.fact_indices)
                    for f in resolution.effective_facts if f.polarity == Polarity.POSITIVE}
        required = set(positive) | context.required_keys
        presence = context.default_human_presence
        if required & {('object', 'human'), ('object', 'body')}:
            presence = 'single_person'
        elif ('object', 'hands') in required:
            presence = 'hands_only'
        presence_binding = next((p for p in context.presence_bindings if p.presence == presence), None)
        if presence_binding is None:
            _veto('HUMAN_PRESENCE_CONFLICT', 'candidate')
        bans = _assembly_bans(resolution, context, presence)
        banned = {(b.domain, b.key) for b in bans}
        presence_fragments = tuple(self._fragment(s) for s in presence_binding.fragments)
        anatomy = {('object', 'human'), ('object', 'hands'), ('object', 'body')}
        # A registered scene default remains soft before reconciliation, in both
        # directions: required hands can displace none; exclusions can displace
        # an optional person. A fixed context with no compatible enum blocks.
        if (not required & anatomy and any(
                (f.positive_keys | f.conditional_keys) & banned for f in presence_fragments)):
            presence_binding = next((p for p in context.presence_bindings if p.presence == 'none'), None)
            if presence_binding is None:
                _veto('HUMAN_PRESENCE_CONFLICT', 'candidate')
            presence = 'none'
            presence_fragments = tuple(self._fragment(s) for s in presence_binding.fragments)
            bans = _assembly_bans(resolution, context, presence)
            banned = {(b.domain, b.key) for b in bans}
        presence_keys = frozenset().union(*(f.positive_keys for f in presence_fragments))
        if (presence == 'hands_only' and ('object', 'hands') not in presence_keys
                or presence in {'single_person', 'distant_figure'} and ('object', 'human') not in presence_keys):
            _veto('HUMAN_PRESENCE_CONFLICT', 'candidate')
        if required & banned:
            _veto('FORBIDDEN_POSITIVE_CONTENT', 'candidate')
        if not banned <= self._policy.covered_keys:
            _veto('UNTRUSTED_ENFORCEMENT_UNPROVEN', 'candidate')
        fragments = [*(self._fragment(s) for s in context.base_fragments), *presence_fragments]
        if any(f.role in {'mandatory_exclusion', 'no_text', 'untrusted_prose'} for f in fragments):
            _veto('INVALID_ASSEMBLY', 'candidate')
        if not any(f.role == 'style' for f in fragments):
            _veto('STYLE_CONFLICT', 'candidate')
        for key in sorted(required):
            binding = next((b for b in self._registry.positive_bindings if b.key == key), None)
            if binding is None:
                _veto('MISSING_REQUIRED_VISUAL_FACT', 'candidate', refs=positive.get(key, ()))
            fragment = self._fragment(binding.selection,
                                      'user_projection' if key in positive else 'curated', positive.get(key, ()))
            if key not in fragment.positive_keys or fragment.role not in {'positive_scene', 'qualifier'}:
                _veto('MISSING_REQUIRED_VISUAL_FACT', 'candidate', refs=positive.get(key, ()))
            fragments.append(fragment)
        for selection in optional_selections:
            fragment = self._fragment(selection)
            if fragment.role not in {'positive_scene', 'qualifier', 'soft_avoid', 'conditional_anatomy'}:
                _veto('UNTRUSTED_AUTHORITY', 'candidate')
            fragments.append(fragment)
        # Optional scene avoids yield to required facts before becoming final.
        fragments = [f for f in fragments if not (f.role == 'soft_avoid' and f.excluded_keys & required)]
        for ban in sorted(bans, key=lambda b: (b.domain == 'system', b.domain, b.key)):
            key = (ban.domain, ban.key)
            binding = next((b for b in self._registry.exclusion_bindings if b.key == key), None)
            if binding is None:
                _veto('MISSING_MANDATORY_EXCLUSION', 'candidate', refs=ban.evidence_refs)
            fragment = self._fragment(binding.selection,
                                      'user_projection' if ban.evidence_refs else 'system_rule', ban.evidence_refs)
            role = 'no_text' if key == ('system', 'text_marks') else 'mandatory_exclusion'
            if fragment.excluded_keys != frozenset({key}) or fragment.role != role:
                _veto('MISSING_MANDATORY_EXCLUSION', 'candidate', refs=ban.evidence_refs)
            fragments.append(fragment)
        for index, fragment in enumerate(fragments):
            if fragment.role != 'soft_avoid' and not fragment.excluded_keys <= banned:
                _veto('UNTRUSTED_ENFORCEMENT_UNPROVEN', 'candidate')
            if ((fragment.positive_keys | fragment.conditional_keys) & banned
                    or fragment.excluded_keys & required
                    or presence == 'none' and fragment.conditional_keys & {
                        ('object', 'human'), ('object', 'hands'), ('object', 'body')}):
                safety_failure(_result('candidate', resolution.resolution_digest, (
                    ValidationIssue('FORBIDDEN_POSITIVE_CONTENT', 'candidate', (), (index,)),)))
        # A closed qualifier slot cannot carry two incompatible enum values.
        slots = {}
        for fragment in fragments:
            p = fragment.provenance
            if fragment.role == 'qualifier' and p.slot_value is not None:
                if p.registry_id in slots and slots[p.registry_id] != p.slot_value:
                    _veto('SCENE_CONFLICT', 'candidate')
                slots[p.registry_id] = p.slot_value
        return PromptCandidate(resolution, tuple(fragments), context.scene_type, presence,
                               context.resolved_style, context.mode, trace, receipt, optional_selections), bans

    def check_preflight(self, *, resolution=None, capacity=None, enforcement_route=None):
        def check():
            resolved = self.resolution if resolution is None else resolution
            route = self._route if enforcement_route is None else enforcement_route
            cap = self._capability.capacity if capacity is None and self._capability else capacity
            self._verify_resolution(resolved, route, 'preflight')
            self._verify_context(cap, 'preflight')
            receipt = PreflightEvidence(_result('preflight', self.resolution.resolution_digest),
                                        self._authority_digest, cap, self._adapter_id, self._model, self._size)
            candidate, _ = self._make_candidate(receipt)
            prompt, _ = _serialize(candidate.fragments)
            if _measure(prompt, cap) > cap.maximum:
                _veto('FINAL_PROMPT_OVER_CAPACITY', 'preflight')
            if self._receipt is None:
                self._receipt = receipt
            return receipt.validation
        return self._run('preflight', check)

    def preflight(self):
        safety_failure(self.check_preflight())
        return self._receipt

    def assemble(self, *, optional_selections=(), trace='offline') -> FinalAssembly:
        receipt = self.preflight()
        try:
            candidate, bans = self._make_candidate(receipt, optional_selections, trace)
            prompt, spans = _serialize(candidate.fragments)
            return FinalAssembly(candidate, self._route, prompt, spans, bans, receipt.capacity,
                                 self._model, self._adapter_id, self._size, self._policy.policy_version,
                                 self._registry.version, self._authority_digest)
        except VisualSafetyFailure:
            self._failed = True
            raise

    def check_final_assembly(self, assembly):
        def check():
            if type(assembly) is not FinalAssembly:
                invalid_evidence('final')
            self._verify_resolution(assembly.candidate.resolution, assembly.enforcement_route, 'final')
            self._verify_context(assembly.capacity, 'final')
            if self._receipt is None or assembly.candidate.preflight is not self._receipt:
                _veto('STALE_VALIDATION', 'final')
            expected, bans = self._make_candidate(self._receipt, assembly.candidate.optional_selections,
                                                   assembly.candidate.trace)
            issues = []
            def issue(code):
                issues.append(ValidationIssue(code, 'final'))
            if assembly.candidate != expected:
                issue('INVALID_ASSEMBLY')
                if assembly.candidate.fragments != expected.fragments:
                    issue('UNTRUSTED_AUTHORITY')
            # Coverage comes from exact verified fragments, never from key sets
            # asserted on an altered fragment or an appended general disclaimer.
            required = {(f.domain, f.key) for f in self.resolution.effective_facts
                        if f.polarity == Polarity.POSITIVE} | self._context.required_keys
            for fragment in expected.fragments:
                if fragment not in assembly.candidate.fragments:
                    if fragment.role in {'mandatory_exclusion', 'no_text'}:
                        issue('MISSING_MANDATORY_EXCLUSION')
                    elif fragment.role in {'positive_scene', 'qualifier'} and fragment.positive_keys & required:
                        issue('MISSING_REQUIRED_VISUAL_FACT')
            if assembly.mandatory_bans != bans:
                issue('MISSING_MANDATORY_EXCLUSION')
            prompt, spans = _serialize(expected.fragments)
            if assembly.prompt != prompt or assembly.fragment_spans != spans:
                issue('INVALID_ASSEMBLY')
            if ((assembly.adapter_id, assembly.model, assembly.size) != (self._adapter_id, self._model, self._size)
                    or assembly.policy_version != self._policy.policy_version
                    or assembly.registry_version != self._registry.version
                    or assembly.authority_digest != self._authority_digest):
                issue('STALE_VALIDATION')
            # Count the WHOLE supplied prompt too: suffixes/separators cannot escape.
            if _measure(assembly.prompt, assembly.capacity) > assembly.capacity.maximum:
                issue('FINAL_PROMPT_OVER_CAPACITY')
            return _result('final', self.resolution.resolution_digest, issues, _hash_record(assembly))
        return self._run('final', check)

    def validate_final_assembly(self, assembly) -> SyntheticValidatedAssembly:
        validation = self.check_final_assembly(assembly)
        safety_failure(validation)
        artifact = SyntheticValidatedAssembly(assembly, validation, _key=_FACTORY_KEY)
        self._issued = artifact
        return artifact

    def check_artifact(self, artifact):
        """Offline integrity check only. There is deliberately no dispatch API."""
        def check():
            if (type(artifact) is not SyntheticValidatedAssembly or artifact is not self._issued
                    or artifact.assembly_digest != _hash_record(artifact.assembly)
                    or artifact.validation != _result('final', self.resolution.resolution_digest,
                                                       assembly_digest=artifact.assembly_digest)):
                _veto('STALE_VALIDATION', 'final')
            return self.check_final_assembly(artifact.assembly)
        return self._run('final', check)


def create_synthetic_gate(resolution, registry, policy, *, context_id, adapter_id, model, size):
    """Explicit test harness; no supplied data can create production trust."""
    return SyntheticAssemblyGate(resolution, registry, policy, context_id=context_id,
                                 adapter_id=adapter_id, model=model, size=size, _key=_FACTORY_KEY)


def check_preflight(resolution, *, gate=None, capacity=None, enforcement_route=None):
    if type(gate) is not SyntheticAssemblyGate:
        return _result('preflight', '', (ValidationIssue('UNTRUSTED_ENFORCEMENT_UNPROVEN', 'preflight'),))
    return gate.check_preflight(resolution=resolution, capacity=capacity, enforcement_route=enforcement_route)


def check_final_assembly(assembly, *, gate=None):
    if type(gate) is not SyntheticAssemblyGate:
        return _result('final', '', (ValidationIssue('UNTRUSTED_AUTHORITY', 'final'),))
    return gate.check_final_assembly(assembly)


def validate_final_assembly(assembly, *, gate=None) -> SyntheticValidatedAssembly:
    if type(gate) is not SyntheticAssemblyGate:
        _veto('UNTRUSTED_AUTHORITY', 'final')
    return gate.validate_final_assembly(assembly)
