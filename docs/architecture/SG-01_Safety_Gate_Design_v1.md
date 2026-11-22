# SG-01 Visual Safety Gate — Architecture Specification v1

Date: 2026-11-22  
Revision: D0-R2, targeted corrections following SG-01-DESIGN-REVIEW-R2  
Author role: Architecture Designer — Codex  
Status: **D0-R2 targeted verification accepted as Owner-supplied evidence; Stage 1A only authorized; O-1 conditionally approved**

### Authorization update — 2026-11-22

The Owner reports independent Claude Code targeted verification: **GO FOR OWNER DECISION — no remaining architectural contradictions**, and authorizes **SG-01 Stage 1A only** (structural interpretation, immutable evidence, pure resolution and interpretation-level deterministic tests). The original D0 statements below about work not performed describe that design revision, not this later authorization. Section 13 records the controlling O-1 decision.

Stage 1A does not activate SG-01, select an enforcement route, certify provider prompts, change generation behavior/configuration, or authorize Package B+C integration or deployment. Its `check_interpretation` result has stage `interpretation`; `allowed` means visual-policy eligibility only. The retained `enforcement_route=None` is deliberately incomplete for V1–V4 and conveys no dispatch authority. Future route selection, capacity verification, Custom Style fidelity/enforcement, final assembly and entry-point integration require separately authorized work. See [Stage 1A implementation record](SG-01_Stage1A_Implementation_Record.md) for evidence and deliberate test migrations.

## 1. Scope, evidence and fixed decisions

This document specifies a deterministic gate between current visual instructions and image-provider dispatch. It defines evidence retention, resolution, assembly and failure handling. It does not implement SG-01, integrate Package B+C, modify Package A, change configuration, run tests, invoke providers, deploy, migrate data or authorize any of those actions.

The last independently confirmed full test baseline supplied by the Owner is **5,335 PASS**. It was not rerun for this documentation revision. Existing test expectations cited below are evidence of current behavior, not proof that production already satisfies this design.

The evidence is the Owner's D0 request, the current repository sources, Package A structural/semantic oracles, the frozen [FIX-03 specification](../product/RS_FIX03_Visual_Diversity_Frozen_Specification_v1.0.md), and the Owner's confirmed follow-up extracts from independent Claude Code report **SG-01-DESIGN-REVIEW-01: DR-11, DR-12 and section H.2 (N-2)**. The report verdict/counts are Owner-supplied: 3 BLOCKER, 5 MAJOR, 2 MINOR, 2 NOTE. DR-11/DR-12/N-2 are confirmed findings, not unverified placeholders. Section 12 records design responses without claiming independent audit acceptance.

This D0-R2 revision applies the Owner-supplied corrections from **SG-01-DESIGN-REVIEW-R2**, verdict **REVISE BEFORE IMPLEMENTATION**, including the confirmed exact R2-N1–N7 extracts from section C supplied in the follow-up. Section 12 records each finding's design disposition without claiming independent acceptance. Only this architecture document changes; D1-A, SG-D1 and SG-D2 remain frozen, and Package B+C integration is not started.

The following are frozen, not options for a new policy vote:

- **D1-A:** structural negative-list continuity, source-specific authority, independent directive boundaries and exactly two closed standalone-hard-chunk legacy exceptions: `No people, ocean` and `No people, beach at sunset`.
- **SG-D1:** a visual relational exclusion that cannot be safely represented is `BLOCKED: UNRESOLVED_EXCLUSION`. A local restriction must not become a global object ban.
- **SG-D2:** a narrative request such as `Покажи историю про кружки и окна` alone is unsupported; its mentioned objects do not become literal visual requests. An explicit visual artifact or scene request remains eligible.
- **AR-01 migration is approved:** structural boundaries and polarity come from shared AR-01 evidence. Preserving the old parsers' negative-to-positive promotion is not an alternative policy.
- FIX-03A coastal precedence is preserved. Accepted LLM enrichment validation, FIX-03B-2B-2, remains a separate task. No additional paid LLM/reviewer call is introduced.

Here, `MUST` defines the proposed implementation contract. It does not mean the implementation has been accepted. “Safe prompt” means conformance to the bounded deterministic contract, not a guarantee about arbitrary natural-language meaning or the pixels produced by an image model.

## 2. Current entry points and the migration boundary

The following inventory was read from the working files without Git. Names, rather than line numbers, are the stable references.

| Current surface | Actual behavior relevant to SG-01 | Required future change |
|---|---|---|
| `services/directive_segments.py`: `segment_directives`, `nominal_core` | Isolated Package A; immutable original offsets, source/scope/directive identities, hard chunks, polarity and bounded nominal grammar. No production callers yet. | Become the sole structural authority; add vocabulary-independent frame/attachment evidence described in section 4. |
| `services/visual_intent.py`: `interpret_directives`, `interpret_visual_intent` | Isolated Package A. `VisualFact` retains provenance. Six-word nominal recognition can leave negative facts ineligible; unknown nouns may produce no facts. Only object conflicts currently raise `ValueError`. | Consume shared structure once, classify requests and retain unresolved negative evidence even when recognition yields zero facts. Resolve through typed results rather than incomplete canonical sets. |
| `services/visual_constraints.py`: `_fragments`, `user_visual_constraints`, `positive_objects`, `forbidden_objects` | Independent object polarity/list parser, raw-text scanners, human cascade and compatibility helpers. | Replace production intent use with projections of resolved AR-01 output. Move closure ownership to one resolver; compatibility checks consume evidence or registered fragment semantics. |
| `services/coastal_intent.py`: `_scoped_fragments`, `parse_coastal_text`, `user_coastal_intent`, `user_scene_prompt_parts`, `coastal_request_text` | Independent coastal scope/polarity reconstruction; some fragments are parsed again. `CoastalIntent`, style/time helpers implement FIX-03A behavior. | Keep useful rendering/routing projections; remove independent polarity reconstruction from every production path, including generated-content checks. |
| `handlers/generation.py`: `_generation_preflight_error`, `_start_generation_after_preflight`, `_run_generation` | Coastal-only early preflight. `_run_generation` repeats preflight, reserves daily usage, generates card text, builds a scene or enrichment prompt, calls `generate_image`. A broad controlled-scene catch sets `prompt_final=None`, allowing another path. | Build/recheck shared intent before reservation/paid text, pass it through all builders, catch typed safety failures before generic handlers, retain existing `finally` release. |
| Profile generation and `again_affirmation` in `handlers/generation.py` | Profile requests reread current preferences; More reconstructs a request. | Rebuild evidence from the actual current authorized sources. Do not reuse a previous prompt or interpretation as current user authority. |
| `scheduler.py`: `_process_due_delivery`, `_deliver_subscription`, `_release_failed_attempt` | Claims a logical delivery; `_deliver_subscription` uses `user_text=None` and `custom_style_description=None`, generates text and an image. Controlled-build generic catch can select the enriched/template builder, with LLM use disabled while the scene flag is on. Permanent classification currently includes Telegram forbidden and `ProviderOutputValidationError`, not SG-01. | Resolve the actual scheduled sources before paid work; propagate typed safety failures; mark them terminal using the existing attempt-fenced ledger operation. |
| `cli.py`: `async_main` | Optional STT, then `asyncio.gather(generate_affirmations(...), generate_image(...))`; broad catch becomes `SystemExit`. | Preflight after transcription and before creating either generation task; typed safety exit; settle/cancel sibling work on later failure. |
| `services/yandex_gpt.py`: `build_enriched_image_prompt` | Builds a local template, optionally makes an enrichment call, returns `(str, trace)`. Transport/format and coastal checks can return `template_fallback`; accepted LLM text still receives later image assembly. | Return a provenance-bearing candidate. Run safety checks outside fallback catches; never convert an SG-01 veto into fallback. Preserve the separate enrichment-review scope. |
| `services/scene_planner.py`: `normalize_scene_plan`, `reconcile_scene_constraints`, `apply_coastal_scene_intent`, `build_scene_image_prompt` | Reparse inputs; merge `constraint_sources['user_*']` from mutable plan dictionaries; duplicate human closure/default handling. | Receive resolved intent, derive user arrays only from that object, and treat all generated plan strings as generated data. |
| `services/scene_prompt_builder.py`: `build_controlled_scene_prompt` | Repeats reconciliation/parsing; parses style-generated negative strings as if they were user text; joins plan strings and extras. Lines 280–284 interpolate cleaned `focus_title` as emotional-focus prose after only a bounded object check; `handlers/generation.py:1377–1389` can supply the raw user theme through this input. | Assemble typed fragments. A local join of LLM-derived plan fields or cleaned focus prose does not make those fields trusted. |
| `services/openai_image.py`: `_build_image_prompt`, `_ensure_no_text_clause`, `generate_image` | `generate_image` accepts raw overrides and trace strings; may select presets, augment photo overrides, enforce no-text, or discard override for symbolic mode; finally posts mutable `payload['prompt']` via `aiohttp`. Lines 698–700 interpolate `positive_text` into a quoted scene-idea clause. | Own the final assembly/validation boundary after all mutations. Parsed/filtered user prose is still untrusted; only a validated assembly can reach the internal transport. |
| `handlers/generation_formatting.py`: `update_image_meta`; `services/ritual_config.py`: `has_coastal_intent` | Metadata and compatibility surfaces call `user_coastal_intent` again. | Metadata reads the actual resolution/assembly. A standalone compatibility query delegates to AR-01, never the old scoper. |

Scene planner/shadow/orchestrator output, image hints, memory avoids, generated affirmations and provider-authored text are auxiliary evidence. They cannot populate authoritative user requests/exclusions, even if a dictionary labels them `user_requests`, a trace says `template`, or text contains the two legacy phrases. Profile `avoid_topics` and `avoid_words` retain their existing textual contract; SG-01 does not turn them into visual exclusions.

### Intended authoritative flow

```text
actual entry-point source snapshot + requested style/mode
    -> AR-01 structural segmentation, once per immutable source
    -> vocabulary-independent frames/attachments on those same identities
    -> visual_intent: semantic eligibility + canonical recognition + unresolved evidence
    -> resolve_visual_intent: precedence, conflicts and authoritative closure
    -> preflight result (or typed safety failure)
    -> scene/template/enrichment candidate with fragment provenance
    -> deterministic reconciliation and last assembly changes
    -> validate exact final prompt and complete constraint coverage
    -> opaque ValidatedAssembly
    -> internal image dispatch using precisely its validated prompt
```

No consumer may infer source authority or user polarity from the final prompt. A generated-content inspection may reuse AR-01 segmentation with a generated source kind; it cannot create authoritative user facts. No additional independent raw-text polarity parser is permitted for either purpose.

### Migration sequence and compatibility

1. Specify/verify structural frame evidence and semantic classification in isolated AR-01. Retain original objects and identities. Add negative coverage accounting before using effective sets. Existing Package A characterization tests of lost exclusions must become explicit blocked-result oracles during the separately authorized implementation. Migrate positive-frame expectations for supported artifact/scene heads and attachments as specified in section 11; preserve narrative rejection and D1-A fences.
2. Add the pure resolution and assembly contracts, then the typed safety failure and non-bypassable internal provider boundary. These are future implementation steps, not work performed in D0.
3. Convert `visual_constraints` and `coastal_intent` to adapters over one `ResolvedVisualIntent`; convert scene planner/builder, template builder, enrichment checks and style/time routing to consume the same instance. Register curated style/preset semantics rather than parsing their negative strings into user authority. Ignore model-supplied `constraint_sources['user_*']`; overwrite compatibility arrays from resolution.
4. Wire interactive, Profile/More, scheduler, CLI and direct `generate_image` entry points. Wire metadata and `has_coastal_intent` so telemetry cannot report the old interpretation. Install typed catches before enabling the changed gate in a runtime.
5. Verify import/call-path and transport assertions in section 11. A production cutover is one coherent integration: do not enable a path that uses AR-01 for objects but old coastal polarity, or vice versa. An offline comparison may characterize intentional changes; old results never arbitrate disagreements.

Internal production calls use `visual_constraints_projection(resolution)` and `coastal_projection(resolution)`, without raw strings. Transitional public convenience functions may keep raw-input signatures, but MUST call the shared snapshot/AR-01/resolver pipeline and raise the typed failure on blocked resolution. They may not call `_fragments` or `_scoped_fragments`. `positive_objects(text)` and `parse_coastal_text(text)` cannot remain safety bypasses: production uses fragment metadata or shared generated-source interpretation instead. Old parser implementations can remain temporarily as explicitly isolated test characterization helpers, with no production reachability; removal is a later implementation detail.

`generate_image(...) -> str` can keep its path-returning external shape. A direct raw-input caller creates the same resolution and candidate internally; a raw `prompt_override` becomes `UNTRUSTED` evidence, regardless of `image_prompt_trace`. Internal callers pass a typed candidate/resolution. No caller can certify a prompt by supplying a trace or `validated=True`. Incompatible inputs fail explicitly; compatibility does not preserve incorrect polarity or allow a missing resolution.

### Proposed code ownership and core operations

During a separately approved implementation, `directive_segments` owns structural evidence and `visual_intent` owns interpretation/classification. A provider-free `services/visual_safety.py` owns the proposed resolution/validation/assembly contracts, the single closure definition, the typed failure, and final certification. A neutral, versioned registry owns all curated semantics used by the gate: object/coastal aliases and qualifier tables, `COASTAL_STYLES`, `COASTAL_SCENES`, `COASTAL_STYLE_DIRECTIONS`, style identities/aliases and prohibitions, **`normalize_style_key` and fixed-style incompatibility sets** (including coast/interior and dedicated-beach incompatibilities), scene/photo presets and their semantics, composition/color/focus fragments, symbolic subject/accent/prohibition contracts, conditional anatomy, canonical exclusions and no-text fragments. It also owns approved enforcement-policy records. `normalize_style_key` is a pure alias lookup over that registry; it must not import `ritual_config` or `coastal_intent`. Preserve the existing mode-specific compatibility rules. Existing modules may re-export these definitions; they must not maintain competing copies.

The dependency direction is neutral data -> interpretation/gate/builders (each imports the data). The neutral registry has no imports from `visual_safety`, `coastal_intent`, `visual_constraints`, `scene_planner`, `scene_prompt_builder`, `openai_image`, `yandex_gpt`, `ritual_config`, handlers or scheduler, and performs no configuration, provider or application I/O. The gate must not import any of those consumer/builder modules, including `coastal_intent` just to obtain coastal constants. Builders create candidates; they cannot issue certificates. `openai_image` owns the private transport and consumes the certificate.

The core API shapes are:

```text
# visual_intent: pure, including when facts conflict; no generic ValueError
interpret_directives(segmentations) -> VisualInterpretation

# visual_safety: pure derivation, followed by explicit checks
resolve_visual_intent(interpretation, *, requested_style, requested_mode,
                      policy_version, vocabulary_version,
                      enforcement_policy) -> ResolvedVisualIntent
check_preflight(resolution, *, capacity, enforcement_route) -> ValidationResult
check_final_assembly(assembly) -> ValidationResult

# enforcement factory: returns only on success; otherwise VisualSafetyFailure
validate_final_assembly(assembly) -> ValidatedAssembly

# openai_image: internal, never accepts raw prompt text
_dispatch_validated_image(validated: ValidatedAssembly) -> str
```

These signatures describe the complete integration contracts. `check_preflight` verifies the resolution-owned enforcement route under approved policy and the conditional O-1 constraints in section 13; it cannot infer a reroute from a safety failure. Stage 1A implements interpretation resolution only, without `check_preflight` or route selection. Existing Package A object-conflict `ValueError` moves into the resolver's typed validation result so evidence survives. Future transitional wrappers enforce that result before returning legacy projections.

## 3. Structural and semantic division

### Structural authority

`directive_segments` owns markers, nested negative predicates, list continuity, hard chunks, independent command boundaries, frames and syntactic attachments. It may use bounded RU/EN grammatical vocabulary (verbs, conjunctions, prepositions, function words). It MUST NOT import the visual vocabulary, decide whether a head denotes a visual object/artifact, or vary segmentation when a noun changes from `mug` to `glarg`.

The frame extension records an opaque nominal head and dependent spans instead of treating every function word as a reason to reject an entire render command. Structural recognition of `with`, `featuring`, `at`, `on`, `про`, etc. records a relationship; it does not itself grant or revoke visual eligibility. This replaces dependence on a growing preposition blacklist. Unsupported syntax remains explicitly uncertain. The supported grammar is bounded, not a promise of general parsing.

The extension MUST cover, at minimum, nominal render complements, their coordinated nominal dependents, relation modifiers, the current negative predicates, independent commands and conditional clauses. It records whether a modifier attaches to an opaque nominal head, its governing frame, or an uncertain host. It does not decide that a noun denotes a scene. `Море без пляжа` and an opaque nominal substitution must have the same structural evidence; downstream coastal recognition authorizes the approved scene-level meaning. `No mugs on tables` also retains its relational evidence, which downstream recognition must not flatten.

### Visual interpretation

`visual_intent` examines the structural head and its attachments, using bounded, versioned registries:

- Existing canonical objects and coastal categories, with aliases shared by every projection.
- Visual artifact heads; minimum SG-D2 coverage includes `poster` and the corresponding explicit visual-artifact forms covered by the implementation oracle.
- Explicit scene heads mapped to existing scene/environment vocabulary; minimum coverage includes `mountain(s)` with the `sunrise` qualifier. No artifact noun is required for a scene.
- Supported qualifier facts preserve existing coastal lighting and tropical/palm cues, plus the required scene `sunrise` case. Qualifier recognition consumes the structural spans and governed head; it cannot create an independent positive subject from a negative or narrative span.
- Narrative/content heads such as `story`/`история`, `report` and discussion/read complements. These block literal promotion of their dependent mentions.
- Known nonvisual idiom/abstract-head forms needed to preserve established cases such as `No time for my notebook`. Unknown negative heads do not enter this nonvisual registry by default.

The first recognized object somewhere in a sentence is never a head-classification algorithm. A positive directive is eligible only when its structural head is a supported visual artifact, object or scene in a supported render/nominal frame. Supported attachments then contribute dependent facts without losing their inherited polarity. Thus `Show a poster featuring mugs and windows` and `Show a poster with a mug` are eligible, while `Show a story about mugs and windows` is unsupported. `Show mountains at sunrise` is eligible through the scene head and qualifier.

A narrative frame denies authority to all members of that content complement, including coordinated or comma-separated mentions. A separate supported directive remains eligible: `Покажи историю про кружки и окна; покажи стол` requires the table only. The same applies to a structurally independent `, show a table` command. An ambiguous coordinator without a supported independent directive does not let a narrative sibling escape its frame.

Eligible does not imply unrestricted support for every modifier. Unknown essential heads/relations yield an unsupported classification; no invented paraphrase is rendered. Semantically optional descriptive modifiers may only be rendered through supported qualifier slots. A positive unknown object does not become a known object merely because a familiar noun appears nearby.

### SG-D1: structural relationship followed by visual-head recognition

First apply the closed D1-A legacy classification to the complete original hard chunk, once per interpreted scope, **before effective SG-D1 exclusion derivation**. Only its designated coastal member (and the approved attached sunset qualifier) may receive the existing positive legacy basis. Keep that member's structural NEGATIVE polarity, original spans and full source/scope/directive provenance. Record its ledger disposition as `resolved_positive_legacy_exception`; it is no longer an active negative exclusion. This ordering neither expands matching nor exempts any other member or independent negative directive.

For every remaining active authoritative negative exclusion, inspect its existing structural evidence before deriving sets:

1. A supported unqualified object/coastal head with a global scene scope resolves to a canonical exclusion.
2. A relational modifier attached to a recognized visual head, or to a recognized visual render frame, is potentially local. `No mugs on tables`, `No people near windows`, and `Show a mug without a logo` are not flattened into global bans on mugs, people, tables, windows or logos. The minimum SG-01 renderer does not represent these local relationships: preserve their full evidence and block with `UNRESOLVED_EXCLUSION / RELATIONAL_SCOPE`.
3. A relationship with an unknown/ambiguous head cannot establish that the ban is harmless. Preserve it and block with `UNKNOWN_TARGET` or `AMBIGUOUS_SCOPE` if an active visual exclusion remains possible.
4. A positively established nonvisual/narrative head in the bounded registry does not create a visual exclusion: `No time for my notebook` and `No report about mugs and windows` retain nonvisual classification and contribute no object bans. This is an explicit classification, not an unlogged discard.
5. Approved scene-level coastal constructions, such as `Море без пляжа` and `Show rocky coast without beach`, are represented as positive coastal facts plus scene-level coastal exclusions under FIX-03A. This narrowly supported composition is not a generic rule that any `without` attachment is global. A qualified negative coastal relation such as `No beaches near houses` remains unresolved.

Structural attachment alone can overblock harmless prose; visual-head recognition alone can overmatch metaphors or quoted text. The two-stage decision reduces those errors without claiming to eliminate them. Uncertain active visual negatives fail closed. Inactive custom notes and auxiliary generated sources do not cause user-exclusion blocks. Quotation, metaphor and unsupported RU morphology are residual coverage risks; uncertain cases are observable and are not silently accepted.

## 4. Immutable evidence and resolution contracts

These are proposed Python-level type contracts, not executable additions to the repository. All records below are `@dataclass(frozen=True, slots=True)` unless an opaque factory is specified. Containers are tuples/frozensets, never mutable dictionaries or lists. All enums have the literal values listed. Type aliases do not create a second identity system.

### 4.1 Reuse of Package A and structural additions

Reuse existing `Span`, `DirectiveSource`, `SourceKind`, `Polarity`, `Scope`, `Directive`, `SegmentedSource`, `VisualFact`, `FactDomain` and `FactBasis`. Offsets remain half-open Python string offsets into the unmodified source. Do not clip, normalize or concatenate source text before computing offsets.

```python
DirectiveRef = tuple[str, int]  # existing (source_id, directive_id)
ScopeRef = tuple[str, int]      # existing (source_id, scope_id)

Frame = Literal['nominal', 'render_complement', 'conditional', 'unknown']
Attachment = Literal['frame_level', 'head_local', 'uncertain']

class RelationEvidence:
    marker_span: Span
    dependent_span: Span
    dependent_directive_ids: tuple[int, ...]  # same source; may be empty
    attachment: Attachment

class DirectiveStructure:
    directive_id: int           # key into this SegmentedSource.directives
    frame: Frame
    head_span: Span | None      # opaque grammatical head, not a visual key
    nominal_span: Span | None
    qualifier_spans: tuple[Span, ...]
    relations: tuple[RelationEvidence, ...]
    governing_directive_id: int | None
    uncertain: bool

# Add to SegmentedSource, produced in the same structural pass:
# structure: tuple[DirectiveStructure, ...]
```

There is exactly one structure record per directive, keyed by its existing ID. Relations/heads remain inside the source and the owning frame; governing links are acyclic. The existing directive's scope link remains authoritative: no new independent source, scope or directive IDs are minted. A scope may own several member records. The frame extension must retain complement ownership even where conjunctions produce separate members, so a narrative head controls its dependent mentions.

**DR-11 identity invariant:** `directive_id` and `scope_id` are integers local to one source, in separate namespaces. Global identity is only `(source_id, directive_id)` or `(source_id, scope_id)`, respectively. Both `user_text` and `custom_notes` can have directive 0 and scope 0 without collision. `source_id` is unique within an interpretation/snapshot; a ref used across snapshots must also be bound to that snapshot's resolution digest. A bare integer cannot key a cross-source cache, lookup, conflict or provenance join.

Existing `VisualFact` retains its exact fields: `domain`, `key`, `polarity`, `source_id`, `source_kind`, `directive_id`, `scope_id`, `span`, `eligible`, `basis`. These fields already provide provenance; no parallel copy of those identities is added. Fact eligibility remains subordinate to the source's activity/authority and semantic classification. Extend `FactDomain` with `ARTIFACT='artifact'`, `SCENE='scene'` and `QUALIFIER='qualifier'`; extend `FactBasis` with `VISUAL_HEAD='visual_head'` for newly supported visual-head complements/qualifiers. Existing basis values and closed legacy bases remain unchanged.

`VisualFact.source_kind` is derivable from the referenced source and is deliberately retained for evidence locality. It MUST equal that source's `kind`; the fact's `scope_id` MUST equal its referenced directive's scope. These useful derivable fields are checked, not treated as independent authority. A mismatched source kind or scope is `INVALID_EVIDENCE`.

The initial additional keys are artifact `poster`, scene `mountain`, and qualifiers `sunrise`, `sunset`, `morning`, `evening`, `tropical`, `palms`. Qualifiers are linked to their existing governing directive through structural evidence; a standalone mention cannot grant unrelated scene authority. `dedicated_beach` and coastal time/subtype routing are projections of eligible coastal/qualifier facts and the existing FIX-03A rules, not independently reparsed raw prose. A qualifier whose negative meaning cannot be represented creates unresolved evidence; unsupported qualifiers cannot disappear from an active exclusion.

The structural polarity in the original directive is immutable. A permitted interpreted polarity change (D1-A legacy or the existing active-custom nominal rule) is recorded only in a fact with its explicit basis. It never mutates structural evidence or creates a rule applicable to generated text.

For the exact legacy beach-at-sunset chunk, the eligible coastal fact also authorizes its structurally attached supported sunset qualifier. That qualifier carries the same closed legacy basis; it does not become a contradictory negative qualifier. This override cannot apply to unrelated facts, list extensions, auxiliary sources or another chunk.

**DR-12 scope-level legacy basis:** compute the closed legacy classification once for each `(source_id, scope_id)` from that scope's complete original `chunk_span`, before interpreting its member recognitions. Reuse that immutable semantic scope annotation for all its facts. Do not recompute it per fact/member or from a normalized member substring. It belongs to interpretation, not the vocabulary-independent structural `Scope`. This is a nonblocking design improvement to prevent future divergence; the verified D1-A behavior and exactly two allowed chunks are unchanged.

### 4.2 Interpretation records, including zero-recognition negatives

```python
RequestClass = Literal[
    'eligible', 'unsupported_narrative', 'unsupported_visual_form',
    'nonvisual', 'ambiguous', 'inactive_or_auxiliary'
]
NegativeClass = Literal[
    'resolved', 'resolved_positive_legacy_exception',
    'unresolved', 'nonvisual', 'inactive_or_auxiliary'
]
UnresolvedDetail = Literal[
    'relational_scope', 'unknown_target', 'ambiguous_scope',
    'unsupported_structure'
]

class DirectiveClassification:
    ref: DirectiveRef
    request_class: RequestClass
    head_span: Span | None
    fact_indices: tuple[int, ...]  # indexes in this VisualInterpretation.facts

class NegativeAssessment:
    ref: DirectiveRef
    classification: NegativeClass
    fact_indices: tuple[int, ...]
    target_span: Span             # full original negative target/attachment
    unresolved_detail: UnresolvedDetail | None

class UnresolvedNegative:
    ref: DirectiveRef
    detail: UnresolvedDetail
    target_span: Span             # original full target; no raw-text copy

class UnsupportedVisualRequest:
    ref: DirectiveRef
    kind: Literal['narrative', 'unsupported_form', 'ambiguous_head']
    head_span: Span | None

class VisualInterpretation:
    segmentations: tuple[SegmentedSource, ...]
    facts: tuple[VisualFact, ...]
    classifications: tuple[DirectiveClassification, ...]
    negatives: tuple[NegativeAssessment, ...]
    # unresolved_negatives and unsupported_requests: read-only derived views
```

`NegativeAssessment` is a coverage ledger, not a second parser. It is populated from AR-01 negative directives and structurally attached negative relations, including an ambiguous member whose owning frame carries negative polarity. It MUST exist even if the object/coastal recognizers return no matches. A detached D1-A member whose structural polarity is explicitly unspecified is not retroactively made negative just because its scope is negative.

**R2-01 ledger invariant:** every relevant structurally negative ref has exactly one explicit assessment, including each promoted legacy member. `resolved` means an active exclusion and has at least one effective canonical negative fact. `resolved_positive_legacy_exception` instead references the eligible positive fact with exactly the applicable `LEGACY_D1_A_OCEAN` or `LEGACY_D1_A_BEACH_SUNSET` basis and the unchanged original NEGATIVE directive; it contributes no negative fact, mandatory ban or unresolved-negative record for that member. In particular, the same promoted member cannot also produce `−water` or `−beach`. Its source/ref/target span and basis remain auditable in the ledger and digest. An independent exclusion of the same key still has its own assessment and participates in normal coastal precedence.

Every `unresolved` assessment has a non-null `unresolved_detail` and exactly one corresponding `UnresolvedNegative`; all other assessments have null detail. Any recognized but ineligible negative fact in an active possibly visual exclusion requires an unresolved assessment unless explicitly classified nonvisual or disposed as the closed positive legacy exception above. No record may be lost by filtering `eligible` facts. Inactive/auxiliary negatives remain observable but cannot become mandatory user restrictions.

`visual_intent` is the sole owner of the authoritative classifications and negative assessments. `unresolved_negatives` is a pure immutable projection of `negatives` (ref, detail and target span); `unsupported_requests` is a pure immutable projection of `classifications` (`unsupported_narrative` -> `narrative`, `unsupported_visual_form` -> `unsupported_form`, `ambiguous` -> `ambiguous_head`). Neither is a separately writable collection. Resolver, validators, adapters and telemetry consume these views from the same interpretation; they cannot rediscover, append or suppress records. Serialization may include a derived view only with equality verification against its owner, never as independent authority.

The three unsupported request classes apply only to explicit positive render requests after authority/activity classification. A negative directive, detached unspecified member or ordinary theme mention does not become an unsupported positive request just because it is ambiguous. Its negative assessment or non-request classification remains authoritative. This keeps D1-A's detached-member policy and normal theme behavior unchanged.

Unsupported narrative requests are separate records from unresolved exclusions. An unsupported positive narrative does not itself become an exclusion. A source containing no explicit visual directive is normal theme input and may use the existing default image path; an explicit unsupported render request alone is a blocked unsupported request, not permission to visualize its nouns.

### 4.3 Resolution, conflicts and one derived-data owner

```python
ConstraintDomain = FactDomain | Literal['system']
FactKey = tuple[ConstraintDomain, str]
RequestDisposition = Literal['none', 'eligible', 'unsupported', 'mixed']

class ResolvedFact:
    domain: FactDomain
    key: str
    polarity: Literal[Polarity.POSITIVE, Polarity.NEGATIVE]
    fact_indices: tuple[int, ...]  # supporting existing VisualFacts

class VisualConflict:
    kind: Literal['object', 'coastal', 'style', 'human_presence', 'scene']
    keys: frozenset[FactKey]
    evidence_refs: tuple[DirectiveRef, ...]
    candidate_field: str | None   # e.g. 'human_presence' or 'selected_style'
    resolution: Literal['blocked', 'exclusion_wins', 'soft_default_removed']

class MandatoryBan:
    domain: ConstraintDomain
    key: str
    evidence_refs: tuple[DirectiveRef, ...]  # empty only for curated/system bans
    causes: tuple[str, ...]        # closed rule IDs listed below

class ResolvedVisualIntent:
    interpretation: VisualInterpretation
    requested_style: str
    requested_mode: str
    disposition: RequestDisposition
    effective_facts: tuple[ResolvedFact, ...]
    mandatory_bans: tuple[MandatoryBan, ...]
    conflicts: tuple[VisualConflict, ...]
    enforcement_route: EnforcementRoute | None  # gate selection; none if blocked
    resolution_digest: str
    policy_version: str
    vocabulary_version: str
    registry_version: str
```

`resolve_visual_intent` owns effective fact derivation and the authoritative closure. All object/coastal set projections are read-only properties of these records. No caller independently unions extra forbidden objects. Candidate reconciliation invokes the same closure owner when a final scene enum creates a mandatory absence; it returns a new resolved candidate/assembly, not a mutated shared intent.

The closed initial cause IDs are `USER_EXCLUSION`, `HUMAN_EXCLUSION_CASCADE`, `COASTAL_EXCLUSION_CASCADE`, `SCENE_HUMAN_NONE`, `SELECTED_STYLE_CONSTRAINT`, `SYSTEM_NO_TEXT`. Curated style/scene constraints carry their registry origin in assembly provenance; they cannot masquerade as user bans. For combined causes, preserve all supporting refs and causes.

Authoritative closure rules:

| Input | Derived bans | Constraint |
|---|---|---|
| Explicit object `human` exclusion | `human`, `hands`, `body` | Preserve the existing human-to-anatomy cascade. No duplicate helper definition. |
| Explicit `hands` or `body` exclusion | That key only | Do not invent a reverse exclusion of all humans. |
| Reconciled scene `human_presence='none'` | `human`, `hands`, `body` | Generated absence is a soft default before reconciliation. An eligible human request may displace that default; an incompatible fixed style/scene blocks. |
| Coastal `beach` exclusion | `beach`, `sandy` | A sandy beach cannot evade a beach ban. |
| Coastal `water` or `coast` exclusion | `water`, `coast`, `beach`, `sandy`, `rocky`, `lagoon` | Preserve current FIX-03A coast-blocking behavior. Do not generalize to inland lakes or all water. |
| Coastal `sandy`, `rocky` or `lagoon` exclusion | That subtype | Never derive a positive complementary shoreline preference. |
| System no-text assembly rule | `('system', 'text_marks')` | Canonical no-text fragment covers text, words, letters, numbers, typography, logos and watermarks. This assembly-only key grants no extra raw-text recognition or user authority. |

Object positive/exclusion contradictions, including across active sources and via the human cascade, block. Coastal overlap retains both original facts and a conflict record; explicit exclusion wins when a compatible residual scene can satisfy FIX-03A. Example: `Ocean view, no rocky coast` remains water, not an invented beach. A suppressed coastal positive is not secretly reintroduced by style/time prose. If an explicit selected style or an indispensable scene requirement cannot coexist with the surviving restrictions, block rather than replace the selected style. Section 8 fixes expected cases.

`resolve_visual_intent` first establishes visual-policy eligibility, then selects an enforcement route for an otherwise ALLOWED resolution from the approved enforcement policy, before enrichment/preflight completion. It owns that immutable route record; builders cannot select or replace it. An unavailable authorized route produces a blocked result, never an empty allowed interpretation.

`resolution_digest` binds immutable sources including active flags, structural/semantic results and derived-view contents, requested style/mode, the complete selected **`enforcement_route`** (rule, policy and bounded-standard IDs/versions) and policy/vocabulary/registry versions through a canonical serialization. A pre-selection source-snapshot digest may identify route inputs; it is not a completed resolution digest or dispatch authority. This avoids a circular route-to-resolution hash. The final resolution digest changes when the route changes, even if effective sets and prompt text are identical. It is an integrity/cache key, not proof of semantic correctness. Equivalent sets with different provenance must not alias a cached resolution. Duplicate source IDs, invalid refs, out-of-range spans or cycles are contract failures, not empty results.

## 5. Validation results, capacities and typed failure

### 5.1 Result and reason codes

```python
Stage = Literal['interpretation', 'preflight', 'candidate', 'final', 'dispatch']
ReasonCode = Literal[
    'UNRESOLVED_EXCLUSION', 'UNSUPPORTED_VISUAL_REQUEST',
    'OBJECT_CONFLICT', 'COASTAL_CONFLICT', 'STYLE_CONFLICT',
    'HUMAN_PRESENCE_CONFLICT', 'SCENE_CONFLICT',
    'MISSING_MANDATORY_EXCLUSION', 'FORBIDDEN_POSITIVE_CONTENT',
    'MISSING_REQUIRED_VISUAL_FACT', 'UNTRUSTED_ENFORCEMENT_UNPROVEN',
    'FINAL_PROMPT_OVER_CAPACITY', 'CAPACITY_UNVERIFIED',
    'INVALID_EVIDENCE', 'UNTRUSTED_AUTHORITY',
    'STALE_VALIDATION', 'INVALID_ASSEMBLY'
]

class ValidationIssue:
    code: ReasonCode
    stage: Stage
    evidence_refs: tuple[DirectiveRef, ...]
    fragment_indices: tuple[int, ...]
    detail: str | None  # only a closed detail token; never source/provider prose

class ValidationResult:
    outcome: Literal['allowed', 'blocked']
    stage: Stage
    issues: tuple[ValidationIssue, ...]
    resolution_digest: str
    assembly_digest: str | None  # absent before final assembly

class SafetyFailureData:
    result: ValidationResult     # MUST be blocked and contain >=1 issue
    public_message_key: str      # selected from a fixed RU/EN message catalog
    retryable: Literal[False]    # deterministic for this snapshot/candidate

class VisualSafetyFailure(Exception):
    failure: SafetyFailureData   # exposed read-only; stable code-only str()
```

The exception is a dedicated `Exception` subclass, not `ValueError`, provider-output error, transport timeout or cancellation. Its data is immutable; messages/chains must not echo raw prompts, personal notes or provider content. Pure validation returns all issues in deterministic order (stage, code, refs, fragment indexes); enforcement raises this exception if blocked. Partial coastal precedence resolutions appear in `conflicts`, not as blocking issues. No generic success/warning result can override a blocking issue.

Use `UNRESOLVED_EXCLUSION` with `detail` from `UnresolvedDetail`; do not relabel it as `UNSUPPORTED_VISUAL_REQUEST`. An unresolved negative blocks even in a mixed request with otherwise eligible positives. An explicit unsupported positive request blocks only when no separate eligible visual directive survives. In mixed positive requests, keep unsupported classifications for observability, render only eligible directives, and set disposition to `mixed`.

### 5.2 No arbitrary exclusion count

There is no SG-01 maximum number of exclusions or six-word exclusion budget. Preserve every original negative span before recognition, deduplication, prompt clipping, or conversion to a set. Repeated exclusions can deduplicate in a projection while retaining every supporting ref.

The current six-word `nominal_core` bound is a grammar-coverage limitation, not a downstream representation capacity. Until that syntax is supported, an active visual ban outside the recognized form is `UNRESOLVED_EXCLUSION / UNSUPPORTED_STRUCTURE`; it cannot simply disappear. Extending grammar support later may resolve it, but must not add an independent polarity parser.

The actual downstream constraint is the chosen image adapter/model's supported prompt capacity. Current `ImageProviderConfig` has no declared capacity field. Neither the enrichment instruction “900 characters” nor the local `len(parsed) > 1200` acceptance check establishes image-provider capacity, and neither may truncate mandatory restrictions.

```python
CapacityUnit = Literal['unicode_codepoints', 'utf8_bytes', 'tokens']

class PromptCapacity:
    adapter_id: str
    model: str
    unit: CapacityUnit
    maximum: int
    counter_version: str         # exact tokenizer revision if unit == 'tokens'
    evidence_reference: str      # verified adapter/provider contract, not a guess
    capability_version: str
```

A later implementation must supply a verified capability for each supported dispatch adapter/model; this is an engineering prerequisite, not a new exclusion policy. For custom endpoints with unknown behavior, return `CAPACITY_UNVERIFIED` before paid generation if knowable then. Do not invent a numeric limit in this design. Verification of concrete external adapter capacities is deferred to the separately authorized implementation; no provider-capacity fact is asserted here.

Measure the entire exact final prompt using the specified counter. Optional generated decorations can be omitted during candidate construction, before final validation. Mandatory bans, eligible required facts, provenance and the original negative coverage ledger cannot be clipped. If the mandatory rendering alone exceeds the actual capacity, or a complete supported prompt cannot fit, block with `FINAL_PROMPT_OVER_CAPACITY`; retain original evidence and measured outcome. No count-limited array may discard a ninth/twentieth/etc. exclusion before this check. Tests use an explicitly small fake adapter capacity to exercise the real capacity algorithm, not a new production limit.

## 6. Prompt fragments and validated assembly

```python
Origin = Literal[
    'curated', 'user_projection', 'system_rule', 'llm', 'generated_plan',
    'scene_hint', 'memory_avoid', 'raw_override', 'raw_user_prose'
]
FragmentRole = Literal[
    'positive_scene', 'style', 'qualifier', 'mandatory_exclusion',
    'soft_avoid', 'conditional_anatomy', 'no_text', 'untrusted_prose'
]

class FragmentProvenance:
    origin: Origin
    evidence_refs: tuple[DirectiveRef, ...]
    registry_id: str | None
    registry_version: str | None

class PromptFragment:
    text: str
    role: FragmentRole
    provenance: FragmentProvenance
    positive_keys: frozenset[FactKey]
    excluded_keys: frozenset[FactKey]
    conditional_keys: frozenset[FactKey]

class EnforcementRoute:
    kind: Literal['fully_controlled', 'bounded_untrusted']
    source_snapshot_digest: str  # route inputs; excludes the route itself
    selection_rule_id: str       # gate-selected rule in approved policy registry
    policy_version: str
    bounded_standard_ids: tuple[str, ...]  # versioned; empty for fully_controlled
    selected_before_enrichment: Literal[True]

class PromptCandidate:
    resolution: ResolvedVisualIntent
    fragments: tuple[PromptFragment, ...]
    scene_type: str | None
    human_presence: Literal['none', 'hands_only', 'single_person', 'distant_figure']
    resolved_style: str
    effective_mode: str
    trace: str                  # descriptive only; no authority

class FinalAssembly:
    candidate: PromptCandidate
    enforcement_route: EnforcementRoute  # same immutable record as resolution
    prompt: str                 # exact output of the final deterministic join
    fragment_spans: tuple[Span, ...]  # offsets in prompt, same order as fragments
    mandatory_bans: tuple[MandatoryBan, ...]  # result of the ONE closure owner
    capacity: PromptCapacity
    model: str
    adapter_id: str
    size: str
    policy_version: str
    registry_version: str

class ValidatedAssembly:         # opaque; constructor private to safety gate
    assembly: FinalAssembly
    validation: ValidationResult # allowed, final; no issues
    assembly_digest: str
```

`ValidatedAssembly` is created only by `validate_final_assembly`; it is not accepted by deserializing user JSON, recreating a dataclass from a dict, setting a flag or passing a trace. Its immutable records are retained for the dispatch. This is an internal API trust boundary, not a security sandbox against hostile Python code in the same process.

Fragment key sets are verified derived metadata, not assertions a caller can freely attach to arbitrary text. Curated fragments are checked against a versioned registry of exact text and slot schemas. User projections are rendered from eligible resolved facts and supported qualifier slots, with refs; they do not paste raw theme/notes into a positive clause. Mandatory exclusions are emitted by canonical renderers from `mandatory_bans`. Untrusted fragments cannot declare themselves free of prohibited content or claim `user_projection` merely by supplying refs. Any LLM-produced setting, mood, main-subject or lighting string remains untrusted even after `normalize_scene_plan` or local string concatenation.

This rule explicitly covers the raw/filtered `positive_text` interpolation in `openai_image.py:698–700` and `focus_title` interpolation in `scene_prompt_builder.py:280–284`, as well as custom style, symbolic optional nuance, color/composition hints, sphere/subsphere labels and generated plan fields. Cleaning, quoting, parsing out exclusions or passing a known-object scan does not validate the remaining prose. A fully controlled route MUST replace image-relevant content with faithful canonical/registered rendering or validated closed slots; it contains **no unvalidated raw user or generated prose**. Optional auxiliary hints may be omitted; required visual/style content may not be discarded to obtain that route. An unrepresentable required custom description fails under section 9.3.

`enforcement_route` is authoritative gate-selected provenance, not a caller-supplied hint or trace. An approved versioned policy rule selects it from the resolved visual facts and applicable assembly restrictions before enrichment; `check_preflight` verifies the supplied route is the resolution-owned record and verifies its coverage. No rule/standard is authorized merely by appearing in this proposal. The complete route is bound into **`resolution_digest`** as defined in section 4.3. `FinalAssembly.enforcement_route` explicitly retains the same immutable record; the gate verifies equality/identity with `candidate.resolution.enforcement_route`, rather than allowing two independent selections. Metadata and the validation seal retain it too. `assembly_digest` binds the route, resolution digest, selection rule/version and all bounded-standard IDs/versions alongside all other section 6 inputs. Missing, forged, late or mismatched selection is invalid evidence; changing route/policy/standard invalidates both digests and the seal even when prompt characters are unchanged. A later-discovered restriction without approved route coverage blocks; it cannot initiate a new route after safety failure.

The registered anatomy anchor is conditional evidence, never a positive request for people, hands or faces. If `human`, `hands` or `body` is forbidden, omit incompatible anatomy/person-direction fragments and render the corresponding mandatory absence. A scene with `human_presence='none'` must contain no remaining positive/conditional anatomy demand. If hands are allowed and explicitly requested, use only a compatible registered anatomy fragment. Do not scan an arbitrary sentence and declare it conditional based only on a prefix.

Final validation MUST establish all of the following:

1. Evidence/refs and registry claims are valid; there are no unresolved active visual negatives or unhandled explicit conflicts. The candidate is bound to this resolution and selected style/mode.
2. Every mandatory ban is represented by its canonical registered exclusion fragment, with all required derived bans. Merely appending a phrase like “respect exclusions” is insufficient.
3. No controlled positive/conditional fragment demands a forbidden key; no forbidden object enters through preset, mood, color, composition, focus, scene setting or style examples. Every eligible effective required object/artifact/scene has a supported rendering. Unsupported narrative spans cannot appear as visual demands.
4. Reconciled scene enums and registered fragments agree, including human absence, coastal subtype, requested lighting and selected style compatibility. A generic avoid cannot suppress a higher-priority eligible request.
5. Untrusted fragments satisfy the selected enforcement boundary in section 9. An empty key set on an untrusted fragment is not evidence of safety.
6. The exact final string equals the deterministic serialization of these fragments and separators; every byte of content is accounted for. No extra suffix, copied raw note, text override or reconstruction is outside that assembly. Validate fragment spans, final no-text rule and full prompt capacity.
7. The gate seals the assembly plus resolution, enforcement-route provenance/standards, fragments/provenance, scene identity, style/mode, model/adapter/size, capabilities and policy/registry versions into `assembly_digest`.

`generate_image` performs all preset choice, photo augmentation, coastal time/composition reconciliation, symbolic routing, no-text completion and deterministic joins **before** this validation. Existing helpers may supply fragments; none may mutate the prompt afterwards. Build `payload['prompt']` directly from `validated.assembly.prompt` in the private transport. Serialization/JSON escaping must preserve the same decoded Unicode prompt value. Metadata stores that same prompt/digest and actual scene identity, not an earlier builder's approximation.

The dispatch guard rejects a stale or fabricated seal, a changed source/active flag/style/mode, changed fragments or order, changed model/capacity/registry, or a mismatch between provider-bound prompt and validated prompt. A cryptographic digest alone does not confer validity; dispatch accepts only a gate-issued in-process object and verifies its binding.

No override path, symbolic branch, retry, fallback, dry-run script or direct CLI caller can call image transport with a bare string. An unchanged transport retry can reuse an intact validated assembly if capabilities/policy are still current; any reconstructed prompt, new random preset, appended no-text clause or alternate provider/model requires a fresh complete assembly and validation. No retries are added by SG-01.

## 7. Validation lifecycle and paid-call guarantees

| Stage | Inputs | Output and fail-closed behavior | Cost guarantee |
|---|---|---|---|
| V0 — snapshot/structure | Actual current theme, requested custom style/notes, requested mode; immutable source registry | One AR-01 structure per source; invalid identity/span graph => `INVALID_EVIDENCE`. Custom notes active only when requested style is `custom`, not because resolved style happens to change. | No text/image generation call. Voice transcription, if used to obtain input, precedes this stage. |
| V1 — interpretation/resolution preflight | V0, bounded vocabulary and frozen rules; statically known selected-style/capacity facts and approved route policy | Ledger every negative, including resolved positive legacy exceptions; classify SG-D2; resolve known conflicts/closure and verify early route selection against section 9. Unresolved negatives, unsupported-only requests, fixed incompatible selections, unavailable enforcement route, unpreservable required custom prose or capacity => typed block. | Before reservation where possible and before card-text/enrichment/shadow paid work: zero paid text and zero image calls. |
| V2 — candidate reconciliation | Allowed resolution, actual scene/style/enum, curated fragments, existing generated output | Remove incompatible soft defaults, select only compatible candidates within the approved style pool; preserve required facts. Unrepresentable hard conflict => typed block. | Card text or an existing permitted enrichment/shadow call may already have happened. Zero image dispatches on block. |
| V3 — final assembly validation | Candidate after every deterministic mutation; exact adapter/model capability | `ValidatedAssembly` or typed failure, never `(unsafe_prompt, fallback_flag)`. | Zero image dispatches on block; cannot promise zero preceding paid text calls. |
| V4 — dispatch guard | Gate-issued assembly and exact payload/adapter binding | Forward precisely the validated prompt, or block `STALE_VALIDATION`/`INVALID_ASSEMBLY`. | Zero image dispatches for a rejected guard. |

Entry points MUST not launch text/image work concurrently until V1 completes. A direct `generate_image` invocation still enforces V0–V4; it cannot guarantee the caller has not independently bought text generation beforehand. Known mandatory-fragment capacity failures can be caught early; a later candidate overflow cannot be predicted before all text is known. “Zero-call” claims in tests must specify `card_text`, `enrichment`, optional paid `shadow`, and `image_post` separately.

Snapshots are per attempt. A source/style/mode change creates a new resolution. Profile/More rereads remain as currently contracted. Scheduled retries retain the persisted logical delivery mode/date and existing claim identity; they re-evaluate the actual allowed inputs, never infer authority from the previous output. SG-01 does not add source snapshot persistence, new database columns or migration requirements.

## 8. Frozen policy decision matrix

`+` and `−` below describe effective canonical facts; original evidence is always retained. “Allowed” is interpretation/preflight eligibility with a compatible deterministic candidate and verified capacity. It does not certify arbitrary later enrichment. All blocked rows have zero image-provider calls; V1-blocked rows also have zero paid generation text calls. `H` means the `human/hands/body` derived absence.

### D1-A boundaries, source authority and legacy fences

| Input/source | Required result |
|---|---|
| `No mugs, tables, and windows` | −mug/table/window; no positive promotion; all members keep one negative scope. |
| `No plants, small tables, and windows` | Structural negative continuity across all members; known −table/window retained; unknown `plants` makes the current minimum vocabulary result `BLOCKED: UNRESOLVED_EXCLUSION / unknown_target`. Do not drop `plants` to allow dispatch. |
| `No mugs, blue lanterns, windows`; RU `Без растений, маленьких столов, и окон` | Same continuity; unknown visual head causes unresolved block. Known exclusions remain in evidence. Vocabulary expansion, if separately supported, changes recognition rather than scope. |
| `Avoid people, show a mug`; `No mug and show a table` | Independent positive command resets polarity: −human +mug, or −mug +table. First case renders H. |
| `I do not want to show a mug`; `Do not ever include a table`; `Never show people` | Nested render verb stays negative; no positive fact. |
| Ordinary `No people, a mug please` / `No people, just me and a mug` | −human; detached member remains non-authoritative/unspecified, never +human or +mug. |
| Same text in **active** custom notes | Existing closed custom nominal rule permits +mug, with `CUSTOM_NOMINAL` basis, and −human/H; “me” does not become a new human request. This is not authority for arbitrary custom narrative. |
| `No people, show a mug` in either active source | −human/H and +mug from an independent command. |
| Custom description while requested style is `auto`, `nature`, or another non-custom selection | Notes are inactive; no effective facts or unresolved-user blocks from them. |
| Generated prose, hints, soft avoids or memory containing any of these strings | No user authority, including no authority from a legacy match. Compatibility may discard unsafe optional content; cannot create requests/exclusions. |
| Standalone hard chunk `No people, ocean` | −human/H, +coastal water with `LEGACY_D1_A_OCEAN`; structural coastal member remains NEGATIVE, ledger `resolved_positive_legacy_exception`, no −water from that member. |
| Standalone hard chunk `No people, beach at sunset` | −human/H, +beach with `LEGACY_D1_A_BEACH_SUNSET`, sunset qualifier; same auditable positive-exception disposition, no −beach or unresolved relation from that member. |
| Case/whitespace variants of those exact chunks; complete chunk separated by `. ; ! ? newline but/но` | Permit only existing normalization: trim/collapse whitespace and casefold within the complete hard chunk. Boundary punctuation is outside the chunk. Preserve source offsets. |
| `No people,ocean`, `No people , ocean`, `Please no people, ocean`, `No people, ocean please` | No legacy match: punctuation/wording differs after the approved normalization. Do not expand the two exceptions. |
| `No humans, ocean`; `No mugs, ocean`; `No people, sea/lagoon/rocky coast` | Negative coastal list members; no legacy positive. |
| `No people, ocean, windows`; `No people, ocean and windows` | −human/H, −water with coast cascade, −window; no legacy positive. |
| `No windows, no people, ocean`; `No people, ocean, no windows` | Entire hard chunk is not a legacy chunk: −window, −human/H, −water; repeated negative markers do not reopen the exception. |
| `No people, ocean, show a table` | Soft-boundary independent +table survives, but does not make its preceding sub-scope a standalone legacy chunk; −human/H and −water remain. |
| `No windows; No people, ocean` | Two complete hard chunks: −window, −human/H, legacy +water. |
| `No people, ocean; No ocean` | Preserve legacy +water evidence and independent −water evidence. Coastal exclusion wins in resolution, recorded as conflict; no positive coast rendered. Incompatible explicitly selected coast style blocks. |

### SG-D1, SG-D2, unknowns and coverage

| Input/source | Required result |
|---|---|
| `No mugs on tables`; `No people near windows`; `No beaches near houses` | Recognized visual head plus structural relation => `BLOCKED: UNRESOLVED_EXCLUSION / relational_scope`; no flattened global ban. |
| `Show a mug without a logo` | Eligible mug directive retained, but local exclusion is unresolved; whole image request blocked. `logo` recognition would not fix the unrepresented local scope. |
| `No glargs`; `No mugs, glargs, windows` | Unknown active visual negative remains in coverage ledger => unresolved block, including when no canonical fact exists for it. |
| `No unusually tiny old bright polished wooden tables; show a table` | Long negative target retained; unsupported structural form => unresolved block before canonical set filtering. It cannot become a conflict-free +table request. |
| Many exclusions, including repeats | No SG-01 count cutoff. Preserve all refs. Fit the complete mandatory rendering or block on actual adapter capacity. |
| `No time for my notebook`; `No report about mugs and windows` | Bounded known nonvisual/narrative classification; no literal positive objects or global visual bans. Unknown similar prose is not automatically safe. |
| `Покажи историю про кружки и окна`; `Show a story about mugs and windows` | `unsupported_narrative`, no eligible visual fact. Alone => `BLOCKED: UNSUPPORTED_VISUAL_REQUEST`. |
| `Show a poster featuring mugs and windows` | Eligible artifact poster with +mug/window through its owned nominal dependents; do not reject solely because `featuring` is a relation. |
| `Show a poster with a mug` | Eligible artifact poster +mug; same head/frame rule, no `with` blacklist. |
| `Show mountains at sunrise` | Eligible scene mountain +sunrise qualifier; no artifact noun required. |
| `Покажи историю про кружки и окна; покажи стол` | Mixed: unsupported story retained as classification; only +table has image authority. |
| `Show a story about mugs and windows, show a notebook` | Independent supported command contributes +notebook; story objects cannot leak into scene/positive fragments. |
| `Show a story about mugs and windows and a table` | No independent supported render boundary for table; unsupported narrative owns all members. |
| Plain narrative theme without an explicit render request | Disposition `none`; existing image defaults allowed subject to actual exclusions/style. Do not promote mentioned objects. |

### Conflicts, anatomy and FIX-03A precedence

| Input/context | Required result |
|---|---|
| `No mugs; show a cup` or same conflict split across active theme/custom notes | `BLOCKED: OBJECT_CONFLICT`; aliases resolve to mug, both refs retained. |
| `No people; show hands` / `No people; show a face` | `BLOCKED: OBJECT_CONFLICT` via human cascade; direct `human_presence` contradictions may additionally report `HUMAN_PRESENCE_CONFLICT`. |
| `No people`, compatible scene | H ban, scene none, no positive/conditional anatomy/person-direction fragments; all three canonical absences reach the exact final prompt. |
| `Show hands` against a generated `human_presence='none'` default | Eligible positive request displaces a soft generated absence if the selected style permits; otherwise block. Do not label the default as a user exclusion. |
| `No hands` | Mandatory hands absence; no automatic global human ban and no anatomy fragment requiring visible hands. |
| `Avoid beach`; `Without ocean`; `Без моря`; `Не хочу пляж` | No positive coastal intent. Relevant coastal exclusions and their closure apply. |
| `Море без пляжа`; `Show rocky coast without beach` | +water/rocky, −beach/sandy; allowed approved scene-level composition, not a general local-to-global rewrite. |
| `Ocean view, no sandy beach`; `Ocean view, no rocky coast` | +water, exclude only requested subtype; never invent an alternate beach/rocky preference. |
| `I want a tropical beach`; `Хочу океан и пальмы` | Positive supported coast remains available; compatible tropical/coastal qualifiers retained by supported rendering. Generic anti-cliche beach avoids cannot suppress it. |
| `Show beach; no beach` | Retain competing evidence, exclusion wins; no positive beach rendering. Only a compatible residual/default choice is allowed; an explicitly fixed beach style blocks. |
| Selected `sea_coast_photo` with `No ocean`; selected interior style with explicit coast | `BLOCKED: STYLE_CONFLICT` before paid generation when known; do not silently replace an explicit style. |
| Auto-resolved coastal style with negative-only coastal input | Choose a compatible noncoastal candidate within existing automatic routing; no evidence of positive coast. |
| Explicit coast in Career/Money with a compatible chosen style | Coast outranks sphere workspace/interior and framing defaults. Compatible style identity and lighting remain. |
| Controlled forest/workspace prompt containing generated `Avoid beach` | Remains forest/workspace; generated negative coastal mention cannot trigger coastal photo augmentation. |
| `research`, `seasonal`, `seated`, `берегу себя` | No coastal fact from substrings or Russian verb forms. |

This matrix states approval-derived outcomes and bounded design cases, not an exhaustive natural-language grammar. In particular, generic SG-01 prose must not widen D1-A's two legacy exceptions.

## 9. LLM-origin text, final veto and the remaining product decision

Typed fragments can prove where text came from and whether controlled renderers obey their registered contract. They cannot prove that arbitrary LLM prose avoids every prohibited synonym, implication, quoted instruction, double negation or semantic conflict. An appended exclusion and a lexical scan are insufficient to make that claim.

### 9.1 Enforceability matrix — mandatory means mandatory

The minimum contract is: **if any mandatory restriction lacks enforceable coverage for an untrusted candidate, block with `UNTRUSTED_ENFORCEMENT_UNPROVEN` and zero image dispatches.** A caller may not rescue that failure with another prompt. Missing canonical coverage, a detected contradiction or an unresolved exclusion uses its more specific typed failure. Authority/hardness and strength of enforcement are separate: accepting a bounded standard would accept residual enforcement risk, not turn a mandatory ban into a preference.

In the matrix, **B** means admission only under a **separately defined and explicitly Owner-approved bounded-enforcement standard** for that precise restriction class and route/context. Such a standard must identify vocabulary/grammar coverage, veto/unknown rules, residual false negatives/positives and versioned evidence. B is conditional, not an approval in this document; no such approval is assumed for any row. All applicable rows must pass, including system/style rules. A bounded veto uses generated-source AR-01 evidence and registered vocabulary, never generated user authority or an extra model call.

| Restriction class | Authority and hardness | Available deterministic evidence | Can an LLM-prose candidate be admitted? Bounded-veto limit/risk | Controlled route requirement and mandatory refusal |
|---|---|---|---|---|
| User-origin mandatory exclusions | Active actual user source; hard, with all refs and closure. | Original AR-01 structure, assessment, canonical bans/renderers and controlled positive-key compatibility. Unresolved local/unknown scope is not enforceable. | B only for represented exclusions; a lexical/structural veto can miss synonyms, implications or indirect demands. No admission under the minimum contract. | Without B, fully controlled construction is necessary for success; proposed O-1 may select it early. Unresolved exclusions always block under SG-D1; absent faithful construction/authorized selection, fail closed. |
| Active custom-note exclusions | User authority only while requested style is `custom`; hard, not a style preference. | Same ledger, refs and canonical closure; inactive notes retain evidence without user-ban authority. The remaining custom prose has separate fidelity/trust requirements. | B only; negative-clause extraction does not make the remaining custom description trusted. Residual violations may be hidden in that prose or enrichment. | Without B require a faithful fully controlled route; if required custom prose cannot be preserved, block even when exclusions themselves render correctly. No empty/default custom replacement. |
| Fixed-style prohibitions | Selected registered style/mode contract; hard once applicable. Auto routing may select a compatible style before fixation; an explicit style cannot be silently replaced. | Versioned style identity, exact registered fragments, prohibited/required keys and compatibility rules. | B only for semantic prohibitions; existing scans do not prove that arbitrary prose respects the style's subject/scene contract. | Without B use compatible controlled fragments. Incompatible explicit style or inability to preserve its required behavior blocks with a typed style/enforcement failure. |
| Coastal exclusions | Active user/custom authority and frozen FIX-03A closure; hard. Curated coastal constraints keep their own authority. | Resolved coastal facts, exact source refs, precedence/conflicts, subtype/time projections and neutral coastal registry. Promoted legacy members are positive exceptions, not bans. | B only; existing coastal checks are bounded vetoes, with alias, indirect scene and lighting/shoreline ambiguity risk. They are not general absence proof. | Without B require controlled coastal-compatible construction. SG-D1 local relations block; incompatible fixed coastal selection blocks; never invent a complementary beach. |
| Explicit human exclusions | Active user/custom authority; hard `human` -> `human/hands/body` closure. Explicit hands/body bans have no reverse cascade. | Canonical closure, human enum, registered anatomy/person-direction semantics and canonical absence clauses. | B only; arbitrary prose can imply people/anatomy without recognized terms. A conditional anchor does not certify surrounding text. | Without B require compatible controlled construction respecting the exact exclusion and its closure. Contradictory explicit positives/fixed style block; all derived absences must be rendered, without turning hands/body alone into a human ban. |
| Default scene human absence | Generated/curated scene default is soft **before reconciliation** and may yield to an eligible compatible human request. Once final `human_presence='none'` is selected, its absence contract is mandatory. | Reconciled enum, `SCENE_HUMAN_NONE` cause, one closure owner and exact positive/conditional fragment semantics. | B only after absence becomes mandatory; an enum alone cannot control LLM prose. Indirect figures/anatomy may evade the veto. | Reconcile the default first. For retained none, without B require controlled construction or block. Do not drop a finalized absence solely to admit enrichment; fixed incompatibility blocks. |
| `SYSTEM_NO_TEXT` | System assembly rule; hard for every final image prompt. Canonical clause presence and semantic noncontradiction are distinct obligations. | Exact registered no-text fragment, full system key coverage and controlled fragment semantics. Clause presence is mechanically verifiable; arbitrary prose noncontradiction is not. | B only for semantic noncontradiction; a veto may miss indirect lettering/logo/typography demands. Appending no-text does not establish it. | Without B all untrusted-prose assemblies fail closed. Fully controlled construction can satisfy the prompt contract; O-1 does not waive the rule or guarantee text-free pixels. |
| Other mandatory assembly restrictions | Applicable system/adapter/selected mode/style and eligible visual requirements; hard. Optional decoration/soft avoids stay optional under existing precedence. | Exact serialization/seal, capacity counter, refs, required-fact renderers, registered scene/qualifier/conditional contracts. | LLM text may pass mechanical identity/capacity/coverage checks deterministically. Semantic subject/fidelity/noncontradiction still requires B; metadata or a clean scan alone is insufficient. | Every mechanical rule must pass on either route. For semantic obligations without B require faithful controlled construction; unsupported coverage, missing facts, overflow or unknown capacity blocks. |

### 9.2 Controlled scene path, enrichment path and conditional O-1 routing

The **controlled scene path** is admissible under the minimum contract only when the entire assembly uses exact registered fragments, canonical user projections and validated closed slots. A planner may suggest a registered ID/enum, but allowlist/type validation, compatibility and required-intent checks must establish the resulting selection. Free-form plan setting/mood/subject/lighting, emotional focus and raw custom prose remain untrusted. The present `build_controlled_scene_prompt` name, local join and `scene_planner_local` trace do not establish a fully controlled route. Registered scene/style choices must preserve every eligible effective visual fact, exclusion and applicable style requirement.

The **enrichment path** admits LLM-authored prose only when every applicable mandatory restriction has an approved enforceability standard. Under the minimum fail-closed default, no B approval is assumed and `SYSTEM_NO_TEXT` applies universally: **all assemblies retaining arbitrary LLM enrichment prose are blocked**, even without explicit user exclusions. This is the designed SG-01 enforcement behavior, not current production behavior or permission for blanket enrichment shutdown. Known impossibility is rejected at V1 before buying enrichment/card text. Existing fully controlled paths remain eligible; future early controlled selection must satisfy every conditional O-1 release/routing constraint in section 13. Raw user/custom prose has the same enforcement limitation even when no LLM was called. Stage 1A activates none of these production changes.

**R2-N6 configuration boundary:** in the current interactive/scheduled non-symbolic routing, when `scene_planner_image_prompt_enabled=True`, the scene builder supplies the image prompt and `should_use_llm_image_prompt_for_fallback` returns false: LLM enrichment is already unused, including the ordinary builder fallback. SG-01 must make this scene/template assembly genuinely controlled or refuse unsafe prose, but O-1 does not newly remove enrichment there. When `scene_planner_image_prompt_enabled=False`, `build_enriched_image_prompt` is the image-prompt construction path; `llm_image_prompt_enabled=True` enables its LLM prose, while false yields its local template. The former faces the all-enrichment refusal above under the minimum default, or early controlled construction under approved O-1; the latter still needs removal/typed projection of raw prose to count as controlled. Symbolic mode uses its dedicated builder independently of this scene flag and has the section 9.3 custom/nuance boundary. No configuration value is changed by this document.

**O-1: CONDITIONALLY APPROVED — EARLY CONTROLLED ROUTING (Owner, 2026-11-22).** For an **ALLOWED visual resolution**, future routing may select a faithful controlled route before enrichment and before any safety failure, subject to all eight section 13 conditions. It must preserve eligible user intent, mandatory exclusions, relevant style/mode and required Custom Style semantics and pass the same final Safety Gate. Where faithful construction is impossible, fail closed. Partial B coverage does not admit a candidate; no B standard or residual-risk acceptance has been approved. Stage 1A does not implement this routing permission.

With conditional O-1 and no approved B standards, the universal no-text rule still requires faithful controlled construction or refusal for otherwise untrusted assemblies. This consequence does not authorize blanket enrichment shutdown, silent degradation or activation with material functional/image-quality regressions: separate Owner review is required by section 13. For a future eligible selected controlled route, enrichment is skipped (`E=0`); scene-driven generation already satisfying the controlled contract does not become a newly disabled enrichment path. A complete separately approved set of B standards could preserve enrichment in those exact contexts. No restriction becomes soft.

Product changes/remaining risks: fewer refusals where controlled construction is faithful, reduced scene/style expressiveness and theme nuance, possible refusal of active custom descriptions, and fewer optional paid enrichment calls. Curated semantic annotations can be incomplete; bounded vetoes can overblock safe wording and miss forbidden implications; the image provider can ignore a compliant prompt. Route approval alone accepts no bounded-veto residual risk. Exact class/context standards and risk acceptance remain separate O-1 decisions in section 13.

Confirmed violations on any route raise typed safety failures, including contradictions found by current coastal checks. They cannot become `template_fallback`. Network failure or malformed enrichment JSON can still select the existing template under section 10 only within the already authorized route/enforcement contract and with independent V2–V4 validation. That alternate is not authority to switch enforcement routes. A controlled route selected before enrichment under approved O-1 is not recovery from a veto.

### 9.3 Registered styles and user-authored Custom Style

A registered style has a versioned identity, exact fragment/slot semantics and explicit prohibitions. The selector key `custom` does **not** register or validate the user's Custom Style description. User-authored prose remains authoritative as an active style request but untrusted as prompt content; recognizing some objects/exclusions does not prove preservation of the complete style request. A deterministic route must not replace it with a generic registered style, remove the prose, or retain only recognized facts while claiming to preserve the original request.

For the minimum safety contract, if required active custom prose and mandatory restrictions cannot both be faithfully represented and enforced, **fail closed with `UNTRUSTED_ENFORCEMENT_UNPROVEN`** (or the specific already-known conflict). Raw insertion is not a controlled solution, and no new approved-safe Custom Style subset, whitelist, paraphraser or custom-style renderer is created here. A future subset or accepted bounded interpretation requires separate explicit Owner approval. O-1's routing permission alone supplies neither that approval nor permission to omit a user's required style.

Ordinary Custom Style product impact: arbitrary active descriptions, including descriptions with no explicit negative words, generally cannot pass the minimum contract because universal no-text and other applicable bans must coexist with untrusted style prose. Canonical exclusion support does not restore full description fidelity. Such requests may be refused before paid work; a generic balanced/default treatment is not a faithful success.

Symbolic/custom nuance product impact is separate: `openai_image.py:335–342` currently interpolates both Custom Style prose and an optional nuance even for a registered symbolic style. The former remains a required style request. The latter grants no user-exclusion authority when its custom-note source is inactive, but any prose actually assembled still remains untrusted. Neither the instruction “ornamental color or linework only” nor the word “optional” establishes safe enforcement or authorizes silently dropping user-provided nuance while claiming preservation. Existing registered symbolic contracts can pass without such prose; if a supplied nuance cannot be faithfully rendered under an already approved contract, fail closed. This revision creates no special symbolic/custom subset or automatic omission policy.

The gate adds no LLM repair, classifier, translator or reviewer call. Existing enabled paid shadow/enrichment calls are neither evidence of safety nor exempt from early preflight ordering. Lexical/semantic enrichment review, quality, richer vocabulary and full visual fidelity remain deferred. SG-01 guarantees the specified prompt boundary, not universal understanding or image-content verification.

## 10. Failure, fallback, reservations and scheduling

### Catch ordering and fallback rule

Every catch capable of invoking a builder, resolver, validator or image call MUST handle `VisualSafetyFailure` explicitly before a generic catch. Propagation can pass through a generic catch only if it immediately re-raises that exact failure; it cannot log-and-continue, wrap it in `RuntimeError`, return `None`, or select another prompt.

```python
try:
    candidate = build_candidate(...)
except VisualSafetyFailure:
    raise
except RecoverableBuilderError:
    candidate = build_alternate_candidate(same_resolution, ...)
# Alternate candidate must independently pass V2, V3 and V4.
```

Prefer enumerating recoverable non-safety exceptions at actual fallback sites. A deliberate safety block, invalid evidence, missing coverage, contract violation or unknown active exclusion is never a recoverable builder/provider outage. Generic internal errors must not fabricate a successful empty resolution. Ordinary network/format fallback must preserve the same resolution, active sources, style/mode, enforcement route and mandatory restrictions. It does not reuse a prior `allowed` result for new text.

Required catch changes include the controlled-scene catches in `handlers/generation.py` and `scheduler.py`, enrichment fallback/validation in `services/yandex_gpt.py`, `generate_image`'s provider-error wrapper, the interactive image/text error paths if safety enforcement is called within them, and CLI's gather handler. Best-effort shadow/metadata wrappers may not swallow a safety failure if newly entrusted with a gate call; prefer keeping authoritative validation outside those wrappers. Metadata I/O failure cannot permit a previously blocked dispatch.

| Failure | Alternate prompt allowed? | Required behavior |
|---|---|---|
| Unresolved/unknown/local negative, explicit hard conflict, unsupported-only render request | No automatic alternate | Typed block; correct input/style or bounded implementation support is needed. |
| Safety veto on deterministic, LLM or raw-override candidate | No automatic alternate, including `template_fallback` | Stop this attempt; preserve safety reason. |
| Enrichment network error / malformed JSON under existing behavior | Existing alternate may be constructed | Same complete restrictions; independently validate the alternate; its failure is typed and terminal for this attempt. |
| Scene builder's recognized recoverable non-safety failure | Only an independently conforming existing alternate | Never catch a safety exception as that failure. |
| Image HTTP/network/timeout failure after allowed dispatch | No less-restricted prompt retry | Preserve current retry policy; any changed assembly/adapter requires full revalidation. |

### N-2 integration requirements — custom-photo fallback remains deferred

Confirmed report section H.2 identifies a reachable existing custom-photo fallback/preset-conflict path ending in generic image-generation error recovery. The existing diagnostic is `tests/test_generation_reservation_handler.py::test_cp05_n2_diagnostic_custom_photo_failure_is_reachable_and_isolated` (the reported region is lines 217–256). It covers active custom notes `No mugs`, `No windows`, `No notebook` with enrichment both disabled/enabled, uses real local prompt selection, asserts no provider HTTP, no photo, style-choice recovery and released reservation. This is evidence of existing fail-closed behavior, not an N-2 fix.

SG-01 establishes only these requirements on any later N-2 custom-photo fallback:

1. Preserve the authoritative AR-01 `VisualIntent`, represented here by the same immutable interpretation/resolution, including active source identities, all constraints and provenance. A fallback cannot replace it with an empty/default interpretation or reinterpret custom notes under a different authority rule.
2. A `BLOCKED` request, or an `UNSUPPORTED`-only request, cannot become an unvalidated generation through fallback. An eligible mixed request still carries its unsupported classifications and only its separately eligible directives; fallback cannot promote the rejected content.
3. Preserve fail-closed behavior for custom-style preset conflicts. A preset conflict cannot be relabeled as an enrichment outage or relaxed by dropping the custom exclusions.
4. Every legitimate alternate must independently satisfy final validation and provider-dispatch protection under the same complete safety contract; there is no direct raw-prompt escape from the custom-photo path.

No N-2 fallback-selection algorithm, new custom-photo recovery flow or implementation is designed/authorized here. **N-2 is a separate deferred task that must be completed before production deployment**, even if SG-01 later receives design/implementation acceptance. Residual risk remains in this reachable existing path until that task is completed; SG-01 cannot claim to have repaired it. Safety regression requirements below guard against weakening its current failure behavior while N-2 is pending.

### Interactive generation, Profile and More

Expand `_generation_preflight_error` into a typed V1 result shared with `_run_generation`, rather than comparing localized exception strings. `_start_generation_after_preflight` can render a preflight failure without starting `_run_generation`. Direct/repeated `_run_generation` calls MUST repeat or verify the snapshot preflight before reservation; earlier UI checks alone are insufficient. Resolve the actual reread Profile inputs, not stale FSM theme data. Do not activate Profile textual avoids as visual bans.

For V1 failure: no daily reservation, no card-text/enrichment/image calls. Keep useful theme/custom notes in the existing correction flow, set the appropriate choosing-style/input state, and show a fixed localized message. Suggested public keys: `visual_exclusion_unresolved`, `visual_request_unsupported`, `visual_constraints_conflict`, `visual_prompt_cannot_be_validated`, `visual_prompt_too_long`. Messages explain that the scene needs clarification or compatible input; they do not invite an automatic retry of identical deterministic failure. Do not reveal internal evidence or provider output in UI.

For a V2–V4 failure after reservation: stop image work, return no successful image/card, write no success history/counters, and let the existing outer `finally` release `release_generation_usage(uid, reservation_day)` if `delivered` is false. Release exactly once using the captured UTC reservation day, including across midnight and when the UI language has changed. Do not release if Telegram has already accepted the delivered card. Daily limit disabled/unlimited paths perform no release for a reservation that was never made.

A failure while sending a localized error must not skip the outer cleanup. Preserve the existing stale-language guard so an old attempt cannot overwrite a new FSM flow; cleanup is still mandatory. If a release database write fails, surface/log a separate operational failure without retrying paid generation or changing the safety reason. Exactly-once successful persistence cannot be promised during a database outage; SG-01 must not create a second release loop that can decrement someone else's usage.

### Scheduled delivery

Keep `(subscription_id, delivery_date)`, the persisted `visual_mode`, attempt fencing, lease, catch-up window and current retry limits/backoff. `scheduler._deliver_subscription` currently supplies no user theme or custom notes: do not manufacture authority from `focus_text`, generated affirmations or historic images. Run the actual scheduled V1 before paid card/shadow/enrichment work. It may happen after claiming the delivery, because the ledger/mode is needed; that is not paid generation.

Handle `VisualSafetyFailure` explicitly in `_process_due_delivery` and include it in permanent classification in `_release_failed_attempt`. Call existing `mark_subscription_delivery_failed(delivery_id, attempts, safe_reason, retryable=False, now=clock())`; this records `abandoned` through the current schema. Safe reason contains stage and stable code only. A deterministic block must not spend three image attempts, set success metadata, advance sent history, or trigger the enrichment fallback.

Preserve retryability for image transport timeouts, transient provider/Telegram errors and other existing retryable failures. Preserve permanent treatment of `ProviderOutputValidationError` and Telegram forbidden. Do not catch `CancelledError` as a safety verdict or change the attempt-timeout classification. Preserve `_STAGE_POST_SEND` handling: a message already accepted by Telegram must not be marked failed due to later bookkeeping.

If terminal-state persistence fails, the existing claim can expire and be reclaimed. Log that limitation honestly. On another attempt, the same safety checks run before paid work; no bypass or forced dispatch is allowed. SG-01 does not promise exactly-once processing under a ledger write outage, add a new durable block table, reset a subscription, or automatically reactivate an abandoned logical delivery. Future dates retain the current scheduling policy; a deterministic block terminates this logical delivery, not the user's entire subscription.

Scheduled safety handling uses safe logs and the existing terminal ledger state. Do not introduce a new proactive Telegram error-notification behavior without product approval; no such message is necessary to implement permanent failure classification.

### CLI and direct image entry

After optional STT has produced the actual `user_text`, run V1 before constructing/starting the `generate_affirmations` or image tasks in `async_main`. An early block exits with proposed stable status **2** and code-only diagnostic on stderr, with no paid generation calls and no success JSON/image output. STT cost, if any, is outside the zero-generation-call promise.

A later safety failure exits with status 2 after cancelling/awaiting any still-running sibling task; cancellation cannot undo already completed text generation or an already dispatched request. Do not leave a background paid task running after exit. No fallback is allowed. Ordinary transport failures retain a distinct nonzero status under the existing CLI contract.

`generate_image` validates direct callers even when the interactive/scheduled/CLI preflight was skipped. Run final validation outside the HTTP `try` where feasible; add `except VisualSafetyFailure: raise` before any catch that could otherwise wrap it. Build no API session/post for a blocked assembly. Direct override strings are untrusted; `template`, `template_fallback`, `llm` and `scene_planner_local` trace labels do not alter enforcement.

## 11. Deterministic acceptance specification — tests not implemented in D0

Oracles are hand-authored expected spans, facts, classifications, reasons and call counts. Do not obtain expected polarity from the old parsers, expected safety from the prompt under test, or success by replacing the resolver/validator with a stub. Tests exercise real interpretation, resolution, builders and final serialization; replace provider transport/configuration, clocks, Telegram and persistence where appropriate. All providers are offline fakes that fail on unexpected calls. No paid/live LLM/image calls or production database access.

**R2-N7 deliberate test migration, only during authorized integration:** review every changed expectation in the structural and semantic Package A oracles, not only lost exclusions. The migration set includes (1) positive/nominal frame and attachment characterization in `tests/test_directive_segments_package_a.py:39–48`, notably `Море без пляжа`, plus corresponding opaque substitutions; retain original structural polarity/IDs/spans and add/review frame/attachment expectations without reopening D1-A; (2) semantic eligibility/basis and governed qualifiers for poster-with/featuring and mountains-at-sunrise, replacing any blanket positive-relation rejection only for the supported visual frames; (3) unknown/long negative characterization, now unresolved blocks rather than allowed lost exclusions; (4) conflict expectations, now typed result records instead of generic `ValueError`; (5) legacy provenance, now including the positive-exception ledger oracle with all closed fences unchanged; and (6) `tests/test_visual_intent_package_a.py::test_package_a_has_no_production_imports_or_provider_dependencies` (around line 308), replacing no-production-import assumptions with approved single-authority integration and neutral dependency boundaries. Retain story/report and owned-sibling rejection, independent-command positives, vocabulary independence and source authority as regression oracles. Each changed fixture needs a deliberate hand-authored policy rationale and independent review; do not mass-regenerate expectations from the implementation. Existing and new entry-point/assembly tests must distinguish route/configuration cases below. No code or test is edited or run in D0-R2.

Use pytest's OS temporary directory; if explicit basetemp is needed, derive a unique absolute path outside the repository from the OS temp root. Concurrent runs need distinct paths. Never create `.pytest_tmp_*` in the repository or delete test/audit artifacts without Owner approval. This document authorizes no test run.

Counters: `T` = card-text generation; `E` = existing enrichment call; `S` = optional paid shadow calls; `I` = `/images/generations` posts. For a V1 block, require `T=E=S=I=0`. For a late block, assert the expected already-purchased text counts explicitly and always `I=0`. For an allowed fixture with no unrelated retries, require `I=1` and compare the captured actual payload prompt to the gate-issued exact prompt.

### A. Structural parser suite

| ID | Fixture and independent oracle |
|---|---|
| STR-01 | Existing D1-A lists in section 8, including unknown noun substitutions, RU conjunctions, reordering and modifier insertion: exact original member offsets, common negative scope, no vocabulary-sensitive boundaries. |
| STR-02 | `No mug and show a table`, comma/semicolon/newline/contrast boundaries, optional supported polite prefix: exact independent positive directive; nested `I do not want to show a mug` remains negative. |
| STR-03 | The two legacy strings: structural coastal member is still negative. Hard chunk vs soft sub-scope evidence remains distinct; no structural legacy override. |
| STR-04 | `Show a poster featuring mugs and windows`, `Show a poster with a mug`, `Show mountains at sunrise`, `Покажи историю про кружки и окна`: head, complement ownership, qualifier and relation spans; opaque noun substitutions leave structure unchanged. Structural tests do not classify a poster/story as visual/nonvisual. |
| STR-05 | `No mugs on tables`, `No people near windows`, `Show a mug without a logo`: relation evidence identifies its attachment and original negative scope without globalizing it. Compare `Море без пляжа` and opaque nominal substitutions: structure is unchanged; only downstream semantics can authorize the coastal scene restriction. |
| STR-06 | Long and unknown negative members, malformed/unsupported relations and detached custom forms retain spans/polarity/uncertainty. Frozen records reject mutation; invalid spans, duplicate IDs and cyclic governing links are rejected. |

### B. Visual interpretation and resolution suite

| ID | Fixture | Required oracle |
|---|---|---|
| VIS-01 | All D1-A rows in section 8 in ordinary text and active custom notes | Exact canonical facts, basis, refs, source authority and negative coverage; known members never become positive due to an unknown sibling. |
| VIS-02 | Exactly both legacy chunks, case/whitespace variants and hard-boundary neighbors; independent same-key exclusion | Classify the complete chunk before SG-D1 derivation; only the designated coastal member gets its permitted positive basis (plus approved sunset qualifier). Keep original NEGATIVE structure/ref/span/source and exactly one `resolved_positive_legacy_exception` assessment linked to that positive fact. No −water/−beach, ban or unresolved record from the promoted member; −human/H remains. An independent same-key negative keeps its own assessment and normal precedence/conflict. Near misses never get this disposition. |
| VIS-03 | Legacy extensions/repeated markers, punctuation near misses, synonyms, soft independent command | No exception; negative coastal member retained; independent +table remains separate. |
| VIS-04 | Each source kind active/inactive; custom notes under `custom` vs `auto`; forged generated `user_requests` | Only actual active user/custom sources have authority; no generated legacy promotion; mutable plan arrays cannot add a user fact. |
| VIS-05 | SG-D1 relational examples and unknown-head relations | `UNRESOLVED_EXCLUSION` with exact detail/ref/target span; no global canonical ban invented. |
| VIS-06 | `No time for my notebook`, narrative negative; nearby ambiguous forms | Known nonvisual classification has no object bans; uncertain possibly visual negative blocks instead of disappearing. |
| VIS-07 | SG-D2 RU/EN story-only, poster featuring/with, mountains at sunrise | Story-only unsupported, poster +dependents eligible, mountain scene eligible; no artifact requirement for scenes and no preposition blacklist. |
| VIS-08 | Mixed story plus independent table/notebook vs narrative-owned table sibling | Only independent eligible facts survive; unsupported provenance remains; mixed plus any unresolved negative still blocks. |
| VIS-09 | Unknown `No glargs` with zero recognitions; unknown list member | Coverage ledger contains the negative; unresolved detail `unknown_target`, never allowed-empty. |
| VIS-10 | Six/seven-word negative table forms plus `show a table` | Supported six-word form produces conflict; unsupported longer form blocks unresolved, retaining full span. No dispatch can occur for either. |
| VIS-11 | Synonym/cross-source object conflicts; human vs hands/body/face | Conflict refs identify both source facts and derivation. No second human closure definition. |
| VIS-12 | All coastal precedence rows, legacy plus independent ocean ban, explicit vs auto style | Exclusions win where compatible; no complementary beach invention; fixed incompatibility blocks; source-scoped time qualifiers survive. |
| VIS-13 | One ban, many repeated bans, many distinct evidence refs | No arbitrary count threshold; provenance preserved through canonical deduplication. |
| VIS-14 | Two sources each with directive 0/scope 0; duplicate source ID; corrupted fact `source_kind`/`scope_id` | Composite refs distinguish both sources. Duplicate source identity or derivable-field mismatch is `INVALID_EVIDENCE`; no cross-source cache collision. |
| VIS-15 | Several recognitions/members in one scope; both legacy chunks and near misses | Instrument legacy-basis evaluation: once per interpreted scope, reused for its facts/qualifiers from full original chunk. No per-member normalization or legacy-policy change. |
| VIS-16 | Unsupported classifications, unresolved assessments, zero-recognition negatives and attempted mismatched serialized views | Views derive exclusively from their authoritative owner with exact ref/head/target/detail; no separately mutable duplicates. A mismatched serialized view is rejected, never reconciled by a consumer. |

### C. Assembly and final-validator suite

| ID | Fixture | Required oracle |
|---|---|---|
| ASM-01 | Curated preset/style/composition/color or emotional-focus fragment demands a forbidden object | Reconcile optional defaults before validation or block; no positive demand remains in an allowed prompt. Required user facts cannot be removed to make it pass. |
| ASM-02 | `No people` / scene none with existing conditional anatomy anchor, person-direction or generated hand hints | Exact H coverage; incompatible anatomy/directions absent. A registered conditional anchor is never counted as +human. Unregistered lookalike stays untrusted. |
| ASM-03 | Explicit hands with soft scene-none default; fixed incompatible style; `No hands` | Default may be reconciled only in a compatible pool; fixed conflict blocks; no reverse human cascade or visible-hands anatomy instruction under hands ban. |
| ASM-04 | Mandatory clause omitted, altered to vague prose, or derived hand/body ban missing | `MISSING_MANDATORY_EXCLUSION`; typed block. Metadata claims cannot substitute for actual registered text. |
| ASM-05 | Unknown exclusion before any clipping; mandatory prompt at fake adapter capacity and one counter unit above | Original ledger retained. At exact capacity allowed if all rules pass; above capacity `FINAL_PROMPT_OVER_CAPACITY`. Use real unit counter, including Unicode codepoints/UTF-8/token fixtures as applicable. No arbitrary exclusion-count oracle. |
| ASM-06 | Missing/unverified adapter capability | `CAPACITY_UNVERIFIED`, never assume 1200/900 is the provider bound. |
| ASM-07 | Final no-text insertion/photo preset/coastal lighting/symbolic reconstruction | All changes occur before V3; captured final string includes them and is exactly validated. Append/replace/reorder any fragment afterwards => stale/invalid block. |
| ASM-08 | Same prompt characters with changed source activity/provenance/style/model/capacity/registry or enforcement route/rule/standard | Prior seal rejected even if a superficial set comparison passes. Route change changes `resolution_digest` and `assembly_digest`; final route must equal the resolution-owned record. Forged or post-enrichment route selection is rejected. |
| ASM-09 | Raw override falsely labelled `template` or LLM plan field falsely labelled `user_projection` | No trust from label/normalization; unverifiable provenance rejected or `UNTRUSTED_ENFORCEMENT_UNPROVEN`. |
| ASM-10 | Mixed unsupported story plus eligible table | No story-owned mug/window mention in positive fragments; table requirement rendered. |
| ASM-11 | Mandatory bans with arbitrary untrusted text; detected forbidden synonym in supported vocabulary | Bounded veto catches known violation; unsupported enforcement blocks. A negative keyword-only scan is never used as proof of general semantic safety. |
| ASM-12 | Attempted mutation of fragment text, provenance container, final assembly or validation result | Immutability holds transitively. No nested mutable payload can change prompt after validation. |
| ASM-13 | Raw theme through scene-idea/emotional-focus interpolations, custom prose, symbolic nuance and arbitrary plan/slot text | A `fully_controlled` assembly contains only registered/canonical content and validated closed slots. Raw/cleaned/quoted prose cannot acquire trust from `template`/`controlled` labels, empty key sets or object scans. Preserve required intent/style through typed rendering or block. |
| ASM-14 | Every section 9.1 class separately and in combination, no B approval vs a fixture with explicit approved policy/standard | No mandatory-to-soft downgrade. Without complete approved coverage, untrusted prose blocks; `SYSTEM_NO_TEXT` alone suffices. With a simulated approved B standard, veto/unknown behavior and residual-risk boundary match that exact standard; another class/context cannot reuse it. This fixture does not approve a real standard. |
| ASM-15 | Ordinary active Custom Style, bans-only recognition plus unrepresented description, registered symbolic style with supplied nuance | Keep all required style intent or fail closed. No generic style replacement, silent prose/nuance omission or invented custom subset; inactive custom notes cannot add user bans merely because symbolic code interpolates them. |

### D. Provider-boundary and entry-point integration suite

| ID | Exercise through real production path | Required assertions |
|---|---|---|
| INT-01 | Interactive `_start_generation_after_preflight` and direct `_run_generation`, each V1-blocked fixture | `T=E=S=I=0`, reservation calls 0, localized fixed error, no success history; direct/repeated invocation cannot skip preflight. |
| INT-02 | Active custom conflict/unknown negative, inactive custom same text; Profile/More reread | Active blocks early; inactive does not add a ban. Current saved Profile semantics remain; text-only avoids never become visual bans. |
| INT-03 | Deterministic template, controlled scene, illustration/photo/symbolic and direct override variants | V2/V3/V4 blocks all have `I=0`. An allowed controlled fixture has `I=1`; HTTP `json['prompt']` equals validated prompt and metadata final prompt, with matching actual scene identity. |
| INT-04 | Inject typed safety failure at reconciliation, controlled build, enrichment validation, final assembly and dispatch guard | Failure retains type/code through each catch; enrichment/template/fallback builders are not called after the safety failure. Generic handler cannot set `prompt_final=None` and continue. |
| INT-05 | Existing enrichment HTTP outage / invalid JSON under an explicitly approved test route/standard; alternate template passes, then fails full safety validation | Valid alternate independently reaches one image call; unsafe alternate yields `I=0`. Both retain the same resolution, route and mandatory constraints; a non-safety alternate cannot authorize a route switch. No extra text/reviewer call. Without such route coverage, V1 blocks before E. |
| INT-06 | Scene flag on/off, LLM flag on/off, LLM-origin/raw override and trace spoof variants; O-1 pending vs explicitly approved fixture | Scene flag on has `E=0` already, but raw plan/focus still must pass controlled-contract checks. Scene flag off plus LLM on blocks at V1 under minimum no-B policy, even with only `SYSTEM_NO_TEXT`: `T=E=S=I=0`. With approved O-1, a faithful early controlled candidate has `E=0`, full V2–V4 and `I=1`; impossible custom/style fidelity blocks. A complete explicitly approved B fixture preserves its LLM route. LLM off still cannot admit raw template prose as controlled. No reroute after a veto; symbolic cases follow their dedicated builder. |
| INT-07 | Late interactive failure after reservation and mocked `T=1` | `I=0`; one release with captured day, delivered false, usage restored, no success metadata/history. Repeat across UTC midnight while a separate new-day reservation exists; preserve new-day usage. |
| INT-08 | Error-notification send raises, stale UI language, disabled limit, successful delivered card | Cleanup still runs once when needed; no release for absent reservation; successful delivery not released; stale flow not overwritten. Separate DB-release outage reported without paid retry. |
| INT-09 | Scheduled V1 safety block after claim; repeated scheduler tick | `T=E=S=I=0`; existing attempt-fenced write `retryable=False`, ledger `abandoned`; same logical delivery not retried after normal successful persistence. No send/history success. |
| INT-10 | Scheduled late safety failure, claim/terminal-write outage, process restart | `I=0` for blocked candidate. After failed terminal write and lease expiry, preflight still blocks before paid work when the failure is preflight-deterministic. Do not claim exactly-once terminal persistence during DB outage. |
| INT-11 | Scheduled timeout/transient provider failure vs Telegram forbidden/ProviderOutputValidationError | Existing retryable failures still retry with persisted delivery date/mode, backoff/lease/max attempts; existing permanent ones remain terminal. No weaker prompt on retries; changed prompt must revalidate. Post-send bookkeeping cannot mark a sent card failed. |
| INT-12 | CLI story-only/unknown/local exclusion after mock STT; direct image-only invocation | Early CLI: status 2, no generated success output, `T=E=S=I=0`; direct image guard: `I=0`. Later CLI failure cancels/awaits sibling; assert realistic already-started T count, no false zero-text claim. |
| INT-13 | Migration proof with sentinel old parsers | Make legacy `visual_constraints._fragments` and `coastal_intent._scoped_fragments` raise if called (or assert removed), then run actual allowed and blocked interactive, scheduled, CLI, builder, enrichment-check and `generate_image` paths. All use AR-01 results without sentinel calls. Instrument AR-01 so downstream consumers receive the same segmentation/resolution identity, not independently reconstructed polarity. |
| INT-14 | Static production call/import inventory plus runtime sentinel; neutral registry imports/re-exports | Reject reachable legacy polarity scanners or regex reimplementations in consumers. Apply the deliberate Package A test migration above only during approved integration. Gate imports neither builders nor `coastal_intent`/`ritual_config`; coastal constants, `normalize_style_key` and fixed-style incompatibility sets resolve from the neutral registry with no reverse imports/competing copies. No test writes in D0. |
| INT-15 | Transport retry with unchanged seal, changed prompt/model, or hand-constructed validation wrapper | Intact allowed object can be reused under existing retry policy; stale/fabricated objects rejected before a post. Every successful payload has an attributable gate-issued assembly. |
| INT-16 | N-2 diagnostic custom-photo fixtures (`No mugs/windows/notebook`), enrichment on/off; attempted alternate after a custom preset conflict | Preserve current fail-closed result, no image HTTP, no photo/success history and reservation cleanup. Any later legitimate alternate retains the exact authoritative interpretation/resolution and all custom constraints and passes V2–V4 independently. A safety/unsupported-only failure cannot invoke it. These are integration requirements, not an N-2 recovery redesign; previously completed card text is not falsely counted as zero. |

The migration proof covers metadata/compatibility adapters as well as the main dispatch path. Runtime sentinels complement, rather than replace, review of reachable consumers. Static searches alone cannot establish that a handwritten equivalent parser was not introduced.

## 12. Audit finding response and closure matrix

“Addressed in design” means this specification defines a reviewable correction. It is not independent audit acceptance, implementation completion or a claim that old tests now pass. DR-01–DR-10 responses follow the Owner's supplied correction groups; DR-11/DR-12 and N-2 additionally use the confirmed report extracts supplied in the follow-up.

| Finding | D0 response | Design status / independent review check |
|---|---|---|
| DR-01 | Sections 4–7: immutable evidence, complete negative ledger, resolved facts, typed result and gate-issued final assembly. | Addressed in design; inspect complete evidence-to-dispatch contract. |
| DR-02 | Sections 3 and 4.1: structural parser exposes grammar/attachments; visual-head eligibility is downstream; no second polarity parser. | Addressed in design; test vocabulary-independent structure and semantic heads separately. |
| DR-03 | Sections 3, 8 and VIS-05–08: SG-D1 relational negatives block; SG-D2 narratives cannot promote nouns; poster-with/featuring and artifact-free scenes supported. | Addressed in design; inspect frame ownership and conservative ambiguous handling. |
| DR-04 | Sections 5 and 10: dedicated immutable failure data/exception; typed catches before generic catches throughout callers. | Addressed in design; integration must prove no swallowed safety error. |
| DR-05 | Sections 7 and 10: interactive release, terminal scheduled safety classification, CLI sibling cleanup, retry preservation and honest paid-call boundary. | Addressed in design; ledger/release outage limits are explicit. |
| DR-06 | Sections 6 and 9: exact final prompt validation, provenance, opaque dispatch contract and limited LLM claims. | Enforcement boundary specified; **O-1 routing conditionally approved in section 13**. No B standard or arbitrary LLM safety proof approved. |
| DR-07 | Section 2: actual consumer inventory, AR-01 migration and compatibility plan; INT-13/14 prove old scanners have no production authority. | Addressed in design; approved migration is not reopened. |
| DR-08 | Sections 4.1–4.3 and 6: reuse source/scope/directive identity, immutable provenance, generated authority denied and derived-data ownership. | Addressed in design under the supplied evidence-contract correction group. |
| DR-09 | Sections 4.2, 5.1 and 8: unresolved negative vs unsupported request; explicit object/coastal/style conflict records and reason codes. | Addressed in design under the supplied evidence-contract correction group. |
| DR-10 | Sections 4.2, 5.2 and 11: unknown/long negatives cannot disappear; actual downstream capacity rather than arbitrary count; closed D1-A exceptions. | Addressed under the same supplied group; concrete adapter capacity evidence is an implementation prerequisite. |
| DR-11 — NOTE | Section 4.1 formally namespaces directive/scope IDs by source, binds cross-snapshot refs, and retains/checks derivable `source_kind` for evidence locality; VIS-14. | Addressed in design; confirmed finding, no identity renumbering or field removal required. |
| DR-12 — NOTE | Section 4.1 computes the closed legacy basis once per semantic scope from the complete original chunk and reuses it; VIS-15. | Addressed in design as a nonblocking improvement; verified D1-A behavior unchanged. |

The confirmed N-2/H.2 finding remains deferred, with its four SG-01 integration requirements in section 10 and INT-16. It is not an unresolved audit-identification gap. No unsupplied individual severity is guessed. Independent Claude Code review remains read-only; Owner acceptance is required before any implementation phase.

### SG-01-DESIGN-REVIEW-R2 targeted disposition

The following are confirmed findings supplied by the Owner, including section C's exact nonblocking notes. “Addressed in design” closes the specification gap for targeted verification; it does not claim the independent reviewer has accepted this revision.

| Finding | Correction and verification target | Disposition |
|---|---|---|
| R2-01 | Sections 3, 4.2, 8 and VIS-02: closed legacy classification precedes effective SG-D1 derivation; explicit auditable positive-exception assessment preserves NEGATIVE structure without a same-member ban. | Addressed in design; D1-A unchanged. |
| R2-02 | Sections 9.1–9.2 and 13: eight-class enforceability matrix, hard authority vs bounded evidence, default all-enrichment impact, controlled/enrichment distinction and early routing. | Addressed in design; O-1 routing conditionally approved, no B standards approved. |
| R2-03 | Section 9.3 and ASM-15: registered styles differ from user prose; ordinary Custom Style and symbolic nuance retain fidelity requirements or fail closed. | Addressed in design; no new custom subset/omission policy. |
| R2-N1 | Section 4.2: `classifications` is the sole authority; `unsupported_requests` derives ref/head/kind exclusively from it. VIS-16 checks equality. | Addressed in design; no duplicate writable request record. |
| R2-N2 | Section 4.2: `negatives` owns unresolved detail/ref/target; `unresolved_negatives` is an immutable derived view. VIS-16 checks equality. | Addressed in design; consumers cannot reconcile competing details. |
| R2-N3 | Sections 2 and 6 inventory both scene-idea and emotional-focus raw-prose sites and the handler source; fully controlled assembly excludes unvalidated raw prose. ASM-13. | Addressed in design; current templates are not certified by name. |
| R2-N4 | Section 2: neutral ownership includes `COASTAL_STYLES`, `COASTAL_SCENES`, pure `normalize_style_key` and fixed-style incompatibility sets, with full one-way dependency boundary. INT-14. | Addressed in design; no gate -> coastal consumer -> gate cycle. |
| R2-N5 | Sections 4.3 and 6: resolution owns the early route; `FinalAssembly` explicitly retains it; both `resolution_digest` and `assembly_digest` bind its rule/policy/standards. ASM-08. | Addressed in design; no inconsistent route reuse. |
| R2-N6 | Section 9.2: scene flag enabled already suppresses enrichment; disabled uses the enriched/template path depending on the LLM flag; symbolic routing is separate. INT-06. | Addressed in design; configuration is unchanged. |
| R2-N7 | Section 11: explicit structural positive/nominal frame fixtures, semantic-frame/qualifier cases, lost negatives, typed conflicts, legacy ledger and isolation/dependency migration; deliberate review of each changed oracle. | Addressed in design; tests remain untouched. |

## 13. Owner decision register

**O-1: CONDITIONALLY APPROVED — EARLY CONTROLLED ROUTING**  
Owner decision date: **2026-11-22**.

Conditions:

1. Routing is selected only for an ALLOWED visual resolution.
2. Selection happens before enrichment and before any safety failure.
3. The controlled route must faithfully preserve eligible user intent, mandatory exclusions, relevant style/mode and required Custom Style semantics.
4. The route must pass the same final Safety Gate.
5. A BLOCKED or UNSUPPORTED request cannot trigger reconstruction or fallback.
6. No blanket LLM enrichment shutdown or silent product degradation is approved.
7. No new bounded-enforcement standard, risk acceptance, custom subset or omission policy is approved.
8. Any material functional or image-quality regression requires separate Owner review before activation.

These are release and routing constraints, not permission to bypass fail-closed safety behavior. The separate implementation authorization covers **Stage 1A only**. No deterministic route is activated or selected in this stage. No B standard, residual-risk acceptance, Custom Style subset, omission policy or production configuration change follows from O-1.

Routing approval does not automatically approve bounded-risk standards, a hard-to-soft reclassification, a new Custom Style subset, custom prose omission/paraphrasing or symbolic nuance omission. Any future such product policy needs a separate explicit proposal/Owner decision; none is needed to retain the minimum fail-closed behavior. The existing soft default before human-absence reconciliation is already defined in section 4.3, not a new softness decision.

AR-01 migration, D1-A, SG-D1, SG-D2, fail-closed unknowns and the two legacy exceptions are already settled and are not decision-register options. Verifying concrete adapter capacities and completing the separate N-2 task before production are engineering/release prerequisites, not requests to reopen product policy. No decision here grants deployment, Stage 1B or full Package B+C implementation approval.

## 14. Residual risks, deferred work and review readiness

- Bounded RU/EN vocabulary and grammar can overblock legitimate requests and miss unsupported metaphors, quotations, morphology, negation or synonyms. Structural/semantic separation prevents inconsistent authority; it does not supply general language understanding.
- Canonical object aliases can be coarse (`face` maps to `body`, cups to mugs). The frozen/established mappings are not silently broadened. Local relational restrictions remain blocked in the minimum implementation until a separately approved representation can preserve their scope.
- Curated fragment semantics can be wrong or incomplete. Exact text/version binding, human review and independent hand-authored oracles are required; a hash proves identity, not meaning. Any new registry content requires renewed final assembly validation.
- The image provider can ignore a compliant prompt. SG-01 validates dispatch intent; pixel-level compliance/vision review and extra paid model calls are outside scope.
- Accepted LLM enrichment validation remains **FIX-03B-2B-2**. SG-01 adds only mandatory enforcement and a final veto/refusal boundary; no broad enrichment-quality, semantic-fidelity or repair subsystem is authorized. Sections 9 and 13 explicitly record the all-untrusted-enrichment refusal under the minimum no-B contract, conditional O-1 controlled selection, configuration-dependent impact and custom-style refusals. No bounded-risk acceptance or blanket enrichment shutdown is implied.
- **N-2 custom-photo fallback is confirmed and deferred, and must be completed before production deployment.** Its reachable current preset-conflict path ends in generic image-error recovery. Preserve current fail-closed conflicts and all four section 10 integration requirements; no repair or recovery redesign is claimed in D0.
- Concrete prompt capacities/counters must be verified for the selected adapter/model before enabling dispatch. Unknown capacity is a typed block, not permission to truncate restrictions.
- Database write outages can delay quota cleanup or terminal delivery persistence. Existing fencing, lease and captured-day semantics remain; SG-01 introduces neither database recovery automation nor exactly-once delivery guarantees.
- Richer taxonomy, natural/geological diversity, memory/diversity changes, subscription product changes, Profile global visual avoids, unrelated audit findings and Package B+C implementation are outside D0.

**D0-R2 targeted verification and conditional O-1 acceptance are recorded as Owner-supplied evidence in the authorization update.** Stage 1A implementation remains subject to independent Claude Code read-only audit and Owner review/acceptance. Broader DR-01–DR-12 and N-2 requirements remain in force. No Stage 1B, Package B+C production integration or deployment begins under this authorization. N-2 completion remains a separate prerequisite before production deployment.
