# Rise and Shine — SAR-02
## Hybrid Structured Generative Architecture Research Charter

| Field | Value |
|---|---|
| Version | 1.0 |
| Date | 2026-11-26 (CP-02 revision and Charter freeze) |
| Status | OWNER ACCEPTED / FROZEN v1.0 |
| Repository | `eliv1982/rise-and-shine-bot` |
| Intended repository path | `docs/architecture/SAR-02_HSGA_Research_Charter_v1.0.md` |
| Development Baseline (Owner-confirmed) | `main`, `482688952f83059e9ffae76472c022472c3e17f0`, GitHub Actions CI #48 PASS |
| Predecessor | SAR-01 + SAR-01-CP-01 — CLOSED / OWNER ACCEPT |
| Governing normative baseline | SG-01 D0-R2, unchanged |
| Production Reference (Owner-supplied) | RS-REL-01, `4a79f420283a0a05f9f0548b1a388047121de795`, deployed 2026-11-25 — POST-DEPLOYMENT CHECKS PASS |
| Experimental Baseline | Fixed separately for each comparison before execution under §§4.4 and 6.2 |

**Authority of this charter.** This is a consolidated research-program document based on the Owner + Teya strategic discussions. The Owner agreed to the research direction, methods and boundaries on 25 November 2026. On 26 November 2026, the Owner accepted and froze the consolidated text as Research Charter v1.0 (see §8.3). Approval of this charter alone does not authorize a research execution package, code changes, a B-standard, a D0-R2 amendment, provider calls, an experiment, operational admission or production deployment. Each execution scope requires separate authorization.

---

## 1. Background, purpose and strategic decisions

### 1.1 Background

SG-01 Stages 1A–1D and the Stage 1D CP-01 are CLOSED / OWNER ACCEPT. The Owner supplied the Development Baseline and historical results: CI #48 PASS (2m 10s), 6,305 offline tests PASS, 394 focused Stage 1D tests PASS and 1,202 affected regression tests PASS. The test counts are historical developer-report evidence. The repository, CI and test outcomes were not independently checked for CP-02.

The Owner reports that RS-REL-01 deployed FIX-03A, FIX-03B-1 and FIX-03B-2A. PostgreSQL, existing data, settings and feature flags were preserved. The pre-deployment backup was verified by actual restoration in an isolated PostgreSQL environment, and the previous production rollback image associated with `d4999cb9` was retained. SG-01 and HSGA remain operationally inactive. N-2 remains OPEN. The release-specific N-2 exception applies exclusively to the identified RS-REL-01 production revision. It provides no amendment to D0-R2, research dispatch authority or general exception. Product Observation remains OPEN, and actual visual quality improvement is unestablished. These are Owner-supplied production facts.

The SAR-01 Codex feasibility assessment concluded **REQUIRES ARCHITECTURAL REVISION**. Independent Claude Code audit concluded **ACCEPT WITH CONDITIONS**: 13 of 14 original findings verified, SAR-F-10 partially verified, five additional findings, and six acceptance conditions. SAR-01-CP-01 reconciled C1–C6; the Owner accepted SAR-01 and CP-01 with minor notes. The original feasibility verdict remains unchanged. Closure accepts the diagnosis, not remediation of the 19 SAR findings or operational feasibility of HSGA.

The research direction is Hybrid Structured Generative Architecture (HSGA) with V3 differentiated evidence. The existing controlled renderer is a specialized, synthetic offline mechanism, not the universal product or an authorized production route.

### 1.2 Purpose

Determine which architecture can preserve or improve Rise and Shine as a personalized creative affirmation and visual-generation product while protecting mandatory user intent and maintaining acceptable fulfillment, latency, cost and reliability. Preserve full LLM enrichment, semantic and artistic creativity, arbitrary Custom Style, symbolic expression, visual diversity and current user-visible capabilities as research objectives subject to independent evaluation and existing authority constraints. Avoid converting the registry into an exhaustive creative catalogue or using subjective aesthetic preferences as automatic mandatory exclusions.

The research must permit negative results, including rejection of HSGA components or of the proposed combined policy if evidence does not support them. Every additional mechanism must justify itself through measurable value; a cheaper or simpler mechanism is preferable if it meets independently established requirements. Cost or artistic quality cannot compensate for a violation of a mandatory obligation.

### 1.3 Strategic decision register

The following are Owner-agreed strategic principles and research objectives, not frozen operational contracts. D01 and D02 describe a future-route objective, not current admission under D0-R2.

| ID | Agreed direction |
|---|---|
| SAR-D01 | Preserve semantic and artistic generative freedom. Novel content must not be rejected for registry absence alone in a future approved route; sufficient mandatory-compliance evidence is still required. |
| SAR-D02 | Investigate HSGA: a generative system with controlled obligations, not deterministic generation with decorative enrichment. Controlled routing remains specialized under O-1. |
| SAR-D03 | Separate source information, protected obligations, personalization and creative proposals; determine authority by source, scope, applicability and obligation strength. Creative generation cannot change mandatory requirements. |
| SAR-D04 | Investigate open structured semantics for new entities, scenes, relationships, metaphors and artistic concepts. Open fields remain untrusted; structure is not semantic proof. |
| SAR-D05 | Retain original arbitrary Custom Style and essential requirements; no silent substitution or omission. Distinguish obligations, preferences, artistic direction and exclusions. |
| SAR-D06 | Preserve free symbolism and metaphor while honoring selected mode subject contracts. Separate mandatory compliance from semantic relevance and subjective artistic QA. |
| SAR-D07 | Treat the registry as versioned trusted knowledge, not an exhaustive creative allowlist. Preserve existing controlled-route pins and guarantees. |
| SAR-D08 | Separate Intent & Authority, Creative Generation, and Validation & Dispatch Authority. LLM outputs are proposals or evidence, never independent dispatch authority. |
| SAR-D09 | Investigate route-aware evidence mechanisms with common applicable obligations, explicitly approved standards and no route switching to bypass failure. |
| SAR-D10 | Investigate V3: deterministic structural verification, bounded semantic verification, probabilistic assessment, explicit uncertainty and separate image assessment. These are distinct evidence types. No threshold or probabilistic authority is approved. |
| SAR-D11 | Distinguish PASS (policy-sufficient evidence), REJECT (established violation) and INDETERMINATE (insufficient evidence). Both non-PASS outcomes prohibit dispatch. Under the current contract distinct diagnostics may map to BLOCKED; no new operational outcome or reason code is approved. |
| SAR-D12 | Experimental direction only: investigate bounded new generative attempts with unchanged Protected Intent and route, full independent validation, terminal prior attempts and no authorization reuse or verdict shopping. Investigate disclosed text-only delivery only when independently valid and permitted by format and policy. No automatic regeneration or partial delivery is currently authorized. |
| SAR-D13 | Distinguish Intent Fidelity, Candidate Compliance, Payload Integrity and Actual Image Compliance & Quality. A conforming prompt does not prove compliant pixels. |
| SAR-D14 | Investigate reuse of SG-01 without escalating synthetic authority. Existing `SyntheticValidatedAssembly`, `authority='synthetic_offline'` and `production_authorized=False` remain binding. |

### 1.4 Research hypotheses

| ID | Testable hypothesis |
|---|---|
| H-01 | Deterministic mechanisms suffice for a meaningful portion of mandatory obligations within explicitly declared coverage. |
| H-02 | Open structured semantics preserves semantic and artistic expressiveness better than a closed creative registry. |
| H-03 | Probabilistic semantic validation detects some material violations missed by deterministic checks. |
| H-04 | Combining appropriate deterministic and probabilistic evidence improves the trade-off between compliance, expressiveness and cost relative to either mechanism alone. |
| H-05 | HSGA can preserve or improve arbitrary Custom Style and symbolic expression relative to the existing generator. |
| H-06 | Bounded regeneration improves admissible fulfillment without weakening obligations or bypassing validation. |
| H-07 | Additional mechanisms can operate without unacceptable cost, latency, abstention or fulfillment loss. |
| H-08 | Constraint-aware creative generation reduces incompatible proposals without materially reducing semantic or artistic freedom. |
| H-09 | LLM-assisted intent interpretation improves completeness and accuracy for arbitrary user intent without adding, weakening or substituting mandatory requirements. |

The Detailed Research Protocol must specify the precise claim type and appropriate evidence and inference for each applicable hypothesis. It must pre-register practically meaningful effect criteria and primary or co-primary endpoints where applicable, the unit of analysis, treatment of repeated generations and dependent observations, a justified multiplicity strategy, conditions for support, contradiction and inconclusiveness, and appropriate uncertainty reporting. The choice of method and endpoint structure depends on the claim. A suitable pre-registered analysis plan is a prerequisite for the corresponding experiment authorization. See §§4.4 and 8.2 for comparator design and protocol requirements.

Deterministic properties may be assessed by formal reasoning, exhaustive checks within a declared domain or other appropriate engineering evidence. Empirical preservation or non-reduction claims require a pre-registered non-inferiority, equivalence or other justified inferential framework. A statistically non-significant difference is insufficient evidence of preservation. Owner approval of applicable product-quality margins must precede the corresponding confirmatory experiment. Statistical margins cannot relax mandatory normative obligations. For multi-objective claims, pre-register an adjudication rule under which mandatory obligations are non-compensable.

For H-03, distinguish evidence that the probabilistic mechanism detects additional violations from evidence that the increment matters in practice. Evaluate incremental detection alongside false alarms and other relevant consequences, including abstention and fulfillment where applicable. Keep confirmatory analyses separate from exploratory analyses. Exploratory findings may motivate later research and cannot retrospectively confirm a pre-registered hypothesis. When a fair comparison is infeasible, narrow the conclusion or leave it inconclusive. Hypotheses without sufficient applicable evidence remain open.

## 2. Research questions and conceptual architecture

### 2.1 Two complementary research tracks

**Track A — Deterministic Enforcement.** Investigate formal integrity, bounded semantics, potential B-standards, mandatory closure, provenance and payload integrity. Under D0-R2 a separately defined and explicitly Owner-approved B-standard may provide bounded-untrusted enforcement for precise restriction classes and route contexts. No B-standard has been approved. Coverage, vocabulary/grammar, veto and unknown handling, residual errors and versioned evidence must be explicit in any proposal. Clause presence is not semantic noncontradiction.

**Track B — Semantic Evidence.** Investigate model-assisted intent interpretation, open creative generation and probabilistic semantic assessment; fidelity, validator errors, correlation, uncertainty, cost and latency. Probabilistic semantic admission and additional gate classifier/reviewer calls are outside the current D0-R2 contract and require an explicit normative amendment before operational use. Upstream LLM interpretation that changes the authoritative gate resolution likewise requires explicit normative authorization; research-only interpretations remain untrusted proposals. Investigation does not confer that authority. A future policy may use both tracks or only particular mechanisms where justified.

### 2.2 Three LLM functional roles (not three mandatory agents or calls)

| Functional role | Proposed function | Output and trust boundary |
|---|---|---|
| Intent Interpreter | Interpret arbitrary user requests, essential Custom Style, conditions, scope and uncertainty. | Untrusted interpretation proposal with source-linked evidence; cannot establish authority, override frozen rules or independently resolve an unsupported request. |
| Creative Generator | Generate new semantic and artistic solutions consistent with the supplied protected obligations and creative space. | Untrusted Creative Proposal; cannot modify Protected Intent. |
| Semantic Validator | Assess intent fidelity and/or candidate compatibility, including open fields and relationships. | Probabilistic evidence or abstention, never dispatch permission. |

Intent Authority is a separate responsibility: it establishes applicable obligations only according to an approved policy. Validation & Dispatch Authority owns admission. No concrete data schema, model topology, number of calls, vendor or runtime sequence is fixed. A deterministic interpreter may suffice; a combined or adaptive architecture may be investigated, provided the evaluation measures error correlation and preserves independent verification where required.

### 2.3 Four conceptual information objects

| Object | Responsibility |
|---|---|
| Source Record | Preserve original supplied information, source identity, activity, provenance and relevant spans. Storage does not confer authority. |
| Protected Intent | Applicable mandatory obligations, essential requirements, precedence, provenance and unresolved obligation-bearing interpretations. Creative generation cannot change these. Unresolved obligations are not permission. |
| Personalization Context | Applicable preferences and contextual data with scope and obligation strength; persisted preferences do not automatically become visual bans. Preserve Profile's existing textual-contract boundaries. |
| Creative Proposal | Untrusted open entities, relationships, symbolism, artistic direction and evidence claims. Generator-declared assertions cannot establish completeness. |

Investigate Intent Fidelity against the Source Record and Candidate Compliance against Protected Intent as distinct comparisons. Test whether independent access to original sources reduces inherited interpretation errors. Agreement between interpreter, generator and validator may reflect a shared mistake rather than correctness. The eventual policy must protect both against missed obligations and against silently invented ones.

### 2.4 Research Questions — Track A

| ID | Question |
|---|---|
| RQ-A01 | Which obligations admit fully deterministic verification? |
| RQ-A02 | Which obligations admit verification only within a bounded semantic model? |
| RQ-A03 | What are the actual coverage limits of AR-01 and the canonical resolver? |
| RQ-A04 | Which candidate B-standards offer meaningful coverage without excessive registry expansion? |
| RQ-A05 | How can contradictions between structured assertions and open fields be detected? |
| RQ-A06 | Which existing SG-01 mechanisms transfer without changing their guarantees? |
| RQ-A07 | How can bounded non-violation be distinguished from insufficient evidence? |
| RQ-A08 | Which provenance, closure and payload-integrity properties can be guaranteed independently of creative generation? |

### 2.5 Research Questions — Track B

**Intent interpretation**

| ID | Question |
|---|---|
| RQ-B01 | How accurately does LLM-assisted interpretation separate obligations, preferences and creative wishes? |
| RQ-B02 | How accurately does it interpret negation, conditionality and scope? |
| RQ-B03 | Does it identify ambiguity instead of choosing an unsupported convenient reading? |
| RQ-B04 | How can interpreted requirements be linked to original source spans? |
| RQ-B05 | How can omitted and erroneously added obligations be detected? |
| RQ-B06 | How can D1-A, SG-D1 and SG-D2 remain invariant with model-assisted interpretation? |

**Creative generation**

| ID | Question |
|---|---|
| RQ-B07 | Which enrichment representation best preserves semantic and artistic freedom? |
| RQ-B08 | How does structuring affect metaphorical originality? |
| RQ-B09 | Does constraint-aware generation reduce incompatible proposals? |
| RQ-B10 | Can arbitrary Custom Style be retained without an exhaustive technique vocabulary? |
| RQ-B11 | How can diversity be preserved without turning preferences into templates? |
| RQ-B12 | How can mandala and symbolic mode identity coexist with open creative semantics? |

**Semantic validation**

| ID | Question |
|---|---|
| RQ-B13 | What material violations are detected beyond deterministic checks? |
| RQ-B14 | What violations are systematically missed? |
| RQ-B15 | How often are compatible creative proposals incorrectly rejected? |
| RQ-B16 | How reliably does the validator recognize and express uncertainty? |
| RQ-B17 | How correlated are interpreter, generator and validator errors? |
| RQ-B18 | How do model capabilities and model choice affect role suitability, cross-model portability, correlated failures, resource use and architecture robustness? |
| RQ-B19 | Which improvements justify added cost and latency? |

RQ-B18 is a distinct model-capability, model-sensitivity and architecture-robustness question. The protocol may investigate role-specific model suitability, portability across models, shared failure patterns and resource implications. The choice of shared or distinct models across the Interpreter, Generator and Validator remains open, as does provider and model selection. RQ-B18 results alone cannot establish HSGA superiority or authorize a provider, model, runtime call or operational configuration.

### 2.6 Candidate research configurations

The following configurations are hypotheses for comparison, not authorized runtime routes. Existing product behavior must be measured rather than assumed to match a particular configuration.

| ID | Enrichment representation | Candidate validation |
|---|---|---|
| R-A | Free LLM prose | Deterministic |
| R-B | Open structured LLM enrichment | Deterministic |
| R-C | Open structured LLM enrichment | Deterministic + LLM |
| R-D | Constraint-aware open structured enrichment | Deterministic |
| R-E | Constraint-aware open structured enrichment | Deterministic + LLM |

| ID | Interpreter | Generator | Validator |
|---|---|---|---|
| E-01 | Deterministic | LLM | Deterministic |
| E-02 | Deterministic | LLM | Hybrid |
| E-03 | LLM-assisted | LLM | Deterministic |
| E-04 | LLM-assisted | LLM | Hybrid |
| E-05 | LLM-assisted | Constraint-aware LLM | Hybrid |

The R and E tables describe overlapping research dimensions, not ten required experiments. Future protocols may select informative subsets or factorial/ablation comparisons, control confounding variables, and report missing comparisons. Candidate representations include prose with an assertion ledger, open entity/relation graphs, and constraint-focused assertions plus open creative content. No JSON schema is approved. Assess all provider-visible content, not only generator-declared entities or nominally semantic fields. Artistic fields, quotations, metaphor, implied entities, multilingual text, cross-field interactions and embedded instructions can affect compliance. A free-form transformation after assessment creates a new validation boundary.

## 3. Research corpus

The corpus plan has three complementary parts. A pass in one does not offset failure in another. This charter defines coverage requirements; it does not create or label the final dataset. All examples are research prompts, not new product oracles.

### 3.1 RC-A — Regression Corpus

| ID | Coverage |
|---|---|
| RC-A01 | AR-01 structural evidence, source and directive scope |
| RC-A02 | D1-A negative enumerations; two exact legacy exceptions and near misses |
| RC-A03 | SG-D1 unresolved relational exclusions |
| RC-A04 | SG-D2 narrative-only mentions |
| RC-A05 | Canonical resolution and mandatory closure |
| RC-A06 | O-1 early routing and no safety bypass |
| RC-A07 | Style/Mode compatibility |
| RC-A08 | Coastal intent, subtype/time, exclusions and conflict precedence |
| RC-A09 | Registry identity, provenance, exact serialization and payload integrity |
| RC-A10 | Attempt lifecycle, issuance and synthetic authority |

Use existing approved normative requirements and oracles. Do not change existing regression expectations to make HSGA pass. A change to previously approved expected behavior requires a separate explicit normative decision. Correction of an erroneous fixture expectation to restore fidelity to existing frozen policy requires separately scoped authorization, evidence and review, not a new policy decision. Neither may be used to make HSGA pass by weakening the approved expectation. Known regression cases remain a fixed regression suite, not evidence of unseen-case generalization.

### 3.2 RC-B — Semantic Challenge Corpus

Include positive/negative contrast pairs, ambiguous cases, out-of-coverage cases, adversarial and multilingual examples. Keep exact D1-A exceptions distinct from synonyms and list extensions. Preserve source activity, literal versus narrative authority, explicit user instructions versus personalization, positive requirements versus permissions, and conditional restrictions. Include SYSTEM_NO_TEXT even when no user exclusions exist.

Cover vocabulary held out relative to a pre-declared frozen registry reference, novel combinations of known elements, novel relationships, linguistic variation, Custom Style, symbolic interpretation, genuine ambiguity and conflicting instructions. Assess out-of-coverage behavior across these dimensions, including cases where each word is known but the meaning falls outside declared coverage.

Illustrative intent cases:

| Request (English gloss unless shown literally) | Research focus |
|---|---|
| I prefer mountains, but today I want the ocean. | Current request versus stored preference |
| No people, but traces of their presence are allowed. | Scope; permission is not a requirement |
| If there are buildings, make them organic in form. | Conditional requirement versus mandatory depiction |
| I dislike overly bright colors. | Preference versus hard prohibition |
| No windows except stained-glass windows. | Exception and negative scope; no new frozen oracle |
| No people by the water. | SG-D1 unresolved relational negative |
| Tell a story of overcoming adversity through a closed-door image. | Narrative versus literal visual authority; assess context under SG-D2 |
| Silver engraving on black silk. | Unregistered artistic technique and material |

Illustrative creative case: for an affirmation about openness to unseen opportunities, investigate a valley beyond a rocky ridge, bioluminescent ocean, crystals within volcanic rock, a multilayered mandala or a spiral architectural perspective. These are examples, not a fixed metaphor catalogue. Assess novelty and relevance across repeated generations.

Illustrative candidate contrast pairs (assume the stated obligation and compatible context):

| Obligation | Candidate 1 | Candidate 2 |
|---|---|---|
| No people | Empty trail | Trail with a distant hiker |
| No text | Abstract geometric ornament | Ornament formed from readable words |
| No windows | Solid stone wall | Wall with stained-glass window |
| Ocean required | Ocean beyond cliffs | Mountain lake beyond cliffs |
| Monochrome | Black-and-white composition | Black-and-white with red accent |
| Central mandala | Recognizable central radial structure | Shapeless abstract texture |

Also include anthropomorphic trees, statues and silhouettes, reflections, footprints, rock profiles, pseudocalligraphy, implied objects, cross-field contradictions, misleading assertions, technique-only Custom Style, long descriptions, distinguishing Unicode capacity cases, and adversarial instructions embedded in candidate text. Ambiguous examples require uncertainty labels, not artificially unique answers. Assess mandatory constraints in the context of actual frozen rules; examples do not expand supported semantics or authorize reconstruction.

### 3.3 RC-C — Real Product Corpus

| ID | Product coverage |
|---|---|
| RC-C01 | Living Nature: mountains, volcanoes, volcanic landscapes, terraces, valleys, high panoramas, rock plateaus, ocean, beaches including palms, forests and new motifs; scale, clear air, diversity |
| RC-C02 | Interiors and architecture: attractive composition, avoid repetitive office/furniture scenes |
| RC-C03 | Illustration and mixed styles: distinctive style identity and creative range |
| RC-C04 | Arbitrary Custom Style: technique, material, combined aesthetics, essential requirements and restrictions |
| RC-C05 | Mandalas and symbols: recognizable mode identity, expressive meaning and original symbolism |
| RC-C06 | Scheduled morning delivery |
| RC-C07 | Generate from Profile |
| RC-C08 | More / fresh generation |
| RC-C09 | Preferences changed between requests |
| RC-C10 | Custom Style plus current direct visual instructions |
| RC-C11 | Repeated generation series for diversity and repetition |
| RC-C12 | Visual failure, future bounded regeneration and partial-delivery behavior |

Apply the relevant frozen FIX-03 product contracts and D0-R2 entry-point requirements as context-specific reference oracles: Living Nature clear air is a default with its specified exceptions; mandala styles retain central radial identity and `daily_symbol` retains its single-emblem contract; Profile retains its illustration default and More rereads preferences; scheduled delivery retains applicable language, mode, claim, retry and accounting contracts. These obligations and defaults must not be generalized to unrelated styles or paths. Distinguish normative requirements from observed existing behavior and desired deferred improvements.

Owner preferences are product evidence for the supported user perspective (see §4.5). Cover registered styles and modes beyond the Owner's favorite nature motifs. Use authorized real scenarios or hand-authored cases; no production data or history access is implied. Deferred product improvements may inform evaluation without entering implementation scope automatically.

### 3.4 Corpus partitioning and ground truth

Require meaningful procedural separation of corpus construction, reference labelling, mechanism development and held-out evaluation. Provide for independent or appropriately blinded corpus authorship and labelling, with documented provenance, access and limitations. External human experts are optional. Separate LLM sessions may assist procedural separation but do not provide inherent statistical independence or the standing of independent human experts. The Detailed Research Protocol must specify authorship, labelling, adjudication and access arrangements. Any remaining independence limitation constrains the strength of the affected conclusions.

Separate development, validation and held-out evaluation for novel research cases and keep regression oracles separate. Assign each complete semantic family, including near-duplicates, paraphrases, contrast pairs and related variants, to exactly one partition. Keep contrast pairs together and prevent leakage across all three partitions. Before held-out evaluation, freeze and version the data together with reference labels, ambiguity classifications, applicable oracles and semantic-family partition membership. Keep the held-out material isolated from mechanism development and tuning of models, prompts, thresholds or configurations.

Use authoritative frozen oracles where applicable, independent hand-authored labels for challenge cases and Owner judgments for product preferences. Record source, obligation strength, applicable context, expected interpretation, and candidate reference status, including compatibility, incompatibility, genuine ambiguity or normative non-resolution as applicable. Distinguish reference ambiguity from assessor abstention. Preserve reviewer disagreement, reasons and alternative justified interpretations. Keep interpretation, candidate and image labels separate. Post-freeze label corrections require documented justification, retained versions and disclosure of effects on denominators and conclusions. Ground ambiguity classifications and any justified corrections in reference evidence. Measured performance plays no role in that classification.

Account for within-family dependence and repeated generations when interpreting uncertainty. Report coverage by obligation class, route, language, style and mode. Distinguish constructed coverage corpora from representative population samples. Convenience sampling and adversarial enrichment cannot establish production prevalence.

## 4. Evaluation framework

### 4.1 Intent Interpreter

| Metric | Meaning |
|---|---|
| Obligation Recall | Correctly retained reference obligations / reference obligations |
| Obligation Precision | Correctly identified obligations / all obligations asserted by the interpreter |
| Scope Fidelity | Correct scope, condition, exception and strength |
| Essential Style Retention | Retention of reference essential Custom Style characteristics |
| Authority Integrity | No unauthorized addition, weakening, substitution or source promotion |
| Ambiguity Handling | Correct recognition of unresolved interpretation; unsupported certainty and unnecessary abstention |
| Provenance Accuracy | Correct source/span and derivation attribution |

Define the obligation matching and equivalence rubric before scoring. Report missed obligations separately from invented ones; report undefined denominators as not applicable, not as perfect scores. Assess fidelity to original sources even when downstream components agree with the interpreter.

**H-01 obligation coverage.** Derive the reference obligation universe independently of the capabilities of every mechanism under evaluation. Authoritative sources include D0-R2, D1-A, SG-D1, SG-D2, applicable frozen FIX-03 requirements and other applicable, documented and Owner-approved product decisions. Concrete user obligations originate in the Source Record under the applicable normative rules.

Distinguish normative obligation principles, the research reference obligation taxonomy (RD-01), corpus obligation instances, and the mechanism coverage map (RD-02). Freeze the reference taxonomy and declared measurement universe before assessing coverage. Keep valid but unsupported obligations in the declared assessment population. Distinguish these from genuine ambiguity and normatively unresolved cases. Match mechanism coverage to the frozen universe and document capability-derived constructs separately from normative obligations. Semantic expressibility confers no normative authority. Freezing the taxonomy leaves user objects, attributes, relations and intentions open to evaluation under the applicable rules. Do not adjust it to fit a mechanism or improve its results. Document any legitimate later correction through versioning and reassessment.

### 4.2 Semantic Validator

Evaluate three distinct logical levels, not a frozen enum or schema:

1. **Semantic Assessment:** COMPATIBLE / INCOMPATIBLE / UNCERTAIN against independently established content obligations and reference labels.
2. **Evidence Sufficiency:** whether the evidence meets the specified policy for the relevant obligation class, route, capability and context; identify candidate-local versus systemic insufficiency.
3. **Policy Admission:** PASS / REJECT / INDETERMINATE under the specified policy. An established violation rejects; insufficient required evidence prevents admission even if content is reference-compatible. Both non-PASS outcomes block dispatch. Record simulated policy decisions separately from any authorized real action; research results confer no dispatch authority.

The following table scores semantic assessments, not admission. Use determinate reference-compatible and reference-incompatible cases, and report unresolved reference labels separately from assessor abstention.

| Reference class | COMPATIBLE | INCOMPATIBLE | UNCERTAIN |
|---|---|---|---|
| Compatible | Correct compatibility assessment | False semantic rejection | Compatible abstention |
| Incompatible | False semantic acceptance | Correct incompatibility assessment | Incompatible abstention |
| Genuinely ambiguous | Report separately and assess unjustified certainty | Report separately and assess unjustified certainty | Report separately |
| Normatively unresolved | Report separately and retain the applicable resolution boundary | Report separately and retain the applicable resolution boundary | Report separately |

Report at least:

- Semantic false-acceptance rate: incompatible references assessed COMPATIBLE / all reference-incompatible cases.
- Semantic false-rejection rate: compatible references assessed INCOMPATIBLE / all reference-compatible cases.
- Semantic abstention rate overall and by reference class; determinate-assessment accuracy and coverage, with unresolved reference labels separately characterized.
- Error among determinate compatible assessments: incompatible references assessed COMPATIBLE / all determinate-reference COMPATIBLE assessments; corresponding error among INCOMPATIBLE assessments using determinate reference cases only.
- Policy false admission and policy false non-admission, adjudicated separately against the specified policy, available evidence, route and context, with denominators of policy-ineligible and policy-eligible cases respectively. Distinguish REJECT and INDETERMINATE and record evidence insufficiency and its cause. A reference-compatible candidate may be correctly blocked by policy; a policy-required block is not a semantic classification error. Conversely, blocking does not establish detection of the underlying semantic violation.
- Compatible candidate non-admission rate: reference-compatible candidates with policy REJECT or INDETERMINATE / all reference-compatible candidates. This is a candidate-level coverage/product-impact metric, not a request-fulfillment rate or necessarily a policy error.
- Per-obligation error counts and rates, case-level outcomes, uncertainty/disagreement, confidence intervals where justified and denominator/sample size for every rate. Undefined denominators remain undefined.

Do not substitute one overall accuracy number for this breakdown. LLM-reported confidence is not calibrated evidence. Check whether added model calls provide genuinely incremental value, whether errors correlate and whether apparent improvements reflect over-refusal. Repeated evaluation of an unchanged candidate to obtain a favorable verdict is prohibited; pre-registered repeated evaluations for reliability measurement may be studied only without operational admission or selecting favorable outcomes.

### 4.3 Creative Generator and image evaluation

| Metric | Focus |
|---|---|
| Constraint Compliance | Applicable mandatory requirements, at candidate and image levels separately |
| Semantic Relevance | Meaningful relationship to the affirmation |
| Metaphorical Expressiveness | Quality and variety of symbolic interpretation |
| Artistic Quality | Aesthetic judgment of actual images |
| Custom Style Fidelity | Preservation of essential characteristics; separate prompt and image evidence |
| Novelty | Originality relative to comparison outputs or preceding series within applicable intent, style and mandatory constraints |
| Diversity | Within-intent variation across a series, including composition recurrence and near-duplication |
| Intent and Style Deviation | Departure from applicable user intent or style, distinguished from legitimate creative interpretation |
| Evaluable Output Availability | Whether the requested output exists and is evaluable, with reasons for unavailability |
| Creative Freedom | Range of legitimate interpretations within applicable intent, style and mandatory boundaries |
| Payload Integrity | Exact authorized candidate/prompt, applicable settings and bindings, serialization and metadata compared with the captured payload; identify fixture/fake transport versus authorized actual submission evidence |
| Candidate Admission Rate | Admitted candidates / evaluated candidates under the specified policy; not request fulfillment |
| Request Fulfillment | Full fulfillment, policy-permitted partial fulfillment, and non-fulfillment, each / all eligible requests in the declared evaluation population; retain unsupported, refused and failed cases within that population |

Define full fulfillment as completion of all requested applicable output and delivery requirements. Permitted partial fulfillment is a separately authorized, disclosed partial outcome that satisfies its own policy. All other eligible request outcomes are non-fulfillment. Record pending or unknown outcomes separately until resolved or at a pre-registered cutoff without counting them as successes. Label simulated completion or intermediate success explicitly in offline or text-only studies.

Report the common paired domains, conditional quality and diversity among evaluable outputs, fulfillment over the full eligible population, and non-admission structure separately. Show coverage, exclusions and reasons outputs were unavailable, including rejection, indeterminacy, unsupported cases and execution failures as applicable. Disclose selection effects from non-admission and unavailable imagery. Keep requests retained in the eligible population visible even where image comparisons cannot include them. Do not fabricate missing images or assign arbitrary aesthetic scores to ungenerated outputs.

Retain the applicable frozen FIX-03 principles. Evaluate novelty and diversity within preserved user intent, applicable style and mandatory constraints. Report intent or style deviation separately from legitimate creative interpretation, including creative interpretations outside a fixed catalogue. Distinguish composition recurrence and near-duplication from recurrence of a legitimately preferred direction. Evaluate Custom Style and symbolic preservation independently of within-intent variation and report creative freedom within applicable boundaries. The Detailed Research Protocol defines operational metrics.

Intent fidelity, candidate compliance, actual payload integrity and actual image compliance and quality are distinct assurance objects. Offline and text-only evidence cannot establish actual image quality. Subjective artistic QA outside admission does not itself require B-standard approval. Additional model calls still require separate authorization. Evaluate these constructs under §4.7 and adjudicate mandatory violations separately under §§4.6 and 6.1.

### 4.4 Comparators and controlled comparisons

| Comparator | Role |
|---|---|
| Existing Generator | Rise and Shine product capability, creative quality and fulfillment comparator |
| SG-01 Controlled Route | The existing SG-01 Controlled Renderer provides a synthetic offline engineering comparator within its declared supported domain. A live controlled route would require its own authorized mechanism. |
| HSGA | Proposed generative architecture for evaluation |

A live controlled route is optional for SAR-02. If an authorized live controlled comparator is unavailable, record it as unavailable and retain the offline engineering comparator in its declared domain. Restrict empirical conclusions and architecture recommendations to the evidence obtained, and report coverage and fulfillment under §4.3. Comparator absence does not imply inferiority or support a three-way live claim. A live controlled comparator requires separate authorization and a mechanism that establishes applicable admission, real capabilities and dispatch authority. Synthetic artifacts retain their offline authority. Every real comparator action is subject to §5.4.

Use paired requests and comparable settings where they support the intended inference. For each comparison, declare the controlled factors, architecture treatment variables, model and provider variables, resource and configuration differences, intended comparison and admissible causal interpretation. Depending on the claim, the protocol may use fixed-model, resource-matched, architecture-native, model-sensitivity or joint architecture-plus-model configuration comparisons. These are options, and architecture-native designs may retain their own internal structures, call counts, role allocations and context processing. Attribute a changed-model benefit to the model where the design supports that attribution. Claim an architecture effect only where the comparison separates it from the model effect. An architecture-native benefit obtained with additional calls or resources establishes no equal-budget advantage. Control the image model and relevant generation settings when required by the image-quality inference. Otherwise narrow the claim.

Component-level comparisons may supply shared, appropriately constructed reference Protected Intent where needed to isolate downstream generation, representation or validation. End-to-end comparisons supply identical source snapshots and applicable source-level context. Each architecture performs its own interpretation using its declared mechanism. Evaluate interpretations and outputs against independent references. When interpretation is itself under study, particularly for H-09, do not require a common precomputed Protected Intent. Research reference objects confer no normative or runtime authority.

For H-02, assess two distinct dimensions.

- **Common Semantic Domain.** Compare representation effectiveness under appropriately matched semantic coverage.
- **Semantic Extensibility.** Evaluate representation and preservation of meaning beyond a frozen creative catalogue. Allow the open representation to express concepts and relationships beyond that catalogue.

Use a faithful closed creative registry comparator and distinguish it from a deterministic Safety Gate registry. Consider, where applicable, semantic coverage, fidelity, compositional and relational expressiveness, Custom Style, symbolic preservation, creative diversity, mandatory compliance and maintenance burden. Evidence for open creative semantics does not establish a case against deterministic Safety Gates. If a suitable matched control is unavailable, narrow the affected causal claim or report it as inconclusive.

Use ablations to isolate contributions of interpretation, structuring, constraint-aware generation and probabilistic validation. Deliberately weakened controls are limited to authorized no-dispatch research, including offline or fake transport or specifically authorized text-only work, with all applicable safety boundaries preserved. For H-04, compare deterministic-semantic-only, probabilistic-semantic-only and combined semantic checks on matched candidates with the same mechanical integrity checks. These weakened controls remain strictly no-image-dispatch, with any text-model calls separately authorized. For H-06, use a matched no-regeneration arm with the same initial conditions and applicable obligations, and report differences in attempts, cost and time. Where an informative matched arm is infeasible, narrow the claim or leave the hypothesis inconclusive.

Fix the exact comparator artifact identity and effective configuration before its comparison. The Development Baseline records the Owner-confirmed repository and CI point. The Production Reference records the Owner-supplied released revision. Either may inform a separately chosen Experimental Baseline if appropriate to the claim. Fix that baseline for each comparison and record provenance under §6.2.

### 4.5 Owner product evaluation

Use both absolute criterion ratings and paired blinded preference comparisons for Owner product evaluation. The protocol must define the rubric for affirmation relevance, adherence to visual requirements, style fidelity, metaphor, originality and aesthetic appeal. Include ties and neither-preferred options in paired reviews. Randomize or counterbalance presentation order where feasible, hide architecture labels and disclose assignments after the series is complete. Record hard-constraint violations and uncertainty separately and include failures and unfulfilled requests in the applicable reporting under §4.3.

The Owner is currently the sole user and is willing to participate in a separately authorized experiment. Owner aesthetic judgments are legitimate product evidence limited to the user perspective supported by the evaluation. Report uncertainty and disagreement. Apply the sampling and residual-risk limitations in §§3.4 and 6.1.

### 4.6 Separate acceptance dimensions

| Decision gate | Required evidence |
|---|---|
| Research validity | The design, comparison, evaluation and evidence support the stated scope of inference. Limited component-level conclusions may be established without full product integration. |
| Technical acceptance | Obligation fidelity, correct authority, no bypass, complete applicable validation, exact payload identity and lifecycle integrity. |
| Functional preservation | Applicable frozen functional contracts and entry-point requirements are met. This is an explicit, non-compensable requirement for operational and production acceptance. |
| Product acceptance | Creative freedom, aesthetic and symbolic quality, personalization, diversity, fulfillment, cost and latency meet the applicable product requirements. |

Functional preservation includes language ownership, subscriptions and scheduled-delivery semantics, Profile contracts, accounting and reservations, lifecycle, persistence, and applicable entry-point behavior. Authoritative specifications define the full obligations. Entry-point parity requires each path to satisfy its applicable contract, including legitimate differences between paths. Untested integration properties remain unestablished.

Any future operational or production recommendation must satisfy the applicable technical, functional and product gates independently. Report mixed outcomes and the applicable decision gates separately. Mixed and domain-specific research recommendations remain admissible when supported by the evidence. Safety, functional preservation and artistic quality cannot offset one another in an overall score. Establish numerical criteria through the appropriate later protocol and approval under §§1.4 and 8.2.

### 4.7 Independent research evaluation

Distinguish runtime interpretation, generation and validation from independent research evaluation. Internal Semantic Validator decisions and other self-assessment cannot independently establish confirmatory correctness. Select evidence according to the construct, using deterministic normative oracles, independent reference labels, human evaluation, calibrated model-based evaluation or observed technical evidence as appropriate. Where applicable, evaluate against the original Source Record and independent references so that assessment can detect errors inherited from the candidate architecture’s own interpretation.

For any confirmatory model-based evaluation, address architecture blinding where feasible, order randomization or counterbalancing, calibration against independent references or human assessment, self-preference and correlated failures. Record judge identity, version, prompt and effective configuration, agreement and disagreement, and residual limitations. Different model families may reduce shared errors without establishing statistical or epistemic independence. An added model evaluator is optional and must suit the construct. Where sufficient evaluation independence cannot be established, limit the evidence to exploratory use or report the conclusion as inconclusive, as appropriate. Owner aesthetic evaluation remains within the scope in §4.5. Any calibration or evaluation calls require separate authorization.

## 5. Research boundaries and authorization

### 5.1 Binding red lines

- D0-R2 remains binding unless explicitly amended or supplemented through its approved mechanisms. The minimum no-B contract refuses uncovered untrusted prose; universal SYSTEM_NO_TEXT requires semantic noncontradiction, not merely a no-text clause. Existing D0-R2 gate rules exclude additional model calls for admission.
- D1-A negative scope persists across nominal enumerations. Exactly two closed legacy exceptions: `No people, ocean` and `No people, beach at sunset`, subject to the previously agreed standalone-segment and normalization rules; no extension to synonyms, other coastal nouns, subjects or mixed lists.
- SG-D1: unresolved relational negatives remain BLOCKED: UNRESOLVED_EXCLUSION. Never turn a local prohibition into a global one. SG-D2: narrative-only mentions have no automatic literal positive visual authority.
- O-1: all eight conditions in D0-R2 §13 are incorporated by reference without alteration. Controlled routing is limited to ALLOWED resolutions, selected both before enrichment and before any safety failure, faithfully preserving intent, mandatory exclusions, registered style/mode and essential Custom Style, and independently passing the same final Safety Gate and all other applicable gates. Any material functional or image-quality regression requires separate Owner review before activation. No controlled reconstruction after a safety failure; no reconstruction of BLOCKED/UNSUPPORTED resolutions. Preserve D0-R2 §10’s tightly scoped non-safety alternate rules; this does not authorize a safety-veto fallback.
- No blanket enrichment shutdown, silent Custom Style or symbolic nuance loss, arbitrary enforcement weakening, or synthetic authority escalation.
- No unapproved operational admission, production access/activation, Git by Codex or Claude Code, credentials/secrets/`.env` access, or `tmp/` access/traversal. No repository-root search paths or unrestricted recursive discovery even with filters. Restrict future inspection to explicit permitted files/directories. No provider calls or code changes under this charter alone.

### 5.2 Evidence and uncertainty boundaries

| Evidence type | Limit |
|---|---|
| Deterministic structural/integrity evidence | Establishes specified mechanical properties, not arbitrary-language meaning |
| Bounded deterministic semantics | Establishes properties only within approved declared coverage |
| Probabilistic semantic evidence | Empirical, fallible; no formal proof or independent authority |
| Insufficient or conflicting evidence | No permission to dispatch |
| Actual-image evidence | Separate post-generation assessment, not retroactive prompt admission |

Distinguish original intent uncertainty, creative candidate uncertainty, evidence uncertainty, provider capability uncertainty and actual-image assessment uncertainty. Also distinguish candidate-local from systemic insufficiency. An unresolved source obligation cannot be cured by creative reconstruction. A candidate-local problem may warrant a genuinely new candidate only under a future approved policy. An absent approved enforcement standard or unknown provider capability cannot be cured by a different creative proposal. Validator outages require separate operational retry policy. No outcome with insufficient required evidence may authorize dispatch.

### 5.3 Lifecycle and delivery research (SAR-D12, experimental only)

D0-R2 defines attempt-local stopping and prohibits automatic alternate prompts following safety vetoes; it does not define a complete request-level terminality object. Automatic regeneration after a safety veto is currently unauthorized. A fresh attempt identifier alone does not confer continuation permission. Distinguish user-initiated fresh requests, candidate regeneration, unchanged transport retry, unknown remote outcomes and delivery retry.

Future regeneration studies must preserve immutable Protected Intent, route identity, full validation of each genuinely new candidate, terminal prior attempts, no reused dispatch permission, no verdict shopping, and bounded request-level attempts/cost/time. D0-R2 permits unchanged transport retries under specified conditions; distinguish reusable validation evidence from future submission authority and do not assume remote idempotency or one charge on timeout.

Partial delivery requires explicit future policy for eligible formats, independent text checks, visible disclosure of visual failure, history/accounting and durable duplicate protection. Preserve D0-R2 §§7 and 10 requirements (normative, not a claim about current generator behavior): an early V1 block requires zero paid generation work (T=E=S=I=0); preceding input transcription is permitted under the applicable input contract. V2–V4 failures may follow paid text work; stop image work, return no successful image/card and apply required cleanup, reservation release and entry-point-specific terminal handling, including scheduled logical-delivery requirements. Measure actual existing-generator behavior separately. Do not authorize text-only delivery after a block by reclassifying it as successful card delivery. Real provider or Telegram dispatch experiments involving behavior outside the current contract require an explicit applicable temporary normative authorization or amendment, not merely budget approval; otherwise use offline/fake providers.

### 5.4 Staged research program and gates

| Stage | Scope | Authorization boundary |
|---|---|---|
| Research Charter (SAR-02) | Objectives, method, red lines and deliverables | Consolidated document review and Owner acceptance; no execution |
| Architecture Research | Static investigation of existing mechanisms and alternatives | Separately scoped research authorization |
| Offline Research Environment | Corpus, reference labels, isolated harness and fake providers | Separate implementation scope, isolation and review |
| Offline Evidence Assessment | Deterministic and static-candidate assessment, lifecycle simulation | Separate approved execution scope; no live provider calls |
| Text Model Experiment | Investigate three functional roles, no image dispatch | Separate protocol, model/call/budget approval and applicable normative boundaries |
| Image Model Experiment | Isolated image evaluation of eligible live comparators, blinded review and offline controlled engineering evidence. A separately authorized live controlled comparator is optional. | Separate approved protocol, applicable normative basis and any required temporary authorization or amendment, capability verification, exact-payload controls, budget and stopping rules |
| Research Conclusions | Evidence synthesis and recommendation, including negative results | Independent review and Owner decision |
| Operational Normative Contract | Propose applicable B-standards, amendments and evidence/lifecycle policy | Separate explicit normative approval |
| Integration & Production Readiness | Dispatch, runtime consumers, integration tests and release prerequisites | Separate implementation scopes, audits and Owner acceptance; separate deployment authorization |

The four distinct authorization decisions are **Research Authorization**, **Experiment Authorization**, **Operational Authorization** and **Production Deployment Authorization**. Each requires independent approval. Charter acceptance grants none of these execution authorities. Research authorization alone does not authorize model calls or code modifications. Every action below requires its own applicable approved scope and normative conditions.

| Action | Scope and authority boundary |
|---|---|
| Offline analysis | Static or deterministic analysis within separately approved research and execution scopes, with no live provider calls or delivery. |
| No-dispatch candidate research | Evaluate candidates without image-provider submission or Telegram delivery, within an approved research or experimental scope. Any actual text-model calls require their own authorization. |
| Fake transport and lifecycle simulation | Use authorized fixtures or fake transport to assess behavior. Simulation supplies evidence about the declared setup and confers no real submission or delivery authority. |
| Actual text-model calls | Require specific experiment, model, call and budget approval and applicable normative conditions. Text-only authorization confers no image submission or delivery authority. |
| Actual image-provider submission | Requires a separately approved experiment, applicable normative admission, verified capabilities, exact-payload controls and stopping rules. An isolated environment, a dedicated research key or absence of user delivery still involves real submission. |
| Telegram delivery | Requires separate applicable permission and compliance with delivery, lifecycle and entry-point contracts. Image submission approval confers no Telegram delivery permission. |
| Production deployment | Requires separate Owner deployment authorization and satisfaction of release prerequisites, including a fresh verified backup and rollback capability. |

Apply the real submission boundaries to every comparator, including Existing Generator. Known-incompatible candidates may not be submitted under this Charter. Unresolved cases require a valid applicable resolution before submission, with all other admission and authority conditions satisfied. The RS-REL-01 release-specific N-2 exception provides no research dispatch authority.

Before any real experiment, define temporary rules, data handling, metrics, model and configuration, cost and call/time limits, stop conditions and responsible reviewers. Any temporary normative permission must be explicit, independently authorized and confined to the particular approved experiment. Preserve D0-R2 everywhere outside that approved scope. If normative constraints prevent a comparison, redesign it, narrow the claim, report an inconclusive result or consider a separately authorized normative permission. This Charter grants no such permission. A temporary experimental authorization does not provide evidence that the policy under evaluation is acceptable. Production rollout requires its own authorization and is outside the experiment stages.

## 6. Experimental integrity

### 6.1 Stop conditions

| Type | Trigger | Required response |
|---|---|---|
| Hard Stop | Authority/scope violation, unauthorized dispatch, admitted hard violation during real dispatch, payload bypass, prohibited route switching, duplicate delivery or other pre-registered critical failure | Stop the affected experiment, prevent further calls/delivery, preserve evidence and review before explicit resumption |
| Methodological Stop | Held-out leakage, invalid reference labels, materially incomparable configurations or broken measurement | Pause the affected evaluation; document the problem, correct the protocol and re-establish independent evaluation where necessary |
| Budget Stop | Reaching the authorized call, time or spending ceiling, or inability to guarantee the next call stays within the ceiling | Stop further calls; record actual use and seek separate approval before expansion |

Intentionally incompatible test candidates, abstentions and simulated rejections can be expected inputs or outcomes of authorized offline research. Distinguish these from actual violations of experiment boundaries. A simulated false acceptance is material negative evidence and confers no authority to submit the candidate. Pre-register how such failures affect the offline study, progression to provider evaluation and stopping. Apply the Hard Stop rules to real provider and image evaluation. Stop affected real image evaluation on applicable critical failures and do not use a fallback route after a veto. Rollback applies to subsequent requests and cannot bypass the current failed attempt.

Record each critical violation individually, distinguishing component-level errors, successful downstream interception, validation errors, policy admission failures and unauthorized provider submission. Analyze decision-relevant critical subgroups where applicable. Report critical violations separately from aggregate metrics, aesthetic quality and fulfillment. None of those results can compensate for a mandatory violation. Empirical reliability confers no normative permission.

Distinguish formally established invariants within their declared domains from empirical zero-event observations. Zero observed violations establish neither zero risk nor universal safety. Report appropriate quantitative uncertainty or residual-risk bounds where the sampling design and statistical assumptions justify them. State explicitly when residual risk has not been quantitatively established because no valid quantitative model is available. Adversarial-corpus results do not establish production prevalence. Leave numerical risk models and confidence levels to the Detailed Research Protocol.

### 6.2 Methodological safeguards

- Pre-register the analysis plan under §1.4, including hypotheses, comparators, metrics, labels, sampling and stopping criteria before the applicable experiment authorization. Report protocol deviations and keep post-result revisions separate as exploratory analyses or new studies.
- Retain negative results, failures, refusals, abstentions and all attempted outcomes. Do not select only attractive images or favorable validator votes.
- Apply §3.4 to disjoint semantic-family partitions, held-out isolation and reference integrity. Use a new independent set if required.
- Record exact comparator artifact and Experimental Baseline identity under §4.4. Evidence provenance includes, as applicable, immutable commit, release or artifact identifiers, effective configuration and feature flags, model and provider identifiers, prompt and policy revisions, context and resource settings, supported seed settings, and corpus and reference-label versions. Record case IDs, source and reference labels, exact candidate and payload identity where applicable, outcomes, decisions, costs and timing as needed for reproducible analysis.
- Control temporal drift in comparable provider-based evaluations using an appropriate design, such as interleaving or block randomization. Record timestamps and available provider-reported model or version identifiers. Document unobserved version information and limits to provider stability. Pre-register the provider-change handling policy. If a change affects comparability, stop, repeat the affected block under separate authorization, or narrow the inference to the supported observation window as appropriate. Disclose the change and its effect on analysis. Affected results may not be silently pooled, discarded or retrospectively redefined.
- Preserve the authorized artifacts and parameters needed to reproduce the analysis even where exact stochastic generation cannot be reproduced. Exclude credentials and secrets. Define data minimization, access, storage, retention and separation from production in the later protocol. Production history access requires separate authority.
- Independently review methods and conclusions under §4.7. The developer must not unilaterally choose criteria for its own solution. Keep observed facts, inference, proposals and unresolved assumptions distinct. Report uncertainty, sample limitations, disagreement, correlated failures and the assumptions of any quantitative bounds.

### 6.3 Research economics

Measure interpretation, enrichment, semantic validation, image generation and unsuccessful-attempt costs separately; record retry count, partial delivery frequency, fulfillment and end-to-end latency. For each declared comparable evaluation population, use total attributable costs (including rejected candidates, failed requests and retries) as the numerator. Report cost per request (all evaluated requests), cost per full fulfillment (fully fulfilled requests), and cost per permitted fulfillment (fully fulfilled plus policy-permitted partially fulfilled requests). Report permitted partial delivery rate over all eligible requests and full and non-fulfillment rates separately under §4.3. Clearly label simulated versus observed delivery outcomes. Zero denominators give undefined rates, not zero costs; report total cost and counts alongside. Do not hide failures by computing only successful-request latency; report failure latency and overall distributions as appropriate.

A cheaper model that causes repeated rejections or calls may be more expensive overall; an extra validator may add little if constraint-aware generation and deterministic checks already suffice. Compare marginal benefits under matched conditions. No model, provider, numeric budget or cost threshold is selected in this charter.

## 7. Research deliverables, responsibilities and open obligations

### 7.1 Program deliverables

These are deliverables of the whole future research program, not claims of completion and not implementation authorizations within SAR-02.

| ID | Deliverable | Expected content |
|---|---|---|
| RD-01 | Obligation Taxonomy & Authority Model | Source/applicability/strength, original sources, protected obligations, unresolved interpretations and provenance |
| RD-02 | Deterministic Enforcement Coverage Map | Fully mechanical, bounded and unsupported classes, potential B coverage, explicit residual risks |
| RD-03 | Intent Interpretation Assessment | Fidelity, omissions, invented obligations, scope, ambiguity, cascade errors |
| RD-04 | Open Creative Representation Assessment | Representation alternatives, expressiveness, completeness and evidence binding |
| RD-05 | Semantic Validator Reliability Assessment | Incremental detection, false decisions, abstention, correlation, limitations |
| RD-06 | Research Corpus & Ground Truth | Versioned RC-A/B/C, labels, partitions, coverage and adjudication |
| RD-07 | Comparative Evaluation & Ablation Results | Three comparators, matched configurations, component contributions, negative results |
| RD-08 | Custom Style & Symbolic Fidelity Assessment | Essential requirements, hard mode identity, creative nuance and image evidence |
| RD-09 | Regeneration & Lifecycle Assessment | Request/attempt/provider/delivery distinctions, terminality, operational failure and partial-delivery policy options |
| RD-10 | Cost, Latency & Fulfillment Assessment | Full cost accounting, retry and refusal rates, performance/quality trade-offs |
| RD-11 | Owner Product Evaluation | Absolute ratings, blinded preference pairs, limitations and disagreement |
| RD-12 | HSGA Architecture Recommendation | Evidence-based options, coverage limits, open risks, recommended scope or rejection of unsupported alternatives |
| RD-13 | Proposed Operational Normative Contract | Proposed B-standards and/or amendments if justified, explicit residual-risk policy, approval prerequisites; proposal only |

### 7.2 Responsibilities

| Role | Responsibility |
|---|---|
| Owner | Product decisions, research/experiment/operational/deployment authorizations as applicable, product evaluation, final acceptance and all Git operations |
| Teya | Joint architecture, hypotheses, research methodology, critical evidence analysis, task preparation and joint review |
| Codex | Technical research, scoped research tools/implementation and tests when separately authorized; no Git or unilateral acceptance-criteria selection |
| Claude Code | Independent read-only audit of methodology, architecture, implementation and evidence under a separately scoped assignment; no Git |
| Cursor Agent | Production deployment only after separate Owner authorization and verified pre-deployment backup/rollback readiness |

No role allocation grants access or permission beyond the applicable scope. In particular, the model roles in Section 2.2 are product-architecture functions, distinct from the development and audit roles in this table.

### 7.3 SAR findings register — carry-forward, not remediation

The following 19 positions are preserved from SAR-01 and its independent audit. Severity reflects consequences for HSGA adoption, not a reopening of accepted Stage 1A–1D work. All remain research, policy, technical or documentation obligations as appropriate; none is remediated by this charter.

| ID | Severity | Disposition / obligation |
|---|---|---|
| SAR-F-01 | BLOCKER | Open semantic admission lacks an approved contract; distinguish B approval and probabilistic amendment; SYSTEM_NO_TEXT applies universally. |
| SAR-F-02 | MAJOR | Bounded interpretation is not complete Protected Intent; investigate open essential requirements and provenance. |
| SAR-F-03 | MAJOR | Structured claims do not establish semantic completeness; evaluate exact provider-visible content and cross-field semantics. |
| SAR-F-04 | MAJOR | Real source/activity authority remains an outstanding dependency raised in Stage 1B; no generated or Profile-context authority promotion. |
| SAR-F-05 | BLOCKER | Production dispatch closure absent; separate production authorization, no raw escape and no synthetic promotion. |
| SAR-F-06 | MAJOR | Existing fallback behavior differs from D0 safety handling; distinguish typed safety failure from operational errors and review oracles individually. |
| SAR-F-07 | MAJOR | Arbitrary Custom Style fidelity unestablished; retain original text and essentiality, measure fidelity. |
| SAR-F-08 | MAJOR | Symbolic freedom must retain selected mode identity and essential nuance. |
| SAR-F-09 | MAJOR | Real provider capability/counter evidence unverified. |
| SAR-F-10 | MAJOR | Corrected policy gap: D0 defines attempt-local stopping and prohibits automatic alternate prompts after safety veto, but lacks a complete request-level terminality object. Automatic regeneration remains unauthorized; fresh attempts alone confer no permission. Explicit future request-level policy required. |
| SAR-F-11 | MAJOR | Text-only completion lacks explicit delivery semantics, checks, accounting and durable duplicate protection. |
| SAR-F-12 | MAJOR | Reconcile reusable validation evidence, provider-submission permission, unchanged retry and uncertain remote outcomes. |
| SAR-F-13 | MAJOR | Acceptable safety/creativity trade-off unverified; empirical question, not a code defect. |
| SAR-F-14 | MAJOR | Three-scene controlled sample cannot provide general product coverage; specialized comparator/route only. |
| SAR-AF-01 | MAJOR | Adapter re-derives style/coastal/exclusions; competing authority must not survive at the future dispatch boundary. |
| SAR-AF-02 | MAJOR | Broad catches could convert future typed safety failures into fallback or scheduler retries; typed handling is an integration prerequisite. |
| SAR-AF-03 | MAJOR | Symbolic mode discards supplied override; future transport must not silently rebuild after validation. |
| SAR-AF-04 | NOTE | Carry forward expanded prompt-mutation inventory; documentation correction, not a newly remediated code defect. |
| SAR-AF-05 | NOTE | Adapter owns sidecar prompt metadata; future metadata must bind authorized and submitted payload. |

SAR-F-10 was partially verified in the original audit and its wording was reconciled in CP-01; the underlying obligation remains open. AF-01/03/05 are observed current code properties with future integration hazards; AF-02 describes current catch structures and potential future consequences, not actual present-day SG-01 bypass. AF-04 is inventory completeness. The inventory includes `_build_image_prompt` positive-text interpolation and image-hint insertion, `_augment_photo_override_prompt`, `apply_coastal_scene_intent`, `image_prompt_trace`-dependent behavior and adapter-owned `prompt`/`final_prompt` sidecar metadata. A single statically identified image POST is not proof of application-wide closure. Complete prompt mutation before final assessment; bind exact payload/settings and metadata. No function signature or implementation is approved.

### 7.4 Existing stage obligations and boundaries

Keep individual original dispositions in their respective audit registers. Do not merge them into SAR, reopen accepted corrections, relabel accepted limitations as open defects, or copy the CP-01 aggregate `Stage 1C F-1–F-9 — OPEN` row as authoritative.

| Register | Carry-forward subjects (not new status assignments) |
|---|---|
| Stage 1A | F-07 vocabulary/aliases reconciliation; F-08 clarified RequestClass semantics; F-09 runtime equivalence and parser isolation; F-10 Attachment.frame_level before reliance |
| Stage 1B | F-04 real V0 source-kind/activity authority; F-07 broader canonicality and subclass/equality hardening |
| Stage 1C | Canonical alias normalization boundary; external release/review governance; registry schema-arity hardening (Stage 1C F-6); declared semantic completeness limitations; production registry compatibility; evidence provenance (Stage 1C F-10). Refer to the individual dispositions in the Stage 1C Implementation Record and the separate Stage 1C register reproduced in the Stage 1D Implementation Record; preserve all accepted, closed and deferred dispositions, without aggregate reassignment |
| Stage 1D + CP-01 | F-1 and F-5 CLOSED; F-2/F-3 ACCEPTED LIMITATIONS; F-4 non-ASCII capacity oracle DEFERRED; F-6 layered offline validation accepted, integration closure assurance DEFERRED; F-7 historically VERIFIED by Owner Git status, isolation-only diff, exact staged file footprint and CI evidence (historical Owner acceptance, not independently reverified in the consistency review; no current worktree assertion); no changes by SAR |

Other prerequisites remain explicit: real provider capabilities/counters, production-approved registries/policies/routes, non-bypassable dispatch, application-wide lifecycle, Interactive/Profile/More/scheduled/CLI coverage, arbitrary Custom Style fidelity, LLM enrichment enforcement, symbolic nuance, actual image-quality assessment, integration regression review and backup/rollback readiness. Registry governance, capacity and idempotency policies, diagnostic INDETERMINATE mapping and exact-payload/metadata binding remain unresolved. N-2 custom-photo fallback remains OPEN and separately scoped. D0-R2 §10 retains the N-2 production prerequisite, including for SG-01 deployment. All four integration requirements and existing fail-closed behavior for custom-style preset conflicts remain binding. The Owner-supplied RS-REL-01 exception is limited to the specific deployed revision identified in §1.1 and the front matter. All eight O-1 conditions in D0-R2 §13, including separate Owner review of material functional or image-quality regression before activation, remain binding; regular backups are separate from mandatory verified pre-deployment backup.

### 7.5 Scope exclusions

Do not automatically absorb N-2 custom-photo fallback; FIX-03B-2B-2 LLM enrichment validation implementation; FIX-03B-2C canonical archetypes; FIX-03B-3 style propagation; FIX-03C visual memory; FIX-03D visual diversity, clear-air nature and interior aesthetics; FIX-03E mandalas/symbols and navigation; RS-UX-01 Reply Keyboard removal; RS-TEXT-01 Russian е instead of ё; regular backup implementation; or small talk. Existing behavior and desired capabilities may inform research coverage and dependency decisions. No implementation of these tasks is authorized here.

## 8. Research Charter acceptance and next step

### 8.1 Acceptance criteria for the charter itself

- Reflect the complete Owner-agreed SAR-D01–D14 direction, including experimental-only SAR-D12 and future-route qualifications for D01/D02.
- Preserve D0-R2, D1-A, SG-D1, SG-D2, O-1, synthetic authority and all existing accepted dispositions.
- Include nine hypotheses, 27 research questions, three functional LLM roles, two complementary tracks, three corpora, three comparators and the 13 program deliverables. Keep research validity, technical acceptance, non-compensable functional preservation and product acceptance distinct.
- State research and experimental authorization boundaries, data handling requirements, methodology, stop conditions and unresolved decisions without pretending to have evidence not yet obtained.
- Record SAR findings and operational deviations without representing them as repaired or erased.
- Obtain repository/normative consistency review and independent methodological review before final document acceptance. Resolve material contradictions through explicit Owner decisions; no implementation or normative changes in either review.

### 8.2 Decisions deliberately left open

The future Detailed Research Protocol must justify sample sizing and evidence sufficiency for each applicable population and comparison (MA-F-13). Address decision-relevant effects, uncertainty, expected variability, dependence among observations, statistical power or precision where applicable, and limits of convenience samples. Deterministic and engineering claims require evidence sufficiency appropriate to their declared domain. Sample sizes and evidence targets remain open.

The protocol must specify, as applicable:

- Numerical margins and acceptance criteria, including prior Owner approval of product-quality margins, and the detailed pre-registered analysis plan and multiplicity methods under §1.4.
- Corpus sizes and partition ratios, label authorship and adjudication arrangements, evaluator selection and calibration, and held-out access controls under §§3.4 and 4.7.
- Temporal execution and provider-change procedures under §6.2, cost and latency models under §6.3, and rare-event uncertainty methods under §6.1.
- Data minimization, access and retention controls, specific research configurations and evidence requirements, and applicable resource and stop criteria.

Normative permissions require independent approval through their applicable mechanisms. These include B-standard approval, probabilistic admission thresholds, changes to authoritative interpretation, operational retry or regeneration, partial delivery and any required D0-R2 amendment or temporary normative instrument. The Detailed Research Protocol specifies research methods and provides no authority to grant those permissions. Providers and models, role combination and topology, schema and implementation, budgets, operational confidence, abstention and diagnostic mapping policy, request-level continuation, retry limits, provider capability contracts, routes and activation conditions remain open. Narrower operating envelopes, different architectures and negative, mixed or inconclusive outcomes remain admissible.

### 8.3 Immediate next step

The SAR-02 Consistency Review returned REVISION REQUIRED (seven MAJOR, five MINOR, no BLOCKER). Owner and Teya agreed the SAR-02-CP-01 document-only correction scope. The Owner confirms that the SAR-02-CP-01 Targeted Verification reported all twelve corrections VERIFIED on 26 November 2026. The historical correction record remains in §8.5.

The independent Claude Code Methodology Audit returned ACCEPT WITH CONDITIONS — TARGETED CORRECTIONS REQUIRED (no BLOCKER, eight MAJOR, seven MINOR). The audit did not reopen CP-01 findings. Owner and Teya completed adjudication and approved OD-1 through OD-11. CP-02 implements their approved resolution as documentary revisions (§8.6). At submission, the Charter was a revised review candidate pending independent targeted verification and explicit Owner Charter Acceptance & Freeze. Any next phase or execution requires separate authorization.

On 26 November 2026, Claude Code completed SAR-02-CP-02 Independent Targeted Verification. The Owner supplied the verdict **SAR-02-CP-02 VERIFIED — READY FOR OWNER CHARTER ACCEPTANCE & FREEZE.** The verification reported 10/10 C01–C10 verified, 15/15 MA-F-01–MA-F-15 addressed and 11/11 OD-1–OD-11 implemented. It verified the MA-F-13 deferral to the Detailed Research Protocol and confirmed preservation of CP-01 corrections and substantive safeguards, existing Charter registers and normative boundaries. It reported no new material findings, no identified CP-02 regressions, no operational deviations and three non-blocking notes.

On 26 November 2026, the Owner accepted SAR-02-CP-01, SAR-02-CP-02 and NB-01 through NB-03 and froze the Research Charter v1.0. The final status is **OWNER ACCEPTED / FROZEN v1.0**. No additional correction package is required.

- **NB-01 — OD traceability granularity.** Accepted without substantive Charter correction. Independent verification located the misassociation in the developer's implementation report and confirmed that the collective C02 row in §8.6 is substantively accurate. OD-3 (Live Controlled-Route Comparator) is in §4.4, OD-8 (Model Capability and Architecture Robustness, including RQ-B18) is in §§2.5 and 4.4, and OD-11 (H-02 Open Semantics versus Closed Registry) is in §4.4.
- **NB-02 — Joint reporting versus parallel reporting.** Accepted without Charter correction. The Detailed Research Protocol will specify how to present related metrics and selection effects while preserving separate, non-compensatory evaluation dimensions.
- **NB-03 — C05 cross-reference breadth.** Accepted without Charter correction. The existing cross-references leave substantive requirements and their interpretation intact.

The Owner authorized Detailed Research Protocol design after documentary closure and repository acceptance, solely as a subsequent documentary research stage. The authorization boundaries in §5 remain binding.

### 8.4 Reference record and limitations

Normative references for CP-02:

- `docs/architecture/SG-01_Safety_Gate_Design_v1.md` (D0-R2)
- `docs/product/RS_FIX03_Visual_Diversity_Frozen_Specification_v1.0.md`

Historical Stage 1 references retained for their individual dispositions in §7.4:

- `docs/architecture/SG-01_Stage1A_Implementation_Record.md`
- `docs/architecture/SG-01_Stage1B_Implementation_Record.md`
- `docs/architecture/SG-01_Stage1C_Implementation_Record.md`
- `docs/architecture/SG-01_Stage1D_Implementation_Record.md`

Decision sources supplied in the project conversation (not asserted to exist as repository files): Codex SAR-01 Hybrid Architecture Feasibility Assessment §§1–17; Claude SAR-01 Independent Architecture Audit §§1–12; SAR-01-CP-01 Targeted Architecture Decision Reconciliation §§1–10; Owner + Teya strategic and SAR-02 discussions of 25 November 2026. CP-01 contains the four-question normative matrix (investigation, B-standard implementation, probabilistic admission, synthetic mechanisms). That matrix remains a historical decision reference, subject to the accepted minor notes: separate subjective QA from admission, map diagnostic uncertainty to BLOCKED without inventing authority, preserve individual Stage 1C dispositions. Its summary counts six non-blocking clarifications while its section 6 enumerates seven; preserve the substance, not the count.

Operational history: Codex SAR-01 reported attempted `tmp/` traversal via unrestricted `rg --files` (access denied, no content returned); Claude SAR-01 audit reported a root-level Grep returning import-line matches from `tmp/fix03a_r3` (no files opened or content used, per report). SAR-01-CP-01 was document-only with no new deviation reported. SAR-02 Codex Consistency Review reported a pre-attachment repository-root AGENTS.md discovery command (`rg --files --hidden -g AGENTS.md -g '!.git'`) that attempted traversal of `tmp/`, received access denied, and returned no `tmp/` file contents; no subsequent traversal was reported. The review did not have the complete SAR-01 reports or Owner–Teya discussion record; exact historical descriptions, severities and reconciliation details were not independently reverified. SAR-02-CP-01 is a document-only correction based on that review and Owner + Teya reconciliation; it does not claim to have independently resolved repository facts or remediated underlying SAR findings. The CP-01 author reported no independent inspection of the source repository, test execution, Git/CI verification or production access. CP-01 was prepared outside the repository as a review candidate pending verification. No underlying technical finding was closed by drafting it.

CP-02 documentary scope and deviation. Before reading the attachment’s restrictions, Codex ran the repository-root discovery command `rg --files --hidden -g AGENTS.md -g '!.git' -g '!.venv' -g '!node_modules'`. It returned `AGENTS.md` and failed with access denied at `tmp/fix03a_r2/pytest_r2`. No `tmp/` file contents were returned or used. The subsequent work used exact authorized paths and the Owner-supplied assignment. The Stage 1 implementation records above were outside the CP-02 evidence scope. Historical development, CP-01 verification and production information were taken from the Owner; CP-02 makes no independent verification claim for them.

### 8.5 SAR-02-CP-01 correction traceability (historical record)

| Consistency finding | Revised sections |
|---|---|
| CR-F-01 | §§4.4, 5.4: offline controlled arm, no synthetic promotion, unavailable live evidence |
| CR-F-02 | §§2.1, 4.2: semantic assessment, evidence sufficiency and policy admission separately |
| CR-F-03 | §§1.4, 4.4: matched controls for H-02, H-04, H-06 |
| CR-F-04 | §§3.4, 6.2: disjoint semantic families across all partitions |
| CR-F-05 | §5.3: D0 normative lifecycle and transcription boundary versus current behavior |
| CR-F-06 | §7.4: N-2 explicit pre-deployment prerequisite |
| CR-F-07 | §§5.1, 7.4: full O-1 by reference, timing, same gate, regression review, non-safety alternatives |
| CR-F-08 | §5.4: four distinct authorization decisions |
| CR-F-09 | §§4.2–4.3, 6.3: candidate versus request metrics, payload integrity, full and permitted fulfillment costs |
| CR-F-10 | §§7.3–7.4, 8.4: individual dispositions, historical Owner evidence qualification |
| CR-F-11 | §3.3: applicable frozen product distinctions |
| CR-F-12 | §3.1: normative oracle change versus scoped fixture correction |

**Original CP-01 drafting disposition**

> All corrections are proposed as document revisions pending targeted verification and independent methodology audit. No consistency finding is marked verified or closed by the author.

The preceding disposition is the original CP-01 drafting record. The Owner subsequently confirmed that the 26 November 2026 Targeted Verification reported all twelve CR-F-01–CR-F-12 corrections VERIFIED (see §8.3). CP-02 preserves those corrections and their traceability.

### 8.6 SAR-02-CP-02 methodology correction traceability

| Correction | Methodology findings | Owner decisions | Revised Charter sections and documentary disposition |
|---|---|---|---|
| CP-02-C01 | MA-F-01, MA-F-02 | OD-1 | §§1.4, 4.2, 8.2. Claim-specific inference, endpoints, pre-registration, preservation and meaningful incremental detection. |
| CP-02-C02 | MA-F-03, MA-F-09 | OD-3, OD-8, OD-11 | §§2.5, 4.4, 4.6, 5.4. Causal design, component and end-to-end comparison, RQ-B18, both H-02 dimensions and limits of the three-comparator framework. |
| CP-02-C03 | MA-F-04 | OD-5 | §§4.5, 4.7. Independent, construct-appropriate evaluation and confirmatory model-judge safeguards. |
| CP-02-C04 | MA-F-05, MA-F-10 | OD-6 | §§3.2–3.4, 6.2. Procedural separation, challenge coverage, held-out and reference freeze, label revision and sampling limits. |
| CP-02-C05 | MA-F-06, MA-F-07 | OD-4 | Front matter and §§1.1, 4.4, 6.2, 7.4, 8.3–8.5. Baseline separation, comparator identity, drift control and Owner-confirmed history. |
| CP-02-C06 | MA-F-08 | OD-2 | §§4.1, 7.1. Independent obligation universe and distinction between normative sources, taxonomy, instances and coverage. |
| CP-02-C07 | MA-F-11 | — | §§3.3, 4.3. Within-intent novelty and diversity, deviation, availability and fulfillment. |
| CP-02-C08 | MA-F-12 | OD-7 | §§4.6, 6.1. Critical events, invariants, empirical uncertainty and residual risk. |
| CP-02-C09 | MA-F-14 | OD-9 | §§4.3–4.4, 5.1–5.4, 6.1. Real-action authorization boundaries, Hard Stops and reporting of selection effects. |
| CP-02-C10 | MA-F-15 | OD-10 | §§4.6, 7.4, 8.1. Separate decision gates, including non-compensable functional preservation. |
| Detailed Research Protocol deferral | MA-F-13 | — | §8.2. Justified sample sizing and evidence sufficiency deferred to the Detailed Research Protocol. |

At submission, CP-02 was a documentary implementation pending independent targeted verification. Findings and Owner decisions above identify the approved scope of the revision. See §8.3 for the subsequent verification and Owner acceptance record.

**Research principle:** We are not required to prove HSGA is the best architecture. We are required to determine which architecture actually serves Rise and Shine best, within explicitly approved obligations and assurance boundaries.

END OF CHARTER
