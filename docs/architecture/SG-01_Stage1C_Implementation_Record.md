# SG-01 Stage 1C — Real Registry Foundation

Date: **2026-11-23**. Implementation scope: offline content foundation only.

**Independent Claude Code read-only audit: PENDING. Owner acceptance: PENDING.
Production authorization: NOT GRANTED.** No later phase is authorized by this record.

## Authority, scope and exact changed files

The Owner supplies the baseline `main` / `5533a4a`, Actions tests #46 PASS,
5,805 offline tests, and Stage 1A/1B closure. These are Owner-supplied facts,
not Git verification. The Owner explicitly confirmed during this implementation
that the full Stage 1C task incorporates and supersedes the accepted READ-ONLY
Scope Lock Proposal. No separate proposal file is required or created.

The four controlling conditions are: the three scenes are an extensible validation
slice; semantic contracts remain separate from compatible artistic construction;
integrity/author review confer no independent acceptance or production authority;
and each scene has two materially different positive constructions.

Exactly five files are created/modified, reported from performed edits without Git:

| File | Change |
|---|---|
| `services/visual_registry.py` | NEW: immutable schemas, canonical encoding, release validation, exact lookup, closed-slot compatibility, pinned snapshots and provenance checks |
| `services/visual_registry_content.py` | NEW: original real English literals, content-local semantic declarations, author-review evidence, six variants and fixed release manifest |
| `tests/test_visual_registry_stage1c.py` | NEW: hand-authored real-content oracles, adversarial tests, exclusively test-local Stage 1B bridge/policy/capability |
| `tests/test_visual_intent_package_a.py` | MODIFY: extend only the existing import-isolation oracle for the two new neutral modules; all Package A semantic expectations retained |
| `docs/architecture/SG-01_Stage1C_Implementation_Record.md` | NEW: this evidence and dependency record |

No runtime consumer is connected. No handler, scheduler, CLI, builder, provider,
configuration, database, migration, deployment or unrelated FIX-03 file is changed.
Repository `tmp/` is not inspected or modified. No Git command, production access,
paid/live model call, artifact cleanup or independent audit is performed.

## D0-R2 compliance mapping

| Normative basis | Implementation and limit |
|---|---|
| §2 neutral dependency direction; §11 INT-14 | Registry imports only standard-library schemas/hash/JSON and existing neutral semantic contracts. Content imports only that registry and neutral fragment types. Static and fresh-process isolation tests keep both unreachable from production and Stage 1B runtime. |
| §3–4.2, §8 D1-A / SG-D1 / SG-D2 | No grammar, alias, user recognizer, source authority, classification, legacy exception or negative-ledger change. Existing regressions remain normative. |
| §4 immutable evidence and identity | Frozen slotted records; exact recursively validated types; tuples/frozensets; versioned selections; complete release/content/review binding. |
| §4.3 one closure owner | Registry declares compatibility, not a new closure algorithm. The test bridge uses the existing Stage 1B scene-none reconciliation and canonical ban derivation with all user refs/causes. |
| §5.2 capacities | No real adapter/capacity registry. A clearly fake test capability exercises existing checks; unregistered/changed capabilities remain blocked. |
| §6 exact fragments, closed slots, provenance, final serialization | Existing neutral `RegisteredFragment`, `ClosedSlotValue`, roles and canonical keys are reused. Each successful preview passes unchanged Stage 1B preflight, reconstruction, exact LF/spans, final validation and artifact checks. |
| §9.1–9.3 no-B / fidelity | No arbitrary prose, new Custom Style subset, symbolic omission rule, enrichment admission or B standard. Unsupported coverage remains explicit. |
| §13 O-1 | Only synthetic test route selection, before construction and before any veto. No production routing rule or fallback promotion. |
| §14 review/quality limits | Author declarations, exact content and hashes do not prove natural-language correctness, independent approval or image quality. |

## Release manifest and immutable architecture

Release ID: `sg01-nature-seed`. Release version and every content, scene and variant
version: **`1.0.0`**. Schema: `sg01-content-schema-v1`.

Pinned SHA-256 payload digest:

```text
a57ab2fbc218564c2ed00290cb8866a25e4a07009889442705990719ac007864
```

Canonical serialization uses UTF-8, sorted compact JSON field names, explicit
record type tags, ordered tuples and lexicographically sorted frozensets. It binds
exact text, slot schemas/values, canonical keys, entity annotations, compatibility,
selections, versions and author-review metadata. LF/CR are forbidden within individual
content literals; final LF separators belong exclusively to unchanged Stage 1B.

The explicit schema whitelist rejects subclasses of new records, neutral nested
records, strings, tuples and frozensets, as well as mutable nested values. No
`isinstance` or caller-overridable record equality establishes registry trust.
Canonical bytes and exact primitive types are checked before comparisons. Snapshot
methods recheck their release against the retained manifest on access. Tests also
exercise local corruption through `object.__setattr__`; normal field mutation fails.

`manifest_for` and a caller-created `RegistrySnapshot` can describe a mechanically
consistent proposed release. They grant no semantic acceptance. `seed_registry`
always compares its supplied release to the fixed `SEED_MANIFEST`; it never derives
a replacement expected digest from caller content. Same ID/version substitutions,
including valid recomputed digests, cannot replace that seed identity. Lookups
return immutable `RegisteredContent` with release ID/version/digest, fragment
ID/version, slot value, exact text/keys/entities and review ID/digest. Verification
reconstructs that evidence; forged metadata and cross-release proofs fail.

This is an internal Python API boundary. Hashes are not signatures, a semantic
proof or an authorization token. Deliberately replacing both module state and its
trust reference in the same process is outside its guarantees. A future trust store
and release governance require separate authorization and review.

## Semantic and artistic inventory; author-review evidence

There are **24 fragments: 19 semantic and 5 artistic**, three scene contracts,
six constructions, five positive projection bindings and fourteen canonical
exclusion bindings. Content and component IDs below all carry version `1.0.0`.

| Semantic content IDs | Declared meaning and review evidence |
|---|---|
| `style.living_nature_photo` | Natural photographic textures, optical depth, restrained contrast. No subject, person, lettering or style replacement is requested. |
| `scene.forest_path` | Continuous earthen footpath, woodland trees and ferns. Required identity entities: footpath and trees. |
| `scene.open_meadow` | Open grassy meadow, scattered wildflowers and a natural horizon. Required identity entities: meadow, grass, wildflowers. |
| `scene.mountain_view` | Layered mountain ridges, rock faces and valley. Required identity entities: mountain, ridges, valley; existing canonical `('scene', 'mountain')`. |
| `subject.mountain` | Separate canonical mountain projection required by Stage 1B; reinforces the essential ridges without adding a new subject. |
| `ban.object.body`, `.hands`, `.human`, `.mug`, `.notebook`, `.table`, `.window` | Seven exact canonical absence clauses. Mug includes existing cup equivalence; body retains the established coarse anatomy meaning. Each binding covers exactly its own canonical key. |
| `ban.coastal.beach`, `.coast`, `.lagoon`, `.rocky`, `.sandy`, `.water` | Six exact coastal absence clauses, with no invented complementary beach and no expansion of coastal water to inland water. |
| `ban.system.text_marks` | Exact complete clause: “No text, words, letters, numbers, typography, logos, or watermarks.” |

Entity IDs such as `footpath`, `grass` and `ridges` are **content-local review
annotations**, not new user-language canonical keys or recognizers. They establish
declared scene identity and component compatibility. They cannot create a user fact.

| Artistic content ID | Closed values and semantic review |
|---|---|
| `composition.forest_path` | `low_leading_curve`: low camera, foreground ferns, path depth; `elevated_diagonal`: oblique high viewpoint, diagonal path, overlapping crowns. Annotated entities remain trees/path/ferns. Forest only. |
| `composition.open_meadow` | `grass_level_depth`: focused near flowers and receding horizon; `elevated_horizon_bands`: broad meadow/sky bands and off-center clusters. Meadow/grass/flowers/sky only. Meadow only. |
| `composition.mountain_view` | `telephoto_layers`: compressed ridge layers and distant summit; `wide_rock_foreground`: granite ledge, diagonal valley, wide distant peaks. Mountain/ridges/rock/valley only. Mountain only. |
| `lighting.time` | `morning`: forest/meadow texture; `daylight`: forest sun/shade; `sunrise`: mountain ridges above shaded valley; `sunset`: meadow and sky; `evening`: mountain rock/valley. Per-value scene and entity declarations bind all spatial language. Existing morning/sunrise/sunset/evening keys are reused; midday is a content slot, not a new recognized user qualifier. |
| `palette.natural` | `cool`: cool green/blue-gray shadows and pale highlights; `warm`: ochre/earth highlights with neutral shadows. Color treatment adds no object or text request. All three scenes. |

All thirteen closed values have explicit immutable slot annotations. Neither an
artistic label nor an empty key set grants immunity: exact release binding and
scene/value compatibility are required. Validation checks all positive, excluded
and conditional keys; content-local forbidden entities; required identity and
canonical keys; dynamic canonical user bans; one value per artistic dimension;
and conflicting time qualifiers. Artistic exclusions and conditional anatomy are
not admitted by this seed schema. All scenes declare final compatible human
absence and exclude people/anatomy, text marks, buildings/interiors and sea/beach
entities within this validation slice. These are not new global product policies.

Review ID: `sg01-stage1c-author-review-v1`. Declared by: **Codex implementation
author**. Basis: **`author_semantic_review`**. Source: original English literals
authored for this task, with the per-component checks above. Every fragment, scene
and variant references this immutable declaration; its evidence/limitations are
included in the pinned digest. This records the author's proposed semantic review,
not a claim that Claude Code or the Owner has already reviewed or accepted it.

## Six successful real-content previews

| Construction ID | Distinct composition | Lighting / palette | Source request |
|---|---|---|---|
| `forest_path.A` | Low camera beside ferns; deep curving path between trunks | Morning / cool | `No people; No mugs` |
| `forest_path.B` | Elevated oblique camera; diagonal path and layered crowns | Midday patches / warm | Same restrictions |
| `open_meadow.A` | Grass-level focused flowers; receding distant horizon | Morning / cool | Same restrictions |
| `open_meadow.B` | Elevated horizontal meadow/sky bands; off-center rhythm | Sunset / warm | Same restrictions |
| `mountain_view.A` | Telephoto panorama compressing ridge layers | Sunrise / cool | `Show mountains at sunrise; No people; No mugs` |
| `mountain_view.B` | Wide view with granite foreground and diagonal valley | Evening / warm | `Show mountains; No people; No mugs` |

The six literal final prompt oracles, including ordering and every separator,
are in `CASES`, `EXPECTED_SCENE`, `EXPECTED_BANS` and the positive-path tests.
They assert exact text rather than obtaining expected output from registry lookup.
Separate spatial oracles require the intended low/elevated or telephoto/wide
contrast. Identity, photo mode, fixed style, complete human/body/hands and mug
absences, system no-text and fragment/slot provenance survive every variation.

For mountain sunrise, canonical scene and qualifier facts both reference
`('user_text', 0)`, with spans `(5, 14)` and `(18, 25)`. The single sunrise fragment
has `origin='user_projection'`, exact `lighting.time` / `sunrise` selection, and that
same directive ref. Human exclusions reference directive 1; mug references 2;
system no-text has no user ref. Tests assert every fragment's origin/ref/selection,
all merged closure causes and exact ordering. No sunrise authority is inferred
from artistic prose or hashes.

## Stage 1B compatibility and unsupported coverage

The test-local bridge constructs a `SyntheticRegistry`, `SyntheticPolicy` and
explicit fake capability, then calls the actual unchanged Stage 1B factory,
preflight, assembly, final validation and artifact check. Its registry version is:

```text
sg01-nature-seed@1.0.0#a57ab2fbc218564c2ed00290cb8866a25e4a07009889442705990719ac007864
```

That version binds individual content versions and review evidence through the
release manifest. Stage 1B has no separate per-fragment-version or review fields:
tests reconstruct and verify the complete Stage 1C lookup alongside every final
fragment. This is explicit release-level binding, not a claim of new Stage 1B fields.

Stage 1B also cannot encode per-value/per-scene compatibility or all cross-fragment
time relationships. The bridge checks Stage 1C compatibility and projects only
scene-compatible exact closed values into its synthetic fixture. No Stage 1B
validation is bypassed or weakened. Required canonical projections are retained;
an identical optional lighting selection is omitted before construction to avoid
duplicating an already required sunrise fragment.

Every issued result remains exactly `SyntheticValidatedAssembly`,
`authority='synthetic_offline'`, `production_authorized=False`. No capability or
route is stored in the real content release. No conversion or dispatch API exists.

Unknown scenes/environments, styles, modes, aliases, IDs, versions and slot values
fail explicitly; there is no redirect to a seed scene. Other landscapes, interiors,
architecture, fixed styles, symbolic contexts and new scene identities are future
independent content registrations. The schema has no three-scene enum or limit;
a mechanical expansion test proves this without registering additional seed content.

Forest/meadow **user-language recognition is not implemented**. Their typed scene
identities are supplied explicitly in tests, while the existing interpreter retains
authority over source restrictions. `Show a forest path` remains unsupported in
the current bounded recognizer; it is not fabricated into a successful parsed
request. Other canonical positive subjects without faithful registered rendering,
arbitrary Custom Style, supplied symbolic nuance and free prose remain unsupported.
The conservative one-time-value contract can also reject otherwise reasonable
combined temporal wording; no runtime behavior is changed.

## Test coverage and execution evidence

Positive coverage asserts all six exact prompts, source semantics/provenance,
scene identities, independent perspective differences, complete mandatory bans,
no-text, spans, style/mode, manifest inventory and real Stage 1B validated artifacts.

Adversarial coverage includes substituted fragment/slot text; semantic annotation,
entity and review forgery; recomputed digests; same-ID/version substitution;
dangling review/scene/version/binding refs; unknown IDs/slots; incompatible scene
and lighting values; hidden object introductions in artistic components; nested
mutable/subclass/equality attacks; corruption after construction; changed final
separators/order/suffix/keys/refs; cross-release substitution; fake capability
claims; attempted synthetic promotion/reconstruction; terminal veto and fresh-process
plus static/dynamic-name import isolation. Mechanically consistent forged releases
are deliberately distinguished from the fixed seed identity; tests do not pretend
that an attacker cannot calculate hashes or author new unreviewed declarations.

Commands use default OS pytest temporary directories, `PYTHONDONTWRITEBYTECODE=1`
and disabled pytest cache. Logs are preserved outside the repository. No skips or
xfails are introduced. The existing unset `asyncio_default_fixture_loop_scope`
deprecation warning remains; configuration is not changed.

| Command | Executed result | Preserved log |
|---|---|---|
| `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_visual_registry_stage1c.py` | **106 passed in 2.89s**, exit 0; 0 failed/skipped/xfail | `C:/Users/eliv/AppData/Local/Temp/sg01-stage1c-targeted-e433d959dcf941b0b9c9a478e7176f2b.log` |
| `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_directive_segments_package_a.py tests/test_visual_intent_package_a.py tests/test_visual_safety_stage1a.py tests/test_visual_safety_stage1b.py` | **1,096 passed in 6.87s**, exit 0; 0 failed/skipped/xfail | `C:/Users/eliv/AppData/Local/Temp/sg01-stage1c-regressions-d42fee19a08a4548afc1ba5cdeca9171.log` |
| `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | **5,911 passed in 211.68s**, exit 0; 0 failed/skipped/xfail; **+106** against the Owner-supplied 5,805 baseline | `C:/Users/eliv/AppData/Local/Temp/sg01-stage1c-full-26492cd654504e8d89b2d6f4002ba6b3.log` |

All three test runs passed on their first execution; no failing oracle was weakened.
The four scoped Python files passed `ast.parse`; all five scoped files passed
trailing-whitespace checks. The full suite ran after the final Python edits; only
this implementation record was subsequently updated with completed evidence.

## Deferred dependencies and required closure points

None of the following obligations is closed by Stage 1C:

| Obligation | Required closure point |
|---|---|
| Stage 1B audit F-04: V0 source-kind/activity authority | Establish and independently review actual entry-point source authority before production integration. Content provenance cannot close this. |
| Stage 1B audit F-07: canonicality under subclassing/equality | Harden and independently review the existing evidence/gate contracts before production integration. New registry exact-type checks do not repair older contracts. |
| Stage 1A audit F-07: vocabulary/aliases reconciliation | Reconcile neutral and legacy vocabularies with reviewed hand-authored oracles before coherent consumer migration; no alias expansion here. |
| Stage 1A audit F-09: runtime registry equivalence/isolation | Complete consumer-equivalence, legacy-parser sentinel, transport identity and all-entry-point INT evidence before runtime activation. Current isolation is foundation-only. |
| Stage 1A audit F-10: `Attachment.frame_level` | Define supported meaning before any new consumer relies on it. No Stage 1C reliance. |
| Real provider capabilities/counters | Verify exact model/adapter/size contracts and complete-prompt counters before any dispatch activation. Unknown stays unverified. |
| Production route/policy registries | Separately authorize exact content coverage, selection rules and release governance before selecting real routes. O-1 alone is insufficient. |
| Non-bypassable dispatch | Implement and audit a distinct production-only artifact/transport boundary before provider integration; reject every synthetic artifact. |
| Attempt lifecycle; interactive/Profile/More, scheduled and CLI migration | Separately authorize coherent V0–V4 integration, early paid-call ordering, quota cleanup, attempt fencing, terminal scheduled states and CLI sibling cancellation before activation. |
| General controlled renderer | Separately scope faithful intent, style, scene and qualifier coverage before using the catalogue as a product renderer. Sample coverage is not product completeness. |
| Free-prose enrichment enforcement / FIX-03B-2B-2 | Complete its separate review work before claiming accepted-enrichment fidelity; any B standard requires its own explicit Owner approval before admission. |
| Arbitrary Custom Style fidelity | Require separately approved faithful handling before admission. No subset, approximation or silent omission is authorized. |
| Symbolic nuance | Require separately approved faithful nuance handling before admission; inactive notes do not become user-ban authority. |
| N-2 custom-photo fallback | Complete the separately deferred task before production deployment, preserving all four D0-R2 §10 restrictions and current fail-closed conflicts. |
| Unrelated FIX-03 and UX work | Separate task and Owner scope authorization before implementation; no closure claim here. |
| Material functionality/image-quality changes | Owner review under all eight O-1 conditions before activation. No live image-quality evidence is supplied. |
| Production deployment | Separate explicit Owner authorization, fresh verified backup and preserved rollback capability before any deployment. |

## Quality risks and acceptance status

Incorrect/incomplete author annotations remain possible. Mechanical compatibility
is conditional on those declarations; an unregistered sentence cannot become trusted
through a clean scan, an artistic label or a hash. Independent read-only semantic
review and explicit Owner acceptance are still necessary. The original source prose
and six hand-authored final prompts make this finite sample reviewable.

Photographic color/composition choices may produce unwanted images, insufficient
scene detail or provider noncompliance. Prompt diversity is demonstrated; final
image quality and pixel-level no-text/absence compliance are **not verified**.
No image was generated. Future activation can affect expressiveness, style fidelity,
fulfillment, fallback availability, latency and costs and needs separate review.

Mechanical implementation and offline acceptance tests are complete within the
five-file scope. **Claude Code independent audit: PENDING. Owner acceptance:
PENDING. Production authorization: NOT GRANTED.**

Implementation verdict: **READY FOR INDEPENDENT READ-ONLY AUDIT**.
