"""Independent finite semantic oracles and real offline boundary attacks."""
import ast
import copy
from dataclasses import FrozenInstanceError, fields, replace
from itertools import product
from pathlib import Path
import pickle
import subprocess
import sys
import traceback

import pytest

from services import visual_renderer as vr, visual_safety as sg, visual_semantics as vs
from services import visual_safety_types as st
from services.visual_registry import (
    RegistrySelection, RegistrySnapshot, RegistryError, canonical_bytes, manifest_for,
)
from services.visual_registry_content import SEED_RELEASE, SEED_MANIFEST, seed_registry


VERSION = '1.0.0'
PIN = 'a57ab2fbc218564c2ed00290cb8866a25e4a07009889442705990719ac007864'
BOUND = 'sg01-nature-seed@1.0.0#' + PIN
STYLE = 'living_nature_photo'
TARGET = vr.SyntheticTarget('offline-adapter', 'offline-model', 'offline-size')
SCENES = ('forest_path', 'open_meadow', 'mountain_view')
ABSENCE = frozenset({('object', 'body'), ('object', 'hands'), ('object', 'human')})
SYSTEM = ('system', 'text_marks')
COVERED = ABSENCE | {SYSTEM} | {('object', k) for k in ('mug', 'notebook', 'table', 'window')} | {
    ('coastal', k) for k in ('water', 'coast', 'beach', 'sandy', 'rocky', 'lagoon')}


def environment(maximum=100000, unit='unicode_codepoints', counter='python-len-v1'):
    return vr.SyntheticEnvironment(
        vs.SyntheticPolicy('offline-stage1d-policy-v1', 'offline-stage1d-rule-v1', BOUND, SCENES,
                           frozenset(COVERED)),
        (vs.SyntheticCapability(st.PromptCapacity(TARGET.adapter_id, TARGET.model, unit, maximum,
             counter, 'synthetic-harness-only', 'offline-cap-v1'), (TARGET.size,)),))


def ref(name, value=None, version=VERSION):
    return RegistrySelection(name, version, value)


def request(scene='forest_path', composition='low_leading_curve', lighting='morning',
            palette='cool', text='No people; No mugs', *, variant=None):
    artistic = (vr.VariantSelector(variant, VERSION) if variant else vr.ArtisticSelections((
        ref('composition.' + scene, composition), ref('lighting.time', lighting),
        ref('palette.natural', palette))))
    return vr.RenderRequest(vr.SourceFields(text), STYLE, 'photo', vr.SceneSelector(scene, VERSION),
                            artistic, TARGET)


def render(req=None, env=None):
    renderer = vr.create_offline_renderer(env or environment())
    preview = renderer.render(req or request())
    return renderer, preview


def codes(error):
    return {i.code for i in error.value.failure.result.issues}


# Literal expectations are independent of registry lookups and renderer output.
STYLE_TEXT = 'Living nature photography with believable natural textures, optical depth, and restrained photographic contrast.'
SCENE_TEXT = {
    'forest_path': 'A continuous earthen footpath curves between living woodland trees, with ferns along its edges.',
    'open_meadow': 'An open meadow of grasses and scattered wildflowers extends to a distant natural horizon.',
    'mountain_view': 'A mountain landscape with layered ridgelines and exposed rock faces above a deep valley.',
}
ANCHOR = 'Keep the mountain ridges as the essential subject of the photograph.'
COMPOSITIONS = {
    'low_leading_curve': 'Composition: a low camera beside foreground ferns follows the path as a deep leading curve between tall tree trunks.',
    'elevated_diagonal': 'Composition: an elevated oblique view places the path diagonally across the frame, with overlapping tree crowns forming successive layers.',
    'grass_level_depth': 'Composition: a grass-level camera holds nearby wildflowers in crisp focus while the meadow recedes into a softly distant horizon.',
    'elevated_horizon_bands': 'Composition: an elevated viewpoint uses broad horizontal bands of meadow and sky, with small flower clusters forming an off-center rhythm.',
    'telephoto_layers': 'Composition: a telephoto panorama compresses successive ridgelines into overlapping silhouettes, with the distant summit high in the frame.',
    'wide_rock_foreground': 'Composition: a wide field of view anchors the lower corner with a granite ledge and opens diagonally into the valley and distant peaks.',
}
LIGHTING = {
    'morning': 'Lighting: soft morning side light reveals fine texture through open shade.',
    'daylight': 'Lighting: clear midday light filters into alternating patches of sun and shade.',
    'sunrise': 'Lighting: at sunrise, low first light touches the upper ridges while the valley remains in cool shadow.',
    'sunset': 'Lighting: at sunset, a low warm glow grazes the meadow beneath a softly luminous sky.',
    'evening': 'Lighting: gentle evening side light outlines the rock faces and lengthens shadows into the valley.',
}
PALETTES = {
    'cool': 'Palette: cool greens and blue-gray shadows, with subtle pale highlights and natural color separation.',
    'warm': 'Palette: warm ochre highlights and muted earth colors balanced by deeper neutral shadows.',
}
BAN_TEXT = {
    'body': 'No visible human body parts.', 'hands': 'No hands.', 'human': 'No people or human figures.',
    'mug': 'No mugs or cups.', 'notebook': 'No notebooks.', 'table': 'No tables.', 'window': 'No windows.',
    'text_marks': 'No text, words, letters, numbers, typography, logos, or watermarks.',
}
ESSENTIALS = {'forest_path': {'footpath', 'trees'}, 'open_meadow': {'meadow', 'grass', 'wildflowers'},
              'mountain_view': {'mountain', 'ridges', 'valley'}}
MATRIX = tuple((scene, c, light, palette)
    for scene, compositions, lighting in (
        ('forest_path', ('low_leading_curve', 'elevated_diagonal'), ('morning', 'daylight')),
        ('open_meadow', ('grass_level_depth', 'elevated_horizon_bands'), ('morning', 'sunset')),
        ('mountain_view', ('telephoto_layers', 'wide_rock_foreground'), ('sunrise', 'evening')))
    for c, light, palette in product(compositions, lighting, ('cool', 'warm')))
SIX = (
    ('forest_path', 'A', 'low_leading_curve', 'morning', 'cool'),
    ('forest_path', 'B', 'elevated_diagonal', 'daylight', 'warm'),
    ('open_meadow', 'A', 'grass_level_depth', 'morning', 'cool'),
    ('open_meadow', 'B', 'elevated_horizon_bands', 'sunset', 'warm'),
    ('mountain_view', 'A', 'telephoto_layers', 'sunrise', 'cool'),
    ('mountain_view', 'B', 'wide_rock_foreground', 'evening', 'warm'),
)


def expected_lines(scene, composition, lighting, palette, *, sunrise=False, bans=('mug',)):
    lines = [STYLE_TEXT, SCENE_TEXT[scene]]
    if sunrise:
        lines.append(LIGHTING['sunrise'])
    if scene == 'mountain_view':
        lines.append(ANCHOR)
    lines.append(COMPOSITIONS[composition])
    if not sunrise:
        lines.append(LIGHTING[lighting])
    lines.extend((PALETTES[palette], *(BAN_TEXT[k] for k in ('body', 'hands', 'human', *bans, 'text_marks'))))
    return tuple(lines)


def assert_success(renderer, preview, expected):
    assembly = preview.artifact.assembly
    assert preview.prompt == '\n'.join(expected)
    assert renderer.state == 'PREVIEW_ISSUED'
    assert type(preview) is vr.OfflinePreview
    assert type(preview.artifact) is sg.SyntheticValidatedAssembly
    assert preview.authority == preview.artifact.authority == 'synthetic_offline'
    assert preview.production_authorized is preview.artifact.production_authorized is False
    assert assembly.candidate.resolved_style == STYLE and assembly.candidate.effective_mode == 'photo'
    assert assembly.candidate.human_presence == 'none'
    assert assembly.candidate.scene_type == preview.request.scene.scene_id
    assert preview.artifact.validation.outcome == 'allowed'
    assert sg.SyntheticAssemblyGate.check_artifact(renderer._gate, preview.artifact).outcome == 'allowed'
    assert renderer.check_preview(preview).outcome == 'allowed'
    assert renderer.check_preview(preview).outcome == 'allowed'
    position = 0
    assert len(preview.occurrences) == len(expected) == len(assembly.candidate.fragments)
    snapshot = seed_registry()
    entities = set()
    for index, (literal, fragment, span, occurrence) in enumerate(zip(
            expected, assembly.candidate.fragments, assembly.fragment_spans, preview.occurrences, strict=True)):
        assert literal == fragment.text == occurrence.content.text
        assert occurrence.position == index and occurrence.span is span
        assert (span.start, span.end) == (position, position + len(literal))
        assert preview.prompt[span.start:span.end] == literal
        position += len(literal) + 1
        proof = occurrence.content
        snapshot.verify_content(proof)
        assert proof.release_id == 'sg01-nature-seed' and proof.release_version == VERSION
        assert proof.release_digest == PIN and proof.selection.version == VERSION
        assert proof.review_id == 'sg01-stage1c-author-review-v1'
        assert len(proof.review_digest) == 64
        assert (fragment.positive_keys, fragment.excluded_keys, fragment.conditional_keys) == (
            proof.positive_keys, proof.excluded_keys, proof.conditional_keys)
        assert fragment.provenance.registry_id == proof.selection.registry_id
        assert fragment.provenance.registry_version == BOUND
        assert fragment.provenance.slot_value == proof.selection.slot_value
        assert occurrence.scene is preview.request.scene
        assert (occurrence.origin, occurrence.evidence_refs) == (
            fragment.provenance.origin, fragment.provenance.evidence_refs)
        entities.update(proof.entities)
        assert not (fragment.positive_keys | fragment.conditional_keys) & (ABSENCE | {SYSTEM})
    assert ESSENTIALS[preview.request.scene.scene_id] <= entities
    assert assembly.candidate.fragments[-1].excluded_keys == {SYSTEM}
    bans = {(b.domain, b.key): b for b in assembly.mandatory_bans}
    assert ABSENCE | {SYSTEM} <= bans.keys()
    for occurrence in preview.occurrences:
        if occurrence.content.excluded_keys:
            key = next(iter(occurrence.content.excluded_keys))
            assert occurrence.exclusion_causes == bans[key].causes
        else:
            assert occurrence.exclusion_causes == ()


@pytest.mark.parametrize('scene,composition,lighting,palette', MATRIX)
def test_all_24_reviewed_combinations(scene, composition, lighting, palette):
    assert len(MATRIX) == 24
    r, p = render(request(scene, composition, lighting, palette))
    assert_success(r, p, expected_lines(scene, composition, lighting, palette))
    artistic = [(o.content.selection.registry_id, o.content.selection.slot_value) for o in p.occurrences
                if o.content.selection.registry_id.startswith(('composition.', 'lighting.', 'palette.'))]
    assert artistic == [('composition.' + scene, composition), ('lighting.time', lighting), ('palette.natural', palette)]


@pytest.mark.parametrize('scene,label,composition,lighting,palette', SIX)
def test_original_six_exact_prompts_and_provenance(scene, label, composition, lighting, palette):
    sunrise = scene == 'mountain_view' and label == 'A'
    text = ('Show mountains at sunrise; No people; No mugs' if sunrise else
            'Show mountains; No people; No mugs' if scene == 'mountain_view' else 'No people; No mugs')
    r, p = render(request(scene, composition, lighting, palette, text, variant=scene + '.' + label))
    assert_success(r, p, expected_lines(scene, composition, lighting, palette, sunrise=sunrise))
    expected = [('style.living_nature_photo', None, 'curated', ()), ('scene.' + scene, None, 'curated', ())]
    if sunrise:
        expected.append(('lighting.time', 'sunrise', 'user_projection', (('user_text', 0),)))
    if scene == 'mountain_view':
        expected.append(('subject.mountain', None, 'user_projection', (('user_text', 0),)))
    expected.append(('composition.' + scene, composition, 'curated', ()))
    if not sunrise:
        expected.append(('lighting.time', lighting, 'curated', ()))
    expected.append(('palette.natural', palette, 'curated', ()))
    human_ref = 1 if scene == 'mountain_view' else 0
    expected.extend(('ban.object.' + k, None, 'user_projection', (('user_text', human_ref),))
                    for k in ('body', 'hands', 'human'))
    expected.extend((('ban.object.mug', None, 'user_projection', (('user_text', human_ref + 1),)),
                     ('ban.system.text_marks', None, 'system_rule', ())))
    assert [(o.content.selection.registry_id, o.content.selection.slot_value, o.origin, o.evidence_refs)
            for o in p.occurrences] == expected


@pytest.mark.parametrize('composition,palette', product(('telephoto_layers', 'wide_rock_foreground'), ('cool', 'warm')))
def test_four_required_sunrise_variations(composition, palette):
    r, p = render(request('mountain_view', composition, 'sunrise', palette,
                          'Show mountains at sunrise; No people; No mugs'))
    assert_success(r, p, expected_lines('mountain_view', composition, 'sunrise', palette, sunrise=True))
    assert p.prompt.count('at sunrise') == 1
    sunrise = [o for o in p.occurrences if o.content.selection == ref('lighting.time', 'sunrise')]
    assert len(sunrise) == 1 and sunrise[0].origin == 'user_projection'
    assert sunrise[0].evidence_refs == (('user_text', 0),)
    facts = p.artifact.assembly.candidate.resolution.interpretation.facts
    assert [(f.key, f.directive_id, (f.span.start, f.span.end)) for f in facts] == [
        ('mountain', 0, (5, 14)), ('sunrise', 0, (18, 25)), ('human', 1, (30, 36)), ('mug', 2, (41, 45))]
    assert not any(word in p.prompt for word in ('evening', 'midday', 'morning'))


@pytest.mark.parametrize('scene,label,composition,lighting,palette', SIX[::2])
def test_scene_only_human_absence_for_every_scene(scene, label, composition, lighting, palette):
    r, p = render(request(scene, composition, lighting, palette, text=''))
    assert_success(r, p, expected_lines(scene, composition, lighting, palette, bans=()))
    for o in p.occurrences:
        if o.content.excluded_keys & ABSENCE:
            assert o.origin == 'system_rule' and o.evidence_refs == ()
            assert o.exclusion_causes == ('SCENE_HUMAN_NONE',)
    assert p.artifact.assembly.candidate.resolution.interpretation.facts == ()


def test_explicit_human_bans_merge_exact_causes_and_refs():
    r, p = render(request(text='No people; No people; No hands'))
    assert_success(r, p, expected_lines('forest_path', 'low_leading_curve', 'morning', 'cool', bans=()))
    bans = {b.key: b for b in p.artifact.assembly.mandatory_bans}
    assert bans['human'].evidence_refs == (('user_text', 0), ('user_text', 1))
    assert bans['human'].causes == ('SCENE_HUMAN_NONE', 'USER_EXCLUSION')
    assert bans['body'].causes == ('HUMAN_EXCLUSION_CASCADE', 'SCENE_HUMAN_NONE', 'USER_EXCLUSION')
    assert bans['hands'].evidence_refs == (('user_text', 0), ('user_text', 1), ('user_text', 2))
    assert bans['hands'].causes == bans['body'].causes
    assert all('SELECTED_STYLE_CONSTRAINT' not in b.causes for b in bans.values())


@pytest.mark.parametrize('noun,key', [('mugs', 'mug'), ('notebooks', 'notebook'), ('tables', 'table'), ('windows', 'window')])
def test_supported_object_exclusions(noun, key):
    r, p = render(request(text='No ' + noun))
    assert_success(r, p, expected_lines('forest_path', 'low_leading_curve', 'morning', 'cool', bans=(key,)))
    o = next(o for o in p.occurrences if o.content.selection.registry_id == 'ban.object.' + key)
    assert o.evidence_refs == (('user_text', 0),) and o.exclusion_causes == ('USER_EXCLUSION',)


def test_many_exclusions_and_source_refs_are_never_clipped():
    r, p = render(request(text='; '.join(['No mugs'] * 21 + ['No notebooks', 'No tables', 'No windows'])))
    assert_success(r, p, expected_lines('forest_path', 'low_leading_curve', 'morning', 'cool',
                                      bans=('mug', 'notebook', 'table', 'window')))
    mug = next(o for o in p.occurrences if o.content.selection.registry_id == 'ban.object.mug')
    assert mug.evidence_refs == tuple(('user_text', i) for i in range(21))


def test_ordinary_theme_and_inactive_notes_never_become_prompt_prose():
    theme = 'Today I am thinking about mugs, windows, and a new chapter'
    req = replace(request(text=theme), sources=vr.SourceFields(theme, 'No glargs; handmade imaginary style'))
    r, p = render(req)
    assert_success(r, p, expected_lines('forest_path', 'low_leading_curve', 'morning', 'cool', bans=()))
    resolution = p.artifact.assembly.candidate.resolution
    assert resolution.disposition == 'none'
    assert not resolution.effective_facts and theme not in p.prompt
    assert not resolution.interpretation.segmentations[1].source.active


def test_mixed_request_preserves_supported_facts_without_narrative_objects():
    r, p = render(request('mountain_view', 'telephoto_layers', 'sunrise', 'warm',
        'Show a story about mugs and windows; Show mountains at sunrise; No notebooks'))
    assert_success(r, p, expected_lines('mountain_view', 'telephoto_layers', 'sunrise', 'warm',
                                      sunrise=True, bans=('notebook',)))
    resolution = p.artifact.assembly.candidate.resolution
    assert resolution.disposition == 'mixed'
    # The coordinated story complement owns two original AR-01 directives.
    assert [(u.ref, u.kind) for u in resolution.interpretation.unsupported_requests] == [
        (('user_text', 0), 'narrative'), (('user_text', 1), 'narrative')]
    assert {(f.domain, f.key) for f in resolution.effective_facts if f.polarity.value == 'positive'} == {
        ('scene', 'mountain'), ('qualifier', 'sunrise')}
    assert all(not (f.positive_keys & {('object', 'mug'), ('object', 'window')})
               for f in p.artifact.assembly.candidate.fragments)
    assert 'story' not in p.prompt and 'mugs' not in p.prompt and 'windows' not in p.prompt
    assert next(o for o in p.occurrences if o.content.selection == ref('lighting.time', 'sunrise')).evidence_refs == (('user_text', 2),)


@pytest.mark.parametrize('unit,counter', [('unicode_codepoints', 'python-len-v1'), ('utf8_bytes', 'utf8-v1')])
def test_complete_prompt_capacity_exact_boundary_and_one_unit_above(unit, counter):
    expected = '\n'.join(expected_lines('forest_path', 'low_leading_curve', 'morning', 'cool'))
    measured = len(expected) if unit == 'unicode_codepoints' else len(expected.encode('utf-8'))
    r, p = render(env=environment(measured, unit, counter))
    assert_success(r, p, tuple(expected.split('\n')))
    cap = p.artifact.assembly.capacity
    assert (cap.maximum, cap.counter_version, cap.capability_version) == (measured, counter, 'offline-cap-v1')
    assert p.artifact.assembly.candidate.preflight.capacity is cap
    failed = vr.create_offline_renderer(environment(measured - 1, unit, counter))
    with pytest.raises(st.VisualSafetyFailure) as error:
        failed.render(request())
    assert codes(error) == {'FINAL_PROMPT_OVER_CAPACITY'}
    assert failed.state == 'FAILED_TERMINAL'


def test_equivalent_requests_are_deterministic_but_attempts_own_separate_issuance():
    a, p = render()
    b, q = render(replace(request()))
    assert p.prompt == q.prompt and p.occurrences == q.occurrences
    assert p.artifact.assembly == q.artifact.assembly
    assert p is not q and p.artifact is not q.artifact
    assert a._gate is not b._gate
    assert a.check_preview(q).outcome == 'blocked'
    assert b.check_preview(q).outcome == 'allowed'


@pytest.mark.parametrize('text,scene,code', [
    ('Show a forest path', 'forest_path', 'UNSUPPORTED_VISUAL_REQUEST'),
    ('Show a story about mugs and windows', 'forest_path', 'UNSUPPORTED_VISUAL_REQUEST'),
    ('No mugs on tables', 'forest_path', 'UNRESOLVED_EXCLUSION'),
    ('No people near windows', 'open_meadow', 'UNRESOLVED_EXCLUSION'),
    ('Show mountains; No glargs', 'mountain_view', 'UNRESOLVED_EXCLUSION'),
    ('Show mountains', 'forest_path', 'SCENE_CONFLICT'),
    ('Show mountains', 'open_meadow', 'SCENE_CONFLICT'),
    ('Show a mug', 'forest_path', 'MISSING_REQUIRED_VISUAL_FACT'),
    ('No people; Show hands', 'forest_path', 'OBJECT_CONFLICT'),
    ('Show mountains at sunrise', 'mountain_view', 'SCENE_CONFLICT'),
])
def test_selector_cannot_forge_user_intent_or_bypass_negatives(text, scene, code):
    req = request(scene, 'wide_rock_foreground' if scene == 'mountain_view' else
                  'grass_level_depth' if scene == 'open_meadow' else 'low_leading_curve',
                  'evening' if scene == 'mountain_view' else 'morning', text=text)
    r = vr.create_offline_renderer(environment())
    with pytest.raises(st.VisualSafetyFailure) as error:
        r.render(req)
    assert codes(error) == {code}
    if text == 'Show mountains':
        # The mountain projection belongs only to the mountain scene; registry
        # occurrence compatibility precedes the aggregate required-key check.
        assert r.registry_failure_code == 'INCOMPATIBLE_SCENE'
        assert error.value.failure.result.stage == 'preflight'
    elif text == 'Show mountains at sunrise':
        # Required sunrise and optional evening occupy the same artistic axis;
        # the duplicate-dimension check precedes the aggregate time-axis check.
        assert r.registry_failure_code == 'CONFLICTING_ARTISTIC_DIMENSION'
        assert error.value.failure.result.stage == 'preflight'
    assert r.state == 'FAILED_TERMINAL'


@pytest.mark.parametrize('change,code', [
    (lambda q: replace(q, style='nature'), 'STYLE_CONFLICT'),
    (lambda q: replace(q, style='sunny_nature_photo'), 'STYLE_CONFLICT'),
    (lambda q: replace(q, style='custom'), 'STYLE_CONFLICT'),
    (lambda q: replace(q, style='unknown'), 'STYLE_CONFLICT'),
    (lambda q: replace(q, mode='symbolic'), 'STYLE_CONFLICT'),
    (lambda q: replace(q, mode='unknown'), 'STYLE_CONFLICT'),
    (lambda q: replace(q, scene=vr.SceneSelector('unknown', VERSION)), 'UNTRUSTED_AUTHORITY'),
    (lambda q: replace(q, scene=vr.SceneSelector('forest_path', 'stale')), 'UNTRUSTED_AUTHORITY'),
    (lambda q: replace(q, artistic=vr.VariantSelector('unknown', VERSION)), 'UNTRUSTED_AUTHORITY'),
    (lambda q: replace(q, artistic=vr.VariantSelector('forest_path.A', 'stale')), 'UNTRUSTED_AUTHORITY'),
    (lambda q: replace(q, artistic=vr.VariantSelector('open_meadow.A', VERSION)), 'SCENE_CONFLICT'),
    (lambda q: replace(q, artistic=vr.ArtisticSelections((ref('unknown'),))), 'UNTRUSTED_AUTHORITY'),
    (lambda q: replace(q, artistic=vr.ArtisticSelections((ref('lighting.time', 'morning', 'stale'),))), 'UNTRUSTED_AUTHORITY'),
    (lambda q: replace(q, artistic=vr.ArtisticSelections((ref('lighting.time', 'unknown'),))), 'UNTRUSTED_AUTHORITY'),
    (lambda q: replace(q, artistic=vr.ArtisticSelections((ref('lighting.time'),))), 'UNTRUSTED_AUTHORITY'),
    (lambda q: replace(q, artistic=vr.ArtisticSelections((ref('scene.forest_path'),))), 'UNTRUSTED_AUTHORITY'),
    (lambda q: replace(q, artistic=vr.ArtisticSelections(q.artistic.components + (ref('palette.natural', 'warm'),))), 'SCENE_CONFLICT'),
    (lambda q: replace(q, artistic=vr.ArtisticSelections(q.artistic.components[:-1])), 'SCENE_CONFLICT'),
    (lambda q: replace(q, artistic=vr.ArtisticSelections((ref('composition.open_meadow', 'grass_level_depth'),
                     *q.artistic.components[1:]))), 'SCENE_CONFLICT'),
    (lambda q: replace(q, artistic=vr.ArtisticSelections((q.artistic.components[0],
                      ref('lighting.time', 'evening'), q.artistic.components[2]))), 'SCENE_CONFLICT'),
    (lambda q: replace(q, target=replace(TARGET, adapter_id='unknown')), 'CAPACITY_UNVERIFIED'),
    (lambda q: replace(q, target=replace(TARGET, model='unknown')), 'CAPACITY_UNVERIFIED'),
    (lambda q: replace(q, target=replace(TARGET, size='unknown')), 'CAPACITY_UNVERIFIED'),
])
def test_unknown_incompatible_and_forged_selectors_fail_terminally(change, code):
    r = vr.create_offline_renderer(environment())
    with pytest.raises(st.VisualSafetyFailure) as error:
        r.render(change(request()))
    assert codes(error) == {code}
    assert r.state == 'FAILED_TERMINAL'


@pytest.mark.parametrize('unit,counter', [('tokens', 'unknown'), ('unicode_codepoints', 'unknown'), ('utf8_bytes', 'unknown')])
def test_unknown_counters_never_become_verified(unit, counter):
    r = vr.create_offline_renderer(environment(unit=unit, counter=counter))
    with pytest.raises(st.VisualSafetyFailure) as error:
        r.render(request())
    assert codes(error) == {'CAPACITY_UNVERIFIED'}
    assert r.state == 'FAILED_TERMINAL'


@pytest.mark.parametrize('mutation', [
    lambda release: replace(release, release_id='foreign'),
    lambda release: replace(release, version='foreign'),
    lambda release: replace(release, reviews=(replace(release.reviews[0], declared_by='unreviewed'),)),
    lambda release: replace(release, fragments=(replace(release.fragments[0],
        content=replace(release.fragments[0].content, text='Substituted style')), *release.fragments[1:])),
    lambda release: replace(release, fragments=(replace(release.fragments[0],
        entities=frozenset({'person'})), *release.fragments[1:])),
    lambda release: replace(release, scenes=(replace(release.scenes[0], required_entities=frozenset()),
                                             *release.scenes[1:])),
    lambda release: replace(release, fragments=tuple(replace(f, slot_annotations=())
                              if f.content.registry_id == 'lighting.time' else f for f in release.fragments)),
])
def test_forged_release_and_recomputed_manifest_cannot_replace_internal_pin(mutation):
    r = vr.create_offline_renderer(environment())
    forged = mutation(SEED_RELEASE)
    object.__setattr__(r._snapshot, 'release', forged)
    object.__setattr__(r._snapshot, 'manifest', manifest_for(forged))
    with pytest.raises(st.VisualSafetyFailure) as error:
        r.render(request())
    assert codes(error) == {'UNTRUSTED_AUTHORITY'}
    assert r.state == 'FAILED_TERMINAL' and r._gate is None
    with pytest.raises(st.VisualSafetyFailure):
        r.render(request(variant='forest_path.B'))
    assert r._gate is None


def test_fake_scene_contract_is_rejected_by_canonical_registry_check():
    r = vr.create_offline_renderer(environment())
    scene = replace(SEED_RELEASE.scenes[0], forbidden_keys=frozenset())
    with pytest.raises(RegistryError):
        r._snapshot.check_compatibility(scene, ())


@pytest.mark.parametrize('boundary', ['initial', 'actual'])
def test_both_compatibility_checks_are_mandatory_and_failures_terminal(monkeypatch, boundary):
    original = RegistrySnapshot.check_compatibility
    calls = []
    def observe(self, scene, selections, **kwargs):
        calls.append(selections)
        if (boundary == 'initial' and len(calls) == 1) or (boundary == 'actual' and len(calls) == 2):
            raise RegistryError('INCOMPATIBLE_SCENE_SLOT')
        return original(self, scene, selections, **kwargs)
    monkeypatch.setattr(RegistrySnapshot, 'check_compatibility', observe)
    r = vr.create_offline_renderer(environment())
    with pytest.raises(st.VisualSafetyFailure) as error:
        r.render(request())
    assert len(calls) == (1 if boundary == 'initial' else 2)
    assert codes(error) == {'SCENE_CONFLICT'}
    assert error.value.failure.result.stage == ('preflight' if boundary == 'initial' else 'final')
    assert r.registry_failure_code == 'INCOMPATIBLE_SCENE_SLOT'
    assert r._preview is None and r.state == 'FAILED_TERMINAL'
    if boundary == 'actual':
        assert any(s.registry_id == 'ban.system.text_marks' for s in calls[-1])


def test_preview_recheck_invokes_actual_compatibility_and_underlying_gate(monkeypatch):
    r, p = render()
    compatible, gate_checks = [], []
    original = RegistrySnapshot.check_compatibility
    gate_original = sg.SyntheticAssemblyGate.check_artifact
    def compatibility(self, scene, selections, **kwargs):
        compatible.append(selections)
        return original(self, scene, selections, **kwargs)
    def gate(self, artifact):
        gate_checks.append(artifact)
        return gate_original(self, artifact)
    monkeypatch.setattr(RegistrySnapshot, 'check_compatibility', compatibility)
    monkeypatch.setattr(sg.SyntheticAssemblyGate, 'check_artifact', gate)
    assert r.check_preview(p).outcome == 'allowed'
    assert len(compatible) == 1 and gate_checks == [p.artifact]
    assert compatible[0][-1] == ref('ban.system.text_marks')


def test_required_projection_cannot_be_lost_through_wrong_dedup(monkeypatch):
    original = sg.SyntheticAssemblyGate.assemble
    def lose(self, **kwargs):
        assembly = original(self, **kwargs)
        parts = tuple(f for f in assembly.candidate.fragments if f.provenance.slot_value != 'sunrise')
        return replace(assembly, candidate=replace(assembly.candidate, fragments=parts))
    monkeypatch.setattr(sg.SyntheticAssemblyGate, 'assemble', lose)
    r = vr.create_offline_renderer(environment())
    with pytest.raises(st.VisualSafetyFailure) as error:
        r.render(request('mountain_view', 'telephoto_layers', 'sunrise', 'cool', 'Show mountains at sunrise'))
    assert codes(error) == {'INVALID_ASSEMBLY'} and r._preview is None


@pytest.mark.parametrize('target,field,value', [
    ('assembly', 'prompt', 'suffix'), ('assembly', 'fragment_spans', ()),
    ('assembly', 'mandatory_bans', ()), ('assembly', 'registry_version', 'stale'),
    ('assembly', 'policy_version', 'stale'), ('assembly', 'authority_digest', 'stale'),
    ('candidate', 'scene_type', 'open_meadow'), ('candidate', 'fragments', ()),
    ('candidate', 'human_presence', 'single_person'), ('candidate', 'resolved_style', 'nature'),
    ('fragment', 'text', 'Changed text'), ('fragment', 'positive_keys', frozenset({('object', 'mug')})),
    ('origin', 'origin', 'raw_user_prose'), ('origin', 'evidence_refs', (('user_text', 99),)),
    ('origin', 'slot_value', 'warm'), ('occurrence', 'position', 99),
    ('occurrence', 'evidence_refs', (('user_text', 99),)), ('occurrence', 'exclusion_causes', ('USER_EXCLUSION',)),
    ('proof', 'release_digest', '0' * 64), ('proof', 'release_id', 'foreign'),
    ('proof', 'review_id', 'forged-review'), ('proof', 'review_digest', '0' * 64),
    ('proof', 'text', 'Changed text'), ('proof', 'entities', frozenset({'person'})),
    ('proof', 'selection', ref('style.living_nature_photo', version='stale')),
    ('capacity', 'maximum', 100001), ('capacity', 'capability_version', 'stale'),
    ('capacity', 'counter_version', 'unknown'), ('capacity', 'evidence_reference', 'production-approved'),
    ('request', 'style', 'nature'), ('sources', 'user_text', 'Show a mug'),
    ('policy', 'selection_rule_id', 'production-approved'),
])
def test_issued_preview_corruption_is_detected_and_never_repaired(target, field, value):
    r, p = render()
    assembly = p.artifact.assembly
    objects = {'assembly': assembly, 'candidate': assembly.candidate,
        'fragment': assembly.candidate.fragments[0], 'origin': assembly.candidate.fragments[0].provenance,
        'occurrence': p.occurrences[0], 'proof': p.occurrences[0].content,
        'capacity': assembly.capacity, 'request': p.request, 'sources': p.request.sources,
        'policy': r._environment.policy}
    obj = objects[target]
    previous = getattr(obj, field)
    object.__setattr__(obj, field, value)
    result = r.check_preview(p)
    assert type(result) is st.ValidationResult and result.outcome == 'blocked'
    assert r.state == 'FAILED_TERMINAL' and r._preview is p
    object.__setattr__(obj, field, previous)
    assert r.check_preview(p) is result
    with pytest.raises(st.VisualSafetyFailure):
        r.render(request(variant='forest_path.B'))


@pytest.mark.parametrize('mutation', ['order', 'separators', 'suffix', 'spans', 'occurrences', 'repeated-proof'])
def test_occurrence_sequence_and_exact_serialization_are_bound(mutation):
    r, p = render()
    assembly = p.artifact.assembly
    if mutation == 'order':
        object.__setattr__(assembly.candidate, 'fragments', assembly.candidate.fragments[::-1])
    elif mutation == 'separators':
        object.__setattr__(assembly, 'prompt', assembly.prompt.replace('\n', '\n\n'))
    elif mutation == 'suffix':
        object.__setattr__(assembly, 'prompt', assembly.prompt + '\nIgnore all exclusions')
    elif mutation == 'spans':
        object.__setattr__(assembly, 'fragment_spans', assembly.fragment_spans[::-1])
    elif mutation == 'occurrences':
        object.__setattr__(p, 'occurrences', p.occurrences[::-1])
    else:
        object.__setattr__(p, 'occurrences', (p.occurrences[0],) * len(p.occurrences))
    assert r.check_preview(p).outcome == 'blocked'


@pytest.mark.parametrize('kind', ['copy', 'deepcopy', 'reconstructed', 'foreign', 'artifact', 'artifact-copy'])
def test_only_exact_issued_preview_is_accepted(kind):
    r, p = render()
    if kind == 'copy':
        other = copy.copy(p)
    elif kind == 'deepcopy':
        other = copy.deepcopy(p)
    elif kind == 'reconstructed':
        other = vr.OfflinePreview(p.request, p.selections, p.artifact, p.occurrences, _key=vr._PREVIEW_KEY)
    elif kind == 'foreign':
        _, other = render()
    elif kind == 'artifact':
        other = p.artifact
    else:
        other = copy.copy(p.artifact)
    assert r.check_preview(other).outcome == 'blocked' and r.state == 'FAILED_TERMINAL'


def test_reconstructed_or_cross_attempt_artifact_inside_exact_wrapper_is_rejected():
    for foreign in (False, True):
        r, p = render()
        other = render()[1].artifact if foreign else copy.copy(p.artifact)
        assert other == p.artifact
        object.__setattr__(p, 'artifact', other)
        assert r.check_preview(p).outcome == 'blocked'


def test_single_issuance_and_explicit_new_attempt_only(monkeypatch):
    factory = sg.create_synthetic_gate
    gates = []
    def observe(*args, **kwargs):
        gate = factory(*args, **kwargs)
        gates.append(gate)
        return gate
    monkeypatch.setattr(sg, 'create_synthetic_gate', observe)
    r, p = render()
    assert len(gates) == 1
    for _ in range(3):
        with pytest.raises(st.VisualSafetyFailure):
            r.render(request(variant='forest_path.B'))
        assert r.check_preview(p).outcome == 'allowed'
    assert len(gates) == 1 and r._preview is p
    new, q = render()
    assert len(gates) == 2 and new is not r and q is not p


def test_gate_veto_never_constructs_replacement_gate(monkeypatch):
    factory = sg.create_synthetic_gate
    calls = []
    def observe(*args, **kwargs):
        calls.append(1)
        return factory(*args, **kwargs)
    monkeypatch.setattr(sg, 'create_synthetic_gate', observe)
    r = vr.create_offline_renderer(environment(1))
    with pytest.raises(st.VisualSafetyFailure):
        r.render(request())
    gate = r._gate
    assert r.state == 'FAILED_TERMINAL' and len(calls) == 1
    for alternate in (request(), request(variant='forest_path.B')):
        with pytest.raises(st.VisualSafetyFailure):
            r.render(alternate)
    assert calls == [1] and r._gate is gate and r._preview is None


def test_environment_substitution_and_post_factory_mutation_fail():
    for field, value in (('capabilities', ()), ('policy', replace(environment().policy, policy_version='other'))):
        env = environment()
        r = vr.create_offline_renderer(env)
        object.__setattr__(env, field, value)
        with pytest.raises(st.VisualSafetyFailure):
            r.render(request())
        assert r.state == 'FAILED_TERMINAL' and r._gate is None


@pytest.mark.parametrize('make', [
    lambda: vr.SourceFields([]), lambda: vr.SceneSelector([], VERSION),
    lambda: vr.ArtisticSelections([]), lambda: vr.ArtisticSelections((object(),)),
    lambda: vr.VariantSelector([], VERSION), lambda: vr.SyntheticTarget([], 'm', 's'),
    lambda: replace(request(), sources=sg.resolve_visual_intent),
    lambda: replace(request(), artistic=[]), lambda: replace(request(), target=[]),
    lambda: vr.SyntheticEnvironment([], ()),
    lambda: vr.SyntheticEnvironment(environment().policy, []),
    lambda: vr.SyntheticEnvironment(environment().policy, (object(),)),
    lambda: vr.SyntheticEnvironment(environment().policy, (environment().capabilities[0],) * 2),
    lambda: replace(environment(), policy=replace(environment().policy, context_ids=('forest_path',) * 2)),
])
def test_new_contracts_reject_malformed_and_nested_mutable_values_with_typed_failures(make):
    with pytest.raises(st.VisualSafetyFailure):
        make()


def test_new_boundary_ignores_overridden_equality_and_rejects_subclasses():
    class EqualStr(str):
        def __eq__(self, other):
            raise AssertionError('untrusted equality invoked')
        __hash__ = str.__hash__
    with pytest.raises(st.VisualSafetyFailure):
        vr.SourceFields(EqualStr('No people'))
    with pytest.raises(st.VisualSafetyFailure):
        vr.SceneSelector(EqualStr('forest_path'), VERSION)
    with pytest.raises(st.VisualSafetyFailure):
        replace(request(), style=EqualStr(STYLE))
    for cls, obj in ((vr.SourceFields, vr.SourceFields()), (vr.SceneSelector, vr.SceneSelector('forest_path', VERSION)),
                     (vr.ArtisticSelections, request().artistic), (vr.VariantSelector, vr.VariantSelector('forest_path.A', VERSION)),
                     (vr.SyntheticTarget, TARGET), (vr.RenderRequest, request()),
                     (vr.SyntheticEnvironment, environment())):
        subclass = type('EqualRecord', (cls,), {'__eq__': lambda self, other: True})
        forged = object.__new__(subclass)
        for f in fields(cls):
            object.__setattr__(forged, f.name, getattr(obj, f.name))
        with pytest.raises(st.VisualSafetyFailure):
            cls.__post_init__(forged)


def test_immutable_preview_and_nested_result_subclasses_are_rejected():
    r, p = render()
    with pytest.raises(FrozenInstanceError):
        p.request = request()
    with pytest.raises(FrozenInstanceError):
        p.occurrences[0].content.text = 'changed'
    for cls, obj in ((vr.OfflinePreview, p), (vr.FragmentOccurrence, p.occurrences[0]),
                     (st.PromptFragment, p.artifact.assembly.candidate.fragments[0]),
                     (st.PromptCapacity, p.artifact.assembly.capacity)):
        subclass = type('EqualResult', (cls,), {'__eq__': lambda self, other: True})
        forged = object.__new__(subclass)
        for f in fields(cls):
            object.__setattr__(forged, f.name, getattr(obj, f.name))
        with pytest.raises(st.VisualSafetyFailure):
            vr._bytes(forged)
    object.__setattr__(p, 'occurrences', list(p.occurrences))
    assert r.check_preview(p).outcome == 'blocked'


def test_request_cannot_admit_extra_authorities_or_production_flags(monkeypatch):
    monkeypatch.setenv('SG01_PRODUCTION_AUTHORIZED', 'true')
    monkeypatch.setenv('SG01_RENDERER_ENABLED', 'true')
    for extra in ('interpretation', 'resolution', 'auxiliary_sources', 'fragments', 'registry',
                  'expected_manifest', 'production_authorized', 'enforcement_route', 'separator', 'suffix'):
        with pytest.raises(TypeError):
            vr.RenderRequest(**{f.name: getattr(request(), f.name) for f in fields(vr.RenderRequest)}, **{extra: True})
    r, p = render()
    assert p.production_authorized is False and p.authority == 'synthetic_offline'
    assert r.check_preview(p).outcome == 'allowed'
    assert not hasattr(r, 'dispatch') and not hasattr(p, 'dispatch')


def test_construction_adapter_is_contract_driven_without_admitting_an_unpinned_scene():
    # Mechanical adapter probe only; it never enters render/issuance. Rename a
    # reviewed scene without a seed-name branch and retain exact component IDs.
    original = SEED_RELEASE.scenes[0]
    scene = replace(original, scene_id='future_woodland')
    fragments = tuple(replace(f, scene_ids=tuple('future_woodland' if s == original.scene_id else s for s in f.scene_ids),
        slot_annotations=tuple(replace(a, scene_ids=tuple('future_woodland' if s == original.scene_id else s
                          for s in a.scene_ids)) for a in f.slot_annotations)) for f in SEED_RELEASE.fragments)
    release = replace(SEED_RELEASE, fragments=fragments,
                      scenes=(scene, *SEED_RELEASE.scenes[1:]), variants=tuple(
                          replace(v, scene_id='future_woodland') if v.scene_id == original.scene_id else v
                          for v in SEED_RELEASE.variants))
    mechanical = RegistrySnapshot(release, manifest_for(release))
    adapted = vr._adapt(mechanical, scene, environment())
    assert adapted.contexts[0].scene_type == 'future_woodland'
    assert adapted.contexts[0].base_fragments[1].registry_id == 'scene.forest_path'
    assert next(f for f in adapted.fragments if f.registry_id == 'composition.forest_path').slot_values
    with pytest.raises(RegistryError):
        seed_registry(release)
    r = vr.create_offline_renderer(environment())
    with pytest.raises(st.VisualSafetyFailure):
        r.render(replace(request(), scene=vr.SceneSelector('future_woodland', VERSION)))


def test_fresh_process_imports_only_offline_dependencies():
    script = (
        "import sys; import services.visual_safety; "
        "assert 'services.visual_renderer' not in sys.modules; "
        "import services.visual_registry_content; "
        "assert 'services.visual_renderer' not in sys.modules; "
        "import services.visual_renderer; "
        "assert not set(sys.modules) & {'config','database','aiohttp','requests',"
        "'services.openai_image','services.yandex_gpt','services.coastal_intent',"
        "'services.ritual_config','services.scene_planner','handlers.generation','scheduler','cli'}"
    )
    subprocess.run([sys.executable, '-B', '-c', script], cwd=Path(__file__).resolve().parents[1],
                   capture_output=True, check=True)


def test_only_designated_renderer_can_import_registry_and_no_consumer_imports_renderer():
    root = Path(__file__).resolve().parents[1]
    paths = list(root.glob('*.py'))
    for directory in ('services', 'handlers', 'keyboards'):
        paths.extend((root / directory).rglob('*.py'))
    for path in paths:
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        names = set()
        for node in ast.walk(tree):
            if type(node) is ast.Import:
                names.update(a.name for a in node.names)
            if type(node) is ast.ImportFrom:
                names.add(node.module or '')
                if node.module == 'services':
                    names.update(a.name for a in node.names)
            if type(node) is ast.Constant and type(node.value) is str:
                names.add(node.value)
        if path.stem != 'visual_renderer':
            assert not names & {'visual_renderer', 'services.visual_renderer'}, path
        if path.stem not in {'visual_renderer', 'visual_registry', 'visual_registry_content'}:
            assert not names & {'services.visual_registry', 'services.visual_registry_content',
                                'visual_registry', 'visual_registry_content'}, path


@pytest.mark.parametrize('value', [None, {}, [], 'prompt', object(), sg.FinalAssembly, RegistrySnapshot])
def test_render_accepts_only_exact_request_and_failure_is_terminal(value):
    r = vr.create_offline_renderer(environment())
    with pytest.raises(st.VisualSafetyFailure):
        r.render(value)
    assert r.state == 'FAILED_TERMINAL' and r._gate is None
    with pytest.raises(st.VisualSafetyFailure):
        r.render(request())
    assert r._gate is None


@pytest.mark.parametrize('field,value', [
    ('sources', []), ('artistic', {}), ('scene', object()), ('target', None), ('style', []),
])
def test_post_construction_mutable_or_malformed_request_is_rejected(field, value):
    req = request()
    object.__setattr__(req, field, value)
    r = vr.create_offline_renderer(environment())
    with pytest.raises(st.VisualSafetyFailure):
        r.render(req)
    assert r.state == 'FAILED_TERMINAL' and r._gate is None


@pytest.mark.parametrize('field,value', [
    ('occurrences', None), ('occurrences', {}), ('artifact', object()), ('request', None), ('selections', []),
])
def test_malformed_issued_preview_returns_stable_typed_failure(field, value):
    r, p = render()
    object.__setattr__(p, field, value)
    result = r.check_preview(p)
    assert type(result) is st.ValidationResult and result.outcome == 'blocked'
    assert r.check_preview(p) is result and r.state == 'FAILED_TERMINAL'


def test_check_before_issuance_terminates_attempt_without_starting_construction():
    r = vr.create_offline_renderer(environment())
    result = r.check_preview(object())
    assert result.outcome == 'blocked' and r._gate is None
    with pytest.raises(st.VisualSafetyFailure):
        r.render(request())


def test_skipping_initial_compatibility_cannot_admit_incompatible_actual_content(monkeypatch):
    original = RegistrySnapshot.check_compatibility
    calls = []
    def skip_first(self, scene, selections, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            return frozenset()
        return original(self, scene, selections, **kwargs)
    monkeypatch.setattr(RegistrySnapshot, 'check_compatibility', skip_first)
    r = vr.create_offline_renderer(environment())
    # Both values exist for mountain, so 1B can build them independently; 1C
    # must reject the incompatible required sunrise + optional evening axis.
    with pytest.raises(st.VisualSafetyFailure):
        r.render(request('mountain_view', 'telephoto_layers', 'evening', 'cool', 'Show mountains at sunrise'))
    assert r.state == 'FAILED_TERMINAL' and r._preview is None
    assert r._gate is not None  # actual gate's qualifier conflict vetoed it


def test_skipping_actual_compatibility_cannot_hide_fragment_provenance_forgery(monkeypatch):
    original_assemble = sg.SyntheticAssemblyGate.assemble
    original_compatibility = RegistrySnapshot.check_compatibility
    calls = []
    def skip_actual(self, scene, selections, **kwargs):
        calls.append(1)
        return original_compatibility(self, scene, selections, **kwargs) if len(calls) == 1 else frozenset()
    def forge(self, **kwargs):
        assembly = original_assemble(self, **kwargs)
        fragment = replace(assembly.candidate.fragments[0], text='A person holding a mug')
        return replace(assembly, candidate=replace(assembly.candidate,
                       fragments=(fragment, *assembly.candidate.fragments[1:])))
    monkeypatch.setattr(RegistrySnapshot, 'check_compatibility', skip_actual)
    monkeypatch.setattr(sg.SyntheticAssemblyGate, 'assemble', forge)
    r = vr.create_offline_renderer(environment())
    with pytest.raises(st.VisualSafetyFailure) as error:
        r.render(request())
    assert codes(error) == {'UNTRUSTED_AUTHORITY'} and r._preview is None


def test_actual_compatibility_includes_required_sunrise_projection(monkeypatch):
    original = RegistrySnapshot.check_compatibility
    calls = []
    def observe(self, scene, selections, **kwargs):
        calls.append((selections, kwargs))
        return original(self, scene, selections, **kwargs)
    monkeypatch.setattr(RegistrySnapshot, 'check_compatibility', observe)
    r, p = render(request('mountain_view', 'telephoto_layers', 'sunrise', 'cool', 'Show mountains at sunrise'))
    assert len(calls) == 2
    for selections, kwargs in calls:
        assert sum(s == ref('lighting.time', 'sunrise') for s in selections) == 1
        assert kwargs['required_keys'] == {('scene', 'mountain'), ('qualifier', 'sunrise')}
    assert p.artifact.assembly.candidate.optional_selections == (
        vs.FragmentSelection('composition.mountain_view', 'telephoto_layers'), vs.FragmentSelection('palette.natural', 'cool'))
    assert r.check_preview(p).outcome == 'allowed' and len(calls) == 3


@pytest.mark.parametrize('failure_point', ['preflight', 'assemble', 'validate_final_assembly', 'check_artifact'])
def test_each_gate_failure_is_terminal_and_never_issues_or_retries(monkeypatch, failure_point):
    def veto(self, *args, **kwargs):
        vr._fail('INVALID_ASSEMBLY', 'final')
    monkeypatch.setattr(sg.SyntheticAssemblyGate, failure_point, veto)
    r = vr.create_offline_renderer(environment())
    with pytest.raises(st.VisualSafetyFailure) as error:
        r.render(request())
    assert codes(error) == {'INVALID_ASSEMBLY'}
    gate = r._gate
    assert r.state == 'FAILED_TERMINAL' and r._preview is None
    with pytest.raises(st.VisualSafetyFailure):
        r.render(request(variant='forest_path.B'))
    assert r._gate is gate


def test_underlying_artifact_verification_failure_on_recheck_is_terminal(monkeypatch):
    r, p = render()
    result = st.ValidationResult('blocked', 'final', (st.ValidationIssue('STALE_VALIDATION', 'final'),), '')
    monkeypatch.setattr(sg.SyntheticAssemblyGate, 'check_artifact', lambda self, artifact: result)
    assert r.check_preview(p) is result and r.state == 'FAILED_TERMINAL'


def test_stale_pin_after_success_is_rechecked():
    r, p = render()
    forged = replace(SEED_RELEASE, reviews=(replace(SEED_RELEASE.reviews[0], declared_by='unreviewed'),))
    object.__setattr__(r._snapshot, 'release', forged)
    assert r.check_preview(p).outcome == 'blocked' and r.state == 'FAILED_TERMINAL'


def test_cross_release_occurrence_proof_does_not_gain_authority_from_equal_text():
    r, p = render()
    foreign = replace(SEED_RELEASE, release_id='foreign')
    snapshot = RegistrySnapshot(foreign, manifest_for(foreign))
    proof = snapshot.lookup(p.occurrences[0].content.selection)
    assert proof.text == p.occurrences[0].content.text
    object.__setattr__(p.occurrences[0], 'content', proof)
    assert r.check_preview(p).outcome == 'blocked'


@pytest.mark.parametrize('mutation', [
    lambda env: object.__setattr__(env.policy, 'context_ids', ['forest_path']),
    lambda env: object.__setattr__(env.policy, 'covered_keys', set(COVERED)),
    lambda env: object.__setattr__(env.capabilities[0], 'sizes', ['offline-size']),
    lambda env: object.__setattr__(env.capabilities[0].capacity, 'maximum', True),
    lambda env: object.__setattr__(env.capabilities[0].capacity, 'adapter_id', []),
])
def test_malformed_nested_environment_is_rejected_even_before_binding(mutation):
    env = environment()
    mutation(env)
    with pytest.raises(st.VisualSafetyFailure):
        vr.create_offline_renderer(env)


def test_empty_capability_registration_is_capacity_unverified():
    env = replace(environment(), capabilities=())
    r = vr.create_offline_renderer(env)
    with pytest.raises(st.VisualSafetyFailure) as error:
        r.render(request())
    assert codes(error) == {'CAPACITY_UNVERIFIED'}


def test_unapproved_policy_binding_and_missing_ban_coverage_are_not_accepted():
    env = environment()
    with pytest.raises(st.VisualSafetyFailure):
        vr.create_offline_renderer(replace(env, policy=replace(env.policy, registry_version='caller-manifest')))
    r = vr.create_offline_renderer(replace(env, policy=replace(env.policy, covered_keys=frozenset())))
    with pytest.raises(st.VisualSafetyFailure) as error:
        r.render(request())
    assert codes(error) == {'UNTRUSTED_ENFORCEMENT_UNPROVEN'}


def test_new_record_schema_arity_matches_declared_contracts():
    assert tuple(f.name for f in fields(vr.RenderRequest)) == ('sources', 'style', 'mode', 'scene', 'artistic', 'target')
    assert tuple(f.name for f in fields(vr.SyntheticEnvironment)) == ('policy', 'capabilities')
    assert tuple(f.name for f in fields(vr.OfflinePreview)) == ('request', 'selections', 'artifact', 'occurrences')
    assert tuple(f.name for f in fields(vr.FragmentOccurrence)) == (
        'position', 'span', 'content', 'origin', 'evidence_refs', 'exclusion_causes', 'scene')


def test_uninitialized_exact_contracts_take_typed_failure_paths():
    with pytest.raises(st.VisualSafetyFailure):
        vr.create_offline_renderer(object.__new__(vr.SyntheticEnvironment))
    r = vr.create_offline_renderer(environment())
    with pytest.raises(st.VisualSafetyFailure):
        r.render(object.__new__(vr.RenderRequest))
    assert r.state == 'FAILED_TERMINAL'


def test_full_no_text_is_exact_and_has_only_system_authority():
    r, p = render(request(text=''))
    occurrence = p.occurrences[-1]
    assert occurrence.content.selection == ref('ban.system.text_marks')
    assert occurrence.content.text == 'No text, words, letters, numbers, typography, logos, or watermarks.'
    assert occurrence.content.role == 'no_text' and occurrence.content.excluded_keys == {SYSTEM}
    assert occurrence.origin == 'system_rule' and occurrence.evidence_refs == ()
    assert occurrence.exclusion_causes == ('SYSTEM_NO_TEXT',)
    assert r.check_preview(p).outcome == 'allowed'


@pytest.mark.parametrize('value', [[], {}, None])
def test_environment_factory_does_not_infer_defaults(value):
    with pytest.raises(st.VisualSafetyFailure):
        vr.create_offline_renderer(value)


@pytest.mark.parametrize('copier', [copy.copy, copy.deepcopy, pickle.dumps])
@pytest.mark.parametrize('state', ['CREATED', 'PREVIEW_ISSUED', 'FAILED_TERMINAL'])
def test_attempt_state_cannot_be_copied_or_serialized_to_restart_it(copier, state):
    r = vr.create_offline_renderer(environment())
    if state == 'PREVIEW_ISSUED':
        r.render(request())
    elif state == 'FAILED_TERMINAL':
        with pytest.raises(st.VisualSafetyFailure):
            r.render(replace(request(), style='unknown'))
    assert r.state == state
    with pytest.raises(st.VisualSafetyFailure) as error:
        copier(r)
    assert codes(error) == {'UNTRUSTED_AUTHORITY'} and r.state == state


def test_occurrence_contract_reports_typed_failures_for_corrupt_nested_records():
    _, p = render()
    original = p.occurrences[0]
    content = replace(original.content)
    object.__setattr__(content, 'positive_keys', [])
    with pytest.raises(st.VisualSafetyFailure):
        replace(original, content=content)
    span = replace(original.span)
    object.__setattr__(span, 'start', False)
    with pytest.raises(st.VisualSafetyFailure):
        replace(original, span=span)


# CP-01: hand-authored expectations, independent of the renderer mapping table.
REGISTRY_VETOES = (
    ('INCOMPATIBLE_SCENE', 'SCENE_CONFLICT'),
    ('INCOMPATIBLE_SCENE_SLOT', 'SCENE_CONFLICT'),
    ('CONFLICTING_ARTISTIC_DIMENSION', 'SCENE_CONFLICT'),
    ('CONFLICTING_TIME_QUALIFIERS', 'SCENE_CONFLICT'),
    ('SEMANTIC_CONFLICT', 'SCENE_CONFLICT'),
    ('FORBIDDEN_CONTENT', 'FORBIDDEN_POSITIVE_CONTENT'),
    ('FORBIDDEN_ENTITY', 'FORBIDDEN_POSITIVE_CONTENT'),
    ('MISSING_SCENE_IDENTITY', 'MISSING_REQUIRED_VISUAL_FACT'),
    ('MISSING_REQUIRED_KEY', 'MISSING_REQUIRED_VISUAL_FACT'),
    ('MISSING_EXCLUSION_COVERAGE', 'MISSING_MANDATORY_EXCLUSION'),
    ('INVALID_RECORD', 'INVALID_EVIDENCE'),
    ('INVALID_UNICODE', 'INVALID_EVIDENCE'),
    ('INVALID_DIGEST', 'INVALID_EVIDENCE'),
    ('DUPLICATE_IDENTITY', 'INVALID_EVIDENCE'),
    ('DANGLING_REVIEW', 'INVALID_EVIDENCE'),
    ('DANGLING_SCENE', 'INVALID_EVIDENCE'),
    ('INCOMPLETE_SLOT_ANNOTATIONS', 'INVALID_EVIDENCE'),
    ('INVALID_SLOT_SCHEMA', 'INVALID_EVIDENCE'),
    ('INVALID_ARTISTIC_CONTRACT', 'INVALID_EVIDENCE'),
    ('INVALID_BINDING', 'INVALID_EVIDENCE'),
    ('EMPTY_VARIANT', 'INVALID_EVIDENCE'),
    ('RELEASE_INTEGRITY_MISMATCH', 'INVALID_EVIDENCE'),
    ('CONTENT_INTEGRITY_MISMATCH', 'INVALID_EVIDENCE'),
    ('INVALID_REVIEW_BASIS', 'UNTRUSTED_AUTHORITY'),
    ('UNKNOWN_SCHEMA', 'UNTRUSTED_AUTHORITY'),
    ('UNKNOWN_FRAGMENT', 'UNTRUSTED_AUTHORITY'),
    ('UNKNOWN_FRAGMENT_VERSION', 'UNTRUSTED_AUTHORITY'),
    ('UNKNOWN_SLOT_VALUE', 'UNTRUSTED_AUTHORITY'),
    ('UNSUPPORTED_COVERAGE', 'UNTRUSTED_AUTHORITY'),
    ('UNKNOWN_SCENE_VERSION', 'UNTRUSTED_AUTHORITY'),
    ('UNKNOWN_VARIANT', 'UNTRUSTED_AUTHORITY'),
    ('UNKNOWN_VARIANT_VERSION', 'UNTRUSTED_AUTHORITY'),
)


def assert_terminal_reuse_is_fenced(monkeypatch, renderer, preview, result):
    gate, issued = renderer._gate, renderer._preview
    def forbidden(*args, **kwargs):
        pytest.fail('terminal attempt re-entered selection, construction or verification')
    with monkeypatch.context() as guard:
        guard.setattr(vr, '_selections', forbidden)
        guard.setattr(vr.OfflineRenderer, '_verify_assembly', forbidden)
        guard.setattr(sg, 'create_synthetic_gate', forbidden)
        for alternate in (request(), request(variant='forest_path.B'),
                          request('mountain_view', 'telephoto_layers', 'sunrise')):
            with pytest.raises(st.VisualSafetyFailure) as error:
                renderer.render(alternate)
            assert codes(error) == {'STALE_VALIDATION'}
        for candidate in (preview, object()):
            assert renderer.check_preview(candidate) is result
    assert renderer.state == 'FAILED_TERMINAL'
    assert renderer._gate is gate and renderer._preview is issued


@pytest.mark.parametrize('registry_code,reason', REGISTRY_VETOES)
@pytest.mark.parametrize('boundary,stage', [('initial', 'preflight'), ('actual', 'final'), ('preview', 'final')])
def test_registry_veto_reason_stage_and_closed_detail(monkeypatch, registry_code, reason, boundary, stage):
    r = vr.create_offline_renderer(environment())
    p = r.render(request()) if boundary == 'preview' else None
    original = RegistrySnapshot.check_compatibility
    calls = []
    def veto(self, scene, selections, **kwargs):
        calls.append(selections)
        if boundary != 'actual' or len(calls) == 2:
            raise RegistryError(registry_code)
        return original(self, scene, selections, **kwargs)
    with monkeypatch.context() as fault:
        fault.setattr(RegistrySnapshot, 'check_compatibility', veto)
        if boundary == 'preview':
            result = r.check_preview(p)
        else:
            with pytest.raises(st.VisualSafetyFailure) as error:
                r.render(request())
            assert error.value.failure.retryable is False
            assert str(error.value) == reason
            result = error.value.failure.result
    assert type(result) is st.ValidationResult and result.outcome == 'blocked'
    assert result.stage == stage
    assert [(i.code, i.stage, i.detail) for i in result.issues] == [(reason, stage, None)]
    assert r.registry_failure_code == registry_code
    with pytest.raises(AttributeError):
        r.registry_failure_code = 'caller-prose'
    assert len(calls) == (2 if boundary == 'actual' else 1)
    assert (r._gate is None) == (boundary == 'initial')
    assert_terminal_reuse_is_fenced(monkeypatch, r, p, result)
    assert r.registry_failure_code == registry_code


@pytest.mark.parametrize('args', [(), ('private caller prose',), ('INCOMPATIBLE_SCENE', 'extra'),
                                  (['INCOMPATIBLE_SCENE'],)])
@pytest.mark.parametrize('operation', ['render', 'preview'])
def test_unknown_registry_errors_remain_typed_terminal_and_never_echo_prose(monkeypatch, args, operation):
    r = vr.create_offline_renderer(environment())
    p = r.render(request()) if operation == 'preview' else None
    def veto(*a, **kw):
        raise RegistryError(*args)
    with monkeypatch.context() as fault:
        fault.setattr(RegistrySnapshot, 'check_compatibility', veto)
        if operation == 'render':
            with pytest.raises(st.VisualSafetyFailure) as error:
                r.render(request())
            assert str(error.value) == 'UNTRUSTED_AUTHORITY'
            assert error.value.__suppress_context__ is True
            assert error.value.failure.retryable is False
            result = error.value.failure.result
        else:
            result = r.check_preview(p)
    stage = 'preflight' if operation == 'render' else 'final'
    assert result == st.ValidationResult('blocked', stage,
        (st.ValidationIssue('UNTRUSTED_AUTHORITY', stage),), '')
    assert r.registry_failure_code == 'UNKNOWN_REGISTRY_ERROR'
    assert_terminal_reuse_is_fenced(monkeypatch, r, p, result)


@pytest.mark.parametrize('registry_code,reason', [
    ('MISSING_EXCLUSION_COVERAGE', 'MISSING_MANDATORY_EXCLUSION'),
    ('RELEASE_INTEGRITY_MISMATCH', 'INVALID_EVIDENCE'),
    ('INVALID_REVIEW_BASIS', 'UNTRUSTED_AUTHORITY'),
    ('private caller prose', 'UNTRUSTED_AUTHORITY'),
])
def test_factory_registry_veto_uses_existing_preflight_contract(monkeypatch, registry_code, reason):
    def veto(*args, **kwargs):
        raise RegistryError(registry_code)
    monkeypatch.setattr(vr, 'seed_registry', veto)
    with pytest.raises(st.VisualSafetyFailure) as error:
        vr.create_offline_renderer(environment())
    assert codes(error) == {reason}
    assert error.value.failure.result.stage == 'preflight'
    assert error.value.failure.retryable is False


def test_real_release_integrity_failure_keeps_specific_diagnostic(monkeypatch):
    r = vr.create_offline_renderer(environment())
    original = r._snapshot.release
    object.__setattr__(r._snapshot, 'release', replace(original, version='foreign'))
    with pytest.raises(st.VisualSafetyFailure) as error:
        r.render(request())
    assert codes(error) == {'INVALID_EVIDENCE'}
    assert error.value.failure.result.stage == 'preflight'
    assert r.registry_failure_code == 'RELEASE_INTEGRITY_MISMATCH'
    object.__setattr__(r._snapshot, 'release', original)
    assert_terminal_reuse_is_fenced(monkeypatch, r, None, error.value.failure.result)


@pytest.mark.parametrize('exception_type', [KeyError, StopIteration, RuntimeError, AssertionError])
@pytest.mark.parametrize('owner,name,stage,has_gate', [
    (vr.OfflineRenderer, '_intact', 'preflight', False),
    (vr.vi, 'interpret_visual_intent', 'interpretation', False),
    (vr, '_selections', 'preflight', False),
    (sg, 'create_synthetic_gate', 'preflight', False),
    (sg.SyntheticAssemblyGate, 'preflight', 'preflight', True),
    (sg.SyntheticAssemblyGate, 'assemble', 'candidate', True),
    (vr.OfflineRenderer, '_verify_assembly', 'final', True),
    (sg.SyntheticAssemblyGate, 'validate_final_assembly', 'final', True),
    (sg.SyntheticAssemblyGate, 'check_artifact', 'final', True),
    (vr, 'OfflinePreview', 'final', True),
])
def test_unexpected_render_defect_is_reraised_with_traceback_and_terminal_state(
        monkeypatch, exception_type, owner, name, stage, has_gate):
    r = vr.create_offline_renderer(environment())
    defect, cause = exception_type('implementation defect'), RuntimeError('original cause')
    calls = []
    def crash(*args, **kwargs):
        calls.append(1)
        raise defect from cause
    with monkeypatch.context() as fault:
        fault.setattr(owner, name, crash)
        with pytest.raises(exception_type) as error:
            r.render(request())
    assert error.value is defect and error.value.__cause__ is cause
    frames = traceback.extract_tb(error.value.__traceback__)
    assert frames[-1].name == 'crash' and any(f.name == 'render' for f in frames)
    assert calls == [1] and r._preview is None
    assert (r._gate is not None) is has_gate
    assert r.registry_failure_code is None
    result = r.check_preview(object())
    assert result == st.ValidationResult('blocked', stage, (st.ValidationIssue('INVALID_EVIDENCE', stage),), '')
    assert_terminal_reuse_is_fenced(monkeypatch, r, None, result)


@pytest.mark.parametrize('exception_type', [KeyError, StopIteration, RuntimeError, AssertionError])
@pytest.mark.parametrize('owner,name', [
    (vr.OfflineRenderer, '_intact'), (vr, '_bytes'), (RegistrySnapshot, 'scene'),
    (vr, '_selections'), (vr.OfflineRenderer, '_verify_assembly'),
    (sg.SyntheticAssemblyGate, 'check_artifact'),
])
def test_unexpected_preview_defect_invalidates_issued_preview_and_preserves_traceback(
        monkeypatch, exception_type, owner, name):
    r, p = render()
    defect, cause = exception_type('implementation defect'), RuntimeError('original cause')
    def crash(*args, **kwargs):
        raise defect from cause
    with monkeypatch.context() as fault:
        fault.setattr(owner, name, crash)
        with pytest.raises(exception_type) as error:
            r.check_preview(p)
    assert error.value is defect and error.value.__cause__ is cause
    frames = traceback.extract_tb(error.value.__traceback__)
    assert frames[-1].name == 'crash' and any(f.name == 'check_preview' for f in frames)
    result = r.check_preview(p)
    assert result == st.ValidationResult('blocked', 'final',
        (st.ValidationIssue('INVALID_EVIDENCE', 'final'),), '')
    assert r.registry_failure_code is None and r._preview is p
    assert_terminal_reuse_is_fenced(monkeypatch, r, p, result)


@pytest.mark.parametrize('operation', ['render', 'preview'])
def test_expected_safety_veto_retains_its_original_reason_stage_and_result(monkeypatch, operation):
    r = vr.create_offline_renderer(environment())
    p = r.render(request()) if operation == 'preview' else None
    # Deliberately different from the wrapper's current phase: preserve owner data.
    result = st.ValidationResult('blocked', 'interpretation',
        (st.ValidationIssue('UNRESOLVED_EXCLUSION', 'interpretation', detail='relational_scope'),), '')
    def veto(*args, **kwargs):
        st.safety_failure(result)
    with monkeypatch.context() as fault:
        fault.setattr(vr.OfflineRenderer, '_verify_assembly', veto)
        if operation == 'render':
            with pytest.raises(st.VisualSafetyFailure) as error:
                r.render(request())
            assert error.value.failure.result is result
            assert error.value.failure.retryable is False
        else:
            assert r.check_preview(p) is result
    assert r.registry_failure_code is None
    assert_terminal_reuse_is_fenced(monkeypatch, r, p, result)


@pytest.mark.parametrize('exception_type', [KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize('operation', ['render', 'preview'])
def test_process_control_exceptions_are_never_normalized_or_suppressed(monkeypatch, exception_type, operation):
    r = vr.create_offline_renderer(environment())
    p = r.render(request()) if operation == 'preview' else None
    control = exception_type('stop')
    def interrupt(*args, **kwargs):
        raise control
    monkeypatch.setattr(vr.OfflineRenderer, '_intact', interrupt)
    with pytest.raises(exception_type) as error:
        r.render(request()) if operation == 'render' else r.check_preview(p)
    assert error.value is control
