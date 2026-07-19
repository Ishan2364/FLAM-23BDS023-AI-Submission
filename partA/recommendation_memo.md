# A4 — Recommendation Memo: Tokenizer Fertility & Routing

## Corrected headline numbers

REPORT_v0's "Hindi costs 6x, route all Indic traffic separately" was measured with `gpt2` — a tokenizer with effectively no Kannada/Tamil coverage. Re-measured on FLORES-200 (997 parallel sentences, eng/hin/kan/tam), using **tokens per sentence** (the fairest denominator — see below) and an Indic-aware tokenizer:

| tokenizer | hin vs eng | kan vs eng | tam vs eng |
|---|---|---|---|
| gpt2 (original report) | 7.18x | 13.10x | 14.88x |
| xlm-roberta-base (corrected) | **1.24x** | **1.34x** | **1.33x** |

The reported 6-19x gap collapses to a real but modest 1.2-1.3x once the tokenizer actually has Indic-script coverage. Confirmed independently across two more Indic-aware tokenizers (muril-base-cased, ai4bharat/indic-bert) and two corpora (FLORES-200 primary, FLORES-101 cross-check) — not a one-tokenizer fluke.

**Why tokens/sentence, not tokens/word or tokens/byte:** tokens/word (the original metric) conflates language cost with tokenizer training coverage — that's the report's core conceptual bug. tokens/byte looked like a fix but has its own confound: Devanagari/Kannada/Tamil are ~3 bytes/codepoint in UTF-8 vs. English's 1 byte/char, so it systematically favors Indic scripts regardless of real cost. Tokens per *parallel sentence* (same meaning, same content, different language) is the one denominator that holds the actual unit of value constant, and it's what determines real context/compute usage per request.

## Routing recommendation

**Do not stand up a separate Indic-specialized tokenizer/model purely to fix a 6x cost gap — it isn't a 6x gap.** The real, measured residual is ~1.2-1.3x with the *current* tokenizer swapped for an Indic-aware one (xlm-roberta-base or similar). Two options, in order of preference:
1. Switch the production tokenizer to an Indic-aware one (xlm-roberta-base performed best/most-consistent of the three tested). This alone closes most of the gap for all three languages, no separate routing infrastructure needed.
2. If a tokenizer swap isn't feasible near-term, budget capacity at **~1.3x for Hindi/Kannada/Tamil**, not 6x — the original number would have led to a large capacity over-allocation.

## Biggest caveat

FLORES is professionally-translated encyclopedic/news prose (Wikinews/Wikijunior/Wikivoyage) — 997 sentences, no code-switching, no informal register, no production-traffic patterns (chat, slang, mixed-script input). The 1.2-1.3x residual gap is measured on this benchmark text; real user traffic could shift it in either direction, and this analysis cannot rule that out. Treat 1.2-1.3x as a benchmark-grounded estimate to validate against live traffic, not a guarantee.

## Production metric to monitor

**Tokens-per-request ratio (Indic-language requests ÷ English requests), measured on live traffic after any tokenizer change** — directly checks whether the FLORES-based 1.2-1.3x estimate holds in production. If it drifts meaningfully above ~1.5x on real traffic, that's the signal this analysis's domain-caveat was load-bearing and needs re-investigation, not that the conceptual fix was wrong.
