# Card validation after FIX-04 / FIX-04A / FIX-04B

The accepted FIX-04 ownership stays in place: the user row owns the interface
language, a subscription owns its content language, and a completed interactive
card now records its own language in `last_generation.language`. Validation adds
no translation requests, retries, models, database fields or schedule changes.

## One JSON contract

`services.yandex_gpt._parse_card_text` is the only card parser used by production,
`scripts/compare_text_models.py` and the self-contained release contract test. It accepts
one object directly or inside one complete plain/`json` Markdown fence, with
optional outer whitespace and LF/CRLF line endings. Opening and closing fences
must occupy separate lines. Partial/nested fences, multiple objects, trailing
prose, malformed JSON, duplicate keys and nonstandard `NaN`/`Infinity` are rejected.

Required fields are a nonblank string `focus` and a list of exactly four nonblank
string `affirmations`. Harmless unknown fields are ignored after JSON validation.
This includes any model-generated `gentle_step`, regardless of its value/type;
the application's existing deterministic micro-step remains authoritative.
Archived array responses no longer pass the comparison script's current contract.
Stored historical experiment results are not modified.

## Language policy

`services.language_policy.is_card_language_compatible` is deliberately separate
from the existing input-language policy. It runs identically on `focus` and each
of the four affirmations; a long correct focus cannot hide a wrong affirmation.

1. Normalize a temporary validation copy to Unicode NFC and tokenize Unicode
   words, retaining apostrophes and digits within product names (`GPT4o`,
   `GPT-4o`, `iPhone16`). Inspect hyphen-separated segments individually: ASCII
   hyphen-minus `-`, Unicode hyphen `‐` (U+2010) and non-breaking hyphen `‑`
   (U+2011). Other dashes act as punctuation separators. Classify letters by
   Unicode Latin/Cyrillic character names. Each segment must use one supported
   script. Preserve the original output spelling, including quote marks.
2. Target-script words form the surrounding prose. Foreign-script spans must be
   short (at most four consecutive alphabetic segments, including across hyphens;
   known whole terms such as `wi-fi`/`e-mail` count once and digit-led product
   suffixes such as `-4o` do not add to that run). A target-script segment resets
   that count. A compact, case-insensitive vocabulary
   permits familiar technical/borrowed terms even when lowercase, e.g. `python`,
   `kubernetes`, `redis`, `ChatGPT`, `OpenAI`, `Microsoft` and `IT`.
3. Foreign function words, pronouns and frequent affirmation/prose words are
   evidence of a foreign clause, even when capitalized. For example `Я feel calm`
   and `I спокойно выбираю` fail. The explicit terminology vocabulary takes
   precedence for ambiguous tokens such as the acronym `IT`.
4. Other short foreign words with an initial or internal capital are treated as
   names, acronyms or brands. Dotted uppercase initials are also allowed. Thus
   `Я спокойно осваиваю Python.`, `Я могу использовать ChatGPT в работе.`,
   `Мой опыт в IT имеет ценность.`, `I enjoy reading Достоевский.` and references
   to `John Smith`, `Иван Петров`, `José` or `А. С. Пушкин` can pass without
   transliteration or translation. Unrecognized lowercase foreign segments fail
   closed. Recognized whole terms such as `wi-fi`/`e-mail` retain their exemption;
   a digit-led suffix in a single-script capitalized product such as `GPT-4o` is
   also allowed. At least one target-script word must remain.
5. Numbers, dates and emojis do not count as foreign prose. A numeric/emoji-only
   field is language-neutral. The parser rejects it separately with the explicit
   content-quality error `card field without prose`, because a card requires text.

### Hyphenated terminology and spoofing

The same term/name/prose checks apply to each alphabetic hyphen segment.
`Я работаю с IT-специалистом.`, `Я Python-разработчик и это ценно.`,
`Я HR-менеджер и верю в себя.` and `Я люблю ChatGPT-помощника.` pass without
whitelisting these compounds. Normal unhyphenated terms remain supported.
Hyphens grant no general foreign-prose exemption: `Я-I-feel-calm`,
`Я Python-разработчик-feel-ready` and `Я Feel-Ready-To-Learn` fail.

Product spellings such as `Python`, `ChatGPT`, `José` and `GPT-4o` have Latin
letters in their Latin segments. `Pуthon` has Cyrillic `у` inside its Latin
segment and fails, also inside `Pуthon-разработчик` or a foreign quotation.
`IT-специaлист` likewise fails because its Russian segment contains Latin `a`.
An intentional script boundary at a hyphen is accepted; a mixed-script segment
is rejected. This distinction does not prove that a product/name is authentic.

### Bounded foreign-language quotations

Only clearly paired, nonnested quotations can exempt foreign prose. Supported
pairs are `«…»`, `“…”`, `„…“`, `"…"`, `‘…’` and `'…'`. Apostrophes between
alphanumeric characters (e.g. `I'm`, `don't`, `O’Connor`) do not open/close quotes.
Ordinary commas, periods, ellipses, exclamation marks and dashes are permitted.
Unmatched, mismatched or nested quote delimiters grant **no quotation exemptions
anywhere in that field**; the ordinary term/name/prose policy still applies.

The following limits apply independently to each field, after NFC normalization:

- At most **two foreign-containing quotations** per field.
- At most **six alphabetic word segments** and **80 Unicode code points** inside
  each quotation (excluding its delimiters, including spaces/punctuation).
- At most **eight quoted alphabetic segments total**. Hyphen segments count
  separately; contractions count as one word. Standalone numbers/emoji do not
  count as words, but still count toward the character limit.
- No CR/LF inside an exempt quotation. Each alphabetic segment inside it must
  be entirely Latin or entirely Cyrillic; mixed-script spoofs and other scripts
  are rejected. Foreign prose-marker words are allowed only inside the quote.
- The outside text must pass the ordinary language checks and contain at least
  **two target-script segments**, and at least as many target-script segments as
  all exempt quoted segments combined. Foreign names/terms outside quotes do
  not count as target-language context. Target words inside an exempt quotation
  also do not count as outside context.

Thus `Я помню фразу «I am calm».` passes (three outside target words, three
quoted words), as does `I repeat the words «Я спокоен» every morning.`
`«I am calm»` in a RU field, `«Я спокоен»` in an EN field and
`Я «I am calm»` fail. A correct quotation cannot hide wrong-language prose
outside it. Same-language quotations are validated as ordinary text and do not
use this foreign-quotation budget. Only validation copies are normalized/masked;
the returned card text and user-entered Profile Preferences are not rewritten.

This is a lexical/script heuristic, not a raw character-ratio threshold. A long
surname therefore does not outweigh a short target-language sentence. After
recognized names/terms are exempted, all remaining words must use the target
script outside the bounded quotations; ordinary foreign clauses cannot pass merely by staying below a character
percentage. Both system and user prompts preserve names/brands/terms and ask for
the surrounding prose to be translated into the requested content language.

### Limitations

Semantic language identification is not perfect. The vocabulary is finite:
unlisted lowercase terminology/compound segments, inflected foreign names, very long foreign names
and names colliding with prose words may be rejected. Capitalized words outside
the prose vocabulary may be mistaken for names; short awkward mixtures can pass.
Latin/Cyrillic script does not uniquely identify English/Russian (other languages
use those scripts). Uncased names in other scripts are currently rejected. Unicode
NFC and script checks do not constitute a general spoofing detector. Quote handling
does not support nesting, Markdown/backtick quotations, multiline quotations or
every typographic convention. Possessive apostrophes at word boundaries can make
quote pairing ambiguous and remove exemptions. The context ratio deliberately
rejects some legitimate short introductions and longer quotations; counting
target-script words does not establish grammatical or meaningful context. The
validator cannot establish that quoted material is a real quotation. This check
does not prove fluency, semantic fidelity, personalization quality or that a term
was necessary. These tradeoffs need independent review; no semantic classifier or
additional paid model call has been introduced.

## Failure and delivery policy

`ProviderOutputValidationError`, a `RuntimeError` subclass, represents deterministic
card JSON/schema/language/quality failures and invalid/truncated/refused provider
output. It escapes the card client without being rewrapped as a transient error.
The scheduler persists `abandoned` on the first such failure, leaves `sent_at`
unset and stops before image generation or Telegram delivery. Later ticks cannot
claim that same dated delivery. A later scheduled date has its own ledger row;
the subscription is not disabled. No generic fallback card is sent and no repair,
translation or extra paid model call is attempted. This terminal behavior is the
owner's FIX-04B decision for genuine output validation failures, including language
mismatches that remain after these heuristic exceptions. Generic temporary API errors, network failures, timeouts,
HTTP 429 and temporary HTTP 5xx responses retain the three-attempt/backoff policy.

The existing database claim, attempt fencing, lease and post-send rules are
unchanged. Scheduled failures do not consume interactive quota. Interactive
failures still release the existing reservation; successful delivery keeps it.
The first provider call can still be billed by the provider even if its output
is rejected. No automatic repair or translation call is made.

Failure logs and the persisted delivery error retain stage and exception class,
not raw provider bodies, personalized text or exception chains. Card HTTP failure
bodies are neither read for diagnostics nor logged. The comparison/experiment
tools still deliberately retain synthetic raw output and provider usage in their
explicit reports, as before.

An existing edit with absent/invalid FSM `content_language` reads the persisted
subscription language for both preview and saving. Explicit selections still win;
a genuinely new subscription retains the interface-language default. Interactive
TTS uses the completed card's stored language, so RU audio remains available after
switching the UI to EN, while an EN card remains unavailable after switching to RU.
A legacy in-memory card without language metadata asks for a new card rather than
guessing from today's interface language.

`tests/test_release_luna_smoke_contract.py` now directly exercises the production
parser with self-contained RU/EN object fixtures and negative contract cases.
It neither reads nor imports `outputs/release_luna_smoke.py`, has no conditional
skip, and runs when ignored historical outputs are absent. Historical experiment
files are not staged, moved, imported or executed by this test. Their paid-run
guards are outside this contract test; existing experiment tests retain the
mocked usage/budget/run-claim coverage. No paid smoke request is authorized here.
