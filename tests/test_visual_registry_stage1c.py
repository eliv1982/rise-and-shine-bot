"""Hand-authored real-content oracles, through the unchanged offline 1B gate.

The bridge, route and capability below exist ONLY in tests. No live APIs.
"""
import ast
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
import subprocess
import sys

import pytest

from services import visual_intent as vi, visual_safety as sg, visual_semantics as vs
from services.visual_registry import (
    ConstructionVariant, ContentFragment, ContentRelease, KeyBinding,
    RegisteredContent, RegistryError, RegistrySelection, RegistrySnapshot,
    ReleaseManifest, ReviewDeclaration, SceneContract, SlotAnnotation,
    canonical_bytes, content_digest, manifest_for, validate_release,
)
from services.visual_registry_content import SEED_MANIFEST, SEED_RELEASE, seed_registry
from services.visual_safety_types import PromptCapacity, VisualSafetyFailure


STYLE = 'living_nature_photo'
VERSION = '1.0.0'
PIN = 'a57ab2fbc218564c2ed00290cb8866a25e4a07009889442705990719ac007864'
SYSTEM = ('system', 'text_marks')
ABSENCE = frozenset({('object', 'body'), ('object', 'hands'), ('object', 'human')})


def ref(name, value=None, version=VERSION):
    return RegistrySelection(name, version, value)


def _key(domain, key):
    return (domain.value if type(domain) is vi.FactDomain else domain, key)


def bridge(scene_id, label='A', *, text=None, adapter='offline-test-adapter',
           model='offline-test-model', size='offline-test-size'):
    """No runtime adapter. Keep 1B contracts, preflight and final checks intact."""
    snapshot = seed_registry()
    scene = snapshot.scene(scene_id, style=STYLE, mode='photo', version=VERSION)
    variant = snapshot.variant(f'{scene_id}.{label}', version=VERSION)
    if text is None:
        text = ('Show mountains at sunrise; No people; No mugs' if scene_id == 'mountain_view' and label == 'A'
                else 'Show mountains; No people; No mugs' if scene_id == 'mountain_view'
                else 'No people; No mugs')
    resolution = sg.resolve_visual_intent(vi.interpret_visual_intent(text, style=STYLE),
                                         requested_style=STYLE, requested_mode='photo')
    # 1B cannot represent per-scene closed-slot compatibility. Restrict the
    # synthetic fixture to EXACT compatible values, then check 1C combinations.
    fragments, available = [], set()
    for entry in snapshot.release.fragments:
        if scene_id not in entry.scene_ids:
            continue
        content = entry.content
        values = tuple(v for v in content.slot_values if any(
            a.value_id == v.value_id and scene_id in a.scene_ids for a in entry.slot_annotations))
        if content.slot_values and not values:
            continue
        fragments.append(replace(content, slot_values=values))
        available.update((content.registry_id, v.value_id) for v in values)
        if not values:
            available.add((content.registry_id, None))
    positive_bindings = tuple(vs.ProjectionBinding(b.key,
        vs.FragmentSelection(b.selection.registry_id, b.selection.slot_value))
        for b in snapshot.release.positive_bindings
        if (b.selection.registry_id, b.selection.slot_value) in available)
    exclusions = tuple(vs.ProjectionBinding(b.key,
        vs.FragmentSelection(b.selection.registry_id, b.selection.slot_value))
        for b in snapshot.release.exclusion_bindings)
    # Fake capacity is a test algorithm input, never a real model limit.
    cap = PromptCapacity('offline-test-adapter', 'offline-test-model', 'unicode_codepoints',
                         100000, 'python-len-v1', 'synthetic-test-evidence-only', 'test-cap-v1')
    context = vs.ControlledContext(scene.scene_id, scene.style, scene.style, scene.mode, scene.scene_id,
        tuple(vs.FragmentSelection(s.registry_id, s.slot_value) for s in scene.base_fragments),
        (vs.PresenceBinding('none', ()),), scene.human_presence, scene.required_keys)
    # The 1B provenance version binds the entire immutable 1C release, including
    # individual fragment versions and author-review metadata, without new fields.
    bound_version = f'{snapshot.release.release_id}@{snapshot.release.version}#{snapshot.manifest.payload_digest}'
    registry = vs.SyntheticRegistry(bound_version, tuple(fragments), positive_bindings, exclusions,
                                    (context,), (vs.SyntheticCapability(cap, ('offline-test-size',)),))
    policy = vs.SyntheticPolicy('stage1c-test-policy-v1', 'stage1c-test-early-rule-v1', registry.version,
                               (scene.scene_id,), frozenset(b.key for b in exclusions))
    gate = sg.create_synthetic_gate(resolution, registry, policy, context_id=scene.scene_id,
                                    adapter_id=adapter, model=model, size=size)
    required = frozenset(_key(f.domain, f.key) for f in resolution.effective_facts
                         if f.polarity == vi.Polarity.POSITIVE)
    forbidden = frozenset(_key(b.domain, b.key) for b in resolution.mandatory_bans)
    snapshot.check_compatibility(scene, variant.selections, required_keys=required, forbidden_keys=forbidden)
    projected = {(b.selection.registry_id, b.selection.slot_value) for b in snapshot.release.positive_bindings
                 if b.key in required | scene.required_keys}
    optional = tuple(vs.FragmentSelection(s.registry_id, s.slot_value) for s in variant.selections
                     if (s.registry_id, s.slot_value) not in projected)
    return gate, optional, snapshot


# Independent literal oracles. No expected phrase, key, selection or ordering is
# read from the implementation under test. Only the fixed LF join is shared.
EXPECTED_STYLE = 'Living nature photography with believable natural textures, optical depth, and restrained photographic contrast.'
EXPECTED_SCENE = {
    'forest_path': 'A continuous earthen footpath curves between living woodland trees, with ferns along its edges.',
    'open_meadow': 'An open meadow of grasses and scattered wildflowers extends to a distant natural horizon.',
    'mountain_view': 'A mountain landscape with layered ridgelines and exposed rock faces above a deep valley.',
}
EXPECTED_BANS = ('No visible human body parts.', 'No hands.', 'No people or human figures.',
                 'No mugs or cups.', 'No text, words, letters, numbers, typography, logos, or watermarks.')
MOUNTAIN_ANCHOR = 'Keep the mountain ridges as the essential subject of the photograph.'
COOL = 'Palette: cool greens and blue-gray shadows, with subtle pale highlights and natural color separation.'
WARM = 'Palette: warm ochre highlights and muted earth colors balanced by deeper neutral shadows.'
MORNING = 'Lighting: soft morning side light reveals fine texture through open shade.'
SUNRISE = 'Lighting: at sunrise, low first light touches the upper ridges while the valley remains in cool shadow.'
CASES = (
    ('forest_path', 'A', 'low_leading_curve', 'morning', 'cool', (
        'Composition: a low camera beside foreground ferns follows the path as a deep leading curve between tall tree trunks.',
        MORNING, COOL)),
    ('forest_path', 'B', 'elevated_diagonal', 'daylight', 'warm', (
        'Composition: an elevated oblique view places the path diagonally across the frame, with overlapping tree crowns forming successive layers.',
        'Lighting: clear midday light filters into alternating patches of sun and shade.', WARM)),
    ('open_meadow', 'A', 'grass_level_depth', 'morning', 'cool', (
        'Composition: a grass-level camera holds nearby wildflowers in crisp focus while the meadow recedes into a softly distant horizon.',
        MORNING, COOL)),
    ('open_meadow', 'B', 'elevated_horizon_bands', 'sunset', 'warm', (
        'Composition: an elevated viewpoint uses broad horizontal bands of meadow and sky, with small flower clusters forming an off-center rhythm.',
        'Lighting: at sunset, a low warm glow grazes the meadow beneath a softly luminous sky.', WARM)),
    ('mountain_view', 'A', 'telephoto_layers', 'sunrise', 'cool', (
        SUNRISE, MOUNTAIN_ANCHOR,
        'Composition: a telephoto panorama compresses successive ridgelines into overlapping silhouettes, with the distant summit high in the frame.',
        COOL)),
    ('mountain_view', 'B', 'wide_rock_foreground', 'evening', 'warm', (
        MOUNTAIN_ANCHOR,
        'Composition: a wide field of view anchors the lower corner with a granite ledge and opens diagonally into the valley and distant peaks.',
        'Lighting: gentle evening side light outlines the rock faces and lengthens shadows into the valley.', WARM)),
)


@pytest.mark.parametrize('scene,label,composition,lighting,palette,middle', CASES)
def test_six_real_content_positive_paths(scene, label, composition, lighting, palette, middle):
    gate, optional, snapshot = bridge(scene, label)
    assert gate.preflight().validation.outcome == 'allowed'
    assembly = gate.assemble(optional_selections=optional)
    expected = (EXPECTED_STYLE, EXPECTED_SCENE[scene], *middle, *EXPECTED_BANS)
    assert assembly.prompt == '\n'.join(expected)
    position = 0
    for fragment, span, literal in zip(assembly.candidate.fragments, assembly.fragment_spans, expected, strict=True):
        assert fragment.text == literal
        assert (span.start, span.end) == (position, position + len(literal))
        position += len(literal) + 1
        proof = snapshot.lookup(ref(fragment.provenance.registry_id, fragment.provenance.slot_value))
        snapshot.verify_content(proof)
        assert (fragment.text, fragment.role, fragment.positive_keys, fragment.excluded_keys,
                fragment.conditional_keys) == (proof.text, proof.role, proof.positive_keys,
                                             proof.excluded_keys, proof.conditional_keys)
        assert fragment.provenance.registry_version == 'sg01-nature-seed@1.0.0#' + PIN
        assert proof.review_id == 'sg01-stage1c-author-review-v1'
    assert assembly.candidate.scene_type == scene
    assert assembly.candidate.resolved_style == STYLE and assembly.candidate.effective_mode == 'photo'
    assert assembly.candidate.human_presence == 'none'
    assert all(not (f.positive_keys | f.conditional_keys) & ABSENCE for f in assembly.candidate.fragments)
    assert {(b.domain, b.key) for b in assembly.mandatory_bans} == ABSENCE | {('object', 'mug'), SYSTEM}
    selections = {(f.provenance.registry_id, f.provenance.slot_value) for f in assembly.candidate.fragments}
    assert {(f'composition.{scene}', composition), ('lighting.time', lighting), ('palette.natural', palette)} <= selections
    artifact = gate.validate_final_assembly(assembly)
    assert type(artifact) is sg.SyntheticValidatedAssembly
    assert artifact.authority == 'synthetic_offline' and artifact.production_authorized is False
    assert gate.check_artifact(artifact).outcome == 'allowed'


def test_mountain_sunrise_has_exact_user_qualifier_and_exclusion_provenance():
    gate, optional, _ = bridge('mountain_view')
    assembly = gate.assemble(optional_selections=optional)
    facts = gate.resolution.interpretation.facts
    assert [(f.domain.value, f.key, f.directive_id, (f.span.start, f.span.end)) for f in facts] == [
        ('scene', 'mountain', 0, (5, 14)), ('qualifier', 'sunrise', 0, (18, 25)),
        ('object', 'human', 1, (30, 36)), ('object', 'mug', 2, (41, 45))]
    projections = [(f.provenance.registry_id, f.provenance.slot_value, f.provenance.origin,
                    f.provenance.evidence_refs) for f in assembly.candidate.fragments]
    assert projections == [
        ('style.living_nature_photo', None, 'curated', ()),
        ('scene.mountain_view', None, 'curated', ()),
        ('lighting.time', 'sunrise', 'user_projection', (('user_text', 0),)),
        ('subject.mountain', None, 'user_projection', (('user_text', 0),)),
        ('composition.mountain_view', 'telephoto_layers', 'curated', ()),
        ('palette.natural', 'cool', 'curated', ()),
        ('ban.object.body', None, 'user_projection', (('user_text', 1),)),
        ('ban.object.hands', None, 'user_projection', (('user_text', 1),)),
        ('ban.object.human', None, 'user_projection', (('user_text', 1),)),
        ('ban.object.mug', None, 'user_projection', (('user_text', 2),)),
        ('ban.system.text_marks', None, 'system_rule', ()),
    ]
    assert [(b.key, b.causes) for b in assembly.mandatory_bans] == [
        ('body', ('HUMAN_EXCLUSION_CASCADE', 'SCENE_HUMAN_NONE', 'USER_EXCLUSION')),
        ('hands', ('HUMAN_EXCLUSION_CASCADE', 'SCENE_HUMAN_NONE', 'USER_EXCLUSION')),
        ('human', ('SCENE_HUMAN_NONE', 'USER_EXCLUSION')),
        ('mug', ('USER_EXCLUSION',)), ('text_marks', ('SYSTEM_NO_TEXT',))]


@pytest.mark.parametrize('scene,essentials,a,b', [
    ('forest_path', {'footpath', 'trees'}, 'low_leading_curve', 'elevated_diagonal'),
    ('open_meadow', {'meadow', 'grass', 'wildflowers'}, 'grass_level_depth', 'elevated_horizon_bands'),
    ('mountain_view', {'mountain', 'ridges', 'valley'}, 'telephoto_layers', 'wide_rock_foreground'),
])
def test_variation_has_independent_spatial_and_lighting_oracles(scene, essentials, a, b):
    snapshot = seed_registry()
    contract = snapshot.scene(scene, style=STYLE, mode='photo', version=VERSION)
    assert contract.required_entities == essentials
    va = snapshot.variant(f'{scene}.A', version=VERSION)
    vb = snapshot.variant(f'{scene}.B', version=VERSION)
    assert va.selections[0] == ref(f'composition.{scene}', a)
    assert vb.selections[0] == ref(f'composition.{scene}', b)
    assert va.selections[1].slot_value != vb.selections[1].slot_value
    for variant in (va, vb):
        snapshot.check_compatibility(contract, variant.selections)
    # Specific perspective changes, rather than ID diversity or synonym counts.
    expected_cues = {
        'forest_path': ('low camera', 'elevated oblique view'),
        'open_meadow': ('grass-level camera', 'elevated viewpoint'),
        'mountain_view': ('telephoto panorama', 'wide field of view'),
    }
    assert expected_cues[scene][0] in snapshot.lookup(va.selections[0]).text
    assert expected_cues[scene][1] in snapshot.lookup(vb.selections[0]).text


def test_manifest_and_canonical_content_inventory():
    validate_release(SEED_RELEASE)
    snapshot = seed_registry()
    assert snapshot.manifest.payload_digest == PIN == content_digest(SEED_RELEASE)
    assert len(snapshot.release.fragments) == 24
    assert tuple(s.scene_id for s in snapshot.release.scenes) == ('forest_path', 'open_meadow', 'mountain_view')
    assert tuple(v.variant_id for v in snapshot.release.variants) == (
        'forest_path.A', 'forest_path.B', 'open_meadow.A', 'open_meadow.B', 'mountain_view.A', 'mountain_view.B')
    assert {b.key for b in snapshot.release.positive_bindings} == {
        ('scene', 'mountain'), ('qualifier', 'morning'), ('qualifier', 'sunrise'),
        ('qualifier', 'sunset'), ('qualifier', 'evening')}
    assert {b.key for b in snapshot.release.exclusion_bindings} == {
        ('object', 'body'), ('object', 'hands'), ('object', 'human'), ('object', 'mug'),
        ('object', 'notebook'), ('object', 'table'), ('object', 'window'),
        ('coastal', 'beach'), ('coastal', 'coast'), ('coastal', 'lagoon'),
        ('coastal', 'rocky'), ('coastal', 'sandy'), ('coastal', 'water'), SYSTEM}
    assert canonical_bytes(ref('lighting.time', 'sunrise')) == (
        b'{"fields":{"registry_id":"lighting.time","slot_value":"sunrise","version":"1.0.0"},"type":"RegistrySelection"}')


@pytest.mark.parametrize('scene,style,mode', [
    ('desert', STYLE, 'photo'), ('interior', STYLE, 'photo'),
    ('forest_path', 'auto', 'photo'), ('forest_path', 'custom', 'photo'),
    ('forest_path', 'sea_coast_photo', 'photo'), ('forest_path', STYLE, 'symbolic'),
    ('forest_path', STYLE, 'illustration'), ('forest_path', 'sunny_nature_photo', 'photo'),
])
def test_unsupported_coverage_is_explicit_without_seed_redirection(scene, style, mode):
    with pytest.raises(RegistryError, match='UNSUPPORTED_COVERAGE'):
        seed_registry().scene(scene, style=style, mode=mode, version=VERSION)


@pytest.mark.parametrize('selection,code', [
    (ref('unknown'), 'UNKNOWN_FRAGMENT'),
    (ref('scene.forest_path', version='2.0.0'), 'UNKNOWN_FRAGMENT_VERSION'),
    (ref('lighting.time', 'after dinner with a mug'), 'UNKNOWN_SLOT_VALUE'),
    (ref('lighting.time'), 'UNKNOWN_SLOT_VALUE'),
    (ref('scene.forest_path', 'sunrise'), 'UNKNOWN_SLOT_VALUE'),
])
def test_exact_lookup_rejects_unknown_id_version_and_arbitrary_slot(selection, code):
    with pytest.raises(RegistryError, match=code):
        seed_registry().lookup(selection)


def test_scene_and_variant_versions_are_required():
    snapshot = seed_registry()
    for version in ('0.0.0', '2.0.0'):
        with pytest.raises(RegistryError, match='UNKNOWN_SCENE_VERSION'):
            snapshot.scene('forest_path', style=STYLE, mode='photo', version=version)
        with pytest.raises(RegistryError, match='UNKNOWN_VARIANT_VERSION'):
            snapshot.variant('forest_path.A', version=version)
    with pytest.raises(RegistryError, match='UNKNOWN_VARIANT'):
        snapshot.variant('forest_path.C', version=VERSION)


def _changed_fragment(release, name, change):
    return replace(release, fragments=tuple(change(f) if f.content.registry_id == name else f
                                           for f in release.fragments))


@pytest.mark.parametrize('mutation', ['text', 'annotations', 'review', 'slot_text', 'slot_entities',
                                     'variant', 'scene_identity', 'binding'])
def test_rehashed_alterations_under_same_release_identity_cannot_replace_seed(mutation):
    original = SEED_RELEASE
    if mutation == 'text':
        changed = _changed_fragment(original, 'composition.forest_path', lambda f: replace(f,
            content=replace(f.content, text='A mug beside the footpath: {value}')))
    elif mutation == 'annotations':
        changed = _changed_fragment(original, 'scene.forest_path', lambda f: replace(f,
            content=replace(f.content, positive_keys=frozenset({('object', 'mug')}))))
    elif mutation == 'review':
        changed = replace(original, reviews=(replace(original.reviews[0],
            declared_by='Forged external reviewer', evidence='Claims of completed independent acceptance'),))
    elif mutation == 'slot_text':
        changed = _changed_fragment(original, 'palette.natural', lambda f: replace(f,
            content=replace(f.content, slot_values=(replace(f.content.slot_values[0],
                text='a bright sign with letters and a visible cup'), f.content.slot_values[1]))))
    elif mutation == 'slot_entities':
        changed = _changed_fragment(original, 'composition.forest_path', lambda f: replace(f,
            slot_annotations=(replace(f.slot_annotations[0], entities=frozenset()), f.slot_annotations[1])))
    elif mutation == 'variant':
        changed = replace(original, variants=(replace(original.variants[0], selections=(
            ref('composition.forest_path', 'elevated_diagonal'), ref('lighting.time', 'morning'),
            ref('palette.natural', 'cool'))), *original.variants[1:]))
    elif mutation == 'scene_identity':
        changed = replace(original, scenes=(replace(original.scenes[0], required_entities=frozenset({'trees'})),
                                            *original.scenes[1:]))
    else:
        changed = replace(original, positive_bindings=original.positive_bindings[:-1])
    # These examples remain mechanically consistent; an attacker can compute
    # hashes. Only comparison to the fixed content/review identity rejects them.
    validate_release(changed)
    recomputed = manifest_for(changed)
    assert recomputed.payload_digest != PIN
    assert RegistrySnapshot(changed, recomputed).manifest.payload_digest == content_digest(changed)
    with pytest.raises(RegistryError, match='RELEASE_INTEGRITY_MISMATCH'):
        seed_registry(changed)
    with pytest.raises(RegistryError, match='RELEASE_INTEGRITY_MISMATCH'):
        seed_registry().verify_release(changed)


@pytest.mark.parametrize('field,value', [
    ('text', 'Substituted exact text.'), ('positive_keys', frozenset({('object', 'mug')})),
    ('review_id', 'forged-review'), ('review_digest', 'f' * 64),
    ('release_version', '2.0.0'), ('release_digest', 'f' * 64),
    ('selection', ref('scene.open_meadow')),
])
def test_lookup_provenance_is_reconstructed_not_asserted(field, value):
    snapshot = seed_registry()
    proof = snapshot.lookup(ref('scene.forest_path'))
    with pytest.raises(RegistryError, match='CONTENT_INTEGRITY_MISMATCH'):
        snapshot.verify_content(replace(proof, **{field: value}))


@pytest.mark.parametrize('mutation,code', [
    ('review', 'DANGLING_REVIEW'), ('scene', 'DANGLING_SCENE'),
    ('fragment_version', 'UNKNOWN_FRAGMENT_VERSION'), ('binding_id', 'UNKNOWN_FRAGMENT'),
    ('slot_annotation', 'INCOMPLETE_SLOT_ANNOTATIONS'),
    ('duplicate_fragment', 'DUPLICATE_IDENTITY'), ('missing_ban', 'MISSING_EXCLUSION_COVERAGE'),
    ('missing_subject', 'MISSING_SCENE_IDENTITY'),
])
def test_mechanical_release_validation_rejects_dangling_or_incomplete_contracts(mutation, code):
    release = SEED_RELEASE
    if mutation == 'review':
        release = replace(release, reviews=(replace(release.reviews[0], review_id='new-review'),))
    elif mutation == 'scene':
        release = _changed_fragment(release, 'scene.forest_path', lambda f: replace(f, scene_ids=('unknown',)))
    elif mutation == 'fragment_version':
        release = _changed_fragment(release, 'scene.forest_path', lambda f: replace(f, version='2.0.0'))
    elif mutation == 'binding_id':
        release = replace(release, positive_bindings=(replace(release.positive_bindings[0],
            selection=ref('unknown')), *release.positive_bindings[1:]))
    elif mutation == 'slot_annotation':
        release = _changed_fragment(release, 'palette.natural', lambda f: replace(f, slot_annotations=()))
    elif mutation == 'duplicate_fragment':
        release = replace(release, fragments=(*release.fragments, release.fragments[0]))
    elif mutation == 'missing_ban':
        release = replace(release, exclusion_bindings=tuple(b for b in release.exclusion_bindings if b.key != SYSTEM))
    else:
        release = replace(release, scenes=(replace(release.scenes[0],
            base_fragments=(ref('style.living_nature_photo'),)), *release.scenes[1:]))
    with pytest.raises(RegistryError, match=code):
        RegistrySnapshot(release, manifest_for(release))


@pytest.mark.parametrize('selections,required,forbidden,code', [
    ((ref('composition.open_meadow', 'grass_level_depth'),), frozenset(), frozenset(), 'INCOMPATIBLE_SCENE'),
    ((ref('lighting.time', 'sunrise'),), frozenset(), frozenset(), 'INCOMPATIBLE_SCENE_SLOT'),
    ((ref('lighting.time', 'morning'), ref('lighting.time', 'daylight')), frozenset(), frozenset(), 'CONFLICTING_ARTISTIC_DIMENSION'),
    ((ref('lighting.time', 'morning'),), frozenset({('qualifier', 'sunrise')}), frozenset(), 'CONFLICTING_TIME_QUALIFIERS'),
    ((ref('lighting.time', 'morning'),), frozenset(), frozenset({('qualifier', 'morning')}), 'FORBIDDEN_CONTENT'),
    ((), frozenset({('object', 'mug')}), frozenset(), 'MISSING_REQUIRED_KEY'),
])
def test_artistic_compatibility_is_semantic_not_a_decorative_exemption(selections, required, forbidden, code):
    snapshot = seed_registry()
    scene = snapshot.scene('forest_path', style=STYLE, mode='photo', version=VERSION)
    with pytest.raises(RegistryError, match=code):
        snapshot.check_compatibility(scene, selections, required_keys=required, forbidden_keys=forbidden)


@pytest.mark.parametrize('introduction', ['entity', 'positive', 'conditional', 'exclusion'])
def test_artistic_object_introduction_is_checked_even_with_recomputed_manifest(introduction):
    def introduce(entry):
        if introduction == 'entity':
            return replace(entry, entities=frozenset({'building'}))
        if introduction == 'positive':
            return replace(entry, content=replace(entry.content, positive_keys=frozenset({('object', 'human')})))
        if introduction == 'conditional':
            return replace(entry, content=replace(entry.content, conditional_keys=frozenset({('object', 'hands')})))
        value = replace(entry.content.slot_values[0], excluded_keys=frozenset({('object', 'mug')}))
        return replace(entry, content=replace(entry.content, slot_values=(value, entry.content.slot_values[1])))
    release = _changed_fragment(SEED_RELEASE, 'composition.forest_path', introduce)
    with pytest.raises(RegistryError, match='FORBIDDEN_ENTITY|FORBIDDEN_CONTENT|INVALID_ARTISTIC_CONTRACT'):
        RegistrySnapshot(release, manifest_for(release))


def test_declared_artistic_mug_cannot_evade_a_dynamic_user_exclusion():
    release = _changed_fragment(SEED_RELEASE, 'composition.forest_path', lambda f: replace(f,
        content=replace(f.content, positive_keys=frozenset({('object', 'mug')}))))
    mechanical = RegistrySnapshot(release, manifest_for(release))
    scene = mechanical.scene('forest_path', style=STYLE, mode='photo', version=VERSION)
    with pytest.raises(RegistryError, match='FORBIDDEN_CONTENT'):
        mechanical.check_compatibility(scene, (ref('composition.forest_path', 'low_leading_curve'),),
                                        forbidden_keys=frozenset({('object', 'mug')}))


def test_cross_release_substitution_and_manifest_spoof_are_rejected():
    changed = replace(SEED_RELEASE, version='2.0.0')
    other = RegistrySnapshot(changed, manifest_for(changed))
    proof = other.lookup(ref('scene.forest_path'))
    with pytest.raises(RegistryError, match='CONTENT_INTEGRITY_MISMATCH'):
        seed_registry().verify_content(proof)
    with pytest.raises(RegistryError, match='RELEASE_INTEGRITY_MISMATCH'):
        RegistrySnapshot(SEED_RELEASE, replace(SEED_MANIFEST, version='2.0.0'))
    with pytest.raises(RegistryError, match='UNKNOWN_SCHEMA'):
        seed_registry(replace(SEED_RELEASE, schema_version='unregistered-schema'))


def _records():
    return (SEED_RELEASE.reviews[0], ref('lighting.time', 'morning'),
            SEED_RELEASE.fragments[5].slot_annotations[0], SEED_RELEASE.fragments[0],
            SEED_RELEASE.positive_bindings[0], SEED_RELEASE.scenes[0], SEED_RELEASE.variants[0],
            SEED_RELEASE, SEED_MANIFEST, seed_registry().lookup(ref('scene.forest_path')),
            SEED_RELEASE.fragments[0].content, SEED_RELEASE.fragments[5].content.slot_values[0])


@pytest.mark.parametrize('original', _records(), ids=lambda r: type(r).__name__)
def test_all_new_records_and_nested_neutral_records_reject_subclass_equality_attacks(original):
    evil_type = type('AlwaysEqual', (type(original),), {
        '__eq__': lambda self, other: True, '__hash__': lambda self: 0,
        '__post_init__': lambda self: None,
    })
    evil = object.__new__(evil_type)
    for field in fields(original):
        object.__setattr__(evil, field.name, getattr(original, field.name))
    assert evil == original  # Demonstrate the attack, then reject exact type.
    with pytest.raises(RegistryError, match='INVALID_RECORD'):
        canonical_bytes(evil)
    if type(original) is RegistrySelection:
        with pytest.raises(RegistryError, match='INVALID_RECORD'):
            seed_registry().lookup(evil)
    if type(original) is ContentRelease:
        with pytest.raises(RegistryError, match='INVALID_RECORD'):
            seed_registry(evil)
    if type(original) is RegisteredContent:
        with pytest.raises(RegistryError, match='INVALID_RECORD'):
            seed_registry().verify_content(evil)
    if type(original) is SceneContract:
        with pytest.raises(RegistryError, match='INVALID_RECORD'):
            seed_registry().check_compatibility(evil, ())


def test_snapshot_subclass_cannot_override_integrity_check_or_equality():
    class FakeSnapshot(RegistrySnapshot):
        def __post_init__(self):
            pass

        def _intact(self):
            pass

        def __eq__(self, other):
            return True

    evil = FakeSnapshot(SEED_RELEASE, SEED_MANIFEST)
    with pytest.raises(RegistryError, match='INVALID_RECORD'):
        evil.lookup(ref('scene.forest_path'))
    with pytest.raises(RegistryError, match='INVALID_RECORD'):
        evil.verify_content(seed_registry().lookup(ref('scene.forest_path')))


@pytest.mark.parametrize('mutation', ['fragment_list', 'entity_set', 'slot_list', 'keys_set',
                                     'nested_list', 'tuple_subclass', 'set_subclass', 'string_subclass'])
def test_nested_mutable_or_overridable_values_never_survive_frozen_contracts(mutation):
    entry = SEED_RELEASE.fragments[5]
    class TupleSubclass(tuple):
        pass
    class SetSubclass(frozenset):
        pass
    class StringSubclass(str):
        def __eq__(self, other):
            return True
        __hash__ = str.__hash__
    with pytest.raises(RegistryError, match='INVALID_RECORD'):
        if mutation == 'fragment_list':
            replace(SEED_RELEASE, fragments=list(SEED_RELEASE.fragments))
        elif mutation == 'entity_set':
            replace(entry, entities={'mug'})
        elif mutation == 'slot_list':
            nested = replace(entry.content, slot_values=TupleSubclass(entry.content.slot_values))
            object.__setattr__(nested, 'slot_values', list(nested.slot_values))
            replace(entry, content=nested)
        elif mutation == 'keys_set':
            nested = replace(entry.content)
            object.__setattr__(nested, 'positive_keys', {('object', 'mug')})
            replace(entry, content=nested)
        elif mutation == 'nested_list':
            nested = replace(entry.slot_annotations[0])
            object.__setattr__(nested, 'scene_ids', ['forest_path'])
            replace(entry, slot_annotations=(nested, entry.slot_annotations[1]))
        elif mutation == 'tuple_subclass':
            replace(entry, scene_ids=TupleSubclass(entry.scene_ids))
        elif mutation == 'set_subclass':
            replace(entry, entities=SetSubclass(entry.entities))
        else:
            nested = replace(entry.content, text=StringSubclass(entry.content.text))
            replace(entry, content=nested)


def test_freezing_is_transitive_and_post_construction_integrity_is_rechecked():
    for record in (*_records(), seed_registry()):
        field = fields(record)[0]
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            setattr(record, field.name, 'changed')
        assert not hasattr(record, '__dict__')
    # Deliberate object.__setattr__ is outside normal freezing, but even this
    # local corruption is detected while the snapshot's pinned manifest stays intact.
    cloned_content = replace(SEED_RELEASE.fragments[0].content)
    cloned_entry = replace(SEED_RELEASE.fragments[0], content=cloned_content)
    cloned_release = replace(SEED_RELEASE, fragments=(cloned_entry, *SEED_RELEASE.fragments[1:]))
    snapshot = RegistrySnapshot(cloned_release, SEED_MANIFEST)
    object.__setattr__(cloned_content, 'text', 'Hidden replacement text.')
    with pytest.raises(RegistryError, match='RELEASE_INTEGRITY_MISMATCH'):
        snapshot.lookup(ref('style.living_nature_photo'))
    assert seed_registry().manifest.payload_digest == PIN


@pytest.mark.parametrize('mutation', ['suffix', 'separator', 'order', 'fragment_text', 'semantic_keys',
                                     'review_version', 'source_ref', 'slot_ref', 'release_version'])
def test_unchanged_stage1b_final_validation_rejects_serialization_and_provenance_forgery(mutation):
    gate, optional, _ = bridge('forest_path')
    assembly = gate.assemble(optional_selections=optional)
    if mutation == 'suffix':
        changed = replace(assembly, prompt=assembly.prompt + '\nShow a cup.')
    elif mutation == 'separator':
        changed = replace(assembly, prompt=assembly.prompt.replace('\n', '; '))
    elif mutation == 'order':
        changed = replace(assembly, candidate=replace(assembly.candidate,
            fragments=tuple(reversed(assembly.candidate.fragments))))
    elif mutation == 'release_version':
        changed = replace(assembly, registry_version='sg01-nature-seed@2.0.0#' + PIN)
    else:
        f = assembly.candidate.fragments[2]
        if mutation == 'fragment_text':
            f = replace(f, text='A cup stands on a table.')
        elif mutation == 'semantic_keys':
            f = replace(f, positive_keys=frozenset({('object', 'mug')}))
        elif mutation == 'review_version':
            f = replace(f, provenance=replace(f.provenance, registry_version='forged-review-release'))
        elif mutation == 'source_ref':
            f = replace(f, provenance=replace(f.provenance, evidence_refs=(('unknown_source', 0),)))
        else:
            f = replace(f, provenance=replace(f.provenance, slot_value='unregistered'))
        changed = replace(assembly, candidate=replace(assembly.candidate,
            fragments=(*assembly.candidate.fragments[:2], f, *assembly.candidate.fragments[3:])))
    assert gate.check_final_assembly(changed).outcome == 'blocked'
    assert gate.check_final_assembly(assembly).outcome == 'blocked'  # terminal veto


@pytest.mark.parametrize('unknown', ['adapter', 'model', 'size', 'asserted_capacity'])
def test_unknown_capability_cannot_be_presented_as_verified(unknown):
    kwargs = {unknown: 'unregistered'} if unknown != 'asserted_capacity' else {}
    gate, _, _ = bridge('forest_path', **kwargs)
    if unknown == 'asserted_capacity':
        claimed = PromptCapacity('offline-test-adapter', 'offline-test-model', 'unicode_codepoints',
            200000, 'python-len-v1', 'Claimed verified real provider', 'test-cap-v1')
        result = gate.check_preflight(capacity=claimed)
    else:
        result = gate.check_preflight()
    assert {i.code for i in result.issues} == {'CAPACITY_UNVERIFIED'}


def test_synthetic_authority_cannot_be_promoted_or_reconstructed(monkeypatch):
    gate, optional, _ = bridge('forest_path')
    artifact = gate.validate_final_assembly(gate.assemble(optional_selections=optional, trace='production approved'))
    monkeypatch.setenv('SG01_PRODUCTION_AUTHORIZED', 'true')
    assert artifact.authority == 'synthetic_offline' and artifact.production_authorized is False
    for field, value in (('authority', 'production'), ('production_authorized', True)):
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            setattr(artifact, field, value)
    forged = sg.SyntheticValidatedAssembly(artifact.assembly, artifact.validation, _key=sg._FACTORY_KEY)
    assert {i.code for i in gate.check_artifact(forged).issues} == {'STALE_VALIDATION'}
    other, _, _ = bridge('forest_path')
    other.preflight()
    assert other.check_artifact(artifact).outcome == 'blocked'


def test_review_evidence_is_not_independent_acceptance_or_production_authority():
    declaration = SEED_RELEASE.reviews[0]
    assert declaration.basis == 'author_semantic_review'
    assert declaration.declared_by == 'Codex implementation author'
    assert 'PENDING' in declaration.limitations
    assert not {'approved', 'accepted', 'production_authorized'} & {f.name for f in fields(declaration)}
    snapshot = seed_registry()
    assert not any(hasattr(snapshot, n) for n in ('dispatch', 'to_production', 'production_authorized'))
    with pytest.raises(RegistryError, match='INVALID_REVIEW_BASIS'):
        replace(declaration, basis='owner_accepted')


@pytest.mark.parametrize('text,code', [
    ('No mugs on tables', 'UNRESOLVED_EXCLUSION'),
    ('No people near windows', 'UNRESOLVED_EXCLUSION'),
    ('No glargs', 'UNRESOLVED_EXCLUSION'),
    ('Show a story about mugs and windows', 'UNSUPPORTED_VISUAL_REQUEST'),
    ('No mugs; Show a cup', 'OBJECT_CONFLICT'),
    ('Show a forest path', 'UNSUPPORTED_VISUAL_REQUEST'),
])
def test_existing_negative_and_narrative_authority_is_not_expanded_for_real_content(text, code):
    with pytest.raises(VisualSafetyFailure, match=code):
        bridge('forest_path', text=text)


def test_registry_is_extensible_without_silently_enabling_other_product_contexts():
    # A NEW mechanically consistent scene needs its own explicit declarations.
    # No enum or three-scene maximum is hard-coded into the contracts.
    extra = replace(SEED_RELEASE.scenes[0], scene_id='future_woodland', version='0.1.0')
    fragments = tuple(replace(f, scene_ids=(*f.scene_ids, 'future_woodland'))
                      if 'forest_path' in f.scene_ids else f for f in SEED_RELEASE.fragments)
    expanded = replace(SEED_RELEASE, version='future-sample', fragments=fragments,
                       scenes=(*SEED_RELEASE.scenes, extra))
    mechanical = RegistrySnapshot(expanded, manifest_for(expanded))
    assert mechanical.scene('future_woodland', style=STYLE, mode='photo', version='0.1.0').scene_id == 'future_woodland'
    with pytest.raises(RegistryError, match='UNSUPPORTED_COVERAGE'):
        seed_registry().scene('future_woodland', style=STYLE, mode='photo', version='0.1.0')


def test_runtime_import_isolation_in_a_fresh_process():
    script = (
        "import sys; import services.visual_safety; "
        "assert 'services.visual_registry' not in sys.modules; "
        "assert 'services.visual_registry_content' not in sys.modules; "
        "from services.visual_registry_content import seed_registry; seed_registry(); "
        "assert not set(sys.modules) & {'config','database','aiohttp','requests',"
        "'services.openai_image','services.yandex_gpt','services.coastal_intent',"
        "'services.ritual_config','services.scene_planner','handlers.generation','scheduler'}"
    )
    subprocess.run([sys.executable, '-B', '-c', script], check=True, capture_output=True,
                   cwd=Path(__file__).resolve().parents[1])


def test_no_runtime_dynamic_registry_import_or_provider_dependency():
    root = Path(__file__).resolve().parents[1]
    paths = list(root.glob('*.py'))
    for directory in ('services', 'handlers', 'keyboards'):
        paths.extend((root / directory).rglob('*.py'))
    for path in paths:
        if path.stem in {'visual_registry', 'visual_registry_content'}:
            continue
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        # Complements Package A's static-import oracle for named dynamic loads.
        assert not any(type(n) is ast.Constant and type(n.value) is str and
                       n.value in {'services.visual_registry', 'services.visual_registry_content',
                                   'visual_registry', 'visual_registry_content'} for n in ast.walk(tree)), path
