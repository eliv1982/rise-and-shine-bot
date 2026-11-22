# SG-01 Stage 1B — Implementation Record

Date: 2026-11-22. Task: **SG-01-STAGE1B-IMPLEMENTATION-01**.
Baseline `main` / `992d233` and Stage 1A closure are Owner-supplied; no Git command was used to verify them. The completed **SG-01 Stage 1B — Scope Lock Proposal** was supplied by the Owner in the task conversation after the initial missing-document blocker. It and the implementation task authorize the eight-file offline foundation below. Historical Stage 1A-only authorization statements in D0-R2 describe that earlier stage; no architecture rewrite is made here.

This is **not a production-certified Safety Gate**. There is no production route, content catalogue, model capability, transport seal or dispatch authority. Independent audit **SG-01-STAGE1B-REVIEW-01** returned **ACCEPT WITH MINOR NOTES**, with no BLOCKER or MAJOR findings. CP-02 addresses only F-01, F-02 and F-06 below; Owner acceptance remains outstanding. No next phase is authorized by this record.

## Frozen scope and specification mapping

| D0-R2 requirement | Stage 1B implementation | Explicit boundary |
|---|---|---|
| §3, §4.1–4.2, §4.3: authoritative derivation and identity | Re-run original AR-01 segmentation from retained sources; compare structure; re-run the existing semantic interpreter; compare all facts, classifications and negative assessments. Re-run the existing resolver and compare the entire resolution, including its digest. | No new grammar, recognizer, alias, interpretation policy or closure rule. |
| §4.3, §5.1, §7 V1, §13 O-1 | Gate-owned route selected once, only after canonical interpretation is allowed. Preflight checks request, authority, representation, restrictions and capabilities; any veto is terminal for the attempt. | Only explicit synthetic policy inputs. No production policy or runtime route selection. |
| §4 immutability, §6 fragments and candidate | Frozen, slotted typed records; tuple/frozenset containers; exact registry IDs, closed slot values, semantic metadata and source refs. | Fixture data resides in tests. No arbitrary prose admission, scanner-based trust or general production renderer. |
| §4.3, §6 reconciliation | Existing closure owner reused for user bans, registered style constraints, finalized human absence and system no-text. Complete causes and supporting refs retained. | Soft scene defaults remain distinct from user-authoritative bans. |
| §5.2 capacity, §6 serialization and final validation | Exact LF serialization and spans; canonical candidate reconstruction; complete prompt measurement; model/adapter/size and policy/registry/capability checks; assembly digest. | Only synthetic codepoint/UTF-8 capabilities. Tokens and unknown counters fail closed. No external provider capacity is asserted. |
| §6 gate-owned validated artifact | Only the exact `SyntheticValidatedAssembly` issued by the corresponding gate can pass its `check_artifact`, subject to integrity/final rechecks. Direct construction with `_FACTORY_KEY` grants no accepted authority. | This explicitly synthetic type implements the offline portion of the proposed validated-artifact contract. No generic production `ValidatedAssembly` or provider consumer is introduced. |
| §8, §11 deterministic oracles | Actual successful assembly and adversarial mutation tests; all Package A/Stage 1A/CP-01 behavior retained. | Runtime INT-01–16 and image quality certification remain future integration work. |
| §9.1–9.3 Custom Style and untrusted prose | Explicit refusal where faithful representation/enforcement has no approved contract. | No Custom Style subset, approximation, symbolic nuance omission policy, B standard or enrichment shutdown. |

## Exact changed files

Reported from performed edits, without Git:

1. `services/visual_intent.py`: split shape validation from authority verification; canonical structural and semantic re-derivation; F-08 documentation. `interpret_directives` still uses the original semantic algorithm. Construction performs shape validation without recursive authority checks.
2. `services/visual_safety.py`: complete resolution comparison; offline attempt owner; preflight, controlled candidate construction, single-owner assembly constraints, exact serialization, final validation and synthetic artifact factory/check.
3. `services/visual_safety_types.py`: stage-correct failure enforcement; immutable fragment/provenance/capacity contracts and supporting type checks.
4. `services/visual_semantics.py`: neutral immutable registry, slot, projection, context, synthetic policy and capability contract **types**. Existing constants, aliases and version strings are unchanged. No fixture approvals or real rendering data are installed.
5. `tests/test_visual_safety_stage1a.py`: legacy-basis instrumentation now measures one direct interpretation pass, rather than construction plus the newly required independent verification passes. The expected complete-scope inputs are unchanged.
6. `tests/test_visual_intent_package_a.py`: isolation oracle permits only the neutral registry's new `dataclasses` and `visual_safety_types` dependencies. Production import isolation remains required.
7. `tests/test_visual_safety_stage1b.py`: synthetic exact registry/policy/capability fixtures and hand-authored successful/adversarial oracles.
8. `docs/architecture/SG-01_Stage1B_Implementation_Record.md`: this record.

No handler, scheduler, CLI, prompt builder, provider, environment/configuration file, database schema or deployment file was edited.

## Derivation, policy and trust ownership

`directive_segments.segment_directives` remains the structural owner. `visual_intent.interpret_directives` remains the semantic/classification/negative-ledger owner. `validate_interpretation` validates shape, compares segmentation against the same structural owner, and compares semantic records against the same interpreter. Its derived views remain read-only properties of the authoritative ledger/classifications.

`resolve_visual_intent` remains the only interpretation-level fact, precedence and conflict derivation. `check_interpretation` reconstructs that result and compares all fields. Merely recomputing `_digest` cannot validate injected facts, hidden negatives, missing closure, forged refs, altered fact indices, deleted conflicts, changed causes/dispositions or unknown versions. Stage 1A default calls continue to return `enforcement_route=None` and interpretation-stage verdicts.

`_closure` remains the single closure rule definition for this isolated layer. `_assembly_bans` applies it to assembly-specific style/system/scene seeds and merges existing user provenance. Scene-none/style causes do not acquire user refs; combined causes retain every original user ref. The existing runtime parsers remain isolated and unchanged.

The synthetic gate owns one immutable registry/policy/context/capability snapshot and one route. Its route input digest includes the canonical pre-route resolution, synthetic authority digest, context, model, adapter and size. The completed resolution digest includes that route. The existing interpretation policy/vocabulary/registry versions remain in the resolution; synthetic content-policy/registry versions and capability records are additionally bound in the route input, preflight receipt and final assembly. They are distinct authorities, not replacements for the frozen interpretation registry.

Preflight issues an immutable receipt. Final validation requires the exact receipt from the same gate, not merely equal fields or an `allowed` result supplied by a caller. A new source/style/mode, route, policy, model or capability cannot reuse that attempt. A veto prevents subsequent assembly, validation or route recovery within it. An explicitly new gate is a new attempt; the offline foundation does not enforce application-wide attempt lifecycles.

## Supported offline construction

`create_synthetic_gate` is an explicitly synthetic harness. The registry's exact fragments and finite slot options determine text and semantic metadata; selectors cannot supply replacement text. Canonical effective facts determine user projections and exact refs. Context/style requirements, reconciled presence, all mandatory bans and the universal no-text key determine the remaining required content.

The deterministic order is context fragments, reconciled presence fragments, required projections in key order, compatible optional registered selections, canonical exclusions in key order, then system no-text. One LF separates fragments. There is no untracked prefix or suffix. The entire prompt and its fragment spans are rebuilt and compared during final validation. Required-fragment deletion reports missing-fact or missing-exclusion coverage as well as invalid assembly; asserted key metadata cannot repair it.

`FragmentProvenance.slot_value: str | None = None` is an intentional immutable extension of the D0-R2 provenance record for closed-slot provenance. It retains the selected registered `ClosedSlotValue.value_id` alongside the registry identity/version and source refs; fragments without a slot retain `None`. Candidate construction derives it from the registered selection, and final reconstruction checks it with the complete provenance. It does not admit arbitrary slot text or create a new authority source.

Supported synthetic contexts include registered illustration/photo/symbolic identities without unrepresented style prose, object/artifact/scene projections, finite qualifier slots, represented global object/coastal bans, frozen coastal precedence and compatible presence variants. Qualifier slots cannot claim two incompatible values. Soft avoids yield to essential positive facts before finalization. Registered optional person/hands defaults can yield to a compatible registered none variant when mandatory restrictions require it; a fixed context without that variant blocks. The scene enum's required positive metadata must be present. Context/optional fragments cannot smuggle additional unowned mandatory exclusions outside the canonical ban derivation. Missing representations fail; no essential fact, qualifier, negative ledger entry or provenance ref is clipped to fit capacity.

Untrusted text cannot enter through themes, cleaned/paraphrased text, Custom Style, LLM enrichment, generated plans, raw overrides, emotional focus, false origin labels, arbitrary slot values, trace strings, fragment IDs or forged key sets. A descriptive trace is retained as metadata only and does not alter trust. Arbitrary ordinary themes without explicit visual requests retain disposition `none`; only registered defaults and canonical eligible projections enter the synthetic prompt.

Unsupported contexts include local/unknown/unsupported negatives, unsupported-only positive render requests, hard conflicts, missing policy/fragment/slot/intent coverage, unknown capabilities, unknown counters, unknown adapter/model/size combinations, and unrepresentable Custom Style/nuance. Mixed positive requests retain unsupported records but render only independently eligible facts. An unresolved active negative blocks independently of `RequestClass`.

## Final validation and artifact integrity

The real final validator re-verifies canonical resolution derivation and gate bindings, then reconstructs the expected candidate from exact registered selections. It checks candidate scene, presence, style/mode, fragments and complete provenance; all mandatory bans and causes; exact serialization, ordering and spans; the entire prompt; route identity; both policy/registry authorities; capability evidence, counter, model, adapter and size; and final assembly integrity. Mechanical final issues have deterministic ordering.

Capacity measurement counts the complete Unicode prompt including all LF delimiters, absences and any attempted extra suffix. The only implemented counters are versioned Python codepoint length and UTF-8 byte length. A capability must match the gate-owned synthetic registration; an evidence-reference string supplied with a changed capacity is insufficient. Overflow is refusal, never truncation. Known minimum overflow is detected in preflight; optional-fragment overflow is detected in final validation.

`validate_final_assembly` on a gate issues and retains its `SyntheticValidatedAssembly` as `_issued`. The artifact retains the exact immutable assembly, allowed final result and complete assembly digest. Direct object construction is possible by invoking the constructor with private `_FACTORY_KEY`; it does not register that object as issued. Only the exact artifact issued by the corresponding gate can pass its `check_artifact`, which requires `artifact is self._issued` and repeats integrity/final checks. An equal directly constructed wrapper, copied receipt, equal-but-reconstructed route, old gate or recomputed hash has no accepted authority. The CP-02 adversarial oracle constructs an equal wrapper with `_FACTORY_KEY` and verifies final-stage `STALE_VALIDATION` rejection after confirming the issued artifact passes.

These are internal API integrity boundaries. Hostile Python code that rewrites private module state or deliberately invokes private factory internals is outside this trust model, as in D0-R2 §6. The digest is an integrity key, not a semantic proof, signature or transport authorization.

## Strict synthetic/production separation

All synthetic fragment text, semantic annotations, policies and capabilities live in `tests/test_visual_safety_stage1b.py`. Runtime modules contain contract definitions and mechanics only. Caller-provided registry data can produce only the explicitly named **synthetic** result through the explicitly synthetic harness. There is no default production policy, configuration loader, feature flag or environment override.

`SyntheticValidatedAssembly.authority == 'synthetic_offline'` and `production_authorized is False` are read-only properties. There is no production artifact type, dispatch token or provider method to invoke. A successful `ValidationResult` is a validation observation, not dispatch permission. Any future provider boundary must require its separately authorized production-only artifact type and reject this synthetic type; no conversion/admission API is supplied here. Tests exercise environment-flag, descriptive-label, reconstruction and cross-attempt attacks without granting production authority.

Successful tests establish mechanics under hand-authored fixture contracts. They do not approve those literals as product rendering, verify real provider capacities, prove arbitrary natural-language compliance, enforce non-bypassable future provider transport or guarantee image pixels.

## Compatibility and deferred findings

- **FIX-03A, D1-A, SG-D1, SG-D2, CP-01:** existing outcomes remain. Both exact legacy chunks preserve negative structure and positive coastal exception facts; near misses do not gain authority. Independent coastal exclusions retain precedence and conflict provenance. Relational exclusions never become global bans.
- **F-07:** vocabulary reconciliation remains deferred to coherent runtime migration. No additional recognizer, alias expansion or alternate raw-text polarity parser is introduced.
- **F-08:** clarified without enum/behavior changes. `eligible` may classify a supported negative. `nonvisual` as a directive/non-request classification does not waive an unresolved negative assessment. Preflight uses the ledger and canonical resolver verdict.
- **F-09:** new literal alias/compatibility/registry expectations, derivation corruption tests, neutral dependency checks and retained production-isolation oracle cover the foundation. Real runtime equivalence, legacy-parser sentinels, transport identity and all-entry-point certification remain integration obligations.
- **F-10:** structural attachment behavior/enum is unchanged. `frame_level` grants no new authority; an attempted relabeling neither globalizes a relational exclusion nor bypasses canonical structural verification. Define its supported meaning before any future consumer relies on it.

The following IDs refer specifically to **SG-01-STAGE1B-REVIEW-01**, independently of the earlier finding IDs above. Both are **required security review items before production integration**, deferred and unimplemented in CP-02:

- **F-07 — `isinstance`/`__eq__` canonicality hardening:** review canonicality checks that accept subclasses or rely on caller-controlled equality, and define the required hardening before production integration.
- **F-04 — V0 source-kind authority:** review how source-kind authority is established and verified at V0 before production integration.

## CP-02 correction scope

- **F-01:** corrected factory/issuance authority wording and added one adversarial direct-construction oracle using `_FACTORY_KEY`.
- **F-02:** parenthesized the symbolic-mode/notes conjunction in the custom/symbolic veto; evaluation order and behavior are unchanged. Existing tests are preserved.
- **F-06:** documented the intentional immutable `FragmentProvenance.slot_value` extension for closed-slot provenance; no type or behavior change.
- Only `services/visual_safety.py`, `tests/test_visual_safety_stage1b.py` and this record are modified in CP-02. The earlier eight-file list describes the original Stage 1B implementation. No deferred security hardening or new architecture audit is included.

## Validation evidence

**CP-02 (2026-11-22):**

- Targeted command: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_directive_segments_package_a.py tests/test_visual_intent_package_a.py tests/test_visual_safety_stage1a.py tests/test_visual_safety_stage1b.py` — **1,096 passed in 5.65s**, exit 0, 0 failed/skipped/xfail. This includes 170 Stage 1B cases and 926 existing Package A/Stage 1A cases. Preserved log: `C:/Users/eliv/AppData/Local/Temp/sg01-stage1b-cp02-targeted-0bbce322483743e987f2c2d28629dbc8.log`.
- Full offline command: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` — **5,805 passed in 179.26s**, exit 0, 0 failed/skipped/xfail; exactly one additional case relative to the original 5,804-case Stage 1B result. Preserved log: `C:/Users/eliv/AppData/Local/Temp/sg01-stage1b-cp02-full-4938a2d05e814a2f8703052d0f304fb3.log`.
- Service AST comparison before/after is identical; all 58 existing Stage 1B test functions are unchanged, with exactly one new adversarial test function. Syntax parsing and trailing-whitespace checks pass for the permitted files as applicable.
- Both runs use the default OS temporary directory, with `PYTHONDONTWRITEBYTECODE=1` and pytest's cache provider disabled. Logs and test artifacts are preserved; no agent cleanup was performed. No unexpected behavior or regressions were observed. The pre-existing unset `asyncio_default_fixture_loop_scope` deprecation warning remains.

**Original Stage 1B implementation history:**

- Before modifications: Package A structure/semantics and Stage 1A — **926 passed in 4.70s**, 0 failed, 0 skipped.
- Initial expanded focused run — **1 failed, 1,036 passed**. A purported span mutation repeated the original `(7, 10)` span. The test was corrected to alter the span; no implementation acceptance behavior was weakened.
- Intermediate focused verification — **1,037 passed in 7.96s**, 0 failed, 0 skipped.
- Additional adversarial coverage development — **1 failed, 156 passed** in the Stage 1B file. The purported effective-index mutation repeated the canonical mug index. The test was corrected to mutate the table record's index, with an explicit hand-authored ordering explanation.
- Expanded focused command: `.venv/Scripts/python.exe -m pytest -q tests/test_directive_segments_package_a.py tests/test_visual_intent_package_a.py tests/test_visual_safety_stage1a.py tests/test_visual_safety_stage1b.py` — **1,083 passed in 6.73s**, 0 failed, 0 skipped. Log: `C:/Users/eliv/AppData/Local/Temp/sg01-stage1b-focused-3590670780c143ac8974231b52e810e4.log`.
- Further defensive review added bidirectional soft human-default reconciliation, presence-enum semantic checks, rejection of unowned mandatory exclusion metadata and explicit final missing-fragment reasons. Refined focused verification — **1,091 passed in 6.96s**. Log: `C:/Users/eliv/AppData/Local/Temp/sg01-stage1b-refined-focused-eca4b15a7dd94073b1fa45aa6a510a81.log`.
- Final focused command after all Python changes: `.venv/Scripts/python.exe -m pytest -q tests/test_directive_segments_package_a.py tests/test_visual_intent_package_a.py tests/test_visual_safety_stage1a.py tests/test_visual_safety_stage1b.py` — **1,095 passed in 5.77s**, 0 failed, 0 skipped/xfail. Stage 1B adds **169** cases; original Package A/Stage 1A contributes **926** unchanged collected cases. Log: `C:/Users/eliv/AppData/Local/Temp/sg01-stage1b-final-focused-38ba01cd2e304fc0be3845093c578720.log`.
- Intermediate full offline command `.venv/Scripts/python.exe -m pytest -q` started before the final refinements — **5,792 passed in 401.69s**, exit 0, 0 failed, 0 skipped/xfail. It is not final-code certification. Preserved log: `C:/Users/eliv/AppData/Local/Temp/sg01-stage1b-full-12db817743f14cc789fc70ceec6931a4.log`.
- Final full offline command after all Python changes: `.venv/Scripts/python.exe -m pytest -q --basetemp C:/Users/eliv/AppData/Local/Temp/sg01-stage1b-final-tests-3cb0eca11a0f40c2b8e954f82f9463e3` — **5,804 passed in 350.78s**, exit 0, **0 failed, 0 skipped, 0 xfailed**. This is **+169** against the Owner-supplied Stage 1A/CP-01 full baseline of 5,635. No unrelated failing tests were observed. Preserved final log: `C:/Users/eliv/AppData/Local/Temp/sg01-stage1b-final-full-654b034b398b4b27a5bd18e80c826460.log`. The absolute OS-temporary test directory is separate from the intermediate full process's default pytest directory; both were preserved without agent cleanup.
- Final syntax parsing passed for all **7** changed Python files. Trailing-whitespace verification passed for those files and this record. A clean-process import of `services.visual_safety` loaded none of `config`, `database`, `aiohttp`, `requests`, `openai_image`, `yandex_gpt`, `scene_planner`, `coastal_intent` or `ritual_config`.

Focused/intermediate pytest runs use default OS temporary directories. The concurrent final full run uses a fresh absolute OS-temporary `--basetemp` derived from `System.IO.Path.GetTempPath()` plus a GUID, ensuring separate artifacts. Logs and test evidence are preserved outside the repository. No `.pytest_tmp_*` directory is created and no test/audit evidence is deleted by agent cleanup. Existing offline fixtures disable dotenv loading, use fake credentials/mocked providers and isolate databases/output in OS temporary directories. The pre-existing `pytest-asyncio` unset-loop-scope warning is not suppressed by configuration changes.

## Product implications and subsequent decisions

There is no operational product change because runtime consumers remain disconnected. Future activation could change variety, composition, theme expressiveness, successful fulfillment, Custom Style fidelity, symbolic nuance, fallback availability and enrichment use. Refusal is reduced fulfillment, not equivalent to successful preservation. This stage provides no paid-provider/image-quality evidence or runtime cost/latency guarantee.

Ordinary active Custom Style has no approved faithful renderer/subset here and is explicitly refused, including descriptions without bans and descriptions whose exclusions alone were recognized. Registered symbolic construction without supplied nuance can succeed only synthetically; unrepresented supplied custom-note nuance is explicitly refused even when the note is inactive for user-ban authority. No generic preset substitution, prose paraphrasing, nuance omission or blanket enrichment shutdown is activated.

Before runtime integration or activation, separately authorize and review actual production route rules, exact rendering/slot/style content and fidelity coverage; verify real adapter/model capacities/counters; reconcile F-07; complete runtime F-09/INT obligations; decide any proposed B standard or Custom Style/nuance policy; assess material functionality/image-quality regressions under all eight O-1 conditions; and complete the separately deferred N-2 task before production deployment. A fresh verified backup and rollback capability remain required before any separately authorized deployment.

Explicitly unimplemented: production entry-point preflight ordering, quota/reservation cleanup, scheduler terminal writes/fencing, CLI sibling cancellation, safety-catch/fallback migration, metadata identity, provider transport guards/retry seals, production authorization storage, real capability registration, database migrations, deployment and paid model calls. No claim of their completion follows from an offline success.

Residual risks include bounded Stage 1A grammar/vocabulary, incorrect/incomplete future reviewed registry annotations, absence of general NL or pixel compliance proof, same-process trusted-code assumptions, and future consumer misuse unless its exact production-only boundary is independently implemented/audited. Foundation tests do not waive these obligations.

The original independent audit result is recorded above. CP-02 remains limited to the authorized corrections and offline regression verification; it does not claim Owner acceptance, production authorization or permission to start the next phase. No Git command, deployment, production database operation, live/paid model call, new architecture audit, or inspection/modification of repository `tmp/` was performed.
