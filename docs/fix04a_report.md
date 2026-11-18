# R&S-FIX-04A — implementation report

Date: 18 November 2026. Baseline and current HEAD:
`a62ba737acd47b4ae46280ba9b688c91a8941e20` (`main`).

## Recovery and preservation

The interrupted implementation was resumed, not restarted. The initial FIX-04
working tree had 22 modified tracked files. Its bytes, manifest and original diff
were saved in the ignored `.pytest_tmp_fix04a_baseline/` directory before FIX-04A
edits. At recovery, seven tracked implementation files already had partial FIX-04A
changes; the ignored local release smoke assertion was also updated. No FIX-04A
tests or documentation had yet been added. The original focused baseline had
passed 317 tests.

Recovery inspected status, HEAD, the cumulative diff, snapshot differences and
existing tests before further edits. Correct partial implementations were kept.
No reset, checkout, stash, discard, commit, push, deployment or production access
was performed. Nothing was staged. `.claude/` was neither modified nor staged.

## Findings and corrections

| Finding | Root cause | Correction |
| --- | --- | --- |
| A: language false positives | Every opposite-script letter rejected the card. | Separate output-language heuristic in `services/language_policy.py`: target prose plus bounded names/brands/terms, explicit foreign prose markers, Unicode NFC/script checks. All five fields use the same policy; numeric/emoji-only rejection is a separate quality rule. Prompts preserve original name/term spelling. |
| B: fenced JSON | FIX-04 fed the complete fenced response to `json.loads`; comparison also had its own permissive fence stripping and array acceptance. | One production parser accepts plain objects or one complete plain/`json` fence. Comparison calls it directly without preprocessing or legacy array fallback. Malformed/partial/trailing output remains invalid. |
| C: paid scheduled retries | Validation raised generic `RuntimeError`; scheduler treated every non-Telegram failure as retryable. | `ProviderOutputValidationError` survives the client boundary. Scheduler records `abandoned` after one validation failure and never marks it sent. Temporary failures retain backoff/three attempts. Error diagnostics store class/stage without raw content or chains. |
| D: extra keys | Exact key-set equality rejected valid required fields. | Require validated `focus` and exactly four valid `affirmations`; ignore extra fields, including model `gentle_step`. Duplicate keys and nonstandard JSON constants still fail. Deterministic micro-step remains authoritative. |
| E: edit fallback | Missing FSM content language defaulted to today's interface language. | Both confirmation preview and save prefer the persisted subscription language for an existing edit. Explicit content choice wins. New subscriptions keep their existing UI-language default. |
| F: interactive TTS | Availability used current interface language, and completed cards had no language metadata. | Save `last_generation.language` and gate audio using it after global/profile language switching. English audio remains unavailable. Legacy cards without metadata ask for a new card. |
| G: stale contract | Migration docs/comments and the local smoke assertion still described/expected arrays. | Document the object contract, heuristic and retry policy; local smoke uses the shared parser. Its exclusive run-claim guard is unchanged and has not been run. |

The continuation completed the regression coverage and documentation, hardened
the partial heuristic for Unicode scripts, initials, accents and digits inside
product names, rejected nonstandard JSON constants, classified invalid response
JSON/MIME as output validation, and verified both retry and terminal outcomes.
The first full run also exposed the experiment test's obsolete array-shaped mock;
it now supplies RU/EN card objects while retaining all usage, reasoning, budget
and run-claim assertions. The experiment implementation itself is unchanged.

## Language policy and limitations

The complete algorithm and examples are in
[localization_validation.md](localization_validation.md). It evaluates words and
foreign prose markers rather than raw character percentages. Short names and
recognized technical terms are exempted, so a long Cyrillic surname cannot
outweigh an English sentence. The required Python, ChatGPT, IT and Достоевский
examples pass in every display field. Mixed/wrong-language prose fails in every
display field. Numeric dates/emojis are language-neutral but cannot be the sole
content of a card field.

The heuristic is not perfect semantic language identification. Finite vocabularies
can reject unknown lowercase terms or ambiguous names, and unfamiliar capitalized
prose may pass as a name. Long names and scripts other than Latin/Cyrillic have
limited support. Script checks do not prove English/Russian fluency, source-meaning
fidelity or the quality of personalization. No additional paid classifier,
translation or repair request was introduced. A rejected initial request may
still be billed by the provider; local usage accounting is unchanged.

## Regression evidence

All provider boundaries exercised here are mocked. SQLite/FSM integration tests
use temporary isolated databases and output paths; `.env` loading is disabled by
the existing test harness. The optional local smoke tests compile only its parse
assertion from AST and inspect claim ordering, without importing the script,
reading its credentials or executing its network/main code.

Coverage includes valid names/terms in focus and all four affirmations, wrong and
mixed prose, Unicode confusables/accents/initials/product digits, numeric/emoji
quality, real fenced objects, malformed fences and required fields, extra keys,
production/comparison parity, scheduler HTTP-call counts and persisted statuses,
transient recovery/exhaustion/backoff/idempotency, safe logging, existing-edit and
new-subscription language defaults, completed-card TTS after both switch routes,
interactive reservation accounting and Profile → More personalization.

## Scope verification

The accepted FIX-04 interface/content ownership architecture and existing
uncommitted tests were preserved. Models/request budgets, image generation,
subscription schedule rules, database schema/migrations and deployment
infrastructure are unchanged. Existing FIX-01/FIX-02 profile, routing and
personalization checks remain in the focused/full suites. No module was moved
between layers and no paid request or production smoke was executed.

The ignored local `outputs/release_luna_smoke.py` correction is separate from
tracked Git statistics. It is present locally for re-audit and is not staged.

<!-- VALIDATION_AND_DIFF_STATS -->

## Validation results

| Check | Result |
| --- | --- |
| Original FIX-04 focused baseline | 317 passed |
| Main FIX-04A focused regression run | 1068 passed in 78.78s |
| Final Unicode/product-name and optional smoke subset | 178 passed in 1.95s |
| Final experiment + card validation + optional smoke subset | 192 passed in 6.90s |
| Complete final suite | **1750 passed in 306.92s (5:06)** |
| `git diff --check` | Passed; no whitespace errors |

Main focused command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.pytest_tmp_fix04a_targeted_final tests/test_card_validation.py tests/test_text_provider.py tests/test_compare_text_models.py tests/test_scheduler_delivery.py tests/test_subscription_visual_mix_flow.py tests/test_subscription_visual_modes.py tests/test_profile_personalization_integrity.py tests/test_profile_routing.py tests/test_generation_context.py tests/test_generation_reservation_handler.py tests/test_text_prompt_builder.py tests/test_affirmation_prompt.py tests/test_start_voice_router.py
```

Final supplemental command (covers the last fixture/tokenization corrections):

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.pytest_tmp_fix04a_experiment_final tests/test_text_model_experiment.py tests/test_card_validation.py tests/test_release_luna_smoke_contract.py
```

Complete final command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.pytest_tmp_fix04a_full_verified
```

The pre-existing pytest-asyncio loop-scope deprecation warning remains; no pytest
configuration was changed for this correction. An intermediate full run found
one stale array mock (1744 passed, one failed); that mock was corrected without
relaxing the test's usage or budget assertions.

## Changed files and diff statistics

Cumulative FIX-04 + FIX-04A: **30 files, +1860/−303**, including 26 modified tracked files and 4 new, unstaged files.

FIX-04A relative to the saved uncommitted FIX-04 tree: **19 files, +1027/−99**. The local ignored smoke correction adds **+3/−3** separately.

| Path | Status | FIX-04A vs saved FIX-04 (+/−) | Cumulative vs HEAD (+/−) |
| --- | --- | ---: | ---: |
| `bot.py` | modified | +0/−0 | +1/−1 |
| `docs/fix04a_report.md` | new | +232/−0 | +232/−0 |
| `docs/localization_validation.md` | new | +107/−0 | +107/−0 |
| `docs/text_model_migration.md` | modified | +12/−5 | +12/−5 |
| `handlers/generation.py` | modified | +16/−4 | +79/−37 |
| `handlers/start.py` | modified | +0/−0 | +58/−34 |
| `handlers/subscribe.py` | modified | +11/−2 | +53/−36 |
| `handlers/subscribe_formatting.py` | modified | +0/−0 | +4/−2 |
| `keyboards/inline.py` | modified | +0/−0 | +14/−6 |
| `scheduler.py` | modified | +8/−7 | +23/−39 |
| `scripts/compare_text_models.py` | modified | +18/−35 | +19/−26 |
| `services/language_policy.py` | modified | +93/−0 | +102/−0 |
| `services/subscription_ui.py` | modified | +0/−0 | +5/−0 |
| `services/text_prompt_builder.py` | modified | +4/−4 | +11/−3 |
| `services/yandex_gpt.py` | modified | +51/−31 | +116/−53 |
| `tests/test_affirmation_prompt.py` | modified | +0/−0 | +4/−4 |
| `tests/test_card_validation.py` | new | +121/−0 | +121/−0 |
| `tests/test_compare_text_models.py` | modified | +6/−4 | +6/−4 |
| `tests/test_generation_context.py` | modified | +0/−0 | +22/−20 |
| `tests/test_generation_reservation_handler.py` | modified | +0/−0 | +9/−7 |
| `tests/test_profile_personalization_integrity.py` | modified | +69/−1 | +234/−7 |
| `tests/test_profile_routing.py` | modified | +0/−0 | +146/−3 |
| `tests/test_release_luna_smoke_contract.py` | new | +39/−0 | +39/−0 |
| `tests/test_scheduler_delivery.py` | modified | +157/−1 | +268/−4 |
| `tests/test_start_voice_router.py` | modified | +0/−0 | +10/−4 |
| `tests/test_subscription_visual_mix_flow.py` | modified | +46/−0 | +46/−0 |
| `tests/test_subscription_visual_modes.py` | modified | +0/−0 | +4/−2 |
| `tests/test_text_model_experiment.py` | modified | +8/−1 | +8/−1 |
| `tests/test_text_prompt_builder.py` | modified | +3/−3 | +15/−2 |
| `tests/test_text_provider.py` | modified | +26/−1 | +92/−3 |

Tracked `git diff --stat` (new files are counted in the table above):

```text
bot.py                                          |   2 +-
 docs/text_model_migration.md                    |  17 +-
 handlers/generation.py                          | 116 ++++++----
 handlers/start.py                               |  92 +++++---
 handlers/subscribe.py                           |  89 ++++----
 handlers/subscribe_formatting.py                |   6 +-
 keyboards/inline.py                             |  20 +-
 scheduler.py                                    |  62 ++----
 scripts/compare_text_models.py                  |  45 ++--
 services/language_policy.py                     | 102 +++++++++
 services/subscription_ui.py                     |   5 +
 services/text_prompt_builder.py                 |  14 +-
 services/yandex_gpt.py                          | 169 ++++++++++-----
 tests/test_affirmation_prompt.py                |   8 +-
 tests/test_compare_text_models.py               |  10 +-
 tests/test_generation_context.py                |  42 ++--
 tests/test_generation_reservation_handler.py    |  16 +-
 tests/test_profile_personalization_integrity.py | 241 ++++++++++++++++++++-
 tests/test_profile_routing.py                   | 149 ++++++++++++-
 tests/test_scheduler_delivery.py                | 272 +++++++++++++++++++++++-
 tests/test_start_voice_router.py                |  14 +-
 tests/test_subscription_visual_mix_flow.py      |  46 ++++
 tests/test_subscription_visual_modes.py         |   6 +-
 tests/test_text_model_experiment.py             |   9 +-
 tests/test_text_prompt_builder.py               |  17 +-
 tests/test_text_provider.py                     |  95 ++++++++-
 26 files changed, 1361 insertions(+), 303 deletions(-)
```

## Final Git state

HEAD: `a62ba737acd47b4ae46280ba9b688c91a8941e20`; branch: `main`; staged changes: none.

```text
 M bot.py
 M docs/text_model_migration.md
 M handlers/generation.py
 M handlers/start.py
 M handlers/subscribe.py
 M handlers/subscribe_formatting.py
 M keyboards/inline.py
 M scheduler.py
 M scripts/compare_text_models.py
 M services/language_policy.py
 M services/subscription_ui.py
 M services/text_prompt_builder.py
 M services/yandex_gpt.py
 M tests/test_affirmation_prompt.py
 M tests/test_compare_text_models.py
 M tests/test_generation_context.py
 M tests/test_generation_reservation_handler.py
 M tests/test_profile_personalization_integrity.py
 M tests/test_profile_routing.py
 M tests/test_scheduler_delivery.py
 M tests/test_start_voice_router.py
 M tests/test_subscription_visual_mix_flow.py
 M tests/test_subscription_visual_modes.py
 M tests/test_text_model_experiment.py
 M tests/test_text_prompt_builder.py
 M tests/test_text_provider.py
?? docs/fix04a_report.md
?? docs/localization_validation.md
?? tests/test_card_validation.py
?? tests/test_release_luna_smoke_contract.py
```

Implementation is ready for an independent Claude Code FIX-04A/FIX-04 re-audit. All required implementation and validation work is complete. No commit, push or deployment is authorized or performed.
