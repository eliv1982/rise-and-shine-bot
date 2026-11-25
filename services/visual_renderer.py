"""Narrow Stage 1D renderer. Explicit synthetic harness, no provider or runtime I/O.

One factory call creates one attempt. Content authority is the Stage 1C pin;
interpretation, closure, routing, serialization and capacity remain with 1A/1B.
Private Python state is trusted implementation, not a hostile-code sandbox.
"""
from dataclasses import dataclass, fields, replace
import json

from services import directive_segments as ds, visual_intent as vi
from services import visual_safety as sg, visual_semantics as vs
from services import visual_safety_types as st
from services.visual_registry import (
    RegistryError, RegistrySelection, RegisteredContent, RegistrySnapshot,
    canonical_bytes,
)
from services.visual_registry_content import seed_registry, SEED_MANIFEST


def _fail(code='INVALID_EVIDENCE', stage='candidate'):
    st.safety_failure(st.ValidationResult('blocked', stage,
        (st.ValidationIssue(code, stage),), ''))


def _require(condition, code='INVALID_EVIDENCE'):
    if not condition:
        _fail(code)


# Closed renderer-local diagnostics: ValidationIssue.detail is reserved for the
# existing interpreter tokens. Never copy arbitrary RegistryError prose there.
_REGISTRY_REASONS = {
    'INCOMPATIBLE_SCENE': 'SCENE_CONFLICT',
    'INCOMPATIBLE_SCENE_SLOT': 'SCENE_CONFLICT',
    'CONFLICTING_ARTISTIC_DIMENSION': 'SCENE_CONFLICT',
    'CONFLICTING_TIME_QUALIFIERS': 'SCENE_CONFLICT',
    'SEMANTIC_CONFLICT': 'SCENE_CONFLICT',
    'FORBIDDEN_CONTENT': 'FORBIDDEN_POSITIVE_CONTENT',
    'FORBIDDEN_ENTITY': 'FORBIDDEN_POSITIVE_CONTENT',
    'MISSING_SCENE_IDENTITY': 'MISSING_REQUIRED_VISUAL_FACT',
    'MISSING_REQUIRED_KEY': 'MISSING_REQUIRED_VISUAL_FACT',
    'MISSING_EXCLUSION_COVERAGE': 'MISSING_MANDATORY_EXCLUSION',
    'INVALID_RECORD': 'INVALID_EVIDENCE',
    'INVALID_UNICODE': 'INVALID_EVIDENCE',
    'INVALID_DIGEST': 'INVALID_EVIDENCE',
    'DUPLICATE_IDENTITY': 'INVALID_EVIDENCE',
    'DANGLING_REVIEW': 'INVALID_EVIDENCE',
    'DANGLING_SCENE': 'INVALID_EVIDENCE',
    'INCOMPLETE_SLOT_ANNOTATIONS': 'INVALID_EVIDENCE',
    'INVALID_SLOT_SCHEMA': 'INVALID_EVIDENCE',
    'INVALID_ARTISTIC_CONTRACT': 'INVALID_EVIDENCE',
    'INVALID_BINDING': 'INVALID_EVIDENCE',
    'EMPTY_VARIANT': 'INVALID_EVIDENCE',
    'RELEASE_INTEGRITY_MISMATCH': 'INVALID_EVIDENCE',
    'CONTENT_INTEGRITY_MISMATCH': 'INVALID_EVIDENCE',
    'INVALID_REVIEW_BASIS': 'UNTRUSTED_AUTHORITY',
    'UNKNOWN_SCHEMA': 'UNTRUSTED_AUTHORITY',
    'UNKNOWN_FRAGMENT': 'UNTRUSTED_AUTHORITY',
    'UNKNOWN_FRAGMENT_VERSION': 'UNTRUSTED_AUTHORITY',
    'UNKNOWN_SLOT_VALUE': 'UNTRUSTED_AUTHORITY',
    'UNSUPPORTED_COVERAGE': 'UNTRUSTED_AUTHORITY',
    'UNKNOWN_SCENE_VERSION': 'UNTRUSTED_AUTHORITY',
    'UNKNOWN_VARIANT': 'UNTRUSTED_AUTHORITY',
    'UNKNOWN_VARIANT_VERSION': 'UNTRUSTED_AUTHORITY',
}


def _registry_diagnostic(error):
    args = error.args
    code = args[0] if len(args) == 1 and type(args[0]) is str else None
    return code if code in _REGISTRY_REASONS else 'UNKNOWN_REGISTRY_ERROR'


def _registry_result(code, stage):
    reason = _REGISTRY_REASONS.get(code, 'UNTRUSTED_AUTHORITY')
    return st.ValidationResult('blocked', stage, (st.ValidationIssue(reason, stage),), '')


def _text(value, *, empty=False):
    _require(type(value) is str and (empty or bool(value)))
    try:
        value.encode('utf-8')
    except UnicodeEncodeError:
        _fail()


@dataclass(frozen=True, slots=True)
class SourceFields:
    """Exact original primitives; kinds/activity are assigned by the interpreter."""
    user_text: str = ''
    custom_style_description: str = ''

    def __post_init__(self):
        _require(type(self) is SourceFields)
        _text(self.user_text, empty=True)
        _text(self.custom_style_description, empty=True)


@dataclass(frozen=True, slots=True)
class SceneSelector:
    scene_id: str
    version: str

    def __post_init__(self):
        _require(type(self) is SceneSelector)
        _text(self.scene_id)
        _text(self.version)


@dataclass(frozen=True, slots=True)
class ArtisticSelections:
    components: tuple[RegistrySelection, ...]

    def __post_init__(self):
        _require(type(self) is ArtisticSelections and type(self.components) is tuple)
        for selection in self.components:
            _require(type(selection) is RegistrySelection)
            try:
                canonical_bytes(selection)
            except RegistryError:
                _fail()


@dataclass(frozen=True, slots=True)
class VariantSelector:
    variant_id: str
    version: str

    def __post_init__(self):
        _require(type(self) is VariantSelector)
        _text(self.variant_id)
        _text(self.version)


@dataclass(frozen=True, slots=True)
class SyntheticTarget:
    adapter_id: str
    model: str
    size: str

    def __post_init__(self):
        _require(type(self) is SyntheticTarget)
        for value in (self.adapter_id, self.model, self.size):
            _text(value)


@dataclass(frozen=True, slots=True)
class RenderRequest:
    sources: SourceFields
    style: str
    mode: str
    scene: SceneSelector
    artistic: ArtisticSelections | VariantSelector
    target: SyntheticTarget

    def __post_init__(self):
        _validate_request(self)


@dataclass(frozen=True, slots=True)
class SyntheticEnvironment:
    """Explicit harness registrations, separate from real content; no defaults."""
    policy: vs.SyntheticPolicy
    capabilities: tuple[vs.SyntheticCapability, ...]

    def __post_init__(self):
        _validate_environment(self)


@dataclass(frozen=True, slots=True)
class FragmentOccurrence:
    position: int
    span: ds.Span
    content: RegisteredContent
    origin: str
    evidence_refs: tuple[st.DirectiveRef, ...]
    exclusion_causes: tuple[str, ...]
    scene: SceneSelector

    def __post_init__(self):
        _require(type(self) is FragmentOccurrence)
        _require(type(self.position) is int and self.position >= 0)
        _require(type(self.span) is ds.Span and type(self.content) is RegisteredContent)
        ds.Span.__post_init__(self.span)
        _require(type(self.scene) is SceneSelector)
        SceneSelector.__post_init__(self.scene)
        try:
            canonical_bytes(self.content)
        except RegistryError:
            _fail()
        _text(self.origin)
        _require(type(self.evidence_refs) is tuple and type(self.exclusion_causes) is tuple)
        for ref in self.evidence_refs:
            _require(type(ref) is tuple and len(ref) == 2)
            _text(ref[0])
            _require(type(ref[1]) is int and ref[1] >= 0)
        for cause in self.exclusion_causes:
            _text(cause)


_PREVIEW_KEY = object()


@dataclass(frozen=True, slots=True, init=False)
class OfflinePreview:
    request: RenderRequest
    selections: tuple[RegistrySelection, ...]
    artifact: sg.SyntheticValidatedAssembly
    occurrences: tuple[FragmentOccurrence, ...]

    def __init__(self, request, selections, artifact, occurrences, *, _key=None):
        _require(type(self) is OfflinePreview and _key is _PREVIEW_KEY, 'UNTRUSTED_AUTHORITY')
        for name, value in (('request', request), ('selections', selections),
                            ('artifact', artifact), ('occurrences', occurrences)):
            object.__setattr__(self, name, value)

    @property
    def authority(self):
        return 'synthetic_offline'

    @property
    def production_authorized(self):
        return False

    @property
    def prompt(self):
        return self.artifact.assembly.prompt


# Exact recursive types before any equality or legacy canonicality check. The
# whitelist covers internally constructed 1A/1B evidence, without changing it.
_RECORDS = frozenset((
    SourceFields, SceneSelector, ArtisticSelections, VariantSelector,
    SyntheticTarget, RenderRequest, SyntheticEnvironment, FragmentOccurrence,
    OfflinePreview, RegistrySelection, RegisteredContent,
    ds.Span, ds.DirectiveSource, ds.Scope, ds.Directive, ds.SegmentedSource,
    ds.RelationEvidence, ds.DirectiveStructure, vi.VisualFact,
    vi.DirectiveClassification, vi.NegativeAssessment, vi.VisualInterpretation,
    sg.ResolvedFact, sg.VisualConflict, sg.MandatoryBan, sg.EnforcementRoute,
    sg.ResolvedVisualIntent, sg.PreflightEvidence, sg.PromptCandidate,
    sg.FinalAssembly, sg.SyntheticValidatedAssembly,
    st.ValidationIssue, st.ValidationResult, st.PromptCapacity,
    st.FragmentProvenance, st.PromptFragment,
    vs.SyntheticPolicy, vs.SyntheticCapability, vs.FragmentSelection,
))
_ENUMS = frozenset((ds.SourceKind, ds.Polarity, ds.DirectiveKind, vi.FactDomain, vi.FactBasis))


def _tree(value):
    cls = type(value)
    if value is None or cls in (str, int, bool):
        return value
    if cls in _ENUMS:
        return [cls.__name__, value.value]
    if cls is tuple:
        return ['tuple', [_tree(v) for v in value]]
    if cls is frozenset:
        return ['frozenset', sorted((_tree(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True))]
    _require(cls in _RECORDS)
    return [cls.__name__, [[f.name, _tree(getattr(value, f.name))] for f in fields(cls)]]


def _bytes(value):
    try:
        return json.dumps(_tree(value), ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    except (UnicodeEncodeError, RecursionError):
        _fail()


def _validate_request(request):
    _require(type(request) is RenderRequest)
    for value, cls in ((request.sources, SourceFields), (request.scene, SceneSelector),
                       (request.target, SyntheticTarget)):
        _require(type(value) is cls)
        cls.__post_init__(value)
    _text(request.style)
    _text(request.mode)
    _require(type(request.artistic) in (ArtisticSelections, VariantSelector))
    type(request.artistic).__post_init__(request.artistic)


def _bound_version(snapshot):
    return f'{snapshot.release.release_id}@{snapshot.release.version}#{snapshot.manifest.payload_digest}'


def _validate_environment(environment):
    _require(type(environment) is SyntheticEnvironment)
    _require(type(environment.policy) is vs.SyntheticPolicy)
    policy = environment.policy
    for value in (policy.policy_version, policy.selection_rule_id, policy.registry_version):
        _text(value)
    _require(type(policy.context_ids) is tuple and bool(policy.context_ids))
    for value in policy.context_ids:
        _text(value)
    _require(len(set(policy.context_ids)) == len(policy.context_ids))
    _require(type(policy.covered_keys) is frozenset)
    for key in policy.covered_keys:
        _require(type(key) is tuple and len(key) == 2)
        for value in key:
            _text(value)
    st.semantic_keys(policy.covered_keys)
    _require(type(environment.capabilities) is tuple)
    identities = []
    for capability in environment.capabilities:
        _require(type(capability) is vs.SyntheticCapability)
        cap = capability.capacity
        _require(type(cap) is st.PromptCapacity)
        for value in (cap.adapter_id, cap.model, cap.unit, cap.counter_version,
                      cap.evidence_reference, cap.capability_version):
            _text(value)
        _require(type(cap.maximum) is int and cap.maximum > 0)
        st.PromptCapacity.__post_init__(cap)
        _require(type(capability.sizes) is tuple and bool(capability.sizes))
        for value in capability.sizes:
            _text(value)
        _require(len(set(capability.sizes)) == len(capability.sizes))
        identities.append((cap.adapter_id, cap.model))
    _require(len(identities) == len(set(identities)))
    _bytes(environment)


def _key(domain, key):
    return (domain.value if type(domain) is vi.FactDomain else domain, key)


def _requirements(resolution):
    return frozenset(_key(f.domain, f.key) for f in resolution.effective_facts
                     if f.polarity is ds.Polarity.POSITIVE)


def _selections(snapshot, scene, artistic):
    if type(artistic) is VariantSelector:
        variant = snapshot.variant(artistic.variant_id, version=artistic.version)
        _require(variant.scene_id == scene.scene_id, 'SCENE_CONFLICT')
        selections = variant.selections
    else:
        selections = artistic.components
    dimensions = []
    for selection in selections:
        snapshot.lookup(selection)
        entry = next(f for f in snapshot.release.fragments if f.content.registry_id == selection.registry_id)
        _require(entry.kind == 'artistic', 'UNTRUSTED_AUTHORITY')
        dimensions.append(entry.dimension)
    _require(sorted(dimensions) == ['composition', 'lighting', 'palette'], 'SCENE_CONFLICT')
    return selections


def _projected(snapshot, scene, resolution):
    required = _requirements(resolution) | scene.required_keys
    selections = []
    for key in sorted(required):
        binding = next((b for b in snapshot.release.positive_bindings if b.key == key), None)
        _require(binding is not None, 'MISSING_REQUIRED_VISUAL_FACT')
        selections.append(binding.selection)
    return tuple(selections)


def _optional(selections, projections):
    # Omit only the optional occurrence. Required origin/refs remain gate-owned.
    projected = {canonical_bytes(s) for s in projections}
    return tuple(s for s in selections if canonical_bytes(s) not in projected)


def _adapt(snapshot, scene, environment):
    """Project exact contracts to 1B; never parse scene IDs or invent bans."""
    fragments, available = [], set()
    for entry in snapshot.release.fragments:
        if scene.scene_id not in entry.scene_ids:
            continue
        content = entry.content
        values = tuple(v for v in content.slot_values if any(
            a.value_id == v.value_id and scene.scene_id in a.scene_ids for a in entry.slot_annotations))
        if content.slot_values and not values:
            continue
        fragments.append(replace(content, slot_values=values))
        available.update((content.registry_id, v.value_id) for v in values)
        if not values:
            available.add((content.registry_id, None))

    def selection(s):
        return vs.FragmentSelection(s.registry_id, s.slot_value)

    positive = tuple(vs.ProjectionBinding(b.key, selection(b.selection))
                     for b in snapshot.release.positive_bindings
                     if (b.selection.registry_id, b.selection.slot_value) in available)
    excluded = tuple(vs.ProjectionBinding(b.key, selection(b.selection))
                     for b in snapshot.release.exclusion_bindings)
    context = vs.ControlledContext(scene.scene_id, scene.style, scene.style, scene.mode, scene.scene_id,
        tuple(selection(s) for s in scene.base_fragments),
        (vs.PresenceBinding(scene.human_presence, ()),), scene.human_presence, scene.required_keys)
    # Scene prohibitions are NOT selected-style prohibitions. 1B owns closure;
    # the renderer later checks that the actual bans cover the scene contract.
    return vs.SyntheticRegistry(_bound_version(snapshot), tuple(fragments), positive, excluded,
                                (context,), environment.capabilities)


class OfflineRenderer:
    """One render attempt; use the factory explicitly for a separate attempt."""
    __slots__ = ('_environment', '_environment_bytes', '_snapshot', '_request', '_request_bytes',
                 '_state', '_failure', '_registry_failure_code', '_gate', '_preview', '_preview_bytes')

    def __init__(self, environment, *, _key=None):
        _require(type(self) is OfflineRenderer and _key is _PREVIEW_KEY, 'UNTRUSTED_AUTHORITY')
        _validate_environment(environment)
        snapshot = seed_registry()
        _require(environment.policy.registry_version == _bound_version(snapshot), 'UNTRUSTED_AUTHORITY')
        _require(set(environment.policy.context_ids) <= {s.scene_id for s in snapshot.release.scenes},
                 'UNTRUSTED_AUTHORITY')
        self._environment, self._environment_bytes = environment, _bytes(environment)
        self._snapshot = snapshot
        self._request = self._request_bytes = None
        self._state, self._failure = 'CREATED', None
        self._registry_failure_code = None
        self._gate = self._preview = self._preview_bytes = None

    @property
    def state(self):
        return self._state

    @property
    def registry_failure_code(self):
        """Closed local detail for the terminal registry veto, never raw prose."""
        return self._registry_failure_code

    def __copy__(self):
        _fail('UNTRUSTED_AUTHORITY')

    def __deepcopy__(self, memo):
        _fail('UNTRUSTED_AUTHORITY')

    def __reduce_ex__(self, protocol):
        _fail('UNTRUSTED_AUTHORITY')

    def _intact(self):
        _validate_environment(self._environment)
        _require(_bytes(self._environment) == self._environment_bytes, 'STALE_VALIDATION')
        _require(type(self._snapshot) is RegistrySnapshot, 'UNTRUSTED_AUTHORITY')
        _require(canonical_bytes(self._snapshot.manifest) == canonical_bytes(SEED_MANIFEST),
                 'UNTRUSTED_AUTHORITY')
        # Re-enter the fixed pin, rather than trusting a caller-consistent pair.
        seed_registry(self._snapshot.release)
        if self._request is not None:
            _validate_request(self._request)
            _require(_bytes(self._request) == self._request_bytes, 'STALE_VALIDATION')

    def _terminal(self, error, stage):
        self._state = 'FAILED_TERMINAL'
        if type(error) is st.VisualSafetyFailure:
            self._failure = error.failure.result
        elif isinstance(error, RegistryError):
            self._registry_failure_code = _registry_diagnostic(error)
            self._failure = _registry_result(self._registry_failure_code, stage)
        else:
            self._failure = st.ValidationResult('blocked', stage,
                (st.ValidationIssue('INVALID_EVIDENCE', stage),), '')
        return self._failure

    def render(self, request):
        if self._state != 'CREATED':
            _fail('STALE_VALIDATION')
        self._state = 'VALIDATING'
        stage = 'preflight'
        try:
            _validate_request(request)
            self._request, self._request_bytes = request, _bytes(request)
            self._intact()
            _require(request.style == 'living_nature_photo' and request.mode == 'photo', 'STYLE_CONFLICT')
            stage = 'interpretation'
            interpretation = vi.interpret_visual_intent(request.sources.user_text, style=request.style,
                custom_style_description=request.sources.custom_style_description)
            resolution = sg.resolve_visual_intent(interpretation,
                requested_style=request.style, requested_mode=request.mode)
            sg.require_valid_interpretation(resolution)
            stage = 'preflight'
            scene = self._snapshot.scene(request.scene.scene_id, style=request.style,
                mode=request.mode, version=request.scene.version)
            selections = _selections(self._snapshot, scene, request.artistic)
            projections = _projected(self._snapshot, scene, resolution)
            optional = _optional(selections, projections)
            # Check proposed selectors and required projections before creating
            # the sole gate. A failed check has no alternate construction path.
            self._snapshot.check_compatibility(scene, (*projections, *optional),
                required_keys=_requirements(resolution),
                forbidden_keys=frozenset(_key(b.domain, b.key) for b in resolution.mandatory_bans))
            registry = _adapt(self._snapshot, scene, self._environment)
            self._gate = sg.create_synthetic_gate(resolution, registry, self._environment.policy,
                context_id=scene.scene_id, adapter_id=request.target.adapter_id,
                model=request.target.model, size=request.target.size)
            self._gate.preflight()
            stage = 'candidate'
            assembly = self._gate.assemble(optional_selections=tuple(
                vs.FragmentSelection(s.registry_id, s.slot_value) for s in optional), trace='stage1d-offline')
            stage = 'final'
            occurrences = self._verify_assembly(assembly, scene, selections)
            artifact = self._gate.validate_final_assembly(assembly)
            _require(type(artifact) is sg.SyntheticValidatedAssembly, 'UNTRUSTED_AUTHORITY')
            st.safety_failure(self._gate.check_artifact(artifact))
            preview = OfflinePreview(request, selections, artifact, occurrences, _key=_PREVIEW_KEY)
            self._preview_bytes = _bytes(preview)
            self._preview, self._state = preview, 'PREVIEW_ISSUED'
            return preview
        except (st.VisualSafetyFailure, RegistryError) as error:
            st.safety_failure(self._terminal(error, stage))
        except (AttributeError, TypeError, ValueError, RecursionError):
            # Malformed/corrupted records cannot escape as an apparent result.
            st.safety_failure(self._terminal(None, stage))
        except Exception:
            # Fence reuse, then preserve the implementation defect and traceback.
            self._terminal(None, stage)
            raise

    def _verify_assembly(self, assembly, scene, selections):
        """Reconstruct each occurrence independently, including required refs."""
        _require(type(assembly) is sg.FinalAssembly)
        _bytes(assembly)  # reject nested subclasses/mutables before legacy checks
        resolution = self._gate.resolution
        required = _requirements(resolution)
        projections = _projected(self._snapshot, scene, resolution)
        optional = _optional(selections, projections)
        expected = [(s, 'curated', (), ()) for s in scene.base_fragments]
        for key, selection in zip(sorted(required | scene.required_keys), projections, strict=True):
            fact = next((f for f in resolution.effective_facts
                         if _key(f.domain, f.key) == key and f.polarity is ds.Polarity.POSITIVE), None)
            refs = tuple(sorted({(resolution.interpretation.facts[i].source_id,
                                  resolution.interpretation.facts[i].directive_id)
                                 for i in fact.fact_indices})) if fact else ()
            expected.append((selection, 'user_projection' if fact else 'curated', refs, ()))
        expected.extend((s, 'curated', (), ()) for s in optional)
        banned = frozenset(_key(b.domain, b.key) for b in assembly.mandatory_bans)
        _require(scene.forbidden_keys | {('system', 'text_marks')} <= banned,
                 'MISSING_MANDATORY_EXCLUSION')
        for ban in sorted(assembly.mandatory_bans, key=lambda b: (b.domain == 'system', b.domain, b.key)):
            binding = next((b for b in self._snapshot.release.exclusion_bindings
                            if b.key == _key(ban.domain, ban.key)), None)
            _require(binding is not None, 'MISSING_MANDATORY_EXCLUSION')
            expected.append((binding.selection, 'user_projection' if ban.evidence_refs else 'system_rule',
                             ban.evidence_refs, ban.causes))
        candidate = assembly.candidate
        _require((candidate.scene_type, candidate.resolved_style, candidate.effective_mode,
                  candidate.human_presence) == (scene.scene_id, scene.style, scene.mode, scene.human_presence),
                 'SCENE_CONFLICT')
        _require(len(candidate.fragments) == len(expected) == len(assembly.fragment_spans), 'INVALID_ASSEMBLY')
        occurrences, actual, position, texts = [], [], 0, []
        for index, (fragment, span, (selection, origin, refs, causes)) in enumerate(zip(
                candidate.fragments, assembly.fragment_spans, expected, strict=True)):
            proof = self._snapshot.lookup(selection)
            self._snapshot.verify_content(proof)
            expected_fragment = st.PromptFragment(proof.text, proof.role,
                st.FragmentProvenance(origin, refs, proof.selection.registry_id,
                                      _bound_version(self._snapshot), proof.selection.slot_value),
                proof.positive_keys, proof.excluded_keys, proof.conditional_keys)
            _require(_bytes(fragment) == _bytes(expected_fragment), 'UNTRUSTED_AUTHORITY')
            _require((span.start, span.end) == (position, position + len(proof.text)), 'INVALID_ASSEMBLY')
            position += len(proof.text) + 1
            texts.append(proof.text)
            actual.append(selection)
            occurrences.append(FragmentOccurrence(index, span, proof, origin, refs, causes, self._request.scene))
        _require(type(assembly.prompt) is str and assembly.prompt == '\n'.join(texts), 'INVALID_ASSEMBLY')
        # Includes every ACTUAL positive/conditional and exclusion occurrence,
        # including required projections. Base occurrences are supplied by 1C.
        self._snapshot.check_compatibility(scene, tuple(actual[len(scene.base_fragments):]),
            required_keys=required, forbidden_keys=banned)
        return tuple(occurrences)

    def check_preview(self, preview):
        """Complete current verification; corruption is terminal, never repaired."""
        if self._state == 'FAILED_TERMINAL':
            return self._failure
        try:
            _require(self._state == 'PREVIEW_ISSUED' and type(preview) is OfflinePreview
                     and preview is self._preview, 'STALE_VALIDATION')
            self._intact()
            _require(preview.request is self._request and type(self._gate) is sg.SyntheticAssemblyGate,
                     'STALE_VALIDATION')
            _require(type(preview.artifact) is sg.SyntheticValidatedAssembly, 'UNTRUSTED_AUTHORITY')
            _require(_bytes(preview) == self._preview_bytes, 'STALE_VALIDATION')
            scene = self._snapshot.scene(self._request.scene.scene_id, style=self._request.style,
                mode=self._request.mode, version=self._request.scene.version)
            selections = _selections(self._snapshot, scene, self._request.artistic)
            _require(_bytes(selections) == _bytes(preview.selections), 'STALE_VALIDATION')
            occurrences = self._verify_assembly(preview.artifact.assembly, scene, selections)
            _require(_bytes(occurrences) == _bytes(preview.occurrences), 'STALE_VALIDATION')
            _require(preview.authority == preview.artifact.authority == 'synthetic_offline'
                     and preview.production_authorized is preview.artifact.production_authorized is False,
                     'UNTRUSTED_AUTHORITY')
            result = self._gate.check_artifact(preview.artifact)
            st.safety_failure(result)
            return result
        except (st.VisualSafetyFailure, RegistryError) as error:
            return self._terminal(error, 'final')
        except (AttributeError, TypeError, ValueError, RecursionError):
            return self._terminal(None, 'final')
        except Exception:
            self._terminal(None, 'final')
            raise


def create_offline_renderer(environment):
    try:
        return OfflineRenderer(environment, _key=_PREVIEW_KEY)
    except RegistryError as error:
        st.safety_failure(_registry_result(_registry_diagnostic(error), 'preflight'))
    except (AttributeError, TypeError, ValueError, RecursionError):
        _fail()
