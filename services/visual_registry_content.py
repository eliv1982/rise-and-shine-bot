"""Original Stage 1C seed literals and proposed author semantic-review evidence.

This extensible validation slice is NOT a product scene/style restriction.
No route, capability, provider, application configuration or renderer is loaded.
Independent Claude Code audit and Owner acceptance remain PENDING.
"""
from services.visual_semantics import ClosedSlotValue, RegisteredFragment
from services.visual_registry import (
    ConstructionVariant, ContentFragment, ContentRelease, KeyBinding,
    RegistrySelection, RegistrySnapshot, ReleaseManifest, ReviewDeclaration,
    SceneContract, SlotAnnotation,
)


VERSION = '1.0.0'
RELEASE_ID = 'sg01-nature-seed'
STYLE = 'living_nature_photo'
MODE = 'photo'
SCENES = ('forest_path', 'open_meadow', 'mountain_view')
REVIEW_ID = 'sg01-stage1c-author-review-v1'


def _ref(name, value=None):
    return RegistrySelection(name, VERSION, value)


def _fragment(name, role, text, *, dimension, scenes=SCENES, entities=frozenset(),
              positive=frozenset(), excluded=frozenset(), values=(), annotations=()):
    return ContentFragment(VERSION,
        RegisteredFragment(name, role, text, positive, excluded, frozenset(), values),
        'artistic' if dimension in {'composition', 'lighting', 'palette'} else 'semantic',
        dimension, scenes, entities, annotations, REVIEW_ID)


_STYLE = _fragment('style.living_nature_photo', 'style',
    'Living nature photography with believable natural textures, optical depth, and restrained photographic contrast.',
    dimension='style')
_SCENE_FRAGMENTS = (
    _fragment('scene.forest_path', 'positive_scene',
        'A continuous earthen footpath curves between living woodland trees, with ferns along its edges.',
        dimension='scene', scenes=('forest_path',), entities=frozenset({'footpath', 'trees', 'ferns'})),
    _fragment('scene.open_meadow', 'positive_scene',
        'An open meadow of grasses and scattered wildflowers extends to a distant natural horizon.',
        dimension='scene', scenes=('open_meadow',), entities=frozenset({'meadow', 'grass', 'wildflowers'})),
    _fragment('scene.mountain_view', 'positive_scene',
        'A mountain landscape with layered ridgelines and exposed rock faces above a deep valley.',
        dimension='scene', scenes=('mountain_view',), entities=frozenset({'mountain', 'ridges', 'rock', 'valley'}),
        positive=frozenset({('scene', 'mountain')})),
    _fragment('subject.mountain', 'positive_scene',
        'Keep the mountain ridges as the essential subject of the photograph.',
        dimension='scene', scenes=('mountain_view',), entities=frozenset({'mountain', 'ridges'}),
        positive=frozenset({('scene', 'mountain')})),
)

_COMPOSITIONS = (
    _fragment('composition.forest_path', 'positive_scene', 'Composition: {value}',
        dimension='composition', scenes=('forest_path',), values=(
            ClosedSlotValue('low_leading_curve',
                'a low camera beside foreground ferns follows the path as a deep leading curve between tall tree trunks.'),
            ClosedSlotValue('elevated_diagonal',
                'an elevated oblique view places the path diagonally across the frame, with overlapping tree crowns forming successive layers.'),
        ), annotations=(
            SlotAnnotation('low_leading_curve', ('forest_path',), frozenset({'ferns', 'footpath', 'trees'})),
            SlotAnnotation('elevated_diagonal', ('forest_path',), frozenset({'footpath', 'trees'})),
        )),
    _fragment('composition.open_meadow', 'positive_scene', 'Composition: {value}',
        dimension='composition', scenes=('open_meadow',), values=(
            ClosedSlotValue('grass_level_depth',
                'a grass-level camera holds nearby wildflowers in crisp focus while the meadow recedes into a softly distant horizon.'),
            ClosedSlotValue('elevated_horizon_bands',
                'an elevated viewpoint uses broad horizontal bands of meadow and sky, with small flower clusters forming an off-center rhythm.'),
        ), annotations=(
            SlotAnnotation('grass_level_depth', ('open_meadow',), frozenset({'grass', 'wildflowers', 'meadow'})),
            SlotAnnotation('elevated_horizon_bands', ('open_meadow',), frozenset({'meadow', 'sky', 'wildflowers'})),
        )),
    _fragment('composition.mountain_view', 'positive_scene', 'Composition: {value}',
        dimension='composition', scenes=('mountain_view',), values=(
            ClosedSlotValue('telephoto_layers',
                'a telephoto panorama compresses successive ridgelines into overlapping silhouettes, with the distant summit high in the frame.'),
            ClosedSlotValue('wide_rock_foreground',
                'a wide field of view anchors the lower corner with a granite ledge and opens diagonally into the valley and distant peaks.'),
        ), annotations=(
            SlotAnnotation('telephoto_layers', ('mountain_view',), frozenset({'mountain', 'ridges'})),
            SlotAnnotation('wide_rock_foreground', ('mountain_view',), frozenset({'rock', 'valley', 'mountain'})),
        )),
)

_LIGHTING = _fragment('lighting.time', 'qualifier', 'Lighting: {value}', dimension='lighting', values=(
    ClosedSlotValue('morning', 'soft morning side light reveals fine texture through open shade.',
                    frozenset({('qualifier', 'morning')})),
    ClosedSlotValue('daylight', 'clear midday light filters into alternating patches of sun and shade.'),
    ClosedSlotValue('sunrise', 'at sunrise, low first light touches the upper ridges while the valley remains in cool shadow.',
                    frozenset({('qualifier', 'sunrise')})),
    ClosedSlotValue('sunset', 'at sunset, a low warm glow grazes the meadow beneath a softly luminous sky.',
                    frozenset({('qualifier', 'sunset')})),
    ClosedSlotValue('evening', 'gentle evening side light outlines the rock faces and lengthens shadows into the valley.',
                    frozenset({('qualifier', 'evening')})),
), annotations=(
    SlotAnnotation('morning', ('forest_path', 'open_meadow')),
    SlotAnnotation('daylight', ('forest_path',)),
    SlotAnnotation('sunrise', ('mountain_view',), frozenset({'ridges', 'valley'})),
    SlotAnnotation('sunset', ('open_meadow',), frozenset({'meadow', 'sky'})),
    SlotAnnotation('evening', ('mountain_view',), frozenset({'rock', 'valley'})),
))

_PALETTE = _fragment('palette.natural', 'qualifier', 'Palette: {value}', dimension='palette', values=(
    ClosedSlotValue('cool', 'cool greens and blue-gray shadows, with subtle pale highlights and natural color separation.'),
    ClosedSlotValue('warm', 'warm ochre highlights and muted earth colors balanced by deeper neutral shadows.'),
), annotations=(SlotAnnotation('cool', SCENES), SlotAnnotation('warm', SCENES)))

_EXCLUSION_TEXTS = (
    ('object', 'body', 'No visible human body parts.'),
    ('object', 'hands', 'No hands.'),
    ('object', 'human', 'No people or human figures.'),
    ('object', 'mug', 'No mugs or cups.'),
    ('object', 'notebook', 'No notebooks.'),
    ('object', 'table', 'No tables.'),
    ('object', 'window', 'No windows.'),
    ('coastal', 'beach', 'No beaches.'),
    ('coastal', 'coast', 'No coastline or seashore.'),
    ('coastal', 'lagoon', 'No lagoons or coastal bays.'),
    ('coastal', 'rocky', 'No rocky coast.'),
    ('coastal', 'sandy', 'No sandy beach.'),
    ('coastal', 'water', 'No sea or ocean.'),
    ('system', 'text_marks', 'No text, words, letters, numbers, typography, logos, or watermarks.'),
)
_EXCLUSIONS = tuple(_fragment(f'ban.{domain}.{key}',
    'no_text' if domain == 'system' else 'mandatory_exclusion', text,
    dimension='no_text' if domain == 'system' else 'exclusion',
    excluded=frozenset({(domain, key)})) for domain, key, text in _EXCLUSION_TEXTS)

_ABSENCE = frozenset({('object', 'human'), ('object', 'hands'), ('object', 'body')})
_SCENE_CONTRACTS = tuple(SceneContract(scene, VERSION, STYLE, MODE, 'none',
    (_ref('style.living_nature_photo'), _ref(f'scene.{scene}')),
    frozenset({('scene', 'mountain')}) if scene == 'mountain_view' else frozenset(),
    _ABSENCE,
    frozenset(entities),
    frozenset({'person', 'hands', 'body', 'text_marks', 'building', 'interior', 'sea', 'beach'}),
    REVIEW_ID) for scene, entities in (
        ('forest_path', ('footpath', 'trees')),
        ('open_meadow', ('meadow', 'grass', 'wildflowers')),
        ('mountain_view', ('mountain', 'ridges', 'valley')),
    ))

_VARIANTS = tuple(ConstructionVariant(f'{scene}.{label}', VERSION, scene,
    (_ref(f'composition.{scene}', composition), _ref('lighting.time', lighting),
     _ref('palette.natural', palette)), REVIEW_ID)
    for scene, label, composition, lighting, palette in (
        ('forest_path', 'A', 'low_leading_curve', 'morning', 'cool'),
        ('forest_path', 'B', 'elevated_diagonal', 'daylight', 'warm'),
        ('open_meadow', 'A', 'grass_level_depth', 'morning', 'cool'),
        ('open_meadow', 'B', 'elevated_horizon_bands', 'sunset', 'warm'),
        ('mountain_view', 'A', 'telephoto_layers', 'sunrise', 'cool'),
        ('mountain_view', 'B', 'wide_rock_foreground', 'evening', 'warm'),
    ))

SEED_RELEASE = ContentRelease(RELEASE_ID, VERSION, 'sg01-content-schema-v1',
    (_STYLE, *_SCENE_FRAGMENTS, *_COMPOSITIONS, _LIGHTING, _PALETTE, *_EXCLUSIONS),
    _SCENE_CONTRACTS,
    (KeyBinding(('scene', 'mountain'), _ref('subject.mountain')),
     *(KeyBinding(('qualifier', key), _ref('lighting.time', key))
       for key in ('morning', 'sunrise', 'sunset', 'evening'))),
    tuple(KeyBinding((domain, key), _ref(f'ban.{domain}.{key}'))
          for domain, key, _ in _EXCLUSION_TEXTS),
    _VARIANTS,
    (ReviewDeclaration(REVIEW_ID, 'Codex implementation author', 'author_semantic_review',
        'Original Stage 1C English literals; component-by-component evidence in SG-01_Stage1C_Implementation_Record.md.',
        'Proposed author declarations only; independent Claude Code audit and Owner acceptance PENDING; no production authority or image-quality proof.'),))

# Fixed out-of-band comparison within this source release; never recomputed by
# seed_registry from supplied content. Hashes are not signatures or NL proofs.
SEED_MANIFEST = ReleaseManifest(RELEASE_ID, VERSION, 'sg01-content-schema-v1',
    'a57ab2fbc218564c2ed00290cb8866a25e4a07009889442705990719ac007864')


def seed_registry(release=SEED_RELEASE) -> RegistrySnapshot:
    """Verify against the pinned seed manifest, including author declarations."""
    return RegistrySnapshot(release, SEED_MANIFEST)
