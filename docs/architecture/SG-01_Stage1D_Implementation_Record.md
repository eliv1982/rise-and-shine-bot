# SG-01 Stage 1D — Narrow Offline Controlled Renderer

Date: **2026-11-24**. Author/developer implementation and semantic review: Codex.
Original Stage 1D Claude Code audit: **ACCEPT WITH MINOR NOTES** (Owner-supplied:
0 BLOCKER, 0 MAJOR, 1 MINOR, 6 NOTE). Independent CP-01 verification: **PENDING**.
Final Stage 1D Owner acceptance: **PENDING**.
Production authorization: **NOT GRANTED**.

The Owner supplies `main`, HEAD `336b33d`, Actions tests #47 PASS, 5,911 offline
tests, accepted Stages 1A–1C, and the approved Stage 1D scope. These are
Owner-supplied facts, not developer Git verification. The supplied task supersedes
the unsaved scope proposal; no separate proposal was sought or created. Earlier
authorization/status statements in the architecture/implementation records are
historical; the supplied task controls this stage.

## Decisions and exact scope

| Decision | Implementation |
|---|---|
| D-1 | Narrow offline renderer with limited interface/issuance hardening. |
| D-2 | Exact primitive source fields and immutable selectors; interpretation/resolution constructed internally by existing owners. |
| D-3 | Exactly `living_nature_photo` / `photo`; even the existing `sunny_nature_photo` alias is rejected. |
| D-4 | Closed reusable recombination of reviewed components, with all 24 nominal combinations exercised. |
| D-5 | Explicit immutable synthetic policy/capabilities, separate from content. No default environment or inferred provider approval. |
| D-6 | Hardening applies to the new renderer and its issuance boundary; deferred older contracts are unchanged. |
| D-7 | Exactly the five files listed below. |
| C-1 | `check_preview` repeats current pin, context, occurrence, compatibility, prompt and underlying artifact verification. |
| C-2 | One renderer owns one attempt, one request, one environment/release, at most one gate and one preview; failures are terminal. |
| C-3 | Bound registrations validate adapter/model/size and existing complete-prompt counters, with immutable/versioned evidence. |
| C-4 | All 24 nominal combinations, original six constructions and four required-sunrise variations have positive tests. |

Original Stage 1D changed files are reported from performed edits, without Git
(the narrower CP-01 three-file scope is recorded separately below):

1. `services/visual_renderer.py` — NEW: contracts, adapter, attempt owner and verification.
2. `tests/test_visual_renderer_stage1d.py` — NEW: independent literals, matrix and boundary tests.
3. `tests/test_visual_intent_package_a.py` — isolation assertions only.
4. `tests/test_visual_registry_stage1c.py` — isolation assertions only; all functional/adversarial oracles retained.
5. `docs/architecture/SG-01_Stage1D_Implementation_Record.md` — NEW: this record.

No existing interpreter, resolver, gate, semantic data, registry schema/content,
runtime consumer, configuration or provider was modified. No Git command, paid
model call, production/database access, migration or deployment was performed.
No test/audit evidence was deleted. Initial AGENTS discovery with `rg --files`
encountered an access-denied traversal under repository `tmp/`; no content there
was read or modified. Subsequent inspection used named source/docs/test paths.

## Normative D0-R2 mapping and responsibility boundaries

| D0-R2 basis | Stage 1D behavior |
|---|---|
| §2 neutral one-way imports; INT-14 | Only designated offline renderer gains dependencies. Existing 1A/1B/registry modules do not import it; runtime consumers remain disconnected. |
| §3–4.2, §8 | AR-01 segmentation and interpreter remain sole structural/semantic/negative-ledger owners. No vocabulary, alias, classification or legacy exception changes. |
| §4.3 | Existing resolver and `_assembly_bans` remain the sole closure owner. Scene absence is `SCENE_HUMAN_NONE`, not an invented style/user ban. |
| §4–6 | Exact immutable renderer contracts, exact recursive type checks and complete ordered registered-content proofs. Registry declarations are used as content authority, not source interpretation. |
| §5.2 | Complete final prompt measured by unchanged gate counters; no exclusion-count cutoff, truncation or inferred model limit. |
| §6 | Gate owns route, receipt, serialization, spans, final validation and `SyntheticValidatedAssembly`. Renderer owns additional compatibility/provenance verification and preview identity. |
| §7, §10 | Terminal attempt-local failures; no alternate selection, reconstruction, second gate or fallback after failure. Application lifecycle integration is deferred. |
| §9.1–9.3 | No untrusted prose, B standard, Custom Style subset, symbolic nuance policy or enrichment admission. Refusal does not establish full compatibility/fidelity. |
| §13 O-1 | Gate selects an offline route only after allowed canonical resolution, before construction/veto. This provides no production routing authorization or product activation. |
| §14 | Developer semantic review depends on accurate annotations; hashes do not prove meaning, independent acceptance or image pixels. |

## Public API and trust boundary

`create_offline_renderer(environment) -> OfflineRenderer` explicitly creates a
new attempt. `renderer.render(request) -> OfflinePreview` constructs at most one
preview. `renderer.check_preview(preview) -> ValidationResult` verifies that
attempt's exact issued object, without constructing/issuing another result.

All public request/value records are frozen and slotted:

| Contract | Fields and meaning |
|---|---|
| `SourceFields` | Exact unmodified strings `user_text`, `custom_style_description`. Empty strings permitted. |
| `SceneSelector` | Registered `scene_id` and exact component `version`. |
| `ArtisticSelections` | Tuple of versioned `RegistrySelection` components; exactly one composition, lighting and palette. Order is retained for exact assembly. |
| `VariantSelector` | Exact registered `variant_id` and version; ownership comes from the contract, never string parsing. |
| `SyntheticTarget` | Explicit adapter/model/size labels matching bound harness registration. |
| `RenderRequest` | Sources, canonical style/mode, scene, artistic selector and target. No replacement environment, release or expected manifest fields. |
| `SyntheticEnvironment` | Exact existing `SyntheticPolicy` and tuple of exact `SyntheticCapability` records. No capability defaults. |
| `FragmentOccurrence` | Position/span, full `RegisteredContent`, gate origin/refs, exclusion causes and bound scene selector. |
| `OfflinePreview` | Exact request, selected registered components, exact gate artifact and ordered occurrence tuple. Private issuance plus retained object identity is required. |

Inputs reject subclasses, overridden equality, mutable nested containers and
malformed primitives before invoking legacy equality/canonicality checks.
The renderer's recursive record encoding admits only explicit exact types,
primitive values, tuples/frozensets and the existing exact enum types. It binds
the complete current request/environment/preview to immutable byte snapshots.
These snapshots are additional integrity checks, not substitutes for live checks.
Renderer operations return/raise existing typed safety results/failures. CP-01
maps registry errors to existing semantic, coverage, evidence or authority reasons
at their actual phase, retaining a closed renderer-local diagnostic code as
specified below. Existing typed interpretation/capacity failures retain their
reason codes and stages. Python
constructor calls with unsupported keyword fields are rejected with `TypeError`
before a request exists; these cannot create an allowed renderer result.

No public parameter admits caller interpretation/resolution, source graphs,
auxiliary source/activity flags, candidates/assemblies, prompt fragments,
validation claims, routing assertions, suffixes, separators or production flags.
Private Python implementation/module state is trusted; this is not cryptographic
protection against arbitrary code monkeypatching that implementation.

## Sources and scene selection

The existing `interpret_visual_intent` assigns `user_text` / `USER_TEXT` as active
and `custom_notes` / `CUSTOM_NOTES` according to canonical requested style. Here
the latter is inactive because only the fixed photo style is admitted. Original
text, directive IDs, offsets, classifications and ledger evidence remain intact.
This is a narrow harness source contract, not real entry-point V0 authority.

Forest and meadow may supply eligible/default construction choices. They do not
become recognized user-language facts. `Show a forest path` and narrative-only
requests remain unsupported. `Show mountains` cannot select forest/meadow.
An unresolved relational negative remains blocked regardless of scene selector.
Ordinary theme prose never enters a fragment. A mixed story plus independently
eligible mountain/sunrise request preserves both unsupported narrative directives
and the supported mountain/sunrise refs, without rendering story-owned mug/window
objects. Active arbitrary Custom Style and enrichment fidelity remain unsupported.

## Environment and lifecycle

Environment policy is explicitly bound to:

`sg01-nature-seed@1.0.0#a57ab2fbc218564c2ed00290cb8866a25e4a07009889442705990719ac007864`.

Its context IDs are checked against pinned registered scenes. Capabilities retain
adapter/model, size tuple, unit, maximum, counter version, evidence reference and
capability version. Registrations are harness inputs; labels including
`production-approved` grant no authority. Requests cannot replace registrations.
Post-binding mutation or substitution fails. Unknown adapter/model/size,
missing capability, tokens and unsupported counter versions remain
`CAPACITY_UNVERIFIED`. Supported counters are existing `python-len-v1` Unicode
codepoints and `utf8-v1` bytes. Registered literals are ASCII, so their counts
coincide in these tests; no new Unicode content or tokenizer is claimed.

```text
CREATED -> VALIDATING -> PREVIEW_ISSUED
                     -> FAILED_TERMINAL
PREVIEW_ISSUED --failed verification--> FAILED_TERMINAL
```

Validation starts before accepting a request. Registry/selector/interpretation/
compatibility/gate failures terminate the attempt. Gate creation happens once,
after initial compatibility. Failed attempts cannot change selection or create
replacement gates. Repeated render calls reject without issuing a second preview;
an already valid preview remains valid after a rejected repeated issuance call.
Successful rechecks perform verification only. Failed rechecks retain their stable
blocked result even if corrupted fields are subsequently restored. A separate
factory call is a new explicit offline attempt. No application-wide fencing,
production retry, scheduling or persistence guarantee is asserted.
The attempt owner rejects copying, deep copying and serialization so copying its
state cannot be used as an alternate construction path after failure.

## Construction, compatibility and provenance

The adapter reads scene IDs, style/mode, base fragments, required keys, presence,
bindings and slot annotations from exact pinned contracts. It selects only the
scene-compatible registered slot values for 1B. It has no three-scene-name branch.
The extensibility test mechanically renames a scene and exercises adaptation;
that unpinned release is never rendered/issued and is rejected by the real pin.

Initial compatibility checks proposed artistic selections together with required
projections. Exact matching optional projections are omitted before gate assembly;
required occurrences retain gate-derived origin and refs. Incompatible dimensions,
time, scene, semantic entities or required facts cannot be rescued by deduplication.
No scene prohibition is blindly copied to `ControlledContext.forbidden_keys`.
The gate derives human absence with its existing closure; actual bans must cover
the scene's required absence keys and complete system no-text.

After actual gate assembly, independent occurrence reconstruction checks every
fragment against its expected registered selection and source role in sequence:
base fragments, sorted required projections, retained optional selections, sorted
canonical exclusions and final no-text. Every occurrence binds release ID/version/
digest, component ID/version/slot, exact text/role/keys/entities, review ID/digest,
scene, position/span, gate origin, source refs and applicable closure causes.
It verifies exact LF serialization with no gaps, suffix or changed spans. A set of
unique IDs, copied strings or caller-consistent hashes cannot stand in for this
complete sequence. Compatibility runs again on actual occurrences, including
required projections, exclusions and conditional metadata. The unchanged 1B final
validator and artifact verifier then must both pass before issuance.

`check_preview` verifies exact preview/artifact types and issued-object identity,
request identity, immutable current bindings, pinned release and selector ownership,
complete current occurrence reconstruction, actual assembled-content compatibility,
exact prompt, and the underlying gate's current artifact check. It also verifies
synthetic authority and false production authorization. Equal copied/reconstructed/
foreign wrappers and cross-attempt artifacts fail. A standalone 1B artifact is
never evidence that 1D checks ran. No corruption repair or reissuance is performed.

## Finite semantic review and successful constructions

The following is **author/developer semantic review**, pending independent Claude
Code audit and Owner acceptance. The independent literal expectations are in
`SCENE_TEXT`, `COMPOSITIONS`, `LIGHTING`, `PALETTES`, `BAN_TEXT`, `SIX` and `MATRIX`
in the Stage 1D tests; expected prompts are not read from renderer/registry output.
All combinations preserve the fixed photographic style, scene identity entities,
human/body/hands absence and the complete registered no-text clause.

Forest compositions retain path/trees/ferns with either a low deep curve or an
elevated diagonal. Both morning side light and midday patches remain compatible.
Meadow compositions retain meadow/grass/wildflowers using near-flower depth or
horizontal meadow/sky bands. Morning and sunset describe different valid times.
Mountain compositions retain ridges/rock/valley using compressed telephoto layers
or granite foreground and diagonal depth. Sunrise/evening describe separate valid
choices, not simultaneous times. Cool and warm palettes are color treatments,
not competing time requirements. Cool shadows can coexist with warm sunset/first
light; warm ochre highlights with neutral shadows do not replace the stated time.
No selected palette/composition introduces people, lettering or unsupported objects.

Each row below is an executed positive test through real 1B and 1D validation:

| # | Scene | Composition | Lighting | Palette | Result |
|---|---|---|---|---|---|
| 1 | forest_path | low_leading_curve | morning | cool | PASS |
| 2 | forest_path | low_leading_curve | morning | warm | PASS |
| 3 | forest_path | low_leading_curve | daylight | cool | PASS |
| 4 | forest_path | low_leading_curve | daylight | warm | PASS |
| 5 | forest_path | elevated_diagonal | morning | cool | PASS |
| 6 | forest_path | elevated_diagonal | morning | warm | PASS |
| 7 | forest_path | elevated_diagonal | daylight | cool | PASS |
| 8 | forest_path | elevated_diagonal | daylight | warm | PASS |
| 9 | open_meadow | grass_level_depth | morning | cool | PASS |
| 10 | open_meadow | grass_level_depth | morning | warm | PASS |
| 11 | open_meadow | grass_level_depth | sunset | cool | PASS |
| 12 | open_meadow | grass_level_depth | sunset | warm | PASS |
| 13 | open_meadow | elevated_horizon_bands | morning | cool | PASS |
| 14 | open_meadow | elevated_horizon_bands | morning | warm | PASS |
| 15 | open_meadow | elevated_horizon_bands | sunset | cool | PASS |
| 16 | open_meadow | elevated_horizon_bands | sunset | warm | PASS |
| 17 | mountain_view | telephoto_layers | sunrise | cool | PASS |
| 18 | mountain_view | telephoto_layers | sunrise | warm | PASS |
| 19 | mountain_view | telephoto_layers | evening | cool | PASS |
| 20 | mountain_view | telephoto_layers | evening | warm | PASS |
| 21 | mountain_view | wide_rock_foreground | sunrise | cool | PASS |
| 22 | mountain_view | wide_rock_foreground | sunrise | warm | PASS |
| 23 | mountain_view | wide_rock_foreground | evening | cool | PASS |
| 24 | mountain_view | wide_rock_foreground | evening | warm | PASS |

The original six constructions have separate exact prompt, order, span, semantic
and full occurrence-origin/ref tests through registered variant selectors:

| Variant | Composition | Lighting/palette | Source |
|---|---|---|---|
| forest_path.A | low_leading_curve | morning/cool | No people; No mugs |
| forest_path.B | elevated_diagonal | daylight/warm | No people; No mugs |
| open_meadow.A | grass_level_depth | morning/cool | No people; No mugs |
| open_meadow.B | elevated_horizon_bands | sunset/warm | No people; No mugs |
| mountain_view.A | telephoto_layers | sunrise/cool | Show mountains at sunrise; No people; No mugs |
| mountain_view.B | wide_rock_foreground | evening/warm | Show mountains; No people; No mugs |

All four constrained mountain/sunrise combinations (both compositions × both
palettes) pass separate tests. Sunrise appears exactly once as a required
`user_projection` with ref `('user_text', 0)` and original qualifier span `(18,25)`;
mountain retains `(5,14)`. Required ordering remains sunrise, mountain anchor,
composition, palette. Optional duplicate lighting is absent. Evening selections
under the explicit sunrise requirement fail; no qualifier/default is rewritten.

Scene-only human-absence success is tested for **all three scenes**, with no
source facts/refs and only `SCENE_HUMAN_NONE` on human/body/hands. Explicit repeated
human bans merge original refs and `USER_EXCLUSION`; hands/body also retain
`HUMAN_EXCLUSION_CASCADE`. No selected-style cause is invented. Mug, notebook,
table and window exclusion successes retain their exact independent refs/causes.
Twenty-one repeated mug bans retain all 21 refs. Ordinary themes and inactive
notes stay out of prompt content. Supported mixed narrative/mountain/sunrise
requests preserve supported facts and unsupported classifications independently.

## Adversarial coverage

Tests exercise unknown/stale scene/variant/component/version/slot and missing slot;
canonical-style alias and mode rejection; forged variant ownership, incompatible
scene/composition/time and duplicate/missing artistic dimensions; unsupported-only
and unresolved-negative selector disguise; fake scene contract; substituted seed
ID/version/text/entities/review/annotations with recomputed manifests; stale pin
and cross-release proof with equal text; both mandatory compatibility calls;
attempts to skip either compatibility layer; lost required projection; gate veto
at preflight/assembly/final/artifact stages; changed origin/refs/slot/review/cause;
subclasses/equality/mutables/uninitialized exact records; order/spans/separators/
suffix/repeated proof; unknown target/counter/capacity; environment/capability
substitution and production-label/flag injection; copied/reconstructed/foreign
preview/artifact; corruption after issuance; stable terminal failures after field
restoration; repeat issuance and alternate selection after registry/gate failure;
no replacement gate; static and fresh-process isolation. Monkeypatches are fault
injection to demonstrate mandatory checks, not a claim to resist arbitrary trusted
implementation rewriting.

## Stage 1D CP-01 — targeted diagnostic and lifecycle correction

Authorized corrective scope: only `services/visual_renderer.py`,
`tests/test_visual_renderer_stage1d.py` and this record. The two original isolation
test files, Stage 1A–1C owners, registry content, shared safety contracts, runtime
consumers and configuration receive no CP-01 edits. This is not Stage 1E or a
reopening of the accepted architecture. No Git command, provider call, production
operation, migration, deployment or test-evidence cleanup was performed. The
initial CP-01 inventory accidentally traversed repository `tmp/` names and received
an access-denied error; no contents were read or changed. All later inspection
uses explicit source, test and documentation paths.

### F-1: closed registry reason/stage mapping

D0-R2 §5.1 and the implemented `visual_safety_types` contracts were read before
the correction. No shared reason code, stage, detail token or retry contract is
added. A blocked result contains one existing reason with the actual wrapper
phase; an existing `VisualSafetyFailure` retains its original result, reason,
stage, detail and refs, even if its stage differs from the wrapper's current
phase. Every veto terminates the attempt; there is no retry/fallback path.

The renderer reaches registry diagnostics through these existing paths:

| Path | Registry checks and reachable diagnostic families |
|---|---|
| Factory `seed_registry`; render/preview `_intact` re-entry | Full release schema/identity/review/binding/slot/scene/variant validation and pinned release integrity. All release-validation tokens below can surface under corrupted evidence; valid pinned content does not naturally trigger them. |
| Scene/variant selection and component lookup | Unsupported scene coverage, unknown scene/variant/component versions/identities and slot values; release integrity is checked on every snapshot operation. |
| Initial compatibility | Component/slot scene ownership, dimensions, positive/excluded/entity conflicts, required scene identity/keys and time axis. |
| Actual occurrence reconstruction and compatibility | The same compatibility families plus registered-content proof integrity, including complete review/release provenance. Preview checking repeats these checks. |

There are **32 declared registry diagnostic tokens**, all explicitly mapped below.
`INVALID_DIGEST` is a defensive mapping for the manifest-constructor invariant;
the renderer normally constructs manifests from a SHA-256 digest, so this token
has no natural failing path with the fixed valid manifest. The other tokens are
in registry methods traversed by the renderer, including full seed revalidation.
Fault injection tests the entire mapping; it is not a claim that every token is
independently reachable from an ordinary valid request against unchanged seed
content. Existing value-contract canonicality guards still reject malformed
records with typed `INVALID_EVIDENCE` before registry selection.

| Exact registry token(s) | Existing safety reason | Rationale |
|---|---|---|
| `INCOMPATIBLE_SCENE`, `INCOMPATIBLE_SCENE_SLOT`, `CONFLICTING_ARTISTIC_DIMENSION`, `CONFLICTING_TIME_QUALIFIERS`, `SEMANTIC_CONFLICT` | `SCENE_CONFLICT` | Registered selections cannot coexist within the proposed scene/semantic construction. A broader code needs the specific local detail below. |
| `FORBIDDEN_CONTENT`, `FORBIDDEN_ENTITY` | `FORBIDDEN_POSITIVE_CONTENT` | Actual positive/conditional semantics or entities violate a ban. |
| `MISSING_SCENE_IDENTITY`, `MISSING_REQUIRED_KEY` | `MISSING_REQUIRED_VISUAL_FACT` | Required subject identity or positive coverage is absent. |
| `MISSING_EXCLUSION_COVERAGE` | `MISSING_MANDATORY_EXCLUSION` | Required exclusion coverage is absent. |
| `INVALID_RECORD`, `INVALID_UNICODE`, `INVALID_DIGEST`, `DUPLICATE_IDENTITY`, `DANGLING_REVIEW`, `DANGLING_SCENE`, `INCOMPLETE_SLOT_ANNOTATIONS`, `INVALID_SLOT_SCHEMA`, `INVALID_ARTISTIC_CONTRACT`, `INVALID_BINDING`, `EMPTY_VARIANT`, `RELEASE_INTEGRITY_MISMATCH`, `CONTENT_INTEGRITY_MISMATCH` | `INVALID_EVIDENCE` | Malformed evidence, broken provenance/reference links, or a failed integrity comparison; distinct from absent trusted authority. |
| `INVALID_REVIEW_BASIS`, `UNKNOWN_SCHEMA`, `UNKNOWN_FRAGMENT`, `UNKNOWN_FRAGMENT_VERSION`, `UNKNOWN_SLOT_VALUE`, `UNSUPPORTED_COVERAGE`, `UNKNOWN_SCENE_VERSION`, `UNKNOWN_VARIANT`, `UNKNOWN_VARIANT_VERSION` | `UNTRUSTED_AUTHORITY` | No admitted review/schema/registered selector authority exists for the supplied identity, version or coverage. This does not label a valid but incompatible registered selection as untrusted. |
| Any unknown token, wrong argument arity/type or arbitrary message | `UNTRUSTED_AUTHORITY` | Fail closed with only `UNKNOWN_REGISTRY_ERROR` as local detail. Never copy error prose into a result or public message. |

`renderer.registry_failure_code` is a read-only property containing the exact
whitelisted registry token, `UNKNOWN_REGISTRY_ERROR`, or `None` when no terminal
registry veto occurred. It remains stable after attempted reuse. This is a
renderer-local diagnostic, not a new safety reason or `ValidationIssue.detail`
token. The existing detail whitelist describes interpreter ambiguity/structure
and cannot faithfully represent registry failures; therefore mapped issues leave
`detail=None`. The specific token distinguishes, for example, a conflicting time
axis from a scene-slot mismatch and an integrity mismatch from a dangling review.
Factory vetoes have no issued renderer to inspect and expose only the existing
typed result. Unknown registry exception chains remain suppressed in the public
typed safety exception, following the existing safe-message contract.

| Failure location | Existing stage used for registry/normalized/unexpected failure |
|---|---|
| Factory binding and seed validation | `preflight` |
| Render input/binding checks; scene/variant/components, projections, initial compatibility, adaptation, gate creation/preflight | `preflight` |
| Interpretation/resolution | `interpretation` |
| Gate assembly | `candidate` |
| Actual occurrence/proof/compatibility verification, final validation, artifact check and preview issuance | `final` |
| All current preview revalidation | `final` |

No `dispatch` stage is manufactured by this offline renderer. Existing typed
safety failures retain their owner's stage rather than being relabeled by this
table. The two previously misleading legacy fixtures now assert the first actual
failure: mountain projection in forest/meadow is `INCOMPATIBLE_SCENE`; required
sunrise plus optional evening is `CONFLICTING_ARTISTIC_DIMENSION` before the later
aggregate time-axis check. Both correctly map to `SCENE_CONFLICT / preflight`.
The complete mapping independently covers missing-key and time-axis diagnostics.

### F-5: terminal lifecycle and exception diagnostics

Render and preview verification now have a final `except Exception` fence:
transition to `FAILED_TERMINAL`, retain a stable blocked `INVALID_EVIDENCE` result
at the current phase, then use bare `raise`. The same unexpected exception object,
original cause and traceback (including the injecting/calling frame) propagate.
These defects do not become expected typed vetoes or apparent successful results.
There is no `BaseException` handler; `KeyboardInterrupt` and `SystemExit` propagate
without normalization. Existing malformed-record normalization for
`AttributeError`, `TypeError`, `ValueError` and `RecursionError` remains in place;
this corrective fence handles other implementation exceptions without swallowing
them. Expected `VisualSafetyFailure` and `RegistryError` remain typed veto paths.

After such a defect, checking any preview returns the retained blocked result.
Restoring the injected function cannot repair the attempt. Repeated render calls
cannot select another scene, reconstruct, create a replacement gate or issue a
preview. An already issued preview is invalidated by a defect during its check.
The repeat-render guard remains outside the active-attempt exception handlers:
rejecting a repeat render still preserves a valid issued preview, as required.

### Added and adjusted regression oracles

CP-01 adds **179** cases to the original 215, for **394** focused cases:

- 96 hand-authored mapping cases: 32 tokens at initial compatibility, actual
  compatibility and preview verification, asserting exact reasons/stages, closed
  read-only diagnostics, terminal state, retry prohibition and fenced reuse.
- 8 unknown/malformed registry-error cases, 4 factory cases and 1 real pinned
  release integrity mutation/restoration case.
- 40 render fault injections across 10 boundaries and 24 preview injections
  across 6 boundaries, using `KeyError`, `StopIteration`, `RuntimeError` and
  `AssertionError`. They assert original exception/cause/traceback and stable
  blocked reuse after restoration.
- 2 original typed-veto result/stage/detail preservation cases and 4
  process-control propagation cases.

Existing expectations change only for the semantic reason corrections and actual
first registry failures described above; the two mandatory-compatibility cases
also gain reason/stage/detail assertions. No successful prompt text, ordering,
span, provenance, closure, capacity, runtime-isolation or synthetic-only oracle
is changed. The original 24/24 matrix, 6/6 constructions, 4/4 constrained sunrise
variations and all three scene-only absence cases remain in the focused suite.

### Independent Stage 1D finding dispositions

This register describes the Owner-supplied Stage 1D audit, separately from all
Stage 1A, 1B and 1C finding registers.

| Stage 1D finding | CP-01 disposition |
|---|---|
| F-1 (MINOR) | Corrected as specified above; targeted independent verification PENDING. |
| F-2 (NOTE) | Accepted synthetic harness registrations; no claim of real provider capability evidence. |
| F-3 (NOTE) | Accepted internal factory sentinels; not secret security tokens or cryptographic authority. |
| F-4 (NOTE) | ASCII-only pinned prompt content makes byte and codepoint counts coincide. A distinguishing non-ASCII capacity oracle is deferred; seed content is unchanged. |
| F-5 (NOTE) | Corrected terminal lifecycle fence and original exception diagnostics; targeted independent verification PENDING. |
| F-6 (NOTE) | Accepted layered offline validation. Future integration must demonstrate consistent gate/renderer enforcement; the existing resolver/gate remains the sole closure owner. No duplicate closure derivation is introduced. |
| F-7 (NOTE) | Owner-performed Git diff/status and CI verification PENDING; no developer Git verification claimed. |

### CP-01 test evidence

Final focused, affected regression and complete offline results are recorded
below. Tests use `PYTHONDONTWRITEBYTECODE=1`, Python `-B`,
`-p no:cacheprovider` and default OS-managed pytest temporary directories. Concurrent
runs receive distinct pytest-managed directories; no `--basetemp`, repository
`tmp/`, `.pytest_tmp_*` directory or evidence cleanup is used. Logs are retained
at unique GUID-named paths in the OS temporary directory.

Every command below ran from the repository root with
`$env:PYTHONDONTWRITEBYTECODE='1'`. PowerShell redirected output with
`*> $cp01Log`, where `$cp01Log` was generated using
`Join-Path ([IO.Path]::GetTempPath()) ('sg01-cp01-<run>-' + [guid]::NewGuid().ToString('N') + '.log')`;
the Python exit code was preserved and reported.

| Exact test command | Result | Preserved log |
|---|---|---|
| `.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/test_visual_renderer_stage1d.py` | **394 passed in 44.34s**, exit 0; 0 failed, 0 skipped, 0 xfailed, 0 xpassed | `C:/Users/eliv/AppData/Local/Temp/sg01-cp01-focused-final-fffb3b8aeb6e4bf680ce2031adc4d8ce.log` |
| `.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/test_directive_segments_package_a.py tests/test_visual_intent_package_a.py tests/test_visual_safety_stage1a.py tests/test_visual_safety_stage1b.py tests/test_visual_registry_stage1c.py` | **1,202 passed in 12.58s**, exit 0; 0 failed, 0 skipped, 0 xfailed, 0 xpassed | `C:/Users/eliv/AppData/Local/Temp/sg01-cp01-regressions-2a0e2d2dc76d4a4f9454e7fa5997a38d.log` |
| `.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider` | **6,305 passed in 320.59s (0:05:20)**, exit 0; 0 failed, 0 skipped, 0 xfailed, 0 xpassed | `C:/Users/eliv/AppData/Local/Temp/sg01-cp01-full-offline-d9509695c40643afb4ac7f40a5743162.log` |

The complete result is the original 6,126 cases plus 179 CP-01 cases. All 215
original Stage 1D cases and all 1,202 affected regressions remain collected and
passing. No functional/adversarial oracle was removed, skipped or weakened.
The pre-existing unset `asyncio_default_fixture_loop_scope` deprecation warning
remains. Existing offline fixtures neutralize dotenv and isolate provider
credentials and temporary SQLite/output paths; no live provider or production
database was accessed.

SHA-256 values recorded before and after the complete run matched exactly;
only this record was then updated with the completed evidence:

| Python file | SHA-256 during complete run |
|---|---|
| `services/visual_renderer.py` | `6eb31361daeaba8e6b923ca0adff0386f12328f20323325ac6ce82e33d12f621` |
| `tests/test_visual_renderer_stage1d.py` | `73fd6d2abedcd19f1e65b44ab5dd1370920f22f4b394d92642dd1a9051c36b30` |
| `tests/test_visual_intent_package_a.py` | `f311ee102707e8e004e14659c2f825661548988939bd9184d48380025e6f848d` |
| `tests/test_visual_registry_stage1c.py` | `a9cab710b5a9690880dfd8007e86b21d98544c18bcdb3249cdf11fe7c89c1de0` |

Syntax parsing and trailing-whitespace checks passed for the two edited Python
files; this record also passed its trailing-whitespace check. Static enumeration
of registry declarations found exactly 32 tokens, with no missing or extra
mapping entries. These are developer checks, not independent audit or CI evidence.

Development run: **391 passed, 3 failed in 41.89s**, exit 1, 0 skips/xfails/xpasses;
log `C:/Users/eliv/AppData/Local/Temp/sg01-cp01-focused-900776cb0dca4c4aa0d7c6c4957ef65c.log`.
The three failures exposed misleading legacy diagnostic names: occurrence scene
ownership and duplicate lighting dimensions fail before the aggregate missing-key
and time checks named by the old tests. Their hand-authored expectations were
corrected as documented above. All 179 newly added cases passed in that run.
This intermediate run does not substitute for the final passing executions.

Independent CP-01 verification and final Owner acceptance remain **PENDING**.
All deferred integration dependencies listed later in this record remain open,
including real source/capability authority, non-bypassable provider transport,
application-wide lifecycle fencing, layered-validation assurance and deployment
backup/rollback prerequisites. CP-01 creates no production authority or next-phase
approval.

## Stage 1C finding dispositions (separate register)

| Finding | Stage 1D disposition |
|---|---|
| F-1 | Canonical-only style; alias admission remains deferred. |
| F-2 | Existing internal pin mandatory; external governance deferred. |
| F-3 | Compatibility mandatory before construction and against actual assembly. |
| F-4 | Full review provenance retained; labels/free text confer no approval. |
| F-5 | Exact release/component bindings; no universal component-version equality rule added. |
| F-6 | New exact-type/arity/corruption failures covered; old registry schema-arity hardening deferred. |
| F-7 | All 24 reviewed/tested by developer; annotations and independent semantic audit remain explicit dependencies. |
| F-8 | Successful scene-only human-absence coverage for every seed scene. |
| F-9 | Scene selector never creates user-language recognition/authority. |
| F-10 | Results below are developer-executed local tests; independent audit/CI/Owner acceptance are not claimed. |

## Original Stage 1D test execution and preservation (before CP-01)

All commands use OS-managed pytest temporary directories, bytecode disabled and
pytest cache disabled. Logs are preserved in the OS temporary directory. Final
focused/regression runs overlapped the intermediate full run and used separate
fresh absolute basetemp paths derived from the OS temporary root plus GUIDs.
No repository-local basetemp or artifact cleanup was used.
The pre-existing unset `asyncio_default_fixture_loop_scope` warning remains.
Existing offline fixtures disable dotenv loading and isolate provider credentials
and SQLite/output fixtures; no real model/provider/production DB was accessed.

Each command was run with `$env:PYTHONDONTWRITEBYTECODE='1'`. Output was redirected
to a GUID-named OS-temporary `.log` with `*> $stage1dLog`, preserving the Python
exit code. Commands and final results:

| Command | Result | Log |
|---|---|---|
| `.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/test_visual_renderer_stage1d.py --basetemp C:\Users\eliv\AppData\Local\Temp\sg01-stage1d-final-focused-tests-ddd2d72d79334e07bdcb5b25c99265e6` | 215 passed in 26.46s, exit 0; 0 failed/skipped/xfail | `C:/Users/eliv/AppData/Local/Temp/sg01-stage1d-focused-verified-4e01127b87e84e418c0f6a7f38b256c3.log` |
| `.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/test_directive_segments_package_a.py tests/test_visual_intent_package_a.py tests/test_visual_safety_stage1a.py tests/test_visual_safety_stage1b.py tests/test_visual_registry_stage1c.py --basetemp C:\Users\eliv\AppData\Local\Temp\sg01-stage1d-final-regression-tests-764c14d640da45d8aaa7ab61053d4d05` | 1,202 passed in 12.74s, exit 0; 0 failed/skipped/xfail | `C:/Users/eliv/AppData/Local/Temp/sg01-stage1d-regressions-verified-ed5b8417d03c47cd84255c539a5a1762.log` |
| `.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider` | 6,126 passed in 215.90s, exit 0; 0 failed/skipped/xfail | `C:/Users/eliv/AppData/Local/Temp/sg01-stage1d-full-verified-2b2b3b4a89e24cf59067691ed0429365.log` |

The final complete run collected/passed the 5,911 baseline tests plus **215 new
Stage 1D cases**. No existing functional oracle was removed, weakened or skipped.
The five affected regression files retain **1,202** cases, including all **106**
Stage 1C cases. Four Python file SHA-256 values were recorded during the final
full run and rechecked afterwards to verify unchanged code; only this record was
then updated with completed evidence. Syntax parsing and trailing-whitespace
checks passed for all four Python files and this record as applicable.

Development evidence: initial Stage 1D run **161 passed, 1 failed in 15.80s**;
log `C:/Users/eliv/AppData/Local/Temp/sg01-stage1d-focused-7f622aea133e44f8bea2a4d1f8bd0c2f.log`.
The new mixed-request oracle incorrectly expected one narrative directive rather
than the two coordinated AR-01 members; it was corrected with the independent
mountain ref 2. No existing oracle or interpretation was changed. Expanded
Stage 1D run **199 passed in 15.50s**, exit 0, no skips/xfails;
log `C:/Users/eliv/AppData/Local/Temp/sg01-stage1d-focused-e559e18fe5454d3daf5cd47573bc698c.log`.
These intermediate runs do not substitute for final-code results.
The earlier regression run also passed 1,202 tests in 8.73s (exit 0), preserved at
`C:/Users/eliv/AppData/Local/Temp/sg01-stage1d-regressions-d05e6e9270ca43529ff7a52285697f84.log`.
Before the final attempt-copy/occurrence-constructor hardening, Stage 1D passed
205 tests in 15.54s (exit 0), preserved at
`C:/Users/eliv/AppData/Local/Temp/sg01-stage1d-focused-final-38d0efc295a84c93963ebd62d6b38870.log`.
The full run begun at that point is intermediate evidence because the final
hardening was added while it was running; it is not final-code certification.
It completed with **6,116 passed in 270.11s**, exit 0, no skips/xfails, preserved at
`C:/Users/eliv/AppData/Local/Temp/sg01-stage1d-full-b600d4000a2849f790d454b2d5bb0e2f.log`.

## Deferred obligations and required future closure points

Stage 1A register (not Stage 1C findings):

| Obligation | Required closure point |
|---|---|
| F-07 vocabulary/alias reconciliation | Review shared/legacy vocabulary equivalence with independent oracles before coherent runtime migration. |
| F-08 `RequestClass` | Preserve clarified meanings for negative/non-request directives before any integration consumer relies on them. |
| F-09 runtime equivalence/parser isolation/consumer sentinels | Complete runtime INT evidence and all-entry-point sentinels before activation. |
| F-10 `Attachment.frame_level` | Define supported semantics before any new consumer relies on it. |

Stage 1B register:

| Obligation | Required closure point |
|---|---|
| F-04 real V0 source/activity/entry-point authority | Implement and independently audit actual production source authority before integration. This harness does not establish it. |
| F-07 broader legacy subclass/equality canonicality | Independently harden/review the existing evidence/gate contracts before production integration. New wrapper checks do not close it. |

Additional obligations:

| Obligation | Required closure point |
|---|---|
| External release governance and additional content | Separately approve trust-store/release governance and independent semantic review before admitting expanded releases/coverage. |
| Verified real capabilities/counters | Verify exact adapter/model/size/tokenizer and complete prompt capacity before any real dispatch. |
| Production policies/routes/validated artifacts | Separately authorize and independently review before production route selection; O-1 is conditional and insufficient alone. |
| Non-bypassable provider guard | Implement a distinct production artifact/transport boundary rejecting synthetic types before provider integration. |
| Application-wide attempt identity/lifecycle | Independently audit attempt fencing, terminality and ownership across consumers before runtime activation. |
| Interactive/Profile/More/scheduled/CLI | Separately authorize coherent V0–V4 migration, early paid-call ordering, quota cleanup, terminal scheduler writes, CLI sibling cancellation and metadata identity before activation. |
| Arbitrary Custom Style fidelity | Separately authorize faithful representation/enforcement before admission; safe refusal is not full compatibility. |
| Symbolic nuance | Separately authorize faithful handling before admission; no omission policy follows from inactive-note authority. |
| Free LLM prose and FIX-03B-2B-2 | Complete separate accepted-enrichment review/enforcement before admission; any B standard needs explicit Owner approval. |
| N-2 custom-photo fallback | Complete before production deployment, preserving all four D0-R2 §10 conditions and existing fail-closed conflicts. |
| RS-UX-01, unrelated FIX-03/diversity | Separate Owner-approved task before implementation. |
| Actual image quality and O-1 product effects | Independently review images and material functionality/style/quality changes before activation. No images were generated here. |
| Production activation/deployment | Explicit Owner authorization, fresh verified backup and rollback capability before any deployment. |

The three scenes remain limited content coverage, not a general renderer or a
product restriction. Other positive objects/artifacts, landscapes, styles, local
relations, arbitrary custom prose, symbolic nuance and enrichment are not rendered
faithfully by this package. Bounded grammar/vocabulary can refuse valid requests.
Exact prompt validation proves neither general natural-language correctness nor
pixel-level absence/no-text compliance. Same-process private-state/module rewrites
remain outside the internal trust model.

The original Stage 1D audit verdict is **ACCEPT WITH MINOR NOTES**, supplied by
the Owner for CP-01. Independent CP-01 verification and final Stage 1D Owner
acceptance are **PENDING**. Owner Git/CI checks remain pending. No next phase,
production authorization or new CI result is asserted by this record.

CP-01 implementation verdict: **CP-01 COMPLETE — READY FOR TARGETED INDEPENDENT AUDIT**.
