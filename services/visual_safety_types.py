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
        if self.detail not in {None, 'relational_scope', 'unknown_target',
                              'ambiguous_scope', 'unsupported_structure'}:
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


@dataclass(frozen=True, slots=True)
class SafetyFailureData:
    result: ValidationResult
    public_message_key: str
    retryable: Literal[False] = False

    def __post_init__(self):
        if self.result.outcome != 'blocked' or not self.result.issues or self.retryable is not False:
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


def invalid_evidence() -> None:
    raise VisualSafetyFailure(SafetyFailureData(
        ValidationResult('blocked', 'interpretation',
                         (ValidationIssue('INVALID_EVIDENCE', 'interpretation'),), ''),
        'visual_prompt_cannot_be_validated',
    )) from None


def immutable_tuple(value) -> None:
    if not isinstance(value, tuple):
        invalid_evidence()
