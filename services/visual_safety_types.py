"""Provider-free SG-01 result contracts. No production gate is activated here."""

from dataclasses import dataclass
from typing import Literal


DirectiveRef = tuple[str, int]
ScopeRef = tuple[str, int]
Stage = Literal['interpretation', 'preflight', 'candidate', 'final', 'dispatch']
ReasonCode = Literal[
    'UNRESOLVED_EXCLUSION', 'UNSUPPORTED_VISUAL_REQUEST', 'OBJECT_CONFLICT',
    'COASTAL_CONFLICT', 'STYLE_CONFLICT', 'HUMAN_PRESENCE_CONFLICT', 'SCENE_CONFLICT',
    'MISSING_MANDATORY_EXCLUSION', 'FORBIDDEN_POSITIVE_CONTENT',
    'MISSING_REQUIRED_VISUAL_FACT', 'UNTRUSTED_ENFORCEMENT_UNPROVEN',
    'FINAL_PROMPT_OVER_CAPACITY', 'CAPACITY_UNVERIFIED', 'INVALID_EVIDENCE',
    'UNTRUSTED_AUTHORITY', 'STALE_VALIDATION', 'INVALID_ASSEMBLY',
]


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: ReasonCode
    stage: Stage
    evidence_refs: tuple[DirectiveRef, ...] = ()
    fragment_indices: tuple[int, ...] = ()
    detail: str | None = None

    def __post_init__(self):
        immutable_tuple(self.evidence_refs)
        immutable_tuple(self.fragment_indices)
        if self.code not in ReasonCode.__args__ or self.stage not in Stage.__args__:
            invalid_evidence()
        if self.detail not in (None, 'relational_scope', 'unknown_target',
                              'ambiguous_scope', 'unsupported_structure'):
            invalid_evidence()
        if any(type(index) is not int or index < 0 for index in self.fragment_indices):
            invalid_evidence()
        if any(not isinstance(ref, tuple) or len(ref) != 2
               or not isinstance(ref[0], str) or type(ref[1]) is not int
               for ref in self.evidence_refs):
            invalid_evidence()


@dataclass(frozen=True, slots=True)
class ValidationResult:
    outcome: Literal['allowed', 'blocked']
    stage: Stage
    issues: tuple[ValidationIssue, ...]
    resolution_digest: str
    assembly_digest: str | None = None

    def __post_init__(self):
        immutable_tuple(self.issues)
        if self.stage not in Stage.__args__ or self.outcome not in {'allowed', 'blocked'}:
            invalid_evidence()
        if (self.outcome == 'blocked') != bool(self.issues):
            invalid_evidence()
        if any(not isinstance(issue, ValidationIssue) or issue.stage != self.stage for issue in self.issues):
            invalid_evidence()
        if (not isinstance(self.resolution_digest, str)
                or self.assembly_digest is not None and not isinstance(self.assembly_digest, str)):
            invalid_evidence()


@dataclass(frozen=True, slots=True)
class SafetyFailureData:
    result: ValidationResult
    public_message_key: str
    retryable: Literal[False] = False

    def __post_init__(self):
        if (type(self.result) is not ValidationResult or self.result.outcome != 'blocked'
                or not self.result.issues or self.retryable is not False):
            invalid_evidence()
        if self.public_message_key not in {
            'visual_exclusion_unresolved', 'visual_request_unsupported',
            'visual_constraints_conflict', 'visual_prompt_cannot_be_validated',
            'visual_prompt_too_long',
        }:
            invalid_evidence()


class VisualSafetyFailure(Exception):
    """A deterministic veto; the printable message contains stable codes only."""

    def __init__(self, failure: SafetyFailureData):
        self._failure = failure
        super().__init__(','.join(issue.code for issue in failure.result.issues))

    @property
    def failure(self) -> SafetyFailureData:
        return self._failure

    def __str__(self) -> str:
        return ','.join(issue.code for issue in self.failure.result.issues)


def safety_failure(result: ValidationResult) -> None:
    """Enforce a typed verdict without disclosing source/provider prose."""
    if result.outcome == 'allowed':
        return
    codes = {issue.code for issue in result.issues}
    key = ('visual_exclusion_unresolved' if 'UNRESOLVED_EXCLUSION' in codes else
           'visual_request_unsupported' if 'UNSUPPORTED_VISUAL_REQUEST' in codes else
           'visual_prompt_too_long' if 'FINAL_PROMPT_OVER_CAPACITY' in codes else
           'visual_prompt_cannot_be_validated')
    raise VisualSafetyFailure(SafetyFailureData(result, key)) from None


def invalid_evidence(stage: Stage = 'interpretation') -> None:
    raise VisualSafetyFailure(SafetyFailureData(
        ValidationResult('blocked', stage,
                         (ValidationIssue('INVALID_EVIDENCE', stage),), ''),
        'visual_prompt_cannot_be_validated',
    )) from None


def immutable_tuple(value) -> None:
    if not isinstance(value, tuple):
        invalid_evidence()


Origin = Literal['curated', 'user_projection', 'system_rule', 'llm', 'generated_plan',
                 'scene_hint', 'memory_avoid', 'raw_override', 'raw_user_prose']
FragmentRole = Literal['positive_scene', 'style', 'qualifier', 'mandatory_exclusion',
                       'soft_avoid', 'conditional_anatomy', 'no_text', 'untrusted_prose']
SemanticKey = tuple[str, str]
HumanPresence = Literal['none', 'hands_only', 'single_person', 'distant_figure']
CapacityUnit = Literal['unicode_codepoints', 'utf8_bytes', 'tokens']


def semantic_keys(value) -> None:
    if (not isinstance(value, frozenset) or any(
            type(key) is not tuple or len(key) != 2
            or not isinstance(key[0], str)
            or key[0] not in {'object', 'coastal', 'artifact', 'scene', 'qualifier', 'system'}
            or not isinstance(key[1], str) or not key[1] for key in value)):
        invalid_evidence()


@dataclass(frozen=True, slots=True)
class PromptCapacity:
    adapter_id: str
    model: str
    unit: CapacityUnit
    maximum: int
    counter_version: str
    evidence_reference: str
    capability_version: str

    def __post_init__(self):
        if (self.unit not in CapacityUnit.__args__ or type(self.maximum) is not int or self.maximum < 1
                or any(not isinstance(s, str) or not s for s in (
                    self.adapter_id, self.model, self.counter_version,
                    self.evidence_reference, self.capability_version))):
            invalid_evidence()


@dataclass(frozen=True, slots=True)
class FragmentProvenance:
    origin: Origin
    evidence_refs: tuple[DirectiveRef, ...]
    registry_id: str | None
    registry_version: str | None
    slot_value: str | None = None

    def __post_init__(self):
        immutable_tuple(self.evidence_refs)
        if (self.origin not in Origin.__args__ or any(
                type(r) is not tuple or len(r) != 2 or not isinstance(r[0], str)
                or type(r[1]) is not int for r in self.evidence_refs)
                or any(s is not None and not isinstance(s, str) for s in (
                    self.registry_id, self.registry_version, self.slot_value))):
            invalid_evidence()


@dataclass(frozen=True, slots=True)
class PromptFragment:
    text: str
    role: FragmentRole
    provenance: FragmentProvenance
    positive_keys: frozenset[SemanticKey] = frozenset()
    excluded_keys: frozenset[SemanticKey] = frozenset()
    conditional_keys: frozenset[SemanticKey] = frozenset()

    def __post_init__(self):
        if (not isinstance(self.text, str) or not self.text or self.role not in FragmentRole.__args__
                or type(self.provenance) is not FragmentProvenance):
            invalid_evidence()
        for keys in (self.positive_keys, self.excluded_keys, self.conditional_keys):
            semantic_keys(keys)
