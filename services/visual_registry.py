"""Offline, versioned content contracts; no rendering or dispatch authority.

Exact types and canonical bytes guard this API against subclass/equality tricks.
Digests bind declarations, not their truth. Author review is distinct from an
independent audit, Owner acceptance and production authorization. Same-process
code capable of rewriting module state is outside this internal API boundary.
"""
from dataclasses import dataclass, fields
import hashlib
import json

from services.visual_semantics import ClosedSlotValue, RegisteredFragment
from services.visual_safety_types import FragmentRole, HumanPresence, SemanticKey


class RegistryError(ValueError):
    """Closed diagnostic codes only; never echo caller prose."""


def _require(condition, code='INVALID_RECORD'):
    if not condition:
        raise RegistryError(code)


@dataclass(frozen=True, slots=True)
class ReviewDeclaration:
    review_id: str
    declared_by: str
    basis: str
    evidence: str
    limitations: str

    def __post_init__(self):
        canonical_bytes(self)
        _require(self.basis == 'author_semantic_review', 'INVALID_REVIEW_BASIS')


@dataclass(frozen=True, slots=True)
class RegistrySelection:
    registry_id: str
    version: str
    slot_value: str | None = None

    def __post_init__(self):
        canonical_bytes(self)


@dataclass(frozen=True, slots=True)
class SlotAnnotation:
    value_id: str
    scene_ids: tuple[str, ...]
    entities: frozenset[str] = frozenset()

    def __post_init__(self):
        canonical_bytes(self)


@dataclass(frozen=True, slots=True)
class ContentFragment:
    version: str
    content: RegisteredFragment
    kind: str
    dimension: str
    scene_ids: tuple[str, ...]
    entities: frozenset[str]
    slot_annotations: tuple[SlotAnnotation, ...]
    review_id: str

    def __post_init__(self):
        canonical_bytes(self)
        _require(self.kind in {'semantic', 'artistic'})
        _require(self.dimension in {
            'style', 'scene', 'exclusion', 'no_text',
            'composition', 'lighting', 'palette', 'detail', 'atmosphere',
        })
        _require((self.kind == 'artistic') == (self.dimension in {
            'composition', 'lighting', 'palette', 'detail', 'atmosphere'}))


@dataclass(frozen=True, slots=True)
class KeyBinding:
    key: SemanticKey
    selection: RegistrySelection

    def __post_init__(self):
        canonical_bytes(self)


@dataclass(frozen=True, slots=True)
class SceneContract:
    scene_id: str
    version: str
    style: str
    mode: str
    human_presence: str
    base_fragments: tuple[RegistrySelection, ...]
    required_keys: frozenset[SemanticKey]
    forbidden_keys: frozenset[SemanticKey]
    required_entities: frozenset[str]
    forbidden_entities: frozenset[str]
    review_id: str

    def __post_init__(self):
        canonical_bytes(self)
        _require(self.human_presence in HumanPresence.__args__)


@dataclass(frozen=True, slots=True)
class ConstructionVariant:
    variant_id: str
    version: str
    scene_id: str
    selections: tuple[RegistrySelection, ...]
    review_id: str

    def __post_init__(self):
        canonical_bytes(self)


@dataclass(frozen=True, slots=True)
class ContentRelease:
    release_id: str
    version: str
    schema_version: str
    fragments: tuple[ContentFragment, ...]
    scenes: tuple[SceneContract, ...]
    positive_bindings: tuple[KeyBinding, ...]
    exclusion_bindings: tuple[KeyBinding, ...]
    variants: tuple[ConstructionVariant, ...]
    reviews: tuple[ReviewDeclaration, ...]

    def __post_init__(self):
        canonical_bytes(self)


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    release_id: str
    version: str
    schema_version: str
    payload_digest: str

    def __post_init__(self):
        canonical_bytes(self)
        _require(len(self.payload_digest) == 64 and all(
            c in '0123456789abcdef' for c in self.payload_digest), 'INVALID_DIGEST')


@dataclass(frozen=True, slots=True)
class RegisteredContent:
    """Exact lookup evidence, including both release and fragment identity."""
    release_id: str
    release_version: str
    release_digest: str
    selection: RegistrySelection
    text: str
    role: str
    positive_keys: frozenset[SemanticKey]
    excluded_keys: frozenset[SemanticKey]
    conditional_keys: frozenset[SemanticKey]
    entities: frozenset[str]
    review_id: str
    review_digest: str

    def __post_init__(self):
        canonical_bytes(self)


# Explicit field schemas also validate nested NEUTRAL Stage 1B records. No
# isinstance(), generic dataclass serializer, caller __eq__ or mutable fallback.
_S = str
_K = 'keys'
_T = lambda cls: ('tuple', cls)
_F = ('set', str)
_SCHEMAS = {
    ReviewDeclaration: (_S, _S, _S, _S, _S),
    RegistrySelection: (_S, _S, ('optional', str)),
    SlotAnnotation: (_S, _T(str), _F),
    ClosedSlotValue: (_S, _S, _K, _K, _K),
    RegisteredFragment: (_S, _S, _S, _K, _K, _K, _T(ClosedSlotValue)),
    ContentFragment: (_S, RegisteredFragment, _S, _S, _T(str), _F,
                      _T(SlotAnnotation), _S),
    KeyBinding: ('key', RegistrySelection),
    SceneContract: (_S, _S, _S, _S, _S, _T(RegistrySelection), _K, _K, _F, _F, _S),
    ConstructionVariant: (_S, _S, _S, _T(RegistrySelection), _S),
    ContentRelease: (_S, _S, _S, _T(ContentFragment), _T(SceneContract),
                     _T(KeyBinding), _T(KeyBinding), _T(ConstructionVariant),
                     _T(ReviewDeclaration)),
    ReleaseManifest: (_S, _S, _S, _S),
    RegisteredContent: (_S, _S, _S, RegistrySelection, _S, _S,
                        _K, _K, _K, _F, _S, _S),
}


def _encode(value, schema):
    if schema == 'key':
        _require(type(value) is tuple and len(value) == 2)
        _require(all(type(v) is str and v for v in value))
        _require(value[0] in {'object', 'coastal', 'artifact', 'scene', 'qualifier', 'system'})
        return list(value)
    if schema == 'keys':
        _require(type(value) is frozenset)
        return sorted(_encode(v, 'key') for v in value)
    if type(schema) is tuple:
        kind, element = schema
        if kind == 'optional':
            return None if value is None else _encode(value, element)
        _require(type(value) is (tuple if kind == 'tuple' else frozenset))
        encoded = [_encode(v, element) for v in value]
        return sorted(encoded) if kind == 'set' else encoded
    _require(type(value) is schema)
    if schema is str:
        _require(bool(value) and '\r' not in value and '\n' not in value)
        return value
    _require(schema in _SCHEMAS)
    return {'type': schema.__name__, 'fields': {
        f.name: _encode(getattr(value, f.name), spec)
        for f, spec in zip(fields(schema), _SCHEMAS[schema], strict=True)}}


def canonical_bytes(record) -> bytes:
    """Schema v1: UTF-8, sorted JSON fields/sets, ordered tuples, exact strings."""
    _require(type(record) in _SCHEMAS)
    encoded = _encode(record, type(record))
    try:
        return json.dumps(encoded, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':')).encode('utf-8')
    except UnicodeEncodeError:
        raise RegistryError('INVALID_UNICODE') from None


def content_digest(record) -> str:
    return hashlib.sha256(canonical_bytes(record)).hexdigest()


def manifest_for(release) -> ReleaseManifest:
    """Mechanical evidence only. This operation confers no review authority."""
    _require(type(release) is ContentRelease)
    return ReleaseManifest(release.release_id, release.version,
                           release.schema_version, content_digest(release))


def _unique(values):
    _require(len(values) == len(set(values)), 'DUPLICATE_IDENTITY')


def _entry(release, selection):
    _require(type(selection) is RegistrySelection)
    canonical_bytes(selection)
    entry = next((f for f in release.fragments
                  if f.content.registry_id == selection.registry_id), None)
    _require(entry is not None, 'UNKNOWN_FRAGMENT')
    _require(entry.version == selection.version, 'UNKNOWN_FRAGMENT_VERSION')
    value = next((v for v in entry.content.slot_values
                  if v.value_id == selection.slot_value), None)
    _require((bool(entry.content.slot_values) and value is not None)
             or (not entry.content.slot_values and selection.slot_value is None), 'UNKNOWN_SLOT_VALUE')
    return entry, value


def _semantics(entry, value):
    f = entry.content
    annotation = next((a for a in entry.slot_annotations
                       if value is not None and a.value_id == value.value_id), None)
    return (f.positive_keys | (value.positive_keys if value else frozenset()),
            f.excluded_keys | (value.excluded_keys if value else frozenset()),
            f.conditional_keys | (value.conditional_keys if value else frozenset()),
            entry.entities | (annotation.entities if annotation else frozenset()))


def _compatible(release, scene, selections, required_keys, forbidden_keys):
    # These are semantic declarations, never interpretation of raw user prose.
    _encode(required_keys, _K)
    _encode(forbidden_keys, _K)
    _encode(selections, _T(RegistrySelection))
    positive, excluded, conditional, entities, dimensions = set(), set(), set(), set(), set()
    for selection in (*scene.base_fragments, *selections):
        entry, value = _entry(release, selection)
        _require(scene.scene_id in entry.scene_ids, 'INCOMPATIBLE_SCENE')
        if value is not None:
            annotation = next(a for a in entry.slot_annotations if a.value_id == value.value_id)
            _require(scene.scene_id in annotation.scene_ids, 'INCOMPATIBLE_SCENE_SLOT')
        if entry.kind == 'artistic':
            _require(entry.dimension not in dimensions, 'CONFLICTING_ARTISTIC_DIMENSION')
            dimensions.add(entry.dimension)
        p, e, c, subjects = _semantics(entry, value)
        positive.update(p)
        excluded.update(e)
        conditional.update(c)
        entities.update(subjects)
    bans = scene.forbidden_keys | forbidden_keys
    _require(not (positive | conditional) & bans, 'FORBIDDEN_CONTENT')
    _require(not excluded & (positive | required_keys | scene.required_keys), 'SEMANTIC_CONFLICT')
    _require(not entities & scene.forbidden_entities, 'FORBIDDEN_ENTITY')
    _require(scene.required_entities <= entities, 'MISSING_SCENE_IDENTITY')
    # Stage 1B only checks conflicts within ONE slot identity. Here all lighting
    # fragments and canonical qualifier requirements share the same time axis.
    times = (positive | required_keys) & {('qualifier', k) for k in ('sunrise', 'sunset', 'morning', 'evening')}
    _require(len(times) <= 1, 'CONFLICTING_TIME_QUALIFIERS')
    _require((scene.required_keys | required_keys) <= positive, 'MISSING_REQUIRED_KEY')
    _require(not (excluded & conditional), 'SEMANTIC_CONFLICT')
    return frozenset(positive)


def validate_release(release) -> None:
    """Structural/coverage consistency; not an independent semantic review."""
    _require(type(release) is ContentRelease)
    canonical_bytes(release)
    _require(release.schema_version == 'sg01-content-schema-v1', 'UNKNOWN_SCHEMA')
    _require(bool(release.fragments) and bool(release.scenes) and bool(release.reviews))
    for records, attr in ((release.fragments, None), (release.scenes, 'scene_id'),
                          (release.variants, 'variant_id'), (release.reviews, 'review_id')):
        _unique(tuple(r.content.registry_id if attr is None else getattr(r, attr) for r in records))
    review_ids = {r.review_id for r in release.reviews}
    scene_ids = {s.scene_id for s in release.scenes}
    for review in release.reviews:
        _require(review.basis == 'author_semantic_review', 'INVALID_REVIEW_BASIS')
    for entry in release.fragments:
        # Recheck local invariants too, including objects altered via object.__setattr__.
        ContentFragment.__post_init__(entry)
        f = entry.content
        _require(entry.review_id in review_ids, 'DANGLING_REVIEW')
        _require(bool(entry.scene_ids) and set(entry.scene_ids) <= scene_ids, 'DANGLING_SCENE')
        _unique(entry.scene_ids)
        _require(f.role in FragmentRole.__args__ and f.role != 'untrusted_prose')
        _unique(tuple(v.value_id for v in f.slot_values))
        _unique(tuple(a.value_id for a in entry.slot_annotations))
        _require({a.value_id for a in entry.slot_annotations} == {v.value_id for v in f.slot_values},
                 'INCOMPLETE_SLOT_ANNOTATIONS')
        for annotation in entry.slot_annotations:
            _require(bool(annotation.scene_ids) and set(annotation.scene_ids) <= set(entry.scene_ids),
                     'DANGLING_SCENE')
            _unique(annotation.scene_ids)
        _require(bool(f.slot_values) == (f.text.count('{value}') == 1), 'INVALID_SLOT_SCHEMA')
        _require(not any(c in f.text.replace('{value}', '') for c in '{}'), 'INVALID_SLOT_SCHEMA')
        for value in (None, *f.slot_values):
            if value is not None:
                _require(not any(c in value.text for c in '{}'), 'INVALID_SLOT_SCHEMA')
            p, e, c, _ = _semantics(entry, value)
            _require(not (p | c) & e, 'SEMANTIC_CONFLICT')
            if entry.kind == 'artistic':
                _require(not e and not c, 'INVALID_ARTISTIC_CONTRACT')
        if entry.kind == 'artistic':
            _require(f.role in {'positive_scene', 'qualifier'} and not f.excluded_keys
                     and not f.conditional_keys, 'INVALID_ARTISTIC_CONTRACT')
    for bindings, exclusion in ((release.positive_bindings, False), (release.exclusion_bindings, True)):
        _unique(tuple(b.key for b in bindings))
        for binding in bindings:
            entry, value = _entry(release, binding.selection)
            p, e, _, _ = _semantics(entry, value)
            _require((e == frozenset({binding.key}) if exclusion else binding.key in p), 'INVALID_BINDING')
            _require(entry.content.role == ('no_text' if binding.key == ('system', 'text_marks')
                                          else 'mandatory_exclusion') if exclusion else
                     entry.content.role in {'positive_scene', 'qualifier'}, 'INVALID_BINDING')
    exclusion_keys = {b.key for b in release.exclusion_bindings}
    for scene in release.scenes:
        SceneContract.__post_init__(scene)
        _require(scene.review_id in review_ids, 'DANGLING_REVIEW')
        _require(not scene.required_keys & scene.forbidden_keys, 'SEMANTIC_CONFLICT')
        _require(not scene.required_entities & scene.forbidden_entities, 'SEMANTIC_CONFLICT')
        _require(scene.forbidden_keys | {('system', 'text_marks')} <= exclusion_keys,
                 'MISSING_EXCLUSION_COVERAGE')
        _compatible(release, scene, (), frozenset(), frozenset())
        roles = {_entry(release, s)[0].content.role for s in scene.base_fragments}
        _require({'style', 'positive_scene'} <= roles, 'MISSING_SCENE_IDENTITY')
    for variant in release.variants:
        _require(variant.review_id in review_ids, 'DANGLING_REVIEW')
        scene = next((s for s in release.scenes if s.scene_id == variant.scene_id), None)
        _require(scene is not None, 'DANGLING_SCENE')
        _require(bool(variant.selections), 'EMPTY_VARIANT')
        _compatible(release, scene, variant.selections, frozenset(), frozenset())


@dataclass(frozen=True, slots=True)
class RegistrySnapshot:
    """Pinned offline release. A caller-created manifest grants no external trust."""
    release: ContentRelease
    manifest: ReleaseManifest

    def __post_init__(self):
        _require(type(self) is RegistrySnapshot)
        _require(type(self.manifest) is ReleaseManifest)
        validate_release(self.release)
        self.verify_release(self.release)

    def verify_release(self, candidate) -> None:
        _require(type(self) is RegistrySnapshot and type(candidate) is ContentRelease)
        _require(type(self.manifest) is ReleaseManifest)
        # Canonical comparison does not invoke record equality.
        _require(canonical_bytes(manifest_for(candidate)) == canonical_bytes(self.manifest),
                 'RELEASE_INTEGRITY_MISMATCH')

    def _intact(self):
        _require(type(self) is RegistrySnapshot)
        RegistrySnapshot.verify_release(self, self.release)

    def scene(self, scene_id, *, style, mode, version):
        RegistrySnapshot._intact(self)
        _require(all(type(v) is str for v in (scene_id, style, mode, version)))
        scene = next((s for s in self.release.scenes if s.scene_id == scene_id), None)
        _require(scene is not None and scene.style == style and scene.mode == mode, 'UNSUPPORTED_COVERAGE')
        _require(scene.version == version, 'UNKNOWN_SCENE_VERSION')
        return scene

    def lookup(self, selection) -> RegisteredContent:
        RegistrySnapshot._intact(self)
        entry, value = _entry(self.release, selection)
        p, e, c, entities = _semantics(entry, value)
        review = next(r for r in self.release.reviews if r.review_id == entry.review_id)
        text = entry.content.text if value is None else entry.content.text.replace('{value}', value.text)
        return RegisteredContent(self.release.release_id, self.release.version, self.manifest.payload_digest,
                                 selection, text, entry.content.role, p, e, c, entities,
                                 entry.review_id, content_digest(review))

    def verify_content(self, content) -> None:
        RegistrySnapshot._intact(self)
        _require(type(content) is RegisteredContent)
        actual = canonical_bytes(content)
        _require(actual == canonical_bytes(self.lookup(content.selection)), 'CONTENT_INTEGRITY_MISMATCH')

    def check_compatibility(self, scene, selections, *, required_keys=frozenset(), forbidden_keys=frozenset()):
        RegistrySnapshot._intact(self)
        _require(type(scene) is SceneContract)
        expected = self.scene(scene.scene_id, style=scene.style, mode=scene.mode, version=scene.version)
        _require(canonical_bytes(scene) == canonical_bytes(expected), 'CONTENT_INTEGRITY_MISMATCH')
        return _compatible(self.release, scene, selections, required_keys, forbidden_keys)

    def variant(self, variant_id, *, version):
        RegistrySnapshot._intact(self)
        _require(type(variant_id) is str and type(version) is str)
        variant = next((v for v in self.release.variants if v.variant_id == variant_id), None)
        _require(variant is not None, 'UNKNOWN_VARIANT')
        _require(variant.version == version, 'UNKNOWN_VARIANT_VERSION')
        return variant
