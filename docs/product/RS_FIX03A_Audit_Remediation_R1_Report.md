# FIX-03A / Audit Remediation R1

Date: 2026-11-19. Scope: the confirmed FIX-03A findings F1–F11. No FIX-03B–03E implementation.

The Frozen Specification was preserved byte for byte. Its SHA-256 before and after R1 is `b8d576bfd87472188f1664db595d6e35c3d1debbe66992e483023f312ea784eb`.

## Closure matrix: cause, correction and evidence

Test names below refer to `tests/test_coastal_audit_remediation.py` unless another file is named. The new regressions run real intent parsing, prompt construction, handlers, text request serialization, image generation serialization and history persistence. HTTP transport, provider configuration, test settings and Telegram are replaced; the logic being checked is not stubbed.

| Finding | Status | Root cause and correction | Deterministic evidence |
| --- | --- | --- | --- |
| F1 — negation scope | Implemented | The first negation governed all following coastal subjects in a clause. A small RU/EN scanner now scopes `no`/`without`/`без` at commas, retains coordinated exclusions, supports coastal `avoid` lists across commas, and ends exclusions at explicit positive directives. Exclusions still have priority across the complete applicable request. | `test_f1_negation_scope_and_coordinated_exclusions` and `test_f1_f5_actual_payload_scope_and_exclusion_clauses`: all supplied examples, negative lists, conflicting positives, `do not include`, contractions and Russian plural directives. Manual/More payload tests cover the four original generic-negative failures. |
| F2 — Russian morphology | Implemented | The noun regex admitted the verb `береги`. The noun forms exclude `берегу себя`, `береги себя`, `Береги себя` and `берегите себя`; genuine noun cases, contextual `на берегу`/`к берегу`, and inflected rocky-shore phrases remain recognized. | `test_f2_verbs_and_word_boundaries`, `test_f2_shoreline_nouns`. |
| F3 — controlled scene identity | Implemented | Disabling secondary photo augmentation also cleared scene identity, and history consumers only read preset fields. Controlled prompts retain their anchored `Scene type` as `scene_type` and the compatible legacy `scene_preset`; `photo_scene_preset` stays null because no secondary preset was applied. Archetypes follow the actual scene. History uses the final API prompt and actual scene; recent history does not count a different shadow plan as a second generated scene when actual identity is available. Legacy field fallbacks remain readable. | `test_f3_controlled_noncoastal_scene_with_automatic_coastal_style`: forest and workspace with auto-resolved coastal style, actual mocked image payload, sidecar metadata, real SQLite history and memory. `test_f3_legacy_history_remains_readable`; manual/More and scheduled/More history tests. |
| F4 — invented beach preference | Implemented | `rocky` exclusion selected the complementary `beach` subtype. Subtypes now follow supported positive mentions; an ocean with an excluded shore subtype falls back to water/horizon rather than inventing another shore preference. | `test_f4_f5_no_invented_positive_scene`, including `Ocean view, no rocky coast` through controlled, template and enriched paths. Tests check scoped exclusions and positive scene content. |
| F5 — mixed directives | Implemented | Complete mixed expressions were inserted into positive coastal requests, theme/style prose and controlled emotional focus. Positive spans are now separated from exclusion spans; contradictory coastal spans are filtered using exclusions from both applicable sources. Enrichment receives separately scoped context and retains coastal exclusion clauses. | `test_f1_f5_actual_payload_scope_and_exclusion_clauses`, `test_f4_f5_no_invented_positive_scene`, existing `test_effective_final_image_api_prompt` and enrichment-drift regressions in `test_coastal_intent_integrity.py`. |
| F6 — style/sphere conflicts | Implemented for the confirmed cases | Sphere safety prose also imposed workspace/interior scenes, automatic framing could require an interior, and incompatible explicit styles were not checked. Explicit coast now takes priority over automatic sphere/style/composition recommendations. Compatible selected styles retain their identity. Clearly incompatible explicit interior/reading/botanical/mandala combinations use the existing localized preflight and style-selection recovery; they are not silently replaced. Enriched prompts that put an explicit coast inside a desk/interior scene use the local template fallback without another model call. | `test_f6_sphere_cannot_override_compatible_explicit_coast`: Career/Money, auto/Living Nature/Sunny Morning/Sea Coast, all three prompt paths. `test_f6_enrichment_cannot_turn_an_explicit_coast_into_an_interior`: photo and illustration. `test_f6_f10_handler_conflicts_before_paid_generation`. |
| F7 — coastal beach defaults | Implemented | Generic anti-cliche `beach` was only removed when a selected subject already spelled out beach. It is now removed for selected coastal families, including lagoon/dunes/rocky/water scenes. Explicit current-user exclusions remain separate and authoritative. | `test_f7_coastal_families_have_no_generic_beach_ban`; tropical/palm/lagoon payload cases in `test_coastal_intent_integrity.py`; mixed-input payload regressions assert explicit `no beach`, `no sandy beach` and `no rocky coast`. |
| F8 — diagnostic sourcing | Implemented | `coastal_hint_detected` OR-ed theme and custom notes regardless of selected style or conflicting exclusions. It now uses the same `user_coastal_intent` calculation and selected-style scope as generation. Other metadata fields retain their existing behavior. | `test_f8_handler_diagnostics_use_applicable_context`: inactive notes, active custom notes, exclusions across both sources and a generic-negative positive request. |
| F9 — coverage gaps | Implemented | Prior coverage missed generic-negative scoping, imperatives, controlled identity with automatic coast, real conflict preflight, Profile and subscription More. R1 adds parameterized regressions at HTTP/provider boundaries while retaining the real tested logic and DB history. | 217 new tests. Manual → More, Profile → More with preference reread and illustration mode, scheduled → subscription More, independent UI/content languages, actual exclusion clauses, actual final prompts, recovery and cancellation. |
| F10 — conflict before paid work | Implemented | Explicit coastal style plus `No ocean` failed at image generation after paid text generation. The existing preflight now rejects clear conflicts; `_run_generation` also checks direct/repeated calls before reservation and paid planner/text work. Recovery presents the existing style keyboard, preserves the request for reselection, and keeps the existing Main Menu cancellation path. Billing/reservation contracts are unchanged. | `test_f6_f10_handler_conflicts_before_paid_generation`: RU/EN and preflight/direct/More, zero text/image HTTP calls, zero quota usage and no generation history. `test_f10_existing_style_reselection_recovers_without_spending_on_conflict`; `test_f10_existing_reservation_cleanup_with_real_transport_boundary` covers cancellation during text transport and failed Telegram delivery. |
| F11 — complete verification | Verification PASS; process exception disclosed | The earlier 1,179 result was a subset. Complete repository verification was executed without test-path filters or deselection: 2,482 collected/passed, 0 failed/skipped/errors. | Full pytest log and JUnit XML. The process exception concerning the two initial Git reads is disclosed separately below. |

## Exact R1 files and functions

This list describes this remediation relative to the source snapshot taken before R1 edits. It does not attribute earlier FIX-03A workspace changes to R1.

| File | Changed or added functions / definitions |
| --- | --- |
| `services/coastal_intent.py` | `_SHORE`, `_SUBJECT`, `_NEGATION`, `_SCOPE_MARKER`, `_LIST_NEGATION`; replaces `_CLAUSE_BREAK`; adds `_scoped_fragments`, `user_scene_prompt_parts`, `coastal_style_conflict`, `coastal_composition_hint`; changes `CoastalIntent.subtype`, `parse_coastal_text`, `coastal_request_text`, `coastal_photo_style` (optional visual-mode argument). |
| `services/openai_image.py` | `_avoid_literal_symbols_clause`, `_build_photo_prompt`, `_build_image_prompt`, `generate_image`. |
| `services/scene_planner.py` | `normalize_scene_plan`, `apply_coastal_scene_intent`. |
| `services/scene_prompt_builder.py` | `build_controlled_scene_prompt`. |
| `services/generation_history.py` | `build_visual_motifs`. |
| `services/visual_memory.py` | `_extract_scene_types_from_visual` (actual-scene precedence; legacy fallback decoding retained). |
| `services/yandex_gpt.py` | `build_enriched_image_prompt` only; affirmation/text-language generation contracts are unchanged. |
| `handlers/generation.py` | `_generation_preflight_error`, `_answer_generation_preflight_error`, `_start_generation_after_preflight`, `_run_generation`, `again_affirmation`; removes unused imports associated with secondary preset selection. |
| `handlers/generation_formatting.py` | `update_image_meta` (only `coastal_hint_detected` calculation). |
| `handlers/generation_messages.py` | Adds localized `scene_style_conflict_text`. |
| `scheduler.py` | `_deliver_subscription` (controlled-preset metadata and effective prompt/scene history only); removes unused secondary-preset selector import. |
| `tests/test_coastal_audit_remediation.py` | New: 217 parameterized tests across negation, morphology, final payloads, metadata/history, style conflicts, diagnostics and generation paths. |
| `tests/test_coastal_intent_integrity.py` | `test_mixed`, `test_effective_final_image_api_prompt`, `test_enrichment_rejects_coastal_intent_drift_at_final_api`: removes requirements to invent rocky scenery for generic ocean requests, and checks controlled workspace identity directly rather than relying on a sphere-inserted workspace directive. |
| `tests/test_openai_image.py` | `test_custom_style_coastal_text_does_not_force_deterministic_coastal_routing`: inactive custom notes must not be appended to the final prompt. |
| `tests/test_visual_memory.py` | Replaces the shadow-inclusive expectation with `test_visual_memory_actual_scene_takes_priority_over_planned_metadata`. Count unchanged. |
| `docs/product/RS_FIX03A_Audit_Remediation_R1_Report.md` | This report. |

`services/ritual_config.py`, the Frozen Specification, database schema, requirements, model configuration and FIX-04 language ownership were not edited in R1.

## Verification and collection reconciliation

Final full-suite result: **PASS**, pytest exit code **0**, **110.55 seconds** wall time reported by pytest.

| Metric | Exact count |
| --- | ---: |
| Collected | 2,482 |
| Passed | 2,482 |
| Failed | 0 |
| Skipped | 0 |
| Errors (collection/setup/teardown) | 0 |
| Deselected | 0 |

JUnit independently reports `tests="2482"`, `errors="0"`, `failures="0"`, `skipped="0"`. It contains 217 cases from the new R1 regression module.

Commands/evidence:

- Before R1: `.\.venv\Scripts\python.exe -X utf8 -m pytest --collect-only -q` — **2,265 collected**; saved as `tmp/fix03a_r1/collection_before.txt`.
- Focused prompt/history regression run before the final boundary additions — **358 passed**; `tmp/fix03a_r1/targeted_new3.txt`.
- First complete suite before the additional negation/enrichment boundary tests — **2,462 passed**, 0 failures/skips/errors, 111.40 seconds; `tmp/fix03a_r1/full_suite.txt` and `full_suite.xml`.
- Final R1 regression module — **217 passed**, 11.17 seconds; `tmp/fix03a_r1/targeted_boundary.txt`.
- Final complete command: `.\.venv\Scripts\python.exe -u -X utf8 -m pytest -q --tb=short --junitxml=tmp/fix03a_r1/full_suite_final.xml --basetemp=tmp/fix03a_r1/pytest_full_final`.
- Final complete evidence: `tmp/fix03a_r1/full_suite_final.txt`, `tmp/fix03a_r1/full_suite_final.xml`.

Collection reconciliation: **2,164 reported baseline + 101 already present FIX-03A coastal-integrity tests = 2,265 at R1 entry; + 217 new R1 tests = 2,482 final collection**. R1 removes no tests and uses no deselection. One existing visual-memory test is renamed and its expectation corrected. Thus the increase over the reported baseline is **318 = 101 + 217**. The older 2,164 baseline was not reconstructed or re-executed; the pre-R1 collection and both complete suite runs were measured locally.

The existing pytest-asyncio unset-loop-scope deprecation warning is emitted at startup. It is not a collection error; no dependency or pytest configuration change is included in R1.

## Limitations and Owner decisions

- Intent handling deliberately uses a small RU/EN vocabulary and scope grammar, not a general natural-language parser. Ambiguous or unsupported phrasing is not claimed to be fully understood.
- Controlled scene identity is recovered from the controlled builder's anchored `Scene type: ...` field. An external override without that field does not acquire an invented controlled identity.
- Historic metadata remains readable; records are not migrated or rewritten. The broader motif-extraction and diversity work remains outside this pass.
- Deterministic payload assertions establish routing and prompt integrity. They do not establish perceptual uniqueness or visual quality. No live visual sampling was performed.
- The confirmed explicit conflicts can use the existing style-choice recovery, so no new product flow or unresolved Owner product decision is required for those cases. Richer hybrid scene/style semantics remain outside this narrow parser and remediation.

## Operations and process exception

No staging, commit, push, deployment, production access, database migration, dependency installation or live model/provider operation was performed. Tests used isolated temporary SQLite databases and mocked provider transport. No model identifiers or billing/reservation contracts were changed.

The requirement of **no Git commands whatsoever was not fully met**: the very first repository inspection ran `git status --short` and `git branch --show-current` concurrently with reading the attachment, before its prohibition was read. This was disclosed immediately. No further Git commands were used. The pre/post source comparison in `tmp/fix03a_r1/remediation.diff` was created with Python against a local source snapshot, not with Git. Owner retains Git review, staging, commit and push ownership.

Work stops after implementation, tests and this report. Independent read-only re-audit and Owner acceptance remain pending.
