# SG-01 Stage 1A implementation record

Date: 2026-11-22. Scope: CODE + TESTS, NO GIT. Implementation awaits independent Claude Code read-only audit and Owner acceptance. Stage 1B has not started.

## Contracts and specification mapping

| Specification | Implemented in Stage 1A |
|---|---|
| Sections 3, 4.1; STR-01–06 | AR-01 retains original sources, scopes, directives, negative predicates and hard chunks. `DirectiveStructure` and `RelationEvidence` add vocabulary-independent nominal heads, render/conditional/unknown frames, coordinated complement ownership, relations and governing links. Invalid spans, local IDs, source links and cycles fail with `INVALID_EVIDENCE`. |
| Sections 3, 4.1–4.2, 8; VIS-01–10 | `VisualInterpretation`, `DirectiveClassification`, `NegativeAssessment`, derived `UnresolvedNegative` and `UnsupportedVisualRequest`. Poster/with/featuring, explicit mountain scenes, governed qualifiers, narrative ownership, source activity, unknown/long/local negatives and the existing custom nominal rule are represented. Semantic classification consumes AR-01 structure; no additional polarity parser was added. |
| Sections 4.2, 8; VIS-02–03, 15–16 | Exactly one negative assessment per negative directive, including zero recognitions and promoted legacy members. Closed legacy classification runs once per scope from its complete original hard chunk. Positive legacy coastal/sunset facts preserve original NEGATIVE structure and do not also emit coastal exclusions. Independent negative directives retain their own refs and precedence. |
| Sections 4.3, 5.1–5.2, 8; VIS-11–14 | `ResolvedVisualIntent`, `ResolvedFact`, `MandatoryBan`, `VisualConflict`; one closure owner in the new isolated layer; human/anatomy and coastal cascades; object conflicts; coastal exclusion precedence; existing mode-specific fixed-style conflicts. Canonical deduplication retains every supporting ref. No arbitrary count limit. |
| Sections 4.3, 5.1; VIS-14, 16 | Immutable evidence, source-local composite refs, checked derivable source/scope fields and deterministic resolution digests binding sources/activity, structure, classifications, ledger, derived views, style/mode, versions and the route slot. `ValidationResult`, `ValidationIssue`, `SafetyFailureData`, dedicated code-only `VisualSafetyFailure`. |
| Sections 2, 4.3, 6, 13 | Neutral `visual_semantics` owns the interpretation vocabulary, version identities and the existing coastal/style aliases, directions and incompatibility sets. Legacy modules re-export the same shared objects/function. The route record shape is declared, but no selection is performed. O-1 is recorded with all eight Owner conditions. |

`resolve_visual_intent`, `check_interpretation` and `require_valid_interpretation` are provider-free. An interpretation result uses the exact specified `allowed`/`blocked` outcome contract. Unsupported-only input is distinguishable through `disposition='unsupported'`, its retained classifications and `UNSUPPORTED_VISUAL_REQUEST`; unresolved negatives use `UNRESOLVED_EXCLUSION` with a closed detail. Mixed requests retain unsupported provenance and only independently eligible positive instructions. Any unresolved negative still blocks.

This is **interpretation validation**, not complete V1 preflight. `enforcement_route` remains `None` for every Stage 1A resolution, including an allowed interpretation. The digest is an integrity key, not a prompt certificate. No caller can use this implementation to certify or dispatch a prompt.

## Changed files

1. `services/directive_segments.py` — extend existing AR-01 structural evidence and integrity checks.
2. `services/visual_intent.py` — authoritative classifications, complete negative ledger, governed semantic facts and derived views; preserve evidence on conflicts.
3. `services/visual_safety_types.py` — new provider-free validation/failure contracts.
4. `services/visual_safety.py` — new isolated interpretation resolver, closure, conflicts, digest and deterministic validation.
5. `services/visual_semantics.py` — new neutral versioned interpretation data and existing shared style/coastal definitions.
6. `services/coastal_intent.py` — re-export moved constants and consume identical fixed compatibility sets; existing runtime scoper remains unchanged.
7. `services/ritual_config.py` — re-export the identical alias table and pure `normalize_style_key`; existing runtime routing remains unchanged.
8. `tests/test_visual_intent_package_a.py` — deliberate expectation migrations and the expanded isolation/dependency assertion.
9. `tests/test_visual_safety_stage1a.py` — new hand-authored structural, semantic, resolution, immutability and corruption oracles.
10. `docs/architecture/SG-01_Safety_Gate_Design_v1.md` — Owner O-1 decision, authorization boundary and current decision-status references.
11. `docs/architecture/SG-01_Stage1A_Implementation_Record.md` — this record.

No Git operation was used to determine or report this list.

## Deliberate Package A test migrations

Existing structural offsets, IDs and polarity oracles remain unchanged. Additional structure/attachment assertions, including `Море без пляжа` and opaque substitutions, are in the new test file. The old coarse kind for temporal relations is now equally conservative for `at sunrise` and an opaque nominal substitution; eligibility uses the richer frame evidence.

- `test_metamorphic_same_object_contradiction`, `test_hand_authored_contradiction_oracle` and the short-form branch of the long-negative oracle: interpretation no longer raises generic `ValueError`. Assert retained facts, resolver conflict keys/refs, typed `OBJECT_CONFLICT` and `VisualSafetyFailure` instead (sections 4.3, 5.1).
- Duplicate source identity: assert typed `INVALID_EVIDENCE` instead of generic `ValueError` (sections 4.1, 4.3).
- Six/seven-word and long-negative characterizations: preserve original fact/span assertions and add an explicit `UNRESOLVED_EXCLUSION / unsupported_structure` block. A seven-word ban cannot become permission for its conflicting positive (sections 4.2, 5.2).
- Qualified beach/sunset near misses in `test_c1_f_a1_reproductions`, `test_c1_metamorphic_repeated_negative_marker_insertion` and `test_c1_legacy_requires_complete_hard_chunk`: outside the exact approved hard chunk, retain structural negative evidence and assert unresolved local scope rather than representing a time-qualified ban as a global beach ban. The independent human/window/table instructions remain intact. Rationale: SG-D1 and the section 4.1 rule that unrepresentable negative qualifiers remain unresolved. This does not widen a legacy exception or change negative-list continuity.
- Isolation assertion: allow the new pure evidence/gate modules and neutral registry dependencies while still forbidding production imports of the Stage 1A structural/interpreter/resolver layer. Neutral data has no consumer/provider imports. This is deliberately narrower than the later production integration migration in section 11.

Existing tests were edited individually; no test expectations were generated from implementation output. All original 626 Package A test cases remain collected.

## Validation evidence

- Before editing: original Package A structural/semantic suites — **626 passed**.
- After the final code/test edits: structural/semantic/Stage 1A suites — **760 passed in 4.07s** (134 added cases).
- First full run, before the final defensive refinements — **5,459 passed in 189.76s**. Log: `C:/Users/eliv/AppData/Local/Temp/sg01-stage1a-full-c8248758dc494f6ca21196b24677ac5a.log`.
- Second full run, before the final negative-qualifier refinement — **5,466 passed in 183.03s**. Log: `C:/Users/eliv/AppData/Local/Temp/sg01-stage1a-final-d02892920e114f068fc44873665f0017.log`.
- Final full-suite verification after all code/test edits — **5,469 passed in 178.73s**, no failures, skips or xfails (**+134** against the Owner-supplied 5,335 baseline). Log: `C:/Users/eliv/AppData/Local/Temp/sg01-stage1a-verified-4768fe1a344440cbb9a34aa14c3b6736.log`.
- Syntax and trailing-whitespace checks passed for all nine changed Python files.

During development, the first expanded Package A run had 69 failures: generic-exception/isolation expectations, qualified-negative expectations, and two colon-scope regressions. The colon regressions were fixed; the incompatible expectations were deliberately migrated as listed above. An intermediate ownership refinement exposed an erroneous capture of preceding independent human/window list members by a later temporal relation; this was fixed without weakening their existing oracles. The new opaque-sunrise substitution oracle also exposed a coarse-kind vocabulary dependency, which was corrected. A final review added explicit unresolved treatment for unrepresented negative qualifiers (`No tropical beach`, `No sunrise`, `No ocean at sunrise`), rather than inventing a global ban or a negative qualifier renderer; exact legacy sunset remains the sole permitted exception. These development failures were resolved before the final targeted run; none was skipped or xfailed.

The test environment emits the pre-existing `pytest-asyncio` notice about unset `asyncio_default_fixture_loop_scope`. Configuration was not changed to suppress it.

Pytest used its default OS temporary directories. Full-run logs are outside the repository. No `.pytest_tmp_*` directory was created and no test/audit artifact was deleted. Existing test fixtures suppress dotenv loading, use fake provider credentials/offline mocks, and isolate database/output paths in OS temporary directories. No paid/live model call, migration or production database operation was performed.

## Deferred boundaries and remaining risks

- Bounded RU/EN grammar/vocabulary may conservatively block unsupported syntax. It is not general language understanding. Unsupported local relations and unknown negatives remain explicit blocks.
- Active Custom Style descriptions are interpreted for authoritative facts/exclusions here; an allowed interpretation does **not** establish fidelity or safe rendering of the remaining custom prose. That later enforcement boundary is deliberately unimplemented, with no new subset or omission policy.
- Route selection, approved policy registration, complete prompt-fragment semantics, capacity verification, Custom Style/mode enforcement, candidate reconciliation, final assembly certification and provider seals remain later work. No `check_preflight`, final validator or dispatch guard is exposed in Stage 1A.
- Existing production object/coastal parsers remain in place until a separately authorized coherent migration. The new closure/classification owner has no production caller. Static import-isolation assertions and the full regression suite protect this boundary; they do not claim the future gate is integrated.
- Independent Claude Code read-only audit and Owner acceptance remain required. N-2 and FIX-03B-2B-2 are untouched and deferred. Material functional/image-quality regressions require separate Owner review before activation under O-1.

Production generation behavior and configuration remain unchanged. Interactive handlers, scheduler, CLI, prompt construction, LLM enrichment selection, feature flags, paid-provider dispatch, environment configuration and database schema were not modified. There was no deployment, deployment artifact, Git command or Stage 1B work.

## CP-01 — targeted correction of SG-01-STAGE1A-REVIEW-01

Date: **2026-11-22**. Owner-authorized correction pass for **F-01 through F-06** following the independent audit verdict **REVISE BEFORE ACCEPTANCE**. These are implementation closure claims for targeted independent re-audit, not independent acceptance. Stage 1A remains isolated; Stage 1B and production integration are not authorized.

### Changes and finding closure

| Finding | Correction | Regression evidence |
|---|---|---|
| F-01 — negative coverage loss | A negative directive resolves only when all its recognized facts are eligible negative facts. Every assessment retains the complete recognition-index tuple. Validation rejects a resolved assessment with ineligible evidence or any assessment that omits a recognition. `No ocean beach` and `No mug table` retain both original facts, refs and spans, and block with `UNRESOLVED_EXCLUSION / unsupported_structure`; their unresolved scope creates no global bans. No object blacklist or polarity parser was added. | `test_cp01_f01_ineligible_negative_mentions_block_without_lost_coverage` (ordinary and active-custom sources); `test_cp01_f01_resolved_ledger_cannot_hide_ineligible_negative_facts`. Existing D1-A enumeration, normalization and both closed legacy-exception suites remain unchanged. |
| F-02 — relational negative mislabeled nonvisual | Narrative/nonvisual ownership starts at an established grammatical head and follows actual structural complement links. A narrative noun in a relation-dependent span cannot relabel a visual head. Both `No people in my report` and `Never show people in my report` now block with `UNRESOLVED_EXCLUSION / relational_scope`, retaining the human mention and relation evidence without a global human ban. A later narrative frame in the same command leaves preceding members ambiguous; it neither owns them as nonvisual content nor grants them independent visual authority. | `test_cp01_f02_visual_head_with_narrative_dependent_is_relational_exclusion`; `test_cp01_f02_narrative_head_does_not_own_unattached_list_members`; `test_cp01_f02_later_narrative_frame_keeps_mixed_command_ambiguous`; corrected `test_vis06_established_nonvisual_negative_is_observable`; all original Package A narrative insertion cases. |
| F-03 — dedicated-beach contextual compatibility | Verified the actual production predicate in `user_coastal_intent` and `coastal_style_conflict`: dedicated beach requires surviving beach subtype (including lagoon priority and subtype exclusions) plus tropical/palm wording and absence of the approved contextual terms. Moved the exact contextual regex into neutral `visual_semantics.COASTAL_CONTEXT`; production reuses that identical regex with unchanged matching behavior. Resolver/property use the shared pattern on authoritative, structurally positive nominal context, excluding negatives, detached negative-scope mentions, narrative/nonvisual heads, unsupported owned mentions, inactive notes and auxiliary text. `Tropical beach, urban city` is compatible with `urban_city_photo`; genuine dedicated-beach and interior/coast conflicts remain. | `test_cp01_f03_contextual_beach_compatibility_matches_fix03a` (12 RU/EN contexts × 3 styles); `test_cp01_f03_genuine_style_conflicts_still_match_fix03a`; `test_cp01_f03_dedicated_beach_requires_surviving_beach_subtype`; `test_cp01_f03_negative_and_narrative_context_cannot_waive_conflict`; `test_cp01_f03_inactive_and_auxiliary_context_cannot_waive_conflict`; extended registry-identity assertions. |
| F-04 — invalid evidence types | Interpretation validates input/record types before source, fact, classification and ledger field access. Structural validation checks source/scope/directive/structure/relation record types before traversing fields or forward links. Fact spans and composite refs are checked before comparisons or dictionary/set access. Malformed evidence takes the existing typed `INVALID_EVIDENCE` path; no broad exception suppression was added. | `test_cp01_f04_wrong_evidence_record_types_are_typed_failures`; `test_cp01_f04_noniterable_segmentation_input_is_typed_failure`; `test_cp01_f04_wrong_structural_record_types_are_typed_failures`; `test_cp01_f04_malformed_nested_spans_are_typed_failures`; `test_cp01_f04_malformed_refs_are_typed_failures`. |
| F-05 — custom-note activity | For every existing custom-note source, `source.active` must equal `requested_style == 'custom'`. Both mismatch directions reject the stale/inconsistent snapshot with typed `INVALID_EVIDENCE`. No requirement to supply a custom-note source was introduced. | `test_cp01_f05_custom_note_activity_must_match_requested_style`; `test_cp01_f05_consistent_note_activity_is_valid`; `test_cp01_f05_custom_style_does_not_require_a_note_source`. |
| F-06 — positive artifact with inline negative | Artifact-complement eligibility checks defer structurally linked negative children to their own negative ledger. Poster/mug positives retain eligibility and effective provenance while their unsupported local exclusions remain unresolved. The overall result stays blocked under SG-D1. Unknown essential positive artifact dependents are still unsupported. | `test_cp01_f06_positive_host_survives_unresolved_inline_exclusion` (poster/mug × people/logo), plus unchanged unknown-essential-artifact tests. |

### Changed files and expectation rationale

CP-01 changes exactly these files, reported without Git:

1. `services/directive_segments.py` — type-first evidence validation only; no segmentation/grammar changes.
2. `services/visual_intent.py` — complete negative coverage, head/complement ownership, artifact-negative-child handling and typed validation.
3. `services/visual_safety.py` — contextual FIX-03A compatibility and bidirectional custom-note activity invariant.
4. `services/visual_semantics.py` — the existing contextual regex as shared neutral semantic data; object/coastal aliases and version identities are unchanged.
5. `services/coastal_intent.py` — import/reuse the identical contextual regex; no production predicate, scoping, routing or matching behavior change.
6. `tests/test_visual_safety_stage1a.py` — 19 new named CP-01 tests (164 parameterized cases); two existing test functions deliberately updated as described below. The replacement/extension of the nonvisual controls adds two further collected cases, for **166** additional cases overall against the previous 5,469 baseline.
7. `docs/architecture/SG-01_Stage1A_Implementation_Record.md` — this CP-01 section.

`test_vis06_established_nonvisual_negative_is_observable` no longer treats `Never show people in my report` as established nonvisual input. That expectation contradicted SG-D1 because `people` is the visual head and `report` is only its relation-dependent noun. The case now has explicit blocked-result coverage under F-02. The legitimate controls `No time for my notebook`, `No report about mugs and windows` and `No time for my notebook and windows` remain; additional report-head controls cover `Never show a report about people`, `No report about people` and `No report about mugs, windows`.

`test_neutral_registry_reexports_preserve_existing_runtime_values` adds identity assertions for both fixed-style incompatibility sets and the shared contextual pattern. The new direct compatibility tests assert hand-authored compatible/incompatible outcomes against both real implementations; expected outcomes are not generated from either parser. Original Package A test files and their expectations are unchanged. Architecture specification changes are unnecessary: the existing negative-coverage invariant, SG-D1/SG-D2 and preservation of FIX-03A already require these corrections. Frozen D1-A, its two exact exceptions and O-1's eight Owner conditions are unchanged.

### CP-01 validation evidence

- Before corrections: original Package A plus Stage 1A — **760 passed in 6.66s**.
- Development verification after the core fixes: Package A plus Stage 1A — **918 passed in 4.90s**. The then-current targeted CP-01/control/registry selection — **163 passed, 129 deselected in 0.98s**.
- First full run, before the final registry/subtype refinements and additional defensive oracles — **5,627 passed in 178.95s**, exit 0. Log: `C:/Users/eliv/AppData/Local/Temp/sg01-stage1a-cp01-full-4339ecdf76ed45e98cbf2be6ac7bd22e.log`. This is intermediate evidence, not final-code certification.
- Final targeted command: `python -m pytest -q tests/test_visual_safety_stage1a.py -k 'cp01 or established_nonvisual_negative or neutral_registry_reexports'` — **171 passed, 129 deselected in 1.29s**. Deselection is the explicit targeted filter, not skipped/xfail cases.
- Final unchanged Package A command: `python -m pytest -q tests/test_directive_segments_package_a.py tests/test_visual_intent_package_a.py` — **626 passed in 3.24s**.
- Final full command after all code/test changes: `python -m pytest -q` — **5,635 passed in 173.82s**, exit 0, no failures, skips or xfails (**+166** against the previous developer-reported 5,469 baseline). Log: `C:/Users/eliv/AppData/Local/Temp/sg01-stage1a-cp01-final-2293bb2bb26f46afa3116037e5fee471.log`.
- Syntax and trailing-whitespace checks passed for all six changed Python files; the implementation record also passed the trailing-whitespace check.

All pytest runs use default OS temporary directories, without repository-local `--basetemp`. Full logs remain outside the repository and are preserved. No test/audit artifact is deleted.

Development checks exposed two incorrectly ordered expected recognitions in the new ocean/beach test; the hand-authored oracle was corrected to retain original match order. The first combined run also exposed 36 original Package A mixed-command cases that the initial ownership narrowing had overpromoted. The implementation was corrected to retain their ambiguity and existing ineligible-fact expectations, with explicit new blocked-negative coverage. No Package A expectation was weakened, skipped or regenerated.

### Remaining nonblocking obligations and isolation

- **F-07:** reconcile object/coastal vocabulary aliases before production migration. This pass does not migrate or broaden those vocabularies.
- **F-08:** document the public interpretation of `RequestClass` for negative/non-request directives before integration. CP-01 changes the negative ledger without redefining that public classification contract.
- **F-09:** improve isolation and registry-equivalence oracle coverage during integration. CP-01 adds directly relevant shared-registry identity and real FIX-03A compatibility assertions; broader integration coverage remains deferred.
- **F-10:** clarify unused `Attachment.frame_level` semantics before any consumer relies on that state; no such reliance is added here.

The existing static import/dependency isolation oracle remains in force. No handler, scheduler, CLI, provider dispatch, image-prompt construction, LLM enrichment selection, configuration flag, database or deployment workflow was connected to Stage 1A. The sole production-module edit reuses the same contextual regex from the neutral registry. An allowed interpretation still has `enforcement_route=None` and stage `interpretation`, with no dispatch authority. N-2, FIX-03B-2B-2, controlled routing and Stage 1B remain deferred. No Git commands, paid/live model calls, database resets or deployment were performed; no test/audit evidence was deleted.

**CP-01 is ready for targeted independent Claude Code read-only re-audit of F-01 through F-06.** Independent acceptance and Owner review remain outstanding; this statement grants no production activation, deployment or Stage 1B authorization.
