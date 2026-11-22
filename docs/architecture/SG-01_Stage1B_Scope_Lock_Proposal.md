# SG-01 Stage 1B — Scope Lock Proposal

**Recommendation:** implement an isolated, provider-free foundation for resolution integrity, preflight, typed assembly and final validation. Exercise successful assembly only with explicitly synthetic test registries, policies and capabilities. Defer real rendering content, production route authorization and runtime integration.

This separates testable enforcement mechanics from product policies that have not been approved. It does **not** establish a production-capable Safety Gate.

This assessment was read-only. No files were changed, no Git commands or tests were run, and `tmp/` was not inspected. The baseline `main` / `992d233` and Stage 1A acceptance are Owner-supplied. Historical acceptance-pending statements in the implementation record do not override the Owner’s current closure statement.

**A. Specification alignment**

The normative source is [SG-01 D0-R2](/C:/Users/eliv/Pet_Projects/rise-and-shine-bot/docs/architecture/SG-01_Safety_Gate_Design_v1.md:1). The [Stage 1A record](/C:/Users/eliv/Pet_Projects/rise-and-shine-bot/docs/architecture/SG-01_Stage1A_Implementation_Record.md:5) identifies implemented contracts and deferred boundaries.

| Proposed deliverable | Exact specification basis | Stage 1B limit |
|---|---|---|
| Resolution derivation integrity | §4.1 identity/provenance invariants; §4.2 authoritative classifications and ledger; §4.3 derived-data ownership and digest; §6 hash limitations | Verify canonical derivation, rather than accepting a self-consistent digest. Preserve existing interpretation behavior. |
| Assembly preflight | §5.1 typed results; §5.2 verified capacity; §7 V1; §9.1 mandatory enforcement; §13 O-1 | Implement checks and fail-closed results. Register no production route or assumed provider capability. |
| Immutable candidate/provenance contracts | §4 immutability; §6 `FragmentProvenance`, `PromptFragment`, `PromptCandidate` | Typed records convey evidence, not automatic trust. |
| Narrow assembly mechanism | §6 exact registered fragments, canonical projections, closed slots and deterministic serialization; §9.2 controlled construction | Implement registry verification and serialization mechanics. Supply no new production scene renderer or rendering catalogue. |
| Final validation and opaque artifact | §6 `FinalAssembly`, `ValidatedAssembly`, seven final-validation obligations; §11 ASM-01–15 | Implement offline validation and factory ownership. Issue no production dispatch authority. |
| Isolation and compatibility tests | §2 dependency direction/migration boundary; §8 frozen matrix; §11 deterministic oracles | Retain Stage 1A isolation and existing runtime behavior. Do not migrate consumers. |

The following requirements cannot be completed operationally within this stage:

- **Complete V1 routing:** requires approved concrete selection rules, faithful construction coverage and verified capabilities.
- **Real style/scene fidelity certification:** requires reviewed exact fragments, slot semantics and coverage of essential intent.
- **Arbitrary Custom Style or enrichment admission:** requires faithful approved rendering or a separately approved enforcement standard.
- **V4 non-bypassable dispatch:** requires provider-boundary and consumer integration, expressly excluded here.
- **Production lifecycle guarantees:** reservations, terminal scheduled failures, CLI task cleanup, metadata identity and fallback catch ordering belong to later integration.

These remain incomplete requirements, not waived requirements.

**B. Inclusion/exclusion matrix**

| Component | Disposition | Exact responsibility | Likely files | Safety dependency and rationale |
|---|---|---|---|---|
| Resolution integrity | **Include** | Re-derive disposition, effective facts, bans, conflicts and supporting provenance; compare against supplied fields and digest | `visual_safety.py`; Stage 1A/1B tests | Mandatory before any new assembly authority consumes those fields. |
| Evidence and version binding | **Include** | Validate types, refs, source activity, snapshot binding and recognized policy/vocabulary/registry versions | `visual_safety.py`, `visual_safety_types.py`; tests | An internally consistent object can still be stale or unauthorized for the current attempt. |
| Preflight contract | **Include** | Reject blocked/unsupported-only interpretations, unresolved negatives, missing route coverage, unavailable capabilities and unrepresentable required content | `visual_safety.py`, types and registry definitions; tests | An interpretation-level `allowed` result cannot authorize assembly. |
| Route provenance verification | **Include** | Verify gate-owned selection, approved rule/version, source snapshot, coverage and early ordering | `visual_safety.py`, neutral registry definitions; tests | A route label or `selected_before_enrichment=True` assertion is insufficient. |
| Production route rules | **Defer** | Actual selection of a supported product route | No production changes | O-1 is conditional; it does not approve a concrete rule or rendering policy. |
| Candidate/provenance types | **Include** | Transitively immutable fragments, semantic metadata, source refs, scene identity, style and mode | `visual_safety.py`, types | Prevent mutable dictionaries and descriptive traces from becoming authority. |
| Controlled construction mechanics | **Include narrowly** | Resolve registered IDs/closed slots, verify their contracts, derive exclusions through the existing closure owner and serialize exact fragments | `visual_safety.py`, neutral registry definitions; tests | Testable without approving production rendering content. |
| Production fragment catalogue/general renderer | **Defer** | Real scene, preset, style, focus, composition and user-fact rendering coverage | No builder changes | Current fragment names and local string joins do not establish trustworthy semantics. |
| Final validation and `ValidatedAssembly` factory | **Include** | Validate the complete artifact, provenance, restrictions, fidelity coverage, serialization, capability and seal | `visual_safety.py`, types; tests | Successful synthetic tests establish mechanics only. |
| Real adapter capability registration | **Defer** | Verify actual adapter/model limits and counters | No provider/configuration changes | Unknown capability remains blocking. Synthetic capacity fixtures are sufficient for algorithm tests. |
| F-08 clarification and F-09 foundation tests | **Include** | Document classification semantics; strengthen isolation and literal registry oracles | `visual_intent.py`; existing/new tests | Required to prevent misuse by the new offline layer. |
| Runtime consumers, transport and fallback migration | **Defer** | Coherent later integration of all entry points/builders/metadata | No changes | Safe to defer while the new foundation remains unreachable from production. |

**Current integrity gap relevant to this scope**

By inspection, [current `check_interpretation`](/C:/Users/eliv/Pet_Projects/rise-and-shine-bot/services/visual_safety.py:297) validates the interpretation, requires no route, checks `_digest`, then uses the supplied disposition and conflicts. It does not compare supplied resolution fields with a fresh canonical derivation from the interpretation.

Consequently, frozen dataclasses and a recomputed digest do not establish that supplied bans or conflicts were correctly derived. Stage 1B must close that gap before using a resolution for assembly authorization.

The smallest correction is to share one pure derivation implementation between resolution construction and verification. Do not add a second closure/conflict algorithm or recursively call the public validator from itself.

**C. Trust-boundary analysis**

```text
Stage 1A evidence
    → validated resolution
    → preflight
    → controlled candidate
    → final validation
    → validated assembly
```

This is an offline flow. It ends without provider dispatch.

| Boundary | Required authority and provenance checks |
|---|---|
| **Evidence → validated resolution** | Validate the existing immutable structure, classifications, ledger and composite refs. Establish that semantic evidence belongs to the Stage 1A interpretation of the retained segmentations; caller-attached facts are not authoritative merely because their refs exist. Re-derive all resolution fields under recognized policy and versions. Compare complete records, including causes, refs, fact indices and coastal conflict dispositions. |
| **Validated resolution → preflight** | Evaluate the canonical interpretation verdict. Unsupported-only requests and every unresolved active exclusion block; a mixed request retains only independently eligible positives. Check applicable system/style restrictions, capability evidence and approved route coverage. Preserve requested-style-based custom-note activity. |
| **Preflight → controlled candidate** | Require successful preflight bound to the same snapshot and route. Accept trusted components only through exact registered content or validated closed slots. Derive key metadata from those contracts. Raw text, cleaned text, LLM output and arbitrary plan fields remain untrusted. |
| **Candidate → final validation** | Reconcile candidate-specific restrictions using the single closure owner. Verify required facts/qualifiers, requested style/mode and registered style requirements. Account for the complete prompt, all fragment spans/separators and the actual model/adapter/capability context. |
| **Final validation → validated assembly** | Only the gate factory creates the opaque immutable artifact. Bind resolution, route, fragments, provenance, scene identity, prompt, policy/registry versions and capabilities into its integrity record. Reconstructed wrappers and caller-supplied “allowed” results confer no authority. |

Additional boundary rules:

- **Digest verification follows derivation verification.** A digest proves identity of the supplied data, not correctness of its derivation.
- A completely new, self-consistent source snapshot is a new attempt. Detecting reuse of an old artifact requires comparison against the gate-owned attempt context; hashing only the replacement object cannot establish freshness.
- Route selection must occur through the gate’s policy operation before candidate construction/enrichment. A boolean field cannot independently prove chronology. A later failure terminates the attempt; it cannot trigger another route.
- Candidate-specific `SCENE_HUMAN_NONE`, registered style restrictions and `SYSTEM_NO_TEXT` must be derived by the same constraint owner. Builders must not independently union or weaken mandatory bans.
- Unknown registry entries, incomplete required-intent coverage, unverified counters and unknown adapter/model combinations block.

**Mechanical checks versus semantic guarantees**

Stage 1B can establish exact serialization, spans, immutable identity, canonical exclusion coverage, registered key compatibility, version consistency and capacity measurement.

For controlled content, fidelity/noncontradiction checks are conditional on the correctness and completeness of reviewed registry semantics. They are not general natural-language proofs.

Under the current no-B contract, arbitrary user/LLM prose cannot obtain trusted certification. Universal `SYSTEM_NO_TEXT` is sufficient to make unsupported untrusted-prose enforcement blocking. A lexical scan must never convert that absence of proof into success. This follows [§9.1–§9.3](/C:/Users/eliv/Pet_Projects/rise-and-shine-bot/docs/architecture/SG-01_Safety_Gate_Design_v1.md:569).

**How to test successful assembly without approving rendering behavior**

Keep synthetic exact fragments, slot schemas, route rules and fake capabilities inside the test suite. Exercise the real derivation, preflight, assembly and validation algorithms against that explicitly test-only context.

Do not expose caller-supplied registries as production trust, load fixture approvals through configuration, or install a default production policy. Without authorized real records, real assembly authorization remains unavailable and fails closed. This limitation must be stated in the implementation record.

**D. F-07–F-10 dependency disposition**

The finding descriptions below come from the [Stage 1A remaining-obligations register](/C:/Users/eliv/Pet_Projects/rise-and-shine-bot/docs/architecture/SG-01_Stage1A_Implementation_Record.md:118); this assessment does not invent additional audit findings.

| Finding | Classification | Minimum correction/test obligation | Consequence and precise basis |
|---|---|---|---|
| **F-07 — object/coastal vocabulary aliases** | **Mandatory before runtime consumer integration**; defer reconciliation beyond Stage 1B | Keep Stage 1B on existing Stage 1A canonical keys. Add no alternate raw-text recognizer or alias expansion. Before migration, reconcile differences with hand-authored recognition/compatibility oracles and deliberate review of changed coverage. | The current neutral and legacy patterns are not identical: compare `visual_semantics.py:12–32`, `visual_constraints.py:11–20`, `coastal_intent.py:23–31`. Using them interchangeably can change recognition and fulfillment. Deferral is safe only because Stage 1B does not migrate consumers or render legacy prose as trusted. Specification §2, §3, §11 INT-13/14. |
| **F-08 — public `RequestClass` interpretation** | **Mandatory for Stage 1B**, narrowly | Document and test that `RequestClass` alone is not a negative-safety verdict. Supported negative directives may be `eligible`; unresolved negative directives can have a non-request classification. The negative ledger and resolver verdict remain authoritative. Preserve enum values and behavior. | A new preflight must not interpret `nonvisual` as permission to ignore an unresolved assessment or treat every `eligible` directive as a positive request. See `visual_intent.py:430–475`; specification §4.2 and §5.1. |
| **F-09 — isolation and registry-equivalence oracles** | **Mandatory for Stage 1B** for the new foundation; broader runtime coverage remains mandatory before integration | Extend isolation assertions to all added contracts/dependencies. Retain no-production-import checks. Add hand-authored literal registry expectations alongside identity checks, including aliases and fixed coastal compatibility. | Existing [isolation checks](/C:/Users/eliv/Pet_Projects/rise-and-shine-bot/tests/test_visual_intent_package_a.py:318) and [registry identity checks](/C:/Users/eliv/Pet_Projects/rise-and-shine-bot/tests/test_visual_safety_stage1a.py:411) are useful but do not alone prove literal semantic correctness or future runtime migration. Specification §2, §11 INT-13/14. |
| **F-10 — unused `Attachment.frame_level`** | **Safely deferrable beyond Stage 1B**, provided no new consumer relies on it | Preserve the existing enum and structural behavior. Test that an attachment label cannot authorize globalization of a relational exclusion. Clarify semantics before any later consumer depends on that state. | `frame_level` is declared, while current construction emits `head_local`/`uncertain` (`directive_segments.py:17`, `315–348`). Stage 1B can consume the authoritative negative ledger without assigning new meaning to it. Specification §3, §4.1 and SG-D1. |

**Resolution derivation integrity is a separate mandatory Stage 1B dependency.** It cannot be deferred under the F-07–F-10 nonblocking labels.

FIX-03A compatibility, D1-A, SG-D1, SG-D2 and custom-note activity remain frozen. In particular, retain the [CP-01 contextual coastal oracles](/C:/Users/eliv/Pet_Projects/rise-and-shine-bot/tests/test_visual_safety_stage1a.py:490) and [bidirectional activity checks](/C:/Users/eliv/Pet_Projects/rise-and-shine-bot/tests/test_visual_safety_stage1a.py:609).

**E. Deterministic test strategy**

All expected outcomes, refs, causes, fragments and prompts must be hand-authored. Tests exercise the real foundation; they must not replace its resolver or validator with success stubs.

| Area | Required oracle |
|---|---|
| **ALLOWED versus BLOCKED** | An eligible `Show a table; No mugs` fixture can proceed only with complete synthetic policy/registry/capability coverage. `No mugs; show a cup` retains alias-based `OBJECT_CONFLICT` and cannot invoke controlled construction. |
| **Unsupported and mixed requests** | Story-only input blocks. Story plus independent table retains unsupported provenance and requires only the table. Story-owned mugs/windows cannot enter positive fragments. |
| **Unresolved exclusions** | `No mugs on tables`, `Show a mug without a logo`, zero-recognition `No glargs` and unsupported long negatives remain blocking with exact ledger/ref/detail oracles. No globalized replacement ban. |
| **Complete mandatory bans** | Human exclusion requires human/hands/body; hands-only has no reverse cascade. Coastal closures match §4.3. Final scene-none, applicable style constraints and system no-text are included. Repeated exclusions preserve every supporting ref without a count cutoff. |
| **Recomputed resolution forgery** | Independently alter bans, causes, refs, effective facts, fact indices, conflicts or disposition, then recompute the digest. Each inconsistent object fails canonical derivation validation. Include conflict removal and human-cascade removal. |
| **Stale provenance/versions** | Changed source, active flag, requested style/mode, snapshot binding, policy/vocabulary/registry/capability version rejects reuse. Include two sources with local directive/scope zero. |
| **Altered route** | Change rule, kind, snapshot digest, policy, standard IDs or ordering provenance while keeping prompt text unchanged. Reject missing/forged/late route selection and any post-veto reselection. |
| **Final prompt/metadata mutation** | Added suffix, replaced fragment, reordered fragments, incorrect spans, changed separators or prompt/scene/style/model metadata fails. Every character must belong to the deterministic serialization. |
| **False trust claims** | Arbitrary text labelled `curated`/`user_projection`, fabricated refs, empty key sets and trace labels fail exact registry/projection verification. |
| **Capacity** | Synthetic codepoint/UTF-8 limits pass at the boundary and block one unit above, using the entire prompt. Unknown adapter/model, unsupported token counter or an evidence-reference string without trusted capability registration remains `CAPACITY_UNVERIFIED`. |
| **Untrusted enrichment** | LLM prose, generated plan fields, cleaned theme, raw overrides and emotional-focus prose cannot become controlled. With no approved B coverage, universal no-text still blocks admission. |
| **Custom Style and symbolic nuance** | Arbitrary active descriptions—including descriptions without bans and bans-only recognition with unrepresented style content—receive explicit refusal when faithful enforcement is unavailable. No generic replacement, omission or new whitelist. Inactive notes add no user bans; prose actually included as symbolic nuance remains subject to enforcement. |
| **Fixed style/coastal compatibility** | Retain contextual tropical-beach compatibility, genuine dedicated-beach/interior conflicts, exclusion precedence, source-scoped qualifiers and no invented complementary shoreline. Use interpretation-level compatibility oracles where real assembly contracts remain unavailable. |
| **Closed legacy exceptions** | Both exact chunks retain negative structure and positive legacy coastal facts; beach-sunset retains its qualifier. No same-member coastal ban. Preserve all near-miss fences and independent same-key exclusion precedence. |
| **Stage 1A isolation/regression** | Default resolution still has `enforcement_route=None`; `check_interpretation` stays interpretation-stage. Preserve existing Package A/CP-01 expectations, custom activity and neutral dependency direction. |

After implementation authorization, run the focused Package A/Stage 1A/Stage 1B suites and the full offline regression suite. Use OS temporary directories and preserve evidence. No paid/live providers or production database access.

Stage 1B cannot prove actual entry-point paid-call ordering or transport protection. Those require the later §11 INT suites; zero-call claims here apply only to the offline foundation exercised.

**F. Product impact**

**The recommended Stage 1B package has no operational product change**, because no production caller, configuration or provider boundary is connected to it.

Its offline refusals and limited synthetic successes must nevertheless be documented honestly:

| Dimension | Effect if these constraints were later activated |
|---|---|
| Image quality and composition | Restricted registered construction could change detail, variety and composition. This stage provides no image-quality evidence. |
| Expressiveness and theme nuance | Content without faithful approved representation would be refused. Required details cannot be silently removed to obtain success. |
| Registered style fidelity | Missing or incompatible style coverage causes refusal; replacing a fixed style is feature loss. |
| Custom Style | Arbitrary active descriptions may be refused under the minimum contract. That is reduced fulfillment, not behavior preservation. |
| Symbolic nuance | Unrepresentable supplied nuance requires refusal unless separately approved faithful handling exists. Silent omission is not preservation. |
| Enrichment availability | A future approved early controlled route may skip enrichment. No blanket shutdown is authorized. Scene-driven generation already suppresses enrichment under the documented configuration boundary. |
| Fallback availability | Safety failures cannot invoke weaker alternate prompts. This can reduce successful recovery compared with current behavior. |
| Capacity and capability | Unknown capabilities and complete-prompt overflow cause refusal rather than guessed limits or truncation. |
| Costs and latency | Stage 1B adds no paid calls. Future early refusals may avoid paid work, but runtime savings are unproven here. |

Material quality, functionality or fulfillment changes require separate Owner review before activation under [O-1’s eight conditions](/C:/Users/eliv/Pet_Projects/rise-and-shine-bot/docs/architecture/SG-01_Safety_Gate_Design_v1.md:812).

**G. Minimum implementation package**

Implement one **offline assembly-validation foundation** containing:

- Canonical resolution re-derivation and integrity verification.
- Immutable candidate, fragment, provenance, capacity, final-assembly and opaque validated-artifact contracts.
- Fail-closed preflight and route/capability verification mechanics.
- Exact registered-fragment/closed-slot assembly mechanics and single-owner constraint derivation.
- Complete final validation for that supported controlled contract.
- Synthetic successful-path fixtures, adversarial tests, F-08 clarification and F-09 foundation coverage.
- A Stage 1B implementation record stating all unavailable production capabilities.

**Exact anticipated file-change list**

| File | Anticipated change |
|---|---|
| [services/visual_safety.py](/C:/Users/eliv/Pet_Projects/rise-and-shine-bot/services/visual_safety.py) | Shared derivation verification; offline preflight, candidate/assembly operations, final validator and opaque factory. Reuse existing resolution/route types and closure owner. |
| [services/visual_safety_types.py](/C:/Users/eliv/Pet_Projects/rise-and-shine-bot/services/visual_safety_types.py) | Necessary immutable supporting contracts and stage-correct typed failure construction, preserving existing default behavior. |
| [services/visual_semantics.py](/C:/Users/eliv/Pet_Projects/rise-and-shine-bot/services/visual_semantics.py) | Neutral immutable assembly-registry/policy/capability contract definitions. No production rendering or route approvals; no alias expansion. |
| [services/visual_intent.py](/C:/Users/eliv/Pet_Projects/rise-and-shine-bot/services/visual_intent.py) | F-08 documentation only; no classification behavior change. |
| [tests/test_visual_safety_stage1a.py](/C:/Users/eliv/Pet_Projects/rise-and-shine-bot/tests/test_visual_safety_stage1a.py) | Derivation-corruption regressions and stronger literal registry/activity/classification oracles. |
| [tests/test_visual_intent_package_a.py](/C:/Users/eliv/Pet_Projects/rise-and-shine-bot/tests/test_visual_intent_package_a.py) | Extend the isolation/dependency oracle only as required by the approved foundation. |
| `tests/test_visual_safety_stage1b.py` — new | Hand-authored offline contract, assembly and adversarial tests; synthetic registries/policies/capabilities remain here. |
| `docs/architecture/SG-01_Stage1B_Implementation_Record.md` — new | Scope, specification mapping, validation evidence, limitations and deferred dependencies. |

No architecture rewrite, consumer edits or additional files are anticipated. A need to expand this list materially should return to Owner scope review.

**Acceptance criteria**

| ID | Criterion |
|---|---|
| AC-1 | Supplied resolution fields match canonical derivation; recomputed hashes cannot conceal altered bans, conflicts, facts, disposition or provenance. |
| AC-2 | Existing Stage 1A public contracts and frozen interpretation outcomes remain intact; default resolutions retain no route. |
| AC-3 | Preflight fails closed for every blocking interpretation, missing enforcement coverage, stale/inconsistent evidence and unknown capability. |
| AC-4 | Trust derives from gate-owned, versioned contracts—not text labels, caller metadata, flags or arbitrary registry injection. Synthetic approvals cannot enable production authorization. |
| AC-5 | Controlled assembly accounts for the complete prompt and preserves every applicable restriction, essential fact/qualifier and supported style/mode requirement. |
| AC-6 | Final validation verifies serialization, spans, route consistency, full capacity and all provenance/version bindings. Only the gate factory can issue an intact validated artifact. |
| AC-7 | Untrusted prose receives no unsupported semantic certification. Custom Style/nuance is faithfully supported or explicitly refused. |
| AC-8 | Focused and full offline regressions pass; isolation remains enforced. No runtime wiring, production route, dispatch authority, configuration change, migration or paid call is introduced. |
| AC-9 | Independent Claude Code read-only audit and Owner acceptance complete the phase; passing implementation tests alone do not authorize integration. |

1. **Recommended exact Stage 1B scope:** the eight-file offline foundation above, including derivation integrity, preflight, immutable assembly contracts, narrow serialization, final validation and synthetic deterministic tests.
2. **Items explicitly deferred:** production routing/content registration, general renderer, real adapter capabilities, runtime consumers/transport, F-07 reconciliation, unused `frame_level` semantics, bounded-enforcement standards, new Custom Style policies, N-2, RS-UX-01 and every other task expressly excluded by the request.
3. **Mandatory safety dependencies:** canonical derivation verification, authoritative ledger preservation, one closure owner, gate-owned route provenance, verified capabilities, complete final-prompt accounting, F-08 clarification and F-09 foundation isolation.
4. **Unresolved Owner decisions:** none blocks this foundation-only scope. Real rendering/route contracts, any bounded-enforcement or Custom Style policy, and material product regressions require separate decisions before later implementation or activation.
5. **Proposed acceptance criteria:** AC-1–AC-9, including successful synthetic-path tests, adversarial refusal tests, unchanged production isolation, independent audit and Owner acceptance.
6. **Verdict: `READY FOR OWNER SCOPE APPROVAL`.**