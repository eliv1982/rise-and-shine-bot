# R&S-FIX-04B — final language policy corrections

Date: 18 November 2026. Baseline and current HEAD:
`a62ba737acd47b4ae46280ba9b688c91a8941e20` (`main`).

## Root causes and exact corrections

1. The FIX-04A tokenizer kept a hyphenated compound as one word. Its script
   check therefore rejected `IT-специалистом`, `Python-разработчик`,
   `HR-менеджер` and `ChatGPT-помощника`. FIX-04B inspects Unicode hyphen
   segments individually, using the existing vocabulary/name/prose checks on
   each segment. Mixed scripts *inside* a segment still fail. Known compound
   terms and digit-led product suffixes retain their existing foreign-word
   budget, avoiding a new false positive for lists of `GPT-4o`, `Wi-Fi`, `e-mail`.
   This is segmentation, not a whitelist of the four reported examples.
2. Quoted foreign prose was treated like unquoted foreign prose. FIX-04B finds
   flat paired quotation spans, validates their scripts and finite budgets,
   masks only those spans in a temporary validation copy, and validates all
   outside prose. Outside target-script context is mandatory and must equal
   or exceed the total quoted word count. Returned card spelling is preserved.
3. The smoke contract test extracted assertions from an ignored historical
   script and skipped when it was absent. The replacement uses self-contained
   RU/EN fixtures directly against the production parser, with no optional
   file dependency, AST execution, credentials or conditional skip.

## Language rules and limitations

The complete implemented policy is in
[localization_validation.md](localization_validation.md).

- Normalize only a validation copy to NFC; classify letters by Unicode names.
  Split ASCII `-`, Unicode hyphen U+2010 and non-breaking hyphen U+2011.
  Each segment must be entirely Latin or Cyrillic. `Pуthon` and
  `IT-специaлист` still fail, including inside quotations.
- Preserve normal unhyphenated brands, abbreviations and technical terms.
  Foreign prose markers override name-like capitalization; unknown lowercase
  foreign segments fail. At most four consecutive foreign units are accepted;
  recognized whole terms count once and product digit suffixes remain attached.
- Support paired `«…»`, `“…”`, `„…“`, `"…"`, `‘…’` and `'…'` quotations;
  embedded word apostrophes remain part of words. Unmatched, mismatched or nested
  delimiters grant no quote exemptions anywhere in that field.
- Per field: at most two foreign-containing quotes, six alphabetic segments
  and 80 normalized code points per quote, eight quoted segments total, no CR/LF
  inside an exempt quote. Require at least two target-script segments outside
  all exempt quotes and at least as many as all quoted segments combined.
  Validate the remaining outside text normally. Entire-field wrong-language
  quotations and substantial foreign prose outside quotes fail.
- Apply the same policy independently to focus and all four affirmations.
  Profile Preferences, source themes and their saved spelling are not rewritten.

This remains a finite lexical/script heuristic. It can reject unfamiliar lowercase
terms, long names/quotes and legitimate short quotation introductions. Unfamiliar
capitalized prose can resemble names. Latin/Cyrillic scripts do not uniquely
identify English/Russian; script checks do not prove fluency, meaningful context,
quotation authenticity, product authenticity or semantic fidelity. Other scripts,
nested/Markdown/multiline quotation conventions and some boundary apostrophes
have limited or no support. No semantic classifier or paid repair was added.

## Owner decision and delivery behavior

The scheduler and provider client implementation are unchanged by FIX-04B.
Genuine provider-output failures retain `ProviderOutputValidationError` and
immediately persist `abandoned` with `sent_at=NULL` and explicit sanitized failure
diagnostics. A first-attempt validation rejection retains `attempts=1`; prior
transient attempts, if any, remain counted in the same ledger. No further request, fallback card, image or
Telegram send is made for that dated delivery. Later ticks cannot claim it;
a later scheduled date has its own ledger row. Temporary transport/API failures
retain the existing backoff and three-attempt policy. Interactive reservations
and scheduled accounting remain unchanged. The rejected initial request may
still be billed by the provider; FIX-04B introduces no extra paid call.

## Changes specific to FIX-04B and preservation

FIX-04B changes only `services/language_policy.py`,
`docs/localization_validation.md`, `tests/test_card_validation.py`,
`tests/test_scheduler_delivery.py`, `tests/test_release_luna_smoke_contract.py`,
and this report. The 30 pre-existing cumulative changed files were saved to an
ignored local baseline before editing. Of those, the other 25 files remain
byte-for-byte unchanged relative to that starting working tree.

The earlier FIX-04/04A implementation remains in place: independent UI/content
language ownership, localized card focus and four affirmations in one request,
strict shared JSON parsing with complete fence support and ignored extra fields,
non-retryable output errors, subscription edit fallback, completed-card TTS
language ownership, Profile → More integrity and comparison/experiment parity.

No provider/model configuration, image-generation implementation, database schema,
migration, schedule, billing policy or deployment changed in FIX-04B. No ignored
historical output was staged, moved, imported, modified or executed in this task.
`.claude/` was not read or modified. No staging, commit, push or deploy occurred.

## Validation

All exercised provider/Telegram transports are mocked. Tests use isolated SQLite
databases, FSM state and output directories; the existing harness disables `.env`
loading. New scheduler regressions exercise the real provider parser, every card
field, both content languages, persisted ledger states across four ticks, exactly
one text request, no image/delivery on rejection, unchanged Profile Preferences,
UI/subscription language separation and scheduled quota accounting.

Existing regressions cover malformed/plain/fenced JSON, extra keys, genuine wrong
languages, non-retryable classification and temporary retry/backoff, comparison
parity, subscription editing, completed-card TTS, Profile → More, reservation
accounting, experiment usage/budget/run-claim guards and provider request options.

<!-- FINAL_VALIDATION -->

| Check | Final result |
| --- | --- |
| Language/parser and self-contained smoke subset | 542 passed in 3.07s |
| Same subset in source snapshot without outputs/, .env, .git or .claude/ | 542 passed in 3.81s; zero skips; includes all 7 release smoke cases |
| Final targeted regressions | 1503 passed in 287.27s (4:47) |
| Complete final suite | 2164 passed in 317.35s (5:17) |
| git diff --check | Passed |

Final targeted command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.pytest_tmp_fix04b_targeted_final tests/test_card_validation.py tests/test_release_luna_smoke_contract.py tests/test_text_provider.py tests/test_compare_text_models.py tests/test_text_model_experiment.py tests/test_scheduler_delivery.py tests/test_subscription_visual_mix_flow.py tests/test_subscription_visual_modes.py tests/test_profile_personalization_integrity.py tests/test_profile_routing.py tests/test_generation_context.py tests/test_generation_reservation_handler.py tests/test_text_prompt_builder.py tests/test_affirmation_prompt.py tests/test_start_voice_router.py
```

Complete final command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.pytest_tmp_fix04b_full_final
```

The clean-source check copied only repository source and current new test files
to an ignored isolated directory. It used the same interpreter and ran
`tests/test_card_validation.py tests/test_release_luna_smoke_contract.py` there.
It did not read or execute any historical outputs. There were no test failures
in the final targeted or full runs.

<!-- /FINAL_VALIDATION -->

The pre-existing `pytest-asyncio` fixture-loop-scope deprecation warning remains.
An intermediate full run was intentionally stopped to preserve the foreign-word
budget for known compound product terms; the final checks below use the corrected
implementation. No historical paid experiment or production smoke was run.

<!-- FINAL_DIFF_SUMMARY -->

## Complete cumulative diff summary

FIX-04B relative to the starting uncommitted FIX-04/04A tree: **6 files,
+645/-60**, including this report.

Cumulative FIX-04/04A/04B versus HEAD: **31 files,
+2445/-303**: 12 runtime/tool files, 15 test files and four
documentation files. Git statistics include the five new unstaged files below.

| Path | FIX-04B vs starting tree (+/-) | Cumulative vs HEAD (+/-) |
| --- | ---: | ---: |
| `bot.py` | +0/-0 | +1/-1 |
| `docs/fix04a_report.md` | +0/-0 | +232/-0 |
| `docs/fix04b_report.md` | +262/-0 | +262/-0 |
| `docs/localization_validation.md` | +88/-18 | +177/-0 |
| `docs/text_model_migration.md` | +0/-0 | +12/-5 |
| `handlers/generation.py` | +0/-0 | +79/-37 |
| `handlers/start.py` | +0/-0 | +58/-34 |
| `handlers/subscribe.py` | +0/-0 | +53/-36 |
| `handlers/subscribe_formatting.py` | +0/-0 | +4/-2 |
| `keyboards/inline.py` | +0/-0 | +14/-6 |
| `scheduler.py` | +0/-0 | +23/-39 |
| `scripts/compare_text_models.py` | +0/-0 | +19/-26 |
| `services/language_policy.py` | +81/-12 | +171/-0 |
| `services/subscription_ui.py` | +0/-0 | +5/-0 |
| `services/text_prompt_builder.py` | +0/-0 | +11/-3 |
| `services/yandex_gpt.py` | +0/-0 | +116/-53 |
| `tests/test_affirmation_prompt.py` | +0/-0 | +4/-4 |
| `tests/test_card_validation.py` | +124/-1 | +244/-0 |
| `tests/test_compare_text_models.py` | +0/-0 | +6/-4 |
| `tests/test_generation_context.py` | +0/-0 | +22/-20 |
| `tests/test_generation_reservation_handler.py` | +0/-0 | +9/-7 |
| `tests/test_profile_personalization_integrity.py` | +0/-0 | +234/-7 |
| `tests/test_profile_routing.py` | +0/-0 | +146/-3 |
| `tests/test_release_luna_smoke_contract.py` | +21/-29 | +31/-0 |
| `tests/test_scheduler_delivery.py` | +69/-0 | +337/-4 |
| `tests/test_start_voice_router.py` | +0/-0 | +10/-4 |
| `tests/test_subscription_visual_mix_flow.py` | +0/-0 | +46/-0 |
| `tests/test_subscription_visual_modes.py` | +0/-0 | +4/-2 |
| `tests/test_text_model_experiment.py` | +0/-0 | +8/-1 |
| `tests/test_text_prompt_builder.py` | +0/-0 | +15/-2 |
| `tests/test_text_provider.py` | +0/-0 | +92/-3 |

<!-- /FINAL_DIFF_SUMMARY -->

Cumulative behavior by area:

- `bot.py`, `handlers/start.py`, `handlers/subscribe.py`,
  `handlers/subscribe_formatting.py`, `keyboards/inline.py` and
  `services/subscription_ui.py`: separate interface and subscription content
  languages, distinct callback routing, localized controls/confirmation/summary,
  preserved subscription language on incomplete edit state, content-aware audio.
- `handlers/generation.py` and `scheduler.py`: use the localized returned focus,
  deterministic micro-step and four affirmations; retain Profile → More context;
  store completed-card language for TTS; apply content/UI ownership consistently;
  keep deterministic validation failures terminal with sanitized diagnostics.
- `services/yandex_gpt.py`, `services/text_prompt_builder.py`,
  `services/language_policy.py` and `scripts/compare_text_models.py`: one text
  request and shared object parser; complete fences, validated required fields,
  ignored extras, no raw-text fallback, original names/terms and bounded quotes.
- Fifteen regression test files cover these contracts and prior findings;
  four documentation files record migration policy, limitations and FIX-04A/04B
  implementation evidence. The per-file table includes all cumulative files,
  including new unstaged files; it excludes the pre-existing `.claude/` directory
  and ignored local artifacts.

## Remaining risks and audit handoff

False positives and false negatives remain possible within the documented
heuristic. Under the owner's decision, a genuine validation rejection leaves
that day's delivery abandoned rather than repairing, retrying or substituting a
generic card. The independent delta-audit should review the quotation thresholds,
segment handling and the clean-source smoke contract. Work stops here for that
Claude Code audit; nothing is staged or committed.

<!-- FINAL_GIT_STATE -->

## Final Git state

HEAD: `a62ba737acd47b4ae46280ba9b688c91a8941e20`; branch: `main`.
There are 26 modified tracked files and five new unstaged deliverable files.
The pre-existing untracked `.claude/` directory remains untouched. Staged changes: none.
No commit, push or deployment was performed.

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
?? .claude/
?? docs/fix04a_report.md
?? docs/fix04b_report.md
?? docs/localization_validation.md
?? tests/test_card_validation.py
?? tests/test_release_luna_smoke_contract.py
```

<!-- /FINAL_GIT_STATE -->
