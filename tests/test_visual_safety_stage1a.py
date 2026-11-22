"""Hand-authored SG-01 STR-01..06 / VIS-01..16 oracles; provider-free."""
from dataclasses import FrozenInstanceError, replace
from collections import Counter

import pytest

from services import visual_intent as vi
from services.directive_segments import DirectiveSource, SourceKind, Span, segment_directives
from services.visual_safety import (
    resolve_visual_intent, check_interpretation, require_valid_interpretation,
)
from services.visual_safety_types import VisualSafetyFailure


def resolve(text='', *, style='auto', notes=None, mode='illustration', auxiliary=()):
    interpretation = vi.interpret_visual_intent(text, style=style, custom_style_description=notes,
                                              auxiliary_sources=auxiliary)
    return resolve_visual_intent(interpretation, requested_style=style, requested_mode=mode)


def issues(resolution):
    return [(i.code, i.detail) for i in check_interpretation(resolution).issues]


@pytest.mark.parametrize('text,head,marker,dependent,child', [
    ('Show a poster featuring mugs and windows', Span(7, 13), Span(14, 23), Span(24, 28), 1),
    ('Show a poster with a mug', Span(7, 13), Span(14, 18), Span(19, 24), None),
    ('Show mountains at sunrise', Span(5, 14), Span(15, 17), Span(18, 25), None),
    ('Покажи историю про кружки и окна', Span(7, 14), Span(15, 18), Span(19, 25), 1),
    ('No mugs on tables', Span(3, 7), Span(8, 10), Span(11, 17), None),
])
def test_str04_05_exact_frame_attachment_spans(text, head, marker, dependent, child):
    s = segment_directives(DirectiveSource('s', SourceKind.USER_TEXT, text))
    root = s.structure[0]
    assert root.frame == 'render_complement' and not root.uncertain
    assert root.head_span == head
    assert root.relations[0].marker_span == marker
    assert root.relations[0].dependent_span == dependent
    assert root.relations[0].attachment == 'head_local'
    assert root.relations[0].dependent_directive_ids == (() if child is None else (child,))
    if child is not None:
        assert s.structure[child].governing_directive_id == 0


@pytest.mark.parametrize('text,opaque', [
    ('Show a poster featuring mugs and windows', 'Show a glargs featuring flub and glargss'),
    ('Show mountains at sunrise', 'Show flurblurs at glargss'),
    ('Море без пляжа', 'Флар без гларг'),
    ('No mugs on tables', 'No blub on glargs'),
])
def test_str04_05_structure_is_vocabulary_independent(text, opaque):
    # Compare grammatical shapes and offsets where token lengths differ.
    def shape(value):
        s = segment_directives(DirectiveSource('s', SourceKind.USER_TEXT, value))
        return ([(d.polarity, d.kind, d.scope_id) for d in s.directives],
                [(r.frame, r.governing_directive_id, r.uncertain,
                  len(r.qualifier_spans), [(x.attachment, x.dependent_directive_ids) for x in r.relations])
                 for r in s.structure])
    assert shape(text) == shape(opaque)


def test_str05_inline_negative_keeps_original_scope_and_host():
    s = segment_directives(DirectiveSource('s', SourceKind.USER_TEXT, 'Show a mug without a logo'))
    assert [d.polarity.value for d in s.directives] == ['positive', 'negative']
    assert [d.scope_id for d in s.directives] == [0, 1]
    assert s.structure[1].governing_directive_id == 0
    assert s.structure[0].relations[0].marker_span == Span(11, 18)
    assert s.structure[0].relations[0].dependent_span == Span(19, 25)
    assert s.structure[0].relations[0].dependent_directive_ids == (1,)


@pytest.mark.parametrize('text', [
    'No mugs, tables, and windows', 'No plants, small tables, and windows',
    'Без растений, маленьких столов, и окон', 'No mugs, blue lanterns, windows',
    'No people, ocean', 'No people, beach at sunset', 'No mugs on tables',
    'No mugs on tables and windows', 'Show a mug without a logo', 'No glargs',
    'No mugs, glargs, windows', 'No unusually tiny old bright polished wooden tables',
    'No time for my notebook', 'No report about mugs and windows',
    'No people, ocean; No ocean', 'No people, a mug please',
    'If a person appears, no hands', 'If a person appears no hands',
])
def test_vis16_exactly_one_assessment_for_each_negative_directive(text):
    r = resolve(text)
    expected = Counter((s.source.source_id, d.directive_id) for s in r.interpretation.segmentations
                       for d in s.directives if d.polarity == vi.Polarity.NEGATIVE)
    assert Counter(n.ref for n in r.interpretation.negatives) == expected
    assert all(count == 1 for count in expected.values())
    assert r.interpretation.unresolved_negatives == tuple(
        vi.UnresolvedNegative(n.ref, n.unresolved_detail, n.target_span)
        for n in r.interpretation.negatives if n.classification == 'unresolved')


@pytest.mark.parametrize('text,excluded,unresolved', [
    ('No mugs, tables, and windows', {'mug', 'table', 'window'}, 0),
    ('No plants, small tables, and windows', {'table', 'window'}, 1),
    ('No mugs, blue lanterns, windows', {'mug', 'window'}, 1),
    ('Без растений, маленьких столов, и окон', {'table', 'window'}, 1),
])
@pytest.mark.parametrize('custom', [False, True])
def test_vis01_d1a_ledger_precedes_canonical_filtering(text, excluded, unresolved, custom):
    r = resolve('', style='custom', notes=text) if custom else resolve(text)
    assert r.excluded_objects == excluded
    assert len(r.interpretation.unresolved_negatives) == unresolved
    assert check_interpretation(r).outcome == ('blocked' if unresolved else 'allowed')
    assert all(n.detail == 'unknown_target' for n in r.interpretation.unresolved_negatives)


@pytest.mark.parametrize('text,key,basis,qualifiers', [
    ('No people, ocean', 'water', vi.FactBasis.LEGACY_D1_A_OCEAN, set()),
    ('No people, beach at sunset', 'beach', vi.FactBasis.LEGACY_D1_A_BEACH_SUNSET, {'sunset'}),
    ('  NO  PEOPLE,\tbeach at   sunset! ', 'beach', vi.FactBasis.LEGACY_D1_A_BEACH_SUNSET, {'sunset'}),
])
@pytest.mark.parametrize('custom', [False, True])
def test_vis02_legacy_positive_disposition_never_emits_same_member_ban(text, key, basis, qualifiers, custom):
    r = resolve('', style='custom', notes=text) if custom else resolve(text)
    i = r.interpretation
    n = next(n for n in i.negatives if n.classification == 'resolved_positive_legacy_exception')
    source = next(s for s in i.segmentations if s.source.source_id == n.ref[0])
    assert source.directives[n.ref[1]].polarity == vi.Polarity.NEGATIVE
    assert n.target_span == source.directives[n.ref[1]].span
    assert all(i.facts[index].polarity == vi.Polarity.POSITIVE and i.facts[index].basis == basis for index in n.fact_indices)
    assert r.positive_coastal == {key} and not r.excluded_coastal
    assert r.excluded_objects == {'human', 'hands', 'body'}
    assert {f.key for f in r.effective_facts if f.domain == vi.FactDomain.QUALIFIER} == qualifiers
    assert not i.unresolved_negatives and check_interpretation(r).outcome == 'allowed'


@pytest.mark.parametrize('text,expected', [
    ('No people,ocean', {'water'}), ('No people , ocean', {'water'}),
    ('No humans, ocean', {'water'}), ('Please no people, ocean', {'water'}),
    ('No people, ocean please', {'water'}), ('No people, ocean, windows', {'water'}),
    ('No windows, no people, ocean', {'water'}), ('No people, ocean, show a table', {'water'}),
])
def test_vis03_no_exception_widening(text, expected):
    r = resolve(text)
    assert not r.positive_coastal and r.interpretation.excluded_coastal == expected
    assert not any(n.classification == 'resolved_positive_legacy_exception' for n in r.interpretation.negatives)


def test_vis02_independent_exclusion_has_own_refs_and_wins():
    r = resolve('No people, ocean; No ocean')
    assert not r.positive_coastal and r.excluded_coastal == {'water', 'coast', 'beach', 'sandy', 'rocky', 'lagoon'}
    assert [(n.ref, n.classification) for n in r.interpretation.negatives] == [
        (('user_text', 0), 'resolved'), (('user_text', 1), 'resolved_positive_legacy_exception'),
        (('user_text', 2), 'resolved')]
    assert [(c.kind, c.resolution, c.evidence_refs) for c in r.conflicts] == [
        ('coastal', 'exclusion_wins', (('user_text', 1), ('user_text', 2)))]
    assert check_interpretation(r).outcome == 'allowed'


def test_vis03_nonlegacy_qualified_negative_keeps_independent_instructions():
    r = resolve('No people, beach at sunset, show a table')
    assert r.required_objects == {'table'} and r.excluded_objects == {'human', 'hands', 'body'}
    assert not r.positive_coastal and not r.excluded_coastal
    assert issues(r) == [('UNRESOLVED_EXCLUSION', 'relational_scope')]
    assert r.interpretation.unresolved_negatives[0].target_span.extract(
        r.interpretation.segmentations[0].source.text) == 'beach at sunset'


@pytest.mark.parametrize('text,detail', [
    ('No mugs on tables', 'relational_scope'), ('No people near windows', 'relational_scope'),
    ('No beaches near houses', 'relational_scope'), ('Show a mug without a logo', 'relational_scope'),
    ('No glargs near windows', 'unknown_target'), ('No mugs on tables and windows', 'relational_scope'),
    ('No glargs', 'unknown_target'), ('No mugs near', 'unsupported_structure'),
    ('No tropical beach', 'unsupported_structure'), ('No sunrise', 'unsupported_structure'),
    ('No ocean at sunrise', 'relational_scope'),
    ('Show a mug without a logo and a window', 'relational_scope'),
    ('If a person appears, no hands', 'ambiguous_scope'), ('If a person appears no hands', 'ambiguous_scope'),
])
def test_vis05_local_unknown_and_uncertain_exclusions_never_globalize(text, detail):
    r = resolve(text)
    assert r.interpretation.unresolved_negatives
    assert all(n.detail == detail for n in r.interpretation.unresolved_negatives)
    assert not r.mandatory_bans
    assert all(code == 'UNRESOLVED_EXCLUSION' for code, _ in issues(r))


@pytest.mark.parametrize('text', ['No time for my notebook', 'No report about mugs and windows',
                                'No time for my notebook and windows', 'Never show a report about people',
                                'No report about people', 'No report about mugs, windows'])
def test_vis06_established_nonvisual_negative_is_observable(text):
    r = resolve(text)
    assert not r.mandatory_bans and not r.required_objects
    assert all(n.classification == 'nonvisual' for n in r.interpretation.negatives)
    assert check_interpretation(r).outcome == 'allowed'


@pytest.mark.parametrize('text', ['No mood for my notebook', 'No glargs about mugs'])
def test_vis06_similar_unknown_prose_is_not_exempt(text):
    assert issues(resolve(text)) == [('UNRESOLVED_EXCLUSION', 'unknown_target')]


@pytest.mark.parametrize('text,objects,artifact,scene,qualifiers', [
    ('Show a poster featuring mugs and windows', {'mug', 'window'}, {'poster'}, set(), set()),
    ('Show a poster with a mug', {'mug'}, {'poster'}, set(), set()),
    ('Покажи плакат с кружкой', {'mug'}, {'poster'}, set(), set()),
    ('Show mountains at sunrise', set(), set(), {'mountain'}, {'sunrise'}),
    ('Покажи горы на рассвете', set(), set(), {'mountain'}, {'sunrise'}),
])
def test_vis07_artifact_and_scene_heads_are_eligible(text, objects, artifact, scene, qualifiers):
    r = resolve(text)
    assert r.disposition == 'eligible' and check_interpretation(r).outcome == 'allowed'
    assert r.required_objects == objects
    for domain, expected in [(vi.FactDomain.ARTIFACT, artifact), (vi.FactDomain.SCENE, scene),
                             (vi.FactDomain.QUALIFIER, qualifiers)]:
        assert {f.key for f in r.effective_facts if f.domain == domain} == expected


@pytest.mark.parametrize('text', ['Покажи историю про кружки и окна', 'Show a story about mugs and windows',
                                'Show a story about mugs and windows and a table'])
def test_vis07_narrative_owns_its_whole_content_complement(text):
    r = resolve(text)
    assert r.disposition == 'unsupported' and not r.effective_facts
    assert issues(r) == [('UNSUPPORTED_VISUAL_REQUEST', None)]
    assert all(c.request_class == 'unsupported_narrative' for c in r.interpretation.classifications)


@pytest.mark.parametrize('text', ['Show a poster with glargs', 'Show a poster with mugs and glargs',
                                'Show a poster featuring mugs and glargs', 'Show a poster with mugs unknownhead',
                                'Show a glarg with mugs and windows'])
def test_vis07_unknown_essential_artifact_dependents_cannot_be_omitted(text):
    r = resolve(text)
    assert r.disposition == 'unsupported' and not r.effective_facts
    assert issues(r) == [('UNSUPPORTED_VISUAL_REQUEST', None)]


@pytest.mark.parametrize('text,key', [
    ('Покажи историю про кружки и окна; покажи стол', 'table'),
    ('Show a story about mugs and windows, show a notebook', 'notebook'),
])
def test_vis08_only_independent_eligible_request_survives(text, key):
    r = resolve(text)
    assert r.disposition == 'mixed' and r.required_objects == {key}
    assert r.interpretation.unsupported_requests and check_interpretation(r).outcome == 'allowed'
    assert issues(resolve(text + '; No glargs')) == [('UNRESOLVED_EXCLUSION', 'unknown_target')]


def test_vis08_ordinary_theme_and_unsupported_and_unresolved_are_distinct():
    theme, unsupported, unresolved = resolve('A story about mugs'), resolve('Show a story about mugs'), resolve('No glargs')
    assert theme.disposition == 'none' and check_interpretation(theme).outcome == 'allowed'
    assert unsupported.disposition == 'unsupported' and not unsupported.interpretation.negatives
    assert unresolved.disposition == 'none' and not unresolved.interpretation.unsupported_requests
    assert issues(unsupported) != issues(unresolved)


def test_vis08_unresolved_and_unsupported_and_conflicts_all_survive_together():
    r = resolve('Show a story about mugs; No glargs; No hands; show hands')
    assert issues(r) == [('OBJECT_CONFLICT', None), ('UNRESOLVED_EXCLUSION', 'unknown_target')]
    assert r.disposition == 'mixed' and r.interpretation.unsupported_requests
    only_unsupported = resolve('Show a story about mugs; No glargs')
    assert issues(only_unsupported) == [('UNRESOLVED_EXCLUSION', 'unknown_target'), ('UNSUPPORTED_VISUAL_REQUEST', None)]


@pytest.mark.parametrize('positive,key', [('hands', 'hands'), ('a face', 'body'), ('body parts', 'body'), ('people', 'human')])
def test_vis11_human_cascade_conflicts_preserve_both_refs(positive, key):
    r = resolve('No people; show ' + positive)
    assert r.excluded_objects == {'human', 'hands', 'body'}
    assert issues(r) == [('OBJECT_CONFLICT', None)]
    assert r.conflicts[0].evidence_refs == (('user_text', 0), ('user_text', 1))
    assert r.conflicts[0].keys == {(vi.FactDomain.OBJECT, key)}


@pytest.mark.parametrize('text,expected', [('No hands', {'hands'}), ('No body parts', {'body'})])
def test_vis11_no_reverse_human_cascade(text, expected):
    r = resolve(text)
    assert r.excluded_objects == expected and check_interpretation(r).outcome == 'allowed'


@pytest.mark.parametrize('text,positive,excluded', [
    ('Море без пляжа', {'water'}, {'beach', 'sandy'}),
    ('Show rocky coast without beach', {'rocky'}, {'beach', 'sandy'}),
    ('Ocean view, no rocky coast', {'water'}, {'rocky'}),
    ('Ocean view, no sandy beach', {'water'}, {'sandy'}),
    ('Show beach; no beach', set(), {'beach', 'sandy'}),
    ('Without ocean', set(), {'water', 'coast', 'beach', 'sandy', 'rocky', 'lagoon'}),
])
def test_vis12_coastal_precedence_does_not_invent_complements(text, positive, excluded):
    r = resolve(text)
    assert r.positive_coastal == positive and r.excluded_coastal == excluded
    assert check_interpretation(r).outcome == 'allowed'


@pytest.mark.parametrize('text,style,mode,blocked', [
    ('No ocean', 'sea_coast_photo', 'photo', True),
    ('No ocean', 'bright_ocean', 'photo', True),
    ('Show ocean', 'cozy_home_photo', 'photo', True),
    ('Show ocean', 'light_interior_photo', 'photo', True),
    ('I want a tropical beach', 'urban_city_photo', 'photo', True),
    ('Ocean view', 'urban_city_photo', 'photo', False),
    ('Show ocean', 'mandala_harmony', 'symbolic', False),
    ('No ocean', 'auto', 'photo', False),
])
def test_vis12_existing_style_and_mode_compatibility(text, style, mode, blocked):
    r = resolve(text, style=style, mode=mode)
    assert issues(r) == ([('STYLE_CONFLICT', None)] if blocked else [])


def test_vis12_qualifiers_do_not_leak_from_suppressed_or_narrative_sources():
    r = resolve('Show ocean at sunrise; no ocean; show a table')
    assert not r.positive_coastal and r.time_of_day is None and r.required_objects == {'table'}
    r = resolve('Show a story about ocean at sunset; show mountains at sunrise')
    assert r.time_of_day == 'sunrise'
    assert {f.key for f in r.effective_facts if f.domain == vi.FactDomain.QUALIFIER} == {'sunrise'}


@pytest.mark.parametrize('style', ['custom', 'auto', 'nature'])
def test_vis04_active_custom_notes_only(style):
    r = resolve('Show a table', style=style, notes='No mugs, glargs')
    assert check_interpretation(r).outcome == ('blocked' if style == 'custom' else 'allowed')
    assert r.excluded_objects == ({'mug'} if style == 'custom' else set())
    assert all(n.classification == 'inactive_or_auxiliary' for n in r.interpretation.negatives) == (style != 'custom')


@pytest.mark.parametrize('kind', [SourceKind.GENERATED_PROSE, SourceKind.SCENE_HINT, SourceKind.SOFT_AVOID, SourceKind.MEMORY_AVOID])
def test_vis04_auxiliary_sources_cannot_create_authority_or_legacy_promotions(kind):
    r = resolve(auxiliary=(DirectiveSource('aux', kind, 'No people, ocean; No glargs; Show a mug'),))
    assert not r.mandatory_bans and not r.effective_facts and not r.interpretation.unresolved_negatives
    assert all(c.request_class == 'inactive_or_auxiliary' for c in r.interpretation.classifications)
    assert not any(f.basis.value.startswith('legacy_d1_a') for f in r.interpretation.facts)


def test_vis13_no_arbitrary_count_and_no_provenance_loss():
    r = resolve('; '.join(['No mugs'] * 100))
    assert len(r.interpretation.negatives) == 100 and len(r.mandatory_bans) == 1
    assert r.mandatory_bans[0].evidence_refs == tuple(('user_text', i) for i in range(100))
    assert check_interpretation(r).outcome == 'allowed'


def test_vis14_local_ids_and_snapshot_digests_keep_sources_distinct():
    r = resolve('No mugs', style='custom', notes='Show a cup')
    assert r.conflicts[0].evidence_refs == (('custom_notes', 0), ('user_text', 0))
    assert issues(r) == [('OBJECT_CONFLICT', None)]
    assert len({r.resolution_digest, resolve('No cups', style='custom', notes='Show a mug').resolution_digest,
                resolve('No mugs', style='auto', notes='Show a cup').resolution_digest}) == 3
    assert resolve('No mugs').resolution_digest == resolve('No mugs').resolution_digest


@pytest.mark.parametrize('change', ['span', 'duplicate', 'cycle', 'source_kind', 'scope_id', 'missing_ledger', 'duplicate_ledger',
                                   'mutable', 'head', 'relation', 'negative_fact_missing'])
def test_str06_vis14_corrupt_evidence_fails_with_typed_invalid_evidence(change):
    i = vi.interpret_visual_intent('No mugs, windows')
    s = i.segmentations[0]
    with pytest.raises(VisualSafetyFailure, match='INVALID_EVIDENCE'):
        if change == 'span':
            replace(s, directives=(replace(s.directives[0], span=Span(3, 999)), s.directives[1]))
        elif change == 'duplicate':
            replace(s, directives=(s.directives[0], s.directives[0]))
        elif change == 'cycle':
            replace(s, structure=(replace(s.structure[0], governing_directive_id=1), s.structure[1]))
        elif change == 'source_kind':
            replace(i, facts=(replace(i.facts[0], source_kind=SourceKind.GENERATED_PROSE), i.facts[1]))
        elif change == 'scope_id':
            replace(i, facts=(replace(i.facts[0], scope_id=9), i.facts[1]))
        elif change == 'missing_ledger':
            replace(i, negatives=i.negatives[:-1])
        elif change == 'duplicate_ledger':
            replace(i, negatives=i.negatives + (i.negatives[0],))
        elif change == 'head':
            replace(i, classifications=(replace(i.classifications[0], head_span=Span(0, 1)), i.classifications[1]))
        elif change == 'relation':
            other = vi.interpret_visual_intent('Show a poster with a mug').segmentations[0]
            relation = replace(other.structure[0].relations[0], dependent_span=Span(0, 1))
            replace(other, structure=(replace(other.structure[0], relations=(relation,)),))
        elif change == 'negative_fact_missing':
            replace(i, negatives=(replace(i.negatives[0], fact_indices=()), i.negatives[1]))
        else:
            replace(i, facts=list(i.facts))


def test_vis15_legacy_basis_is_evaluated_once_per_complete_scope(monkeypatch):
    seen = []
    original = vi._legacy_basis
    def record(text):
        seen.append(text)
        return original(text)
    monkeypatch.setattr(vi, '_legacy_basis', record)
    resolve('No people, beach at sunset; No people, ocean, no windows')
    assert seen == ['No people, beach at sunset', ' No people, ocean, no windows', ' No people, ocean, no windows']


def test_vis16_views_are_owned_derived_and_immutable():
    r = resolve('Show a story about mugs; No glargs')
    i = r.interpretation
    assert i.unsupported_requests == tuple(vi.UnsupportedVisualRequest(c.ref, 'narrative', c.head_span)
                                           for c in i.classifications if c.request_class == 'unsupported_narrative')
    with pytest.raises(TypeError):
        replace(i, unsupported_requests=())
    with pytest.raises(TypeError):
        replace(i, unresolved_negatives=())
    for value, field, replacement in [(i.negatives[0], 'classification', 'resolved'),
                                       (i.unresolved_negatives[0], 'detail', 'unknown_target'),
                                       (r, 'requested_style', 'other'), (i.segmentations[0].structure[0], 'uncertain', False)]:
        with pytest.raises(FrozenInstanceError):
            setattr(value, field, replacement)
    with pytest.raises(VisualSafetyFailure) as error:
        require_valid_interpretation(r)
    assert error.value.failure.retryable is False
    assert 'glargs' not in str(error.value) and 'story' not in str(error.value)
    with pytest.raises(AttributeError):
        error.value.failure = None


def test_stage1a_has_no_route_or_dispatch_authority():
    r = resolve('Show a mug')
    assert require_valid_interpretation(r) is r and r.enforcement_route is None
    assert check_interpretation(r).stage == 'interpretation'
    with pytest.raises(VisualSafetyFailure, match='INVALID_EVIDENCE'):
        check_interpretation(replace(r, requested_style='other'))


def test_neutral_registry_reexports_preserve_existing_runtime_values():
    from services import coastal_intent, ritual_config, visual_semantics
    assert coastal_intent.COASTAL_STYLES is visual_semantics.COASTAL_STYLES
    assert coastal_intent.COASTAL_SCENES is visual_semantics.COASTAL_SCENES
    assert coastal_intent.COASTAL_STYLE_DIRECTIONS is visual_semantics.COASTAL_STYLE_DIRECTIONS
    assert coastal_intent.COAST_INCOMPATIBLE_STYLES is visual_semantics.COAST_INCOMPATIBLE_STYLES
    assert coastal_intent.DEDICATED_BEACH_INCOMPATIBLE_STYLES is visual_semantics.DEDICATED_BEACH_INCOMPATIBLE_STYLES
    assert coastal_intent.COASTAL_CONTEXT is visual_semantics.COASTAL_CONTEXT
    assert ritual_config.PHOTO_STYLE_ALIASES is visual_semantics.PHOTO_STYLE_ALIASES
    assert ritual_config.normalize_style_key is visual_semantics.normalize_style_key


@pytest.mark.parametrize('text,expected', [
    ('No ocean beach', [('water', False), ('beach', True)]),
    ('No mug table', [('mug', False), ('table', True)]),
])
@pytest.mark.parametrize('custom', [False, True])
def test_cp01_f01_ineligible_negative_mentions_block_without_lost_coverage(text, expected, custom):
    r = resolve('', style='custom', notes=text) if custom else resolve(text)
    i = r.interpretation
    source_id = 'custom_notes' if custom else 'user_text'
    assert [(f.key, f.eligible) for f in i.facts] == expected
    assert all(f.source_id == source_id and f.directive_id == 0 and f.scope_id == 0
               and f.polarity == vi.Polarity.NEGATIVE for f in i.facts)
    negative, = i.negatives
    assert negative.ref == (source_id, 0) and negative.classification == 'unresolved'
    assert negative.fact_indices == (0, 1)
    assert negative.target_span.extract(text) == text[3:]
    assert {f.span.extract(text) for f in i.facts} == set(text[3:].split())
    assert not r.mandatory_bans and not r.effective_facts
    assert issues(r) == [('UNRESOLVED_EXCLUSION', 'unsupported_structure')]
    assert check_interpretation(r).outcome == 'blocked'


@pytest.mark.parametrize('indices', [(0, 1), (0,), (1,)])
def test_cp01_f01_resolved_ledger_cannot_hide_ineligible_negative_facts(indices):
    i = vi.interpret_visual_intent('No mug table')
    with pytest.raises(VisualSafetyFailure, match='^INVALID_EVIDENCE$'):
        replace(i, negatives=(replace(i.negatives[0], classification='resolved',
                                     unresolved_detail=None, fact_indices=indices),))


@pytest.mark.parametrize('text', ['No people in my report', 'Never show people in my report',
                                'No people in my report and windows'])
@pytest.mark.parametrize('custom', [False, True])
def test_cp01_f02_visual_head_with_narrative_dependent_is_relational_exclusion(text, custom):
    r = resolve('', style='custom', notes=text) if custom else resolve(text)
    s = next(s for s in r.interpretation.segmentations if s.source.text == text)
    assert s.structure[0].head_span.extract(text) == 'people'
    assert s.structure[0].relations[0].marker_span.extract(text) == 'in'
    assert s.structure[0].relations[0].dependent_span.extract(text) == 'my report'
    assert r.interpretation.facts[0].key == 'human'
    assert all(n.classification == 'unresolved' for n in r.interpretation.negatives)
    assert all(n.fact_indices for n in r.interpretation.negatives)
    assert not r.mandatory_bans and not r.effective_facts
    assert issues(r) == [('UNRESOLVED_EXCLUSION', 'relational_scope')] * len(r.interpretation.negatives)
    assert check_interpretation(r).outcome == 'blocked'


def test_cp01_f02_narrative_head_does_not_own_unattached_list_members():
    r = resolve('No report, mugs')
    assert [n.classification for n in r.interpretation.negatives] == ['nonvisual', 'resolved']
    assert r.excluded_objects == {'mug'} and not r.required_objects
    assert check_interpretation(r).outcome == 'allowed'


@pytest.mark.parametrize('command,expected', [
    ('No', [('UNRESOLVED_EXCLUSION', 'unsupported_structure')]),
    ('Never show', [('UNRESOLVED_EXCLUSION', 'unsupported_structure')]),
    ('Show', [('UNSUPPORTED_VISUAL_REQUEST', None)]),
    ('I want', [('UNSUPPORTED_VISUAL_REQUEST', None)]),
])
def test_cp01_f02_later_narrative_frame_keeps_mixed_command_ambiguous(command, expected):
    r = resolve(command + ' windows and a report about mugs')
    assert not r.effective_facts and not r.mandatory_bans
    assert all(not f.eligible for f in r.interpretation.facts)
    assert check_interpretation(r).outcome == 'blocked' and issues(r) == expected


@pytest.mark.parametrize('context', ['urban city', 'cafe', 'café', 'terrace', 'veranda', 'village',
                                   'waterfront', 'кафе', 'терраса', 'веранда', 'деревня', 'город'])
@pytest.mark.parametrize('style', ['urban_city_photo', 'cafe_terrace_photo', 'rural_calm_photo'])
def test_cp01_f03_contextual_beach_compatibility_matches_fix03a(context, style):
    from services.coastal_intent import coastal_style_conflict, user_coastal_intent
    text = 'Tropical beach, ' + context
    # Both paths have a direct policy oracle; production is not the expectation generator.
    r = resolve(text, style=style, mode='photo')
    assert r.positive_coastal == {'beach'} and not r.dedicated_beach
    assert check_interpretation(r).outcome == 'allowed' and not issues(r)
    legacy = user_coastal_intent(text, style=style)
    assert not legacy.dedicated_beach and not coastal_style_conflict(style, legacy)


@pytest.mark.parametrize('text,style', [
    ('Tropical beach', 'urban_city_photo'), ('Tropical beach', 'cafe_terrace_photo'),
    ('Tropical beach', 'rural_calm_photo'), ('Tropical beach, mountains', 'urban_city_photo'),
    ('Tropical beach, urban city', 'cozy_home_photo'),
])
def test_cp01_f03_genuine_style_conflicts_still_match_fix03a(text, style):
    from services.coastal_intent import coastal_style_conflict, user_coastal_intent
    r = resolve(text, style=style, mode='photo')
    assert issues(r) == [('STYLE_CONFLICT', None)]
    assert check_interpretation(r).outcome == 'blocked'
    assert coastal_style_conflict(style, user_coastal_intent(text, style=style))


@pytest.mark.parametrize('text', ['Tropical beach, lagoon', 'Tropical beach; No sandy beach'])
def test_cp01_f03_dedicated_beach_requires_surviving_beach_subtype(text):
    from services.coastal_intent import coastal_style_conflict, user_coastal_intent
    r = resolve(text, style='urban_city_photo', mode='photo')
    assert not r.dedicated_beach and check_interpretation(r).outcome == 'allowed'
    legacy = user_coastal_intent(text)
    assert legacy.subtype != 'beach' and not legacy.dedicated_beach
    assert not coastal_style_conflict('urban_city_photo', legacy)


@pytest.mark.parametrize('suffix', ['; No urban city', '; Show a story about urban city',
                                  '; A story about mugs and urban city', '; urban report',
                                  '; No people in the city'])
def test_cp01_f03_negative_and_narrative_context_cannot_waive_conflict(suffix):
    r = resolve('Tropical beach' + suffix, style='urban_city_photo', mode='photo')
    assert r.dedicated_beach and ('STYLE_CONFLICT', None) in issues(r)


def test_cp01_f03_inactive_and_auxiliary_context_cannot_waive_conflict():
    r = resolve('Tropical beach', style='urban_city_photo', notes='urban city',
                auxiliary=(DirectiveSource('generated', SourceKind.GENERATED_PROSE, 'urban city'),))
    assert r.dedicated_beach and issues(r) == [('STYLE_CONFLICT', None)]


@pytest.mark.parametrize('value', [None, 'invalid', {}, [], 7])
def test_cp01_f04_wrong_evidence_record_types_are_typed_failures(value):
    i = vi.interpret_visual_intent('No mugs')
    with pytest.raises(VisualSafetyFailure, match='^INVALID_EVIDENCE$'):
        vi.interpret_directives((value,))
    for field in ('segmentations', 'facts', 'classifications', 'negatives'):
        with pytest.raises(VisualSafetyFailure, match='^INVALID_EVIDENCE$'):
            replace(i, **{field: (value,)})
    with pytest.raises(VisualSafetyFailure, match='^INVALID_EVIDENCE$'):
        resolve_visual_intent(value)


@pytest.mark.parametrize('value', [None, 7])
def test_cp01_f04_noniterable_segmentation_input_is_typed_failure(value):
    with pytest.raises(VisualSafetyFailure, match='^INVALID_EVIDENCE$'):
        vi.interpret_directives(value)


@pytest.mark.parametrize('value', [None, 'invalid', {}, [], 7])
@pytest.mark.parametrize('field', ['source', 'scopes', 'directives', 'structure', 'relations'])
def test_cp01_f04_wrong_structural_record_types_are_typed_failures(field, value):
    s = vi.interpret_visual_intent('No mugs on tables').segmentations[0]
    with pytest.raises(VisualSafetyFailure, match='^INVALID_EVIDENCE$'):
        if field == 'source':
            replace(s, source=value)
        elif field == 'relations':
            replace(s, structure=(replace(s.structure[0], relations=(value,)),))
        else:
            replace(s, **{field: (value,)})


@pytest.mark.parametrize('field,value', [
    (field, value)
    for field in ('fact', 'scope', 'chunk', 'directive', 'head', 'nominal', 'qualifier',
                  'marker', 'dependent', 'target', 'classification_head')
    for value in (None, (3, 7), {'start': 3, 'end': 7}, Span(3, 999))
    if field != 'head' or value is not None  # head_span is deliberately optional
])
def test_cp01_f04_malformed_nested_spans_are_typed_failures(field, value):
    i = vi.interpret_visual_intent('No mugs on tables')
    s = i.segmentations[0]
    with pytest.raises(VisualSafetyFailure, match='^INVALID_EVIDENCE$'):
        if field == 'fact':
            replace(i, facts=(replace(i.facts[0], span=value), i.facts[1]))
        elif field in {'scope', 'chunk'}:
            replace(s, scopes=(replace(s.scopes[0], **{'span' if field == 'scope' else 'chunk_span': value}),))
        elif field == 'directive':
            replace(s, directives=(replace(s.directives[0], span=value),))
        elif field in {'head', 'nominal', 'qualifier'}:
            changes = {'qualifier_spans': (value,)} if field == 'qualifier' else {field + '_span': value}
            replace(s, structure=(replace(s.structure[0], **changes),))
        elif field in {'marker', 'dependent'}:
            relation = replace(s.structure[0].relations[0], **{field + '_span': value})
            replace(s, structure=(replace(s.structure[0], relations=(relation,)),))
        elif field == 'target':
            replace(i, negatives=(replace(i.negatives[0], target_span=value),))
        else:
            replace(i, classifications=(replace(i.classifications[0], head_span=value),))


@pytest.mark.parametrize('ref', [(), ('user_text',), ('user_text', []), ([], 0), ('user_text', 0, 1)])
@pytest.mark.parametrize('field', ['classifications', 'negatives'])
def test_cp01_f04_malformed_refs_are_typed_failures(field, ref):
    i = vi.interpret_visual_intent('No mugs')
    with pytest.raises(VisualSafetyFailure, match='^INVALID_EVIDENCE$'):
        replace(i, **{field: (replace(getattr(i, field)[0], ref=ref),)})


@pytest.mark.parametrize('snapshot_style,requested_style', [('auto', 'custom'), ('custom', 'auto'),
                                                          ('nature', 'custom'), ('custom', 'nature')])
def test_cp01_f05_custom_note_activity_must_match_requested_style(snapshot_style, requested_style):
    i = vi.interpret_visual_intent('Show a table', style=snapshot_style, custom_style_description='No mugs')
    with pytest.raises(VisualSafetyFailure, match='^INVALID_EVIDENCE$'):
        resolve_visual_intent(i, requested_style=requested_style)


@pytest.mark.parametrize('style,excluded', [('auto', set()), ('nature', set()), ('custom', {'mug'})])
def test_cp01_f05_consistent_note_activity_is_valid(style, excluded):
    r = resolve('Show a table', style=style, notes='No mugs')
    assert r.required_objects == {'table'} and r.excluded_objects == excluded
    assert check_interpretation(r).outcome == 'allowed'


def test_cp01_f05_custom_style_does_not_require_a_note_source():
    i = vi.interpret_directives((segment_directives(DirectiveSource('s', SourceKind.USER_TEXT, 'Show a table')),))
    r = resolve_visual_intent(i, requested_style='custom')
    assert r.required_objects == {'table'} and check_interpretation(r).outcome == 'allowed'
    assert check_interpretation(resolve('Show a table', style='custom')).outcome == 'allowed'


@pytest.mark.parametrize('text,domain,key', [
    ('Show a poster without people', vi.FactDomain.ARTIFACT, 'poster'),
    ('Show a poster without a logo', vi.FactDomain.ARTIFACT, 'poster'),
    ('Show a mug without people', vi.FactDomain.OBJECT, 'mug'),
    ('Show a mug without a logo', vi.FactDomain.OBJECT, 'mug'),
])
def test_cp01_f06_positive_host_survives_unresolved_inline_exclusion(text, domain, key):
    r = resolve(text)
    i = r.interpretation
    assert r.disposition == 'eligible' and not i.unsupported_requests
    assert [(f.domain, f.key, f.polarity, f.fact_indices) for f in r.effective_facts] == [
        (domain, key, vi.Polarity.POSITIVE, (0,))]
    assert i.facts[0].eligible and i.facts[0].span.extract(text) == key
    assert i.classifications[0].request_class == 'eligible'
    negative, = i.negatives
    assert negative.ref == ('user_text', 1) and negative.classification == 'unresolved'
    assert negative.unresolved_detail == 'relational_scope'
    assert negative.target_span.extract(text) == ('people' if text.endswith('people') else 'a logo')
    assert negative.fact_indices == ((1,) if text.endswith('people') else ())
    assert not r.mandatory_bans and issues(r) == [('UNRESOLVED_EXCLUSION', 'relational_scope')]
    assert check_interpretation(r).outcome == 'blocked'
