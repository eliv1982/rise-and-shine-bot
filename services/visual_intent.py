"""Isolated SG-01 interpretation; AR-01 is the only structural authority.

Classifications and the negative ledger own their derived immutable views.
Canonical evidence sets are not safety verdicts. No production entry point uses
this layer in Stage 1A.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Literal

from services.directive_segments import (
    DirectiveSource, Polarity, SegmentedSource, SourceKind, Span,
    segment_directives, validate_structure,
)
from services import visual_semantics as vocabulary
from services.visual_safety_types import DirectiveRef, immutable_tuple, invalid_evidence

RequestClass = Literal['eligible', 'unsupported_narrative', 'unsupported_visual_form',
                       'nonvisual', 'ambiguous', 'inactive_or_auxiliary']
NegativeClass = Literal['resolved', 'resolved_positive_legacy_exception', 'unresolved',
                        'nonvisual', 'inactive_or_auxiliary']
UnresolvedDetail = Literal['relational_scope', 'unknown_target', 'ambiguous_scope', 'unsupported_structure']


class FactDomain(str, Enum):
    OBJECT = 'object'
    COASTAL = 'coastal'
    ARTIFACT = 'artifact'
    SCENE = 'scene'
    QUALIFIER = 'qualifier'


class FactBasis(str, Enum):
    GRAMMAR = 'grammar'
    CUSTOM_NOMINAL = 'custom_nominal'
    AMBIGUOUS = 'ambiguous'
    LEGACY_D1_A_OCEAN = 'legacy_d1_a_ocean'
    LEGACY_D1_A_BEACH_SUNSET = 'legacy_d1_a_beach_sunset'
    VISUAL_HEAD = 'visual_head'


@dataclass(frozen=True, slots=True)
class Recognition:
    key: str
    span: Span


@dataclass(frozen=True, slots=True)
class VisualFact:
    domain: FactDomain
    key: str
    polarity: Polarity
    source_id: str
    source_kind: SourceKind
    directive_id: int
    scope_id: int
    span: Span
    eligible: bool
    basis: FactBasis


@dataclass(frozen=True, slots=True)
class DirectiveClassification:
    ref: DirectiveRef
    request_class: RequestClass
    head_span: Span | None
    fact_indices: tuple[int, ...]

    def __post_init__(self):
        immutable_tuple(self.ref)
        immutable_tuple(self.fact_indices)


@dataclass(frozen=True, slots=True)
class NegativeAssessment:
    ref: DirectiveRef
    classification: NegativeClass
    fact_indices: tuple[int, ...]
    target_span: Span
    unresolved_detail: UnresolvedDetail | None

    def __post_init__(self):
        immutable_tuple(self.ref)
        immutable_tuple(self.fact_indices)


@dataclass(frozen=True, slots=True)
class UnresolvedNegative:
    ref: DirectiveRef
    detail: UnresolvedDetail
    target_span: Span

    def __post_init__(self):
        immutable_tuple(self.ref)


@dataclass(frozen=True, slots=True)
class UnsupportedVisualRequest:
    ref: DirectiveRef
    kind: Literal['narrative', 'unsupported_form', 'ambiguous_head']
    head_span: Span | None

    def __post_init__(self):
        immutable_tuple(self.ref)


def _keys(facts, domain, polarity):
    return frozenset(f.key for f in facts if f.eligible and f.domain == domain and f.polarity == polarity)


@dataclass(frozen=True, slots=True)
class VisualInterpretation:
    segmentations: tuple[SegmentedSource, ...]
    facts: tuple[VisualFact, ...]
    classifications: tuple[DirectiveClassification, ...]
    negatives: tuple[NegativeAssessment, ...]

    def __post_init__(self):
        validate_interpretation(self)

    @property
    def unresolved_negatives(self) -> tuple[UnresolvedNegative, ...]:
        return tuple(UnresolvedNegative(n.ref, n.unresolved_detail, n.target_span)
                     for n in self.negatives if n.classification == 'unresolved')

    @property
    def unsupported_requests(self) -> tuple[UnsupportedVisualRequest, ...]:
        kinds = {'unsupported_narrative': 'narrative', 'unsupported_visual_form': 'unsupported_form',
                 'ambiguous': 'ambiguous_head'}
        return tuple(UnsupportedVisualRequest(c.ref, kinds[c.request_class], c.head_span)
                     for c in self.classifications if c.request_class in kinds)

    @property
    def required_objects(self):
        return _keys(self.facts, FactDomain.OBJECT, Polarity.POSITIVE)

    @property
    def excluded_objects(self):
        return _keys(self.facts, FactDomain.OBJECT, Polarity.NEGATIVE)

    @property
    def positive_coastal(self):
        return _keys(self.facts, FactDomain.COASTAL, Polarity.POSITIVE)

    @property
    def excluded_coastal(self):
        return _keys(self.facts, FactDomain.COASTAL, Polarity.NEGATIVE)


VisualIntent = VisualInterpretation  # compatibility name, not another record


def _authoritative(source):
    return source.active and source.kind in {SourceKind.USER_TEXT, SourceKind.CUSTOM_NOTES}


def validate_interpretation(result: VisualInterpretation) -> None:
    if not isinstance(result, VisualInterpretation):
        invalid_evidence()
    for items in (result.segmentations, result.facts, result.classifications, result.negatives):
        immutable_tuple(items)
    sources, directives, structures = {}, {}, {}
    for segmented in result.segmentations:
        validate_structure(segmented)
        source = segmented.source
        if source.source_id in sources:
            invalid_evidence()
        sources[source.source_id] = source
        for directive, structure in zip(segmented.directives, segmented.structure):
            ref = (source.source_id, directive.directive_id)
            directives[ref], structures[ref] = directive, structure
    for fact in result.facts:
        if (not isinstance(fact, VisualFact) or not isinstance(fact.source_id, str)
                or type(fact.directive_id) is not int or type(fact.scope_id) is not int
                or not isinstance(fact.source_kind, SourceKind) or not isinstance(fact.span, Span)
                or type(fact.span.start) is not int or type(fact.span.end) is not int):
            invalid_evidence()
        ref = (fact.source_id, fact.directive_id)
        directive = directives.get(ref)
        if (directive is None or fact.source_kind != sources[fact.source_id].kind
                or fact.scope_id != directive.scope_id or not isinstance(fact.domain, FactDomain)
                or not isinstance(fact.basis, FactBasis) or not isinstance(fact.polarity, Polarity)
                or not isinstance(fact.key, str) or type(fact.eligible) is not bool
                or not directive.span.start <= fact.span.start < fact.span.end <= directive.span.end
                or (fact.eligible and not _authoritative(sources[fact.source_id]))):
            invalid_evidence()
        if fact.eligible and fact.polarity != directive.polarity:
            if not (fact.polarity == Polarity.POSITIVE and (
                directive.polarity == Polarity.UNSPECIFIED or fact.basis in {
                    FactBasis.LEGACY_D1_A_OCEAN, FactBasis.LEGACY_D1_A_BEACH_SUNSET})):
                invalid_evidence()
    seen = set()
    for classification in result.classifications:
        if not isinstance(classification, DirectiveClassification):
            invalid_evidence()
        _validate_ref(classification.ref)
        immutable_tuple(classification.fact_indices)
        if any(type(i) is not int for i in classification.fact_indices):
            invalid_evidence()
        ref = classification.ref
        if (ref not in directives or ref in seen or classification.request_class not in RequestClass.__args__
                or classification.head_span != structures[ref].head_span):
            invalid_evidence()
        seen.add(ref)
        expected = tuple(i for i, f in enumerate(result.facts) if (f.source_id, f.directive_id) == ref)
        if classification.fact_indices != expected:
            invalid_evidence()
        if (classification.request_class == 'inactive_or_auxiliary') == _authoritative(sources[ref[0]]):
            invalid_evidence()
        if classification.request_class != 'eligible' and any(result.facts[i].eligible for i in expected):
            invalid_evidence()
    if seen != set(directives):
        invalid_evidence()
    seen = set()
    for negative in result.negatives:
        if not isinstance(negative, NegativeAssessment):
            invalid_evidence()
        _validate_ref(negative.ref)
        immutable_tuple(negative.fact_indices)
        ref = negative.ref
        if (ref not in directives or ref in seen or directives[ref].polarity != Polarity.NEGATIVE
                or negative.classification not in NegativeClass.__args__
                or negative.target_span != directives[ref].span):
            invalid_evidence()
        seen.add(ref)
        if (negative.classification == 'unresolved') != (negative.unresolved_detail is not None):
            invalid_evidence()
        if negative.unresolved_detail is not None and negative.unresolved_detail not in UnresolvedDetail.__args__:
            invalid_evidence()
        for i in negative.fact_indices:
            if type(i) is not int or not 0 <= i < len(result.facts):
                invalid_evidence()
            if (result.facts[i].source_id, result.facts[i].directive_id) != ref:
                invalid_evidence()
        # The ledger covers every recognition, including ineligible mentions.
        expected = tuple(i for i, f in enumerate(result.facts) if (f.source_id, f.directive_id) == ref)
        if negative.fact_indices != expected:
            invalid_evidence()
        selected = tuple(result.facts[i] for i in negative.fact_indices)
        if negative.classification == 'resolved' and (
                not selected or any(not f.eligible or f.polarity != Polarity.NEGATIVE for f in selected)):
            invalid_evidence()
        if negative.classification == 'resolved_positive_legacy_exception' and (
                not selected or any(not f.eligible or f.polarity != Polarity.POSITIVE or f.basis not in {
                    FactBasis.LEGACY_D1_A_OCEAN, FactBasis.LEGACY_D1_A_BEACH_SUNSET} for f in selected)
                or any(f.eligible and f.polarity == Polarity.NEGATIVE for f in result.facts
                       if (f.source_id, f.directive_id) == ref)):
            invalid_evidence()
        if negative.classification == 'inactive_or_auxiliary' and _authoritative(sources[ref[0]]):
            invalid_evidence()
    if seen != {ref for ref, d in directives.items() if d.polarity == Polarity.NEGATIVE}:
        invalid_evidence()


def _validate_ref(ref):
    if (not isinstance(ref, tuple) or len(ref) != 2 or not isinstance(ref[0], str)
            or type(ref[1]) is not int):
        invalid_evidence()


def _recognize(pattern, text):
    return tuple(Recognition(m.lastgroup, Span(m.start(), m.end())) for m in pattern.finditer(text))


def recognize_objects(text: str) -> tuple[Recognition, ...]:
    return _recognize(vocabulary._OBJECT, text)


def recognize_coastal(text: str) -> tuple[Recognition, ...]:
    return _recognize(vocabulary._COASTAL, text)


def _legacy_basis(chunk_text: str) -> FactBasis | None:
    normalized = ' '.join(chunk_text.split()).casefold().rstrip('.;!?')
    return {'no people, ocean': FactBasis.LEGACY_D1_A_OCEAN,
            'no people, beach at sunset': FactBasis.LEGACY_D1_A_BEACH_SUNSET}.get(normalized)


def _mentions(text):
    return tuple((domain, r) for domain, recognitions in (
        (FactDomain.OBJECT, recognize_objects(text)), (FactDomain.COASTAL, recognize_coastal(text)),
        (FactDomain.ARTIFACT, _recognize(vocabulary.ARTIFACT, text)),
        (FactDomain.SCENE, _recognize(vocabulary.SCENE, text)),
        (FactDomain.QUALIFIER, _recognize(vocabulary.QUALIFIER, text)),
    ) for r in recognitions)


def _head_matches(segmented, directive, structure, mentions):
    if structure.head_span is None or structure.nominal_span is None:
        return ()
    result = []
    for domain, recognition in mentions:
        start, end = directive.span.start + recognition.span.start, directive.span.start + recognition.span.end
        if not structure.nominal_span.start <= start < end <= structure.nominal_span.end:
            continue
        if (start <= structure.head_span.start and structure.head_span.end <= end
                or (domain == FactDomain.COASTAL and segmented.source.text[end:structure.nominal_span.end].strip().casefold() == 'view')):
            result.append((domain, recognition))
    return tuple(result)


def interpret_directives(segmentations: Iterable[SegmentedSource]) -> VisualInterpretation:
    """Interpret precomputed structure; conflicts retain evidence for resolution."""
    if not isinstance(segmentations, Iterable):
        invalid_evidence()
    segmentations = tuple(segmentations)
    for segmented in segmentations:
        validate_structure(segmented)
    ids = [s.source.source_id for s in segmentations]
    if len(ids) != len(set(ids)):
        invalid_evidence()
    facts, classifications, negatives = [], [], []
    for segmented in segmentations:
        source, authority = segmented.source, _authoritative(segmented.source)
        # Full original chunk, once per scope (DR-12), before negative derivation.
        legacy = {s.scope_id: _legacy_basis(s.chunk_span.extract(source.text)) for s in segmented.scopes}
        mentions = {d.directive_id: _mentions(d.span.extract(source.text)) for d in segmented.directives}
        heads = {d.directive_id: _head_matches(segmented, d, segmented.structure[d.directive_id], mentions[d.directive_id])
                 for d in segmented.directives}
        unsupported_artifacts = set()
        for structure in segmented.structure:
            if not any(d == FactDomain.ARTIFACT for d, _ in heads[structure.directive_id]):
                continue
            for relation in structure.relations:
                if any(segmented.directives[i].polarity == Polarity.NEGATIVE
                       for i in relation.dependent_directive_ids):
                    continue  # negative children have their own coverage ledger
                word = relation.marker_span.extract(source.text).casefold()
                dep_text = relation.dependent_span.extract(source.text)
                if word not in {'with', 'featuring', 'с'} or not any(
                        r.span.end == len(dep_text) and d != FactDomain.QUALIFIER for d, r in _mentions(dep_text)):
                    unsupported_artifacts.add(structure.directive_id)
                if any(not heads[i] or segmented.structure[i].uncertain for i in relation.dependent_directive_ids):
                    unsupported_artifacts.add(structure.directive_id)
        narrative_heads, nonvisual_heads = set(), set()
        for structure in segmented.structure:
            word = structure.head_span.extract(source.text).casefold() if structure.head_span else ''
            if word in vocabulary.NARRATIVE_HEADS or word in {'read', 'discuss', 'discussion'}:
                narrative_heads.add(structure.directive_id)
            if word in vocabulary.NONVISUAL_HEADS:
                nonvisual_heads.add(structure.directive_id)

        def owned_by(index, established_heads):
            """Only an established head and its actual complements inherit ownership."""
            while index not in established_heads:
                governor = segmented.structure[index].governing_directive_id
                if governor is None or not any(index in r.dependent_directive_ids
                                                for r in segmented.structure[governor].relations):
                    return False
                index = governor
            return True

        for directive, structure in zip(segmented.directives, segmented.structure):
            index, scope = directive.directive_id, segmented.scopes[directive.scope_id]
            ref = (source.source_id, index)
            governor = structure.governing_directive_id
            owner = segmented.structure[governor] if governor is not None else None
            owner_heads = heads[governor] if governor is not None else ()
            narrative = owned_by(index, narrative_heads)
            nonvisual = owned_by(index, nonvisual_heads)
            negative, explicit = directive.polarity == Polarity.NEGATIVE, directive.polarity == Polarity.POSITIVE
            detached = directive.polarity == Polarity.UNSPECIFIED and scope.polarity == Polarity.NEGATIVE
            custom = detached and source.kind == SourceKind.CUSTOM_NOTES and not narrative and not nonvisual
            unsupported = structure.uncertain or structure.frame in {'conditional', 'unknown'}
            # A later narrative frame in the same command does not own earlier
            # members. Without an independent command boundary their visual
            # role is ambiguous, rather than established nonvisual content.
            unsupported |= any(h > index and segmented.directives[h].scope_id == directive.scope_id
                               and segmented.structure[h].relations for h in narrative_heads | nonvisual_heads)
            if scope.marker_span is None and segmented.structure[next(
                    d.directive_id for d in segmented.directives if d.scope_id == scope.scope_id)].frame in {'unknown', 'conditional'}:
                unsupported = True
            attached_negative = negative and owner is not None and any(
                index in r.dependent_directive_ids and r.marker_span == scope.marker_span for r in owner.relations)
            coastal_head = any(domain == FactDomain.COASTAL for domain, _ in heads[index])
            coastal_parent = any(domain == FactDomain.COASTAL for domain, _ in owner_heads)
            approved_coastal_negative = attached_negative and coastal_head and coastal_parent and not structure.relations
            legacy_basis = legacy[scope.scope_id] if authority and coastal_head else None
            negative_qualifier = negative and any(d == FactDomain.QUALIFIER for d, _ in mentions[index])
            if negative_qualifier:
                # A positive qualifier slot is not a supported negative renderer.
                # Preserve the full qualified target; never invent a global ban.
                unsupported = True
            local_negative = negative and (bool(structure.relations) or attached_negative) and not approved_coastal_negative
            owned_relation = (negative and owner is not None and owner.relations
                              and segmented.directives[governor].scope_id == directive.scope_id)
            local_negative |= bool(owned_relation)
            if legacy_basis:
                local_negative, unsupported = False, False

            visual_head = bool(heads[index]) and not all(d == FactDomain.QUALIFIER for d, _ in heads[index])
            artifact_head = any(d == FactDomain.ARTIFACT for d, _ in heads[index])
            relation_supported = True
            for relation in structure.relations:
                word = relation.marker_span.extract(source.text).casefold()
                dep_mentions = _mentions(relation.dependent_span.extract(source.text))
                is_negative_link = any(segmented.directives[i].polarity == Polarity.NEGATIVE
                                       for i in relation.dependent_directive_ids)
                if is_negative_link:
                    continue  # the negative child's ledger owns this exclusion
                if word in {'at', 'на'} and any(d == FactDomain.QUALIFIER for d, _ in dep_mentions):
                    continue
                if artifact_head and word in {'with', 'featuring', 'с'} and dep_mentions:
                    continue
                relation_supported = False
            qualifier_member = (not visual_head and any(d == FactDomain.QUALIFIER for d, _ in heads[index])
                                and any(d in {FactDomain.COASTAL, FactDomain.SCENE} for d, _ in owner_heads))
            owner_artifact = owner is not None and any(d == FactDomain.ARTIFACT for d, _ in owner_heads)
            supported = ((visual_head or qualifier_member) and not unsupported and relation_supported
                         and not narrative and not nonvisual and (not detached or custom))
            if index in unsupported_artifacts or governor in unsupported_artifacts:
                supported = False
            if owner_artifact:
                supported &= not owner.uncertain
            if owner is not None and owner.relations and not attached_negative:
                # A dependent is never an independent positive request merely
                # because its noun is recognized under an unknown host.
                supported &= bool(owner_heads) and not owner.uncertain
            if negative and local_negative:
                supported = False
            if negative and qualifier_member:
                supported = False
            if custom:
                supported = visual_head and not unsupported and not structure.relations
            effective_polarity = (Polarity.POSITIVE if custom or directive.polarity == Polarity.UNSPECIFIED
                                  and not detached else directive.polarity)
            if legacy_basis:
                supported, effective_polarity = True, Polarity.POSITIVE

            if not authority:
                request_class = 'inactive_or_auxiliary'
            elif explicit and narrative:
                request_class = 'unsupported_narrative'
            elif explicit and not supported:
                request_class = 'ambiguous' if unsupported else 'unsupported_visual_form'
            else:
                request_class = 'eligible' if supported else 'nonvisual'
            fact_indices = []
            for domain, recognition in mentions[index]:
                absolute = Span(directive.span.start + recognition.span.start,
                                directive.span.start + recognition.span.end)
                is_head = (domain, recognition) in heads[index]
                is_dependent = any(r.dependent_span.start <= absolute.start < absolute.end <= r.dependent_span.end
                                   for r in structure.relations)
                is_qualifier = domain == FactDomain.QUALIFIER and (visual_head or qualifier_member)
                eligible = authority and supported and (is_head or is_dependent or is_qualifier)
                basis = (FactBasis.CUSTOM_NOMINAL if custom and supported else
                         legacy_basis if legacy_basis and domain in {FactDomain.COASTAL, FactDomain.QUALIFIER} else
                         FactBasis.VISUAL_HEAD if eligible and (domain in {FactDomain.ARTIFACT, FactDomain.SCENE, FactDomain.QUALIFIER}
                                                              or artifact_head or owner_artifact) else
                         FactBasis.GRAMMAR if supported else FactBasis.AMBIGUOUS)
                if legacy_basis and domain == FactDomain.QUALIFIER and recognition.key != 'sunset':
                    eligible = False
                fact_indices.append(len(facts))
                facts.append(VisualFact(domain, recognition.key, effective_polarity, source.source_id, source.kind,
                                        index, directive.scope_id, absolute, eligible, basis))
            classifications.append(DirectiveClassification(ref, request_class, structure.head_span, tuple(fact_indices)))
            if negative:
                detail = None
                if not authority:
                    classification = 'inactive_or_auxiliary'
                elif narrative or nonvisual:
                    classification = 'nonvisual'
                elif legacy_basis:
                    classification = 'resolved_positive_legacy_exception'
                elif (supported and any(facts[i].domain != FactDomain.QUALIFIER for i in fact_indices)
                      and all(facts[i].eligible and facts[i].polarity == Polarity.NEGATIVE for i in fact_indices)):
                    classification = 'resolved'
                else:
                    classification = 'unresolved'
                    detail = ('relational_scope' if local_negative and (visual_head or any(
                                  d != FactDomain.QUALIFIER for d, _ in owner_heads)) else
                              'unsupported_structure' if (unsupported or visual_head) and structure.frame != 'conditional' else
                              'ambiguous_scope' if structure.frame == 'conditional' else 'unknown_target')
                negatives.append(NegativeAssessment(ref, classification, tuple(fact_indices), directive.span, detail))
    return VisualInterpretation(segmentations, tuple(facts), tuple(classifications), tuple(negatives))


def interpret_visual_intent(
    user_text: str | None = None, *, style: str | None = None,
    custom_style_description: str | None = None,
    auxiliary_sources: Iterable[DirectiveSource] = (),
) -> VisualInterpretation:
    sources = (
        DirectiveSource('user_text', SourceKind.USER_TEXT, user_text or ''),
        DirectiveSource('custom_notes', SourceKind.CUSTOM_NOTES, custom_style_description or '', style == 'custom'),
        *auxiliary_sources,
    )
    return interpret_directives(segment_directives(source) for source in sources)
