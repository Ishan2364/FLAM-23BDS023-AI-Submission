# Lab Notebook — Tokenizer & Serving Audit

Chronological log: hypothesis → experiment → result → revision. Dead ends included on purpose. Everything below happened on **2026-07-19**, in the order shown — each entry is numbered as a **Step** instead of repeating the date on every heading.

**Contents**
- Steps 1-2 — Setup, baseline reproduction
- Step 3 — A1 eval corpus writeup
- Steps 4-13 — A2 audit candidates #1-#7, then rerun at scale
- Steps 14-16 — A2 conceptual-bug tokenizer swap (gpt2 vs. xlm-roberta-base/MuRIL/indic-bert), final verdict
- Steps 17-18 — A3 corrected analysis (FLORES-200 primary + FLORES-101 cross-check)
- Steps 19-22 — Part B: B1 (KV-cache), B2 (throughput anomaly), B3 (goodput correction), B4 (confirming metric)

---

# Part A — Tokenizer Audit

## Step 1 — Setup

- Created `23BDS023-submission/` scaffold, kept `starter_kit/` untouched as reference.
- Copied `fertility.py` → `partA/fertility_audit.py` as our working copy (baseline behavior unchanged so far). [superseded by `reproducing_result/` and `audit_experiments/` once those were organized — this early copy was deleted during final cleanup]
- Plan: (1) reproduce the intern's reported numbers on the sample corpus before changing anything, (2) audit the script/metric on that same small corpus, (3) build a real multilingual eval corpus, (4) rerun corrected analysis, (5) write memo.

## Step 2 — Baseline reproduction

Ran unmodified `fertility.py` on the sample corpora (`partA/reproducing_result/`, venv, tiktoken only):

```
python fertility.py --corpus eng=corpus_sample\eng_sample.txt --corpus hin=corpus_sample\hin_sample.txt --tokenizer gpt2
```

```
eng   1.27   0.226
hin   7.45   1.579
hin is 5.89x the fertility of eng (worse tokenization)
```

Matches REPORT_v0.md exactly. Baseline confirmed — starting A2 (script/metric audit) from here.

## Step 3 — A1 eval corpus (writeup)

**Languages (4, as required):** English (eng), Hindi (hin), Kannada (kan), Tamil (tam). Hindi is Indo-Aryan; Kannada and Tamil are both Dravidian, satisfying the "two Dravidian languages" requirement and giving us a script-family contrast (Devanagari vs. Kannada script vs. Tamil script) alongside the Latin-script baseline.

**Corpus and why:** FLORES-200 (`facebook/flores` on HuggingFace) is our primary/declared corpus — it's the current, actively-maintained release the assignment brief itself points to, and pulling it required a personal HF token since the repo is gated (`partA/corpus_prep_flores200.py`, token read from `.env`, never committed). To cross-check and to keep a reproducible, redistributable copy in the repo, we also pulled the same 4 languages from FLORES-101, Meta's earlier public/ungated tarball (`https://dl.fbaipublicfiles.com/flores101/dataset/flores101_dataset.tar.gz`, CC-BY-SA). The two are numerically identical for eng/hin/kan/tam — FLORES-200's dev split for these languages is built on the same underlying dev sentences as FLORES-101 (confirmed: fertility numbers matched to 2 decimal places across all 4 languages, see the two experiment logs below). So while FLORES-200 is the corpus of record, all A2/A3 experiments run against the FLORES-101 copy in practice, because it's identical in content and doesn't require redistributing gated data — `flores200_eval/` stays local-only (gitignored), `flores101_eval/` is committed for grader reproducibility.

**Size:** 997 parallel sentences per language (3,988 sentences total across 4 languages), sentence-aligned by line number — line N in `eng.txt` is a direct translation of line N in `hin.txt`/`kan.txt`/`tam.txt`.

**Domain:** FLORES sentences are professionally translated, drawn from a mix of Wikinews, Wikijunior, and Wikivoyage articles — encyclopedic/journalistic prose, not conversational or transactional text (no chat messages, no code-mixing, no slang).

**Preprocessing:** none beyond what `fertility.py` itself does (NFC normalization, lowercasing). Files saved as plain UTF-8 `.txt`, one sentence per line, no filtering or resampling applied on our end.

**What this corpus cannot tell us:** 997 sentences is a reasonable smoke-test size but still small relative to real production traffic, and formal, professionally-translated encyclopedic prose is not representative of actual user queries — no code-switching, no informal register, no domain-specific jargon (support tickets, casual chat, voice-to-text artifacts) that a production system would actually see. Because FLORES-101 and FLORES-200 collapsed to the same sentences for these 4 languages, we effectively only sampled one translation of each source sentence, not independent corpora — so this doesn't triangulate across corpus sources, only across tokenizers and metrics. Any fertility numbers below should be read as "how this specific benchmark text tokenizes," not as a guaranteed predictor of live traffic cost.

## Step 4 — A2, candidate #1: `.lower()` (line 60)

Hypothesis: lowercasing is a no-op for Hindi (no case in Devanagari) but shifts English token counts (BPE is case-sensitive) — asymmetric effect on a cross-language metric.

Test: `audit_experiments/fertility_no_lower.py` (identical script, `.lower()` removed), same corpus/tokenizer.

| | eng fertility | hin fertility | ratio |
|---|---|---|---|
| with `.lower()` (original) | 1.27 | 7.45 | 5.89x |
| without `.lower()` | 1.23 | 7.45 | 6.06x |

**Confirmed:** effect is real and asymmetric exactly as predicted — Hindi unchanged (0.00), English shifts (-0.04, ~3%). But direction matters: removing `.lower()` *increases* the eng-hin gap, not decreases it, so `.lower()` was making the reported disparity slightly smaller than the true one, not inflating it. Small magnitude (~3% on eng, ratio moves 5.89→6.06) — doesn't flip the headline conclusion. Verdict: real but minor effect, not the flaw driving the report's biggest problems. Moving to next candidate.

## Step 5 — A2, candidate #2: `line.split(" ")` (line 62)

Test: `audit_experiments/fertility_split_ws.py`, `line.split(" ")` → `line.split()`.

| | eng fertility | hin fertility | ratio |
|---|---|---|---|
| `split(" ")` (original) | 1.27 | 7.45 | 5.89x |
| `split()` | 1.28 | 7.60 | 5.92x |

Observation only, no verdict yet.

## Step 6 — A2, candidate #3: `chars = len(line)` (line 63)

Test: `audit_experiments/fertility_grapheme.py` — replaced `len(line)` with a grapheme-cluster approximation (`grapheme_len`: counts codepoints but skips Unicode combining marks, so Devanagari matras attached to a base consonant aren't counted as extra "characters").

| | eng tok/char | hin tok/char |
|---|---|---|
| `len(line)` (original) | 0.226 | 1.579 |
| grapheme-aware count | 0.226 | 1.638 |

Fertility (tok/word) unchanged in both, as expected — this only touches the tok/char column. Observation only, no verdict yet.

## Step 7 — A2, candidate #4: NFC normalization (line 49)

Test: `audit_experiments/fertility_no_nfc.py` — removed `unicodedata.normalize("NFC", line)`.

Result: output identical to original in every column (eng and hin). Sample corpus files are already NFC-normalized, so this line is currently a no-op on this data — flag as red-herring candidate, though could matter on messier real-world/scraped text later.

## Step 8 — A2, candidate #5: macro-avg vs micro-avg (lines 56-67)

Test: `audit_experiments/fertility_micro_avg.py` — sum tokens/words/chars across corpus, divide once, instead of averaging per-line ratios.

| | eng fertility | eng tok/char | hin fertility | hin tok/char | ratio |
|---|---|---|---|---|---|
| macro-avg (original) | 1.27 | 0.226 | 7.45 | 1.579 | 5.89x |
| micro-avg | 1.25 | 0.221 | 7.40 | 1.583 | 5.91x |

Observation only, no verdict yet. At this corpus size (~10 lines) the shift is small; open question for A3 whether it grows at FLORES-200 scale.

## Step 9 — A2, candidate #6: `base = langs[0]` (line 97)

Test: reran with `--corpus` order swapped (hin first, eng second).

| order | printed ratio |
|---|---|
| eng, hin (original) | "hin is 5.89x the fertility of eng" |
| hin, eng (swapped) | "eng is 0.17x the fertility of hin (better tokenization)" |

Per-language fertility numbers unchanged (7.45 / 1.27 either way) — only the printed framing/direction flips with argument order. Confirms base language is an arbitrary artifact of CLI arg order, not a principled reference point.

## Step 10 — A2, candidate #7: `random.seed(1337)` (line 25)

Checked: `random` is imported and seeded but never called anywhere else in the file (`grep -n random fertility.py` → only the import and seed lines). Dead code as it stands in this script.

## Step 11 — A1: real eval corpus (FLORES-101)

`facebook/flores` on HF is gated (403, no access). Used FLORES-101 instead — direct, ungated tarball at `https://dl.fbaipublicfiles.com/flores101/dataset/flores101_dataset.tar.gz` (linked from the official facebookresearch/flores README). Extracted `dev/{eng,hin,kan,tam}.dev`, 997 parallel sentences each (news/Wikipedia domain, sentence-aligned by line number), saved to `partA/data/flores101_eval/{eng,hin,kan,tam}.txt`. Deleted the tarball after extraction.

Ran unmodified `fertility.py` on this corpus, all 4 languages, gpt2 tokenizer:

```
eng    1.28   0.215
hin    7.82   1.528
kan   22.15   2.655
tam   24.73   2.717

hin is 6.10x the fertility of eng
kan is 17.27x the fertility of eng
tam is 19.28x the fertility of eng
```

Big finding: Kannada/Tamil fertility is far worse than Hindi's, not just "somewhat worse" — plausible cause is gpt2's BPE vocab has ~no Kannada/Tamil coverage, so it degrades to near-byte-level encoding for those scripts. This is on the *unmodified* script, so A2's candidate bugs (#1, #2, #3, #5) are still baked into these numbers — next step is rerunning with fixes applied + a second, Indic-aware tokenizer (A3) before drawing conclusions.

## Step 12 — A1: FLORES-200 (gated) via HF token

Also pulled the actual gated `facebook/flores` (FLORES-200) dev sets for eng_Latn/hin_Deva/kan_Knda/tam_Taml using a user-supplied HF token (`partA/corpus_prep_flores200.py`, reads `HF_KEY` from `.env`, `.env` gitignored).

Ran unmodified `fertility.py` on `partA/data/flores200_eval/`:

```
eng    1.28   0.215
hin    7.82   1.528
kan   22.15   2.655
tam   24.73   2.717

hin is 6.10x the fertility of eng
kan is 17.27x the fertility of eng
tam is 19.28x the fertility of eng
```

Numbers are identical to the FLORES-101 run above, to 2 decimal places. Likely explanation: FLORES-200 dev sets are a superset built on the same original FLORES-101 dev sentences for these 4 languages, so the dev split content didn't change here. Treat FLORES-101 and this FLORES-200 pull as one corpus for A3, not two independent ones — worth a caveat in A4 rather than double-counting as separate evidence.

## Step 13 — A2, candidates #1/#2/#3/#5 rerun at scale (FLORES-101, 997 lines)

Reran all four candidate variants on the real corpus to check if the toy-corpus (~10 line) deltas were noise or held at scale.

| variant | eng fert | hin fert | kan fert | tam fert |
|---|---|---|---|---|
| original (macro-avg) | 1.28 | 7.82 | 22.15 | 24.73 |
| micro-avg (#5) | 1.27 | 7.79 | 21.70 | 24.46 |
| `split()` (#2) | 1.28 | 7.83 | 22.95 | 24.87 |
| no `.lower()` (#1) | 1.24 | 7.82 | 22.15 | 24.73 |

tok/char, `.lower()` removed and grapheme-aware (#3) — only tok/char affected:
| variant | eng | hin | kan | tam |
|---|---|---|---|---|
| original `len()` | 0.215 | 1.528 | 2.655 | 2.717 |
| grapheme-aware (#3) | 0.215 | 1.598 | 2.911 | 3.175 |

**Verdict:** at 997-line scale, candidates #1, #2, #3, #5 each move numbers by only ~0-5%, and none flip or meaningfully narrow the headline gap (eng vs hin/kan/tam still off by 6x/18x/20x either way). No `.lower()` (#1) only shifts eng (1.28→1.24, ~3%) — hin/kan/tam completely unchanged (0 combining case in these scripts), confirming the asymmetric-but-minor pattern already seen on the toy corpus, just larger sample this time. Same conclusion as the toy-corpus tests, just confirmed at scale: these are real, measurable, but minor effects — not the conceptual bug the report is missing. The real conceptual problem is elsewhere (see below): comparing "tokens per whitespace-word" as a cost proxy across languages with different morphology/script density, without holding information-content constant — that's the denominator question A3 exists to fix, not any of these code-level nitpicks.

## Step 14 — A2, conceptual bug test: swap tokenizer (gpt2 → xlm-roberta-base)

Hypothesis (user's): gpt2's huge kan/tam fertility isn't measuring language cost, it's measuring that gpt2's BPE vocab was never trained on Kannada/Tamil script and falls back to near-byte-level encoding. If true, an Indic-aware tokenizer should collapse most of the gap while English stays roughly flat.

Ran unmodified `fertility.py` on the same FLORES-101 corpus, `--tokenizer hf:xlm-roberta-base` (SentencePiece, multilingual):

```
eng    1.42   0.237
hin    1.50   0.294
kan    2.51   0.302
tam    2.44   0.269

hin is 1.06x the fertility of eng
kan is 1.77x the fertility of eng
tam is 1.72x the fertility of eng
```

| tokenizer | eng | hin (ratio) | kan (ratio) | tam (ratio) |
|---|---|---|---|---|
| gpt2 | 1.28 | 7.82 (6.10x) | 22.15 (17.27x) | 24.73 (19.28x) |
| xlm-roberta-base | 1.42 | 1.50 (1.06x) | 2.51 (1.77x) | 2.44 (1.72x) |

**Confirmed.** Hindi's gap nearly vanishes (6.10x → 1.06x); Kannada/Tamil collapse from ~17-19x down to ~1.7-1.8x. English stayed roughly flat (1.28→1.42, a normal artifact of a different, larger SentencePiece vocab — not a confound in the same direction). This is the conceptual bug: fertility-via-whitespace-words, measured with a tokenizer that never learned the target script, mostly measures **tokenizer/training-data mismatch**, not intrinsic language cost. The report's "6x more expensive to serve Hindi" and its Kannada/Tamil-scale implications are largely an artifact of benchmarking with gpt2 specifically, not a property of the languages. Note: a small residual gap (~1.7-1.8x for kan/tam) survives even with a better tokenizer — likely genuine, worth keeping in the corrected analysis rather than claiming zero difference.

## Step 15 — More Indic-aware tokenizers: MuRIL, indic-bert

Same corpus, same unmodified `fertility.py`, `--tokenizer hf:google/muril-base-cased`:

```
eng    1.29   0.217
hin    1.25   0.246
kan    1.77   0.213
tam    1.74   0.192

hin is 0.97x the fertility of eng (better tokenization)
kan is 1.37x the fertility of eng
tam is 1.34x the fertility of eng
```

| tokenizer | eng | hin (ratio) | kan (ratio) | tam (ratio) |
|---|---|---|---|---|
| gpt2 | 1.28 | 7.82 (6.10x) | 22.15 (17.27x) | 24.73 (19.28x) |
| xlm-roberta-base | 1.42 | 1.50 (1.06x) | 2.51 (1.77x) | 2.44 (1.72x) |
| muril-base-cased | 1.29 | 1.25 (0.97x) | 1.77 (1.37x) | 1.74 (1.34x) |

MuRIL (trained specifically on 17 Indian languages) closes the gap further than xlm-roberta-base — Hindi fertility is actually *lower* than English's (0.97x), Kannada/Tamil down to ~1.3-1.4x. Reinforces the conceptual-bug finding: the "cost gap" shrinks as the tokenizer's training data covers the target script/language better, which is exactly what you'd expect if the gap is mostly a tokenizer-coverage artifact rather than an intrinsic language property.

`hf:ai4bharat/indic-bert` failed with an `ImportError: protobuf` — its tokenizer is SentencePiece-based (ALBERT) and needs the `protobuf` package to parse `spiece.model`; without it, `transformers` fell back to a tiktoken-style loader that can't read the file, raising a parse error. Not a real finding, just a missing dependency — added `protobuf>=4.25.0` to requirements.txt.

Rerun after installing protobuf:

```
eng    1.38   0.232
hin    1.70   0.333
kan    3.10   0.372
tam    3.34   0.367

hin is 1.23x the fertility of eng
kan is 2.24x the fertility of eng
tam is 2.42x the fertility of eng
```

| tokenizer | eng | hin (ratio) | kan (ratio) | tam (ratio) |
|---|---|---|---|---|
| gpt2 | 1.28 | 7.82 (6.10x) | 22.15 (17.27x) | 24.73 (19.28x) |
| xlm-roberta-base | 1.42 | 1.50 (1.06x) | 2.51 (1.77x) | 2.44 (1.72x) |
| muril-base-cased | 1.29 | 1.25 (0.97x) | 1.77 (1.37x) | 1.74 (1.34x) |
| ai4bharat/indic-bert | 1.38 | 1.70 (1.23x) | 3.10 (2.24x) | 3.34 (2.42x) |

indic-bert lands between xlm-roberta-base and muril-base-cased — worse than MuRIL despite being India-specific, likely because indic-bert's ALBERT-style vocab is much smaller (shared/compressed for a lightweight model) than MuRIL's. All three Indic-aware tokenizers agree on the core finding regardless of exact ranking: the eng-vs-kan/tam gap under gpt2 (17-19x) collapses to roughly 1.2-2.4x under any tokenizer that actually saw these scripts during training — strengthening the conceptual-bug conclusion, not just a one-tokenizer fluke.

## Step 16 — A2 final verdict: the three claims we're taking forward

Of the 7 candidates tested above, these are the three going into the audit writeup — one code bug, one confirmed-harmless ("looks suspicious but fine"), one conceptual flaw. The other four (macro/micro-avg, `.lower()`, base-language ordering, dead `random.seed`) were tested and logged but are either too small to matter or not interesting enough to claim — kept in the notebook as the dead ends they are, not discarded silently.

**1. Clean code bug — `words = line.split(" ")` (line 62).**
A plain single-space split turns any double space in the source text into an empty-string "word," inflating the word count and understating fertility. Both sample corpora and the FLORES-101 corpus contain lines with double spaces. Isolated and measured (`fertility_split_ws.py`, `split(" ")` → `split()`):
- 10-line sample: eng 1.27→1.28, hin 7.45→7.60, ratio 5.89x→5.92x
- FLORES-101 (997 lines): eng 1.28→1.28, hin 7.82→7.83, kan 22.15→22.95, tam 24.73→24.87
Small (~0-4%) but real and consistently in one direction (original always slightly *understates* fertility) — a genuine, if minor, bug.

**2. Suspicious but fine — NFC normalization (line 49).**
Looks like exactly the kind of silent text-mangling that would bias a cross-language comparison. Tested by removing it (`fertility_no_nfc.py`) on both the sample corpus and FLORES-101: output was byte-for-byte identical to the original in every column, every language. The corpora used here are already NFC-normalized, so this line is currently a no-op — confirmed harmless, not flagged as a bug. (Caveat: could matter on messier, non-normalized real-world/scraped text; not something this evidence rules out in general, only on this data.)

**3. Conceptual problem — tokens/word via an English-trained tokenizer conflates language cost with tokenizer coverage.**
The script computes tokens/word exactly as specified — the bug is that this isn't the right question when the tokenizer itself is a confound. gpt2's BPE vocab has effectively no Kannada/Tamil coverage, so it degrades toward byte-level encoding for those scripts, making "fertility" mostly measure *tokenizer-training mismatch*, not intrinsic language cost. Evidence: swapping only the tokenizer, same unmodified script, same FLORES-101 corpus —

| tokenizer | eng | hin (ratio) | kan (ratio) | tam (ratio) |
|---|---|---|---|---|
| gpt2 | 1.28 | 7.82 (6.10x) | 22.15 (17.27x) | 24.73 (19.28x) |
| xlm-roberta-base | 1.42 | 1.50 (1.06x) | 2.51 (1.77x) | 2.44 (1.72x) |
| muril-base-cased | 1.29 | 1.25 (0.97x) | 1.77 (1.37x) | 1.74 (1.34x) |
| ai4bharat/indic-bert | 1.38 | 1.70 (1.23x) | 3.10 (2.24x) | 3.34 (2.42x) |

English stays roughly flat (1.28-1.42) across all four tokenizers; Hindi's "6x worse" collapses to near-parity (0.97x-1.23x); Kannada/Tamil's "17-19x worse" collapses to 1.3x-2.4x — a 7-14x reduction in the reported gap, replicated across three independent Indic-aware tokenizers, not a one-model fluke. The report's "budget 6x serving cost for Hindi, route Indic traffic separately" is largely an artifact of benchmarking with gpt2 specifically. A real, smaller residual gap (~1.2-2.4x for kan/tam) does survive even with better tokenizers — the honest claim is "the gap is far smaller than reported and mostly a tokenizer-choice artifact," not "there is no gap."

## Step 17 — A3: corrected analysis, 3 tokenizers x 4 denominators (FLORES-200, primary corpus)

Built `partA/corrected_analysis.py`: bug-fixed (`split()` not `split(" ")`), keeps NFC (confirmed harmless), reports 4 denominators per language — tok/word, tok/byte (UTF-8), tok/grapheme, and **tok/sentence** (mean tokens per parallel sentence — new, added specifically for A3, since FLORES sentences are translations of each other and so are the one denominator that holds *meaning* constant, not just a proxy like words/bytes/graphemes).

Ran on **FLORES-200** (`partA/data/flores200_eval/`, our declared primary corpus per the A1 writeup), all 4 languages, 3 tokenizers (gpt2, xlm-roberta-base, ai4bharat/indic-bert):

```
gpt2
lang    tok/word  tok/byte  tok/grapheme  tok/sentence
eng        1.283    0.2150        0.2152       26.78
hin        7.826    0.5943        1.5977      192.42
kan       22.946    0.9785        2.9112      350.85
tam       24.867    0.9957        3.1748      398.38

xlm-roberta-base
eng        1.419    0.2372        0.2374       29.58
hin        1.500    0.1144        0.3069       36.75
kan        2.601    0.1116        0.3314       39.74
tam        2.453    0.0987        0.3140       39.23

ai4bharat/indic-bert
eng        1.383    0.2316        0.2318       28.86
hin        1.702    0.1296        0.3479       41.82
kan        3.214    0.1373        0.4082       49.11
tam        3.359    0.1348        0.4292       53.79
```

**Ratio to eng, by denominator and tokenizer (FLORES-200):**

| tokenizer | denom | hin | kan | tam |
|---|---|---|---|---|
| gpt2 | tok/word | 6.10x | 17.89x | 19.38x |
| gpt2 | tok/byte | 2.76x | 4.55x | 4.63x |
| gpt2 | tok/sentence | 7.18x | 13.10x | 14.88x |
| xlm-roberta-base | tok/word | 1.06x | 1.83x | 1.73x |
| xlm-roberta-base | tok/byte | 0.48x | 0.47x | 0.42x |
| xlm-roberta-base | tok/sentence | 1.24x | 1.34x | 1.33x |
| indic-bert | tok/word | 1.23x | 2.32x | 2.43x |
| indic-bert | tok/byte | 0.56x | 0.59x | 0.58x |
| indic-bert | tok/sentence | 1.45x | 1.70x | 1.86x |

**Key observation — tok/byte is its own confound.** Under xlm-roberta-base and indic-bert, Hindi/Kannada/Tamil come out *cheaper* per byte than English (ratios < 1.0x). This isn't because Indic text is cheaper to serve — it's because Devanagari/Kannada/Tamil are multi-byte in UTF-8 (~3 bytes/codepoint) while English ASCII is 1 byte/char, so "tokens per byte" is inflated for English and deflated for Indic scripts independent of any real cost difference. tok/byte fails the same test tok/word failed in A2: it doesn't hold a fair unit constant across languages/scripts.

**tok/sentence is the answer to "which single number should drive the routing decision."** FLORES sentences are translations of each other — same meaning, same content — so tokens-to-encode-one-sentence directly answers "how much context/compute does this language cost for the same request," which is exactly what a routing/capacity decision needs. It isn't distorted by whitespace-word morphology differences (A2's bug) or UTF-8 byte-density differences (this section's finding). Under gpt2 it still shows the same massive, misleading gap (7-15x) as tok/word did; under an Indic-aware tokenizer it shows a real, modest residual: Hindi ~1.2-1.5x, Kannada/Tamil ~1.3-1.9x — consistent with tok/word's residual finding in A2, cross-validating each other.

**A3 conclusion:** the single number to drive the routing-and-cost decision is **tokens per request (operationalized here as tok/sentence on parallel data), measured with an Indic-aware tokenizer** — not tok/word (conflates morphology with tokenizer coverage, A2's conceptual bug) and not tok/byte (conflates UTF-8 script encoding density with cost). Recommendation candidate for A4: xlm-roberta-base showed the smallest, most consistent residual gap (1.24x-1.34x) of the two Indic-aware tokenizers tested here — pending final tokenizer choice in A4.

## Step 18 — A3 cross-check on FLORES-101 (supporting corpus)

FLORES-200 is the primary/declared corpus for this assignment (A1). To confirm the FLORES-200 result above isn't an artifact of one particular data pull or HF access path, reran the identical `corrected_analysis.py` command against `partA/data/flores101_eval/` (the public, ungated tarball — kept in the repo specifically to make this cross-check reproducible without a gated HF token).

Result: **numbers identical to the FLORES-200 run above, in every cell, all 3 tokenizers, all 4 denominators** (e.g. gpt2 tok/sentence: eng 26.78, hin 192.42, kan 350.85, tam 398.38 — matches to 2 decimal places on both corpora). This was expected per the A1 writeup: FLORES-200's dev split for eng/hin/kan/tam is built on the same underlying sentences as FLORES-101 for these languages. FLORES-101 serves its purpose here — an independent, reproducible confirmation that the FLORES-200 primary result holds — not as a second, separate finding. All A3 findings and the conclusion above are reported against FLORES-200 as the headline corpus, with FLORES-101 as corroborating support.

---

# Part B — Capacity Reconciliation

Source files: `starter_kit/bench/model_spec.md` (serving spec for FLM-4B-Instruct on 1x L4 24GB) and `bench_log.csv` (13-row load test log), copied untouched into `partB/data/` for a self-contained working copy.

## Step 19 — B1: KV-cache bytes/token and max concurrent sequences

Built `partB/kv_cache_calc.py` — named, editable constants from `model_spec.md`, so the arithmetic can be re-derived live with different assumptions (e.g. a different GPU or utilization) without touching the formulas.

**KV-cache bytes/token:**
```
2 (K and V) x 28 layers x 8 KV_heads x 128 head_dim x 2 bytes (fp16) = 114,688 bytes/token (112 KiB/token)
```

**Max concurrent 4096-token sequences:**
```
model weights = 4.2e9 params x 2 bytes (fp16) = 7.83 GiB
usable GPU memory for KV cache = 24 GiB x 0.92 (gpu_memory_utilization) - 7.83 GiB (weights) - 1.6 GiB (overhead) = 12.66 GiB
bytes per 4096-token sequence = 114,688 bytes/token x 4096 tokens = 469,762,048 bytes = 448 MiB
max concurrent sequences = 12.66 GiB / 448 MiB ~= 28
```

**Cross-check against `bench_log.csv`**, rows with `prompt_len=3584, gen_len=512` (3584+512 = 4096 tokens total, matching the sequence length assumed above — these are exactly the rows to check):

| batch | kv_cache_util | preempted_seqs |
|---|---|---|
| 4 | 0.16 | 0 |
| 8 | 0.31 | 0 |
| 16 | 0.62 | 0 |
| 24 | 0.93 | 0 |
| 32 | 0.97 | 7 |
| 48 | 0.97 | 23 |

**Verdict — prediction confirmed.** The predicted ceiling (~28 sequences) sits exactly in the transition zone the log shows: batch 24 is below the ceiling and has zero preemptions (system still has headroom, 93% KV util); batch 32 is above the ceiling and immediately shows preemption (7 sequences evicted); batch 48 (further above) shows even more (23 evicted). If the formula's ceiling were wrong — e.g. much lower or much higher than 28 — this clean "fine below it, breaks right above it" pattern wouldn't hold. Two independent sources (a formula derived only from the spec sheet, and a real measured load test) agree on where the system runs out of KV-cache room.

## Step 20 — B2: the long-context throughput anomaly

Naive expectation: throughput (`reported_tok_s`) should keep rising as batch size rises. Looking at the `prompt_len=3584` rows, it does — up through batch 24 — then reverses.

Built `partB/throughput_anomaly.py`: uses batch 24 (the last batch with zero preemptions) as a "no-contention" baseline (per-request rate = 1607.4 / 24 = 66.98 tok/s/request), projects what throughput *should* be at larger batches if that rate held with no contention, and compares to what was actually measured.

```
batch   tok/s   %chg vs prev   naive-projected   shortfall %   preempted
4       565.4                  267.9             -111.0%       0
8       902.6   +59.6%         535.8             -68.5%        0
16      1311.4  +45.3%         1071.6            -22.4%        0
24      1607.4  +22.6%         1607.4             0.0%         0
32      1384.0  -13.9%         2143.2             35.4%        7
48      1298.5  -6.2%          3214.8             59.6%        23
```

**Reading this:** below batch 24, actual throughput is *higher* than the naive per-request-rate projection (negative shortfall) — expected, since small batches don't saturate the GPU's parallelism, so each added request is nearly "free" and total throughput scales better than linearly. batch 24 is the sweet spot (0% shortfall by construction). Past batch 24, throughput doesn't just fail to keep scaling — it drops in absolute terms (-13.9% at batch 32, -19.2% cumulative by batch 48 vs. batch 24's peak), while the shortfall vs. naive projection balloons to 35.4% (batch 32) and 59.6% (batch 48).

**Mechanism, using the specific rows/columns:** `kv_cache_util` hits 0.97 (essentially full) exactly at batch 32, and `preempted_seqs` goes from 0 (batch 24) to 7 (batch 32) to 23 (batch 48) — see B1's table. Once the KV cache is full, the scheduler can't just hold more sequences: it has to preempt (evict) some mid-generation to free room, then resume them later. That eviction/resume cycle burns time without producing new output tokens, so wall-clock time grows faster than useful work does — which is exactly why throughput falls even as `num_requests` rises. This is the same root cause identified in B1 (GPU out of KV-cache room), now shown to directly cause a measurable throughput regression, not just a capacity ceiling.

**Proposed fix:** cap admission at batch size ≤24 for ~4096-token-long requests (admission control keyed off predicted KV-cache usage, not just queue depth) — reject/queue excess requests instead of overcommitting and thrashing. **Predicted quantitative effect:** sustaining batch 24's 1607.4 tok/s instead of degrading to batch 48's 1298.5 tok/s — a **~19.2% throughput improvement** by refusing to over-admit past the point where preemption starts, using already-measured numbers from this log (not a new experiment, a comparison of measured before/after batch sizes).

## Step 21 — B3: the goodput correction

REPORT_v0 Section 2 claims (a) longer prompts give better throughput, and (b) batch 48 will deliver ~3200 tok/s. Both trace to the same misread column: `reported_tok_s`.

Built `partB/goodput_calc.py`. First confirms the hypothesis on the batch=24, prompt_len=3584 row:

```
(prompt_len + gen_len) * num_requests / wall_clock_s = (3584+512) * 24 / 61.16 = 1607.3
reported_tok_s from log                                                       = 1607.4
=> MATCHES
```

`reported_tok_s` is literally `(prompt tokens + generated tokens) / wall_clock_s` — it counts the ~3584 prompt tokens (read in one cheap parallel prefill pass) as if they were generated one-by-one at the same rate as the 512 actually-generated tokens. Long prompts get to "count" thousands of nearly-free tokens toward the throughput number, which is exactly why longer prompts *looked* faster.

**Honest goodput, two independent derivations, same row (batch=24, prompt_len=3584):**

*Method 1 — generated tokens only, over wall clock:*
```
gen_len * num_requests / wall_clock_s = 512 * 24 / 61.16 = 200.9 tok/s
```

*Method 2 — from decode-phase per-token latency (`itl_ms_p50`):*
```
per-request rate = 1000 / 96.07 = 10.409 tok/s/request
goodput = 10.409 * 24 = 249.8 tok/s
```

Both land in the same ballpark (~200-250 tok/s) despite being derived completely differently (one from total wall-clock time, one from steady-state per-token decode latency) — cross-validating each other. Compared to the reported 1607.4 tok/s, the log's number **overstates real generation throughput by ~613%**.

**The batch-48 "~3200 tok/s" claim traces to the exact same bug, compounded with a naive linear-scaling assumption:** `1607.4 (batch 24's reported/blended tok/s) x 2 (batch doubling: 48/24=2) = 3214.8` — matching the report's "~3200" almost exactly. So the report didn't just misread one column once — it took the already-blended, misleading batch-24 number and naively doubled it for batch 48, ignoring that (per B1/B2) the GPU runs out of KV-cache room well before batch 48 and throughput *drops*, not doubles.

**What the report should have said:** honest generation throughput at batch 24 is ~200-250 tok/s, not 1607 — the earlier number counted prompt-reading as if it were generation. Longer prompts don't give "better throughput"; they make the blended metric look better because more prefill tokens get folded into the same denominator. And batch 48 does not deliver ~3200 tok/s — per B2, real throughput at batch 48 is *lower* than at batch 24 (1298.5 vs 1607.4 reported, and honest goodput would be lower still), because the GPU is past its KV-cache capacity and thrashing on preemption, not scaling linearly.

## Step 22 — B4: confirming metric for the B2 mechanism

`bench_log.csv` already contains the smoking-gun counter: `preempted_seqs`, which is 0 through batch 24 and jumps to 7 (batch 32) then 23 (batch 48) — exactly the batch sizes B1 predicted would exceed the ~28-sequence KV-cache ceiling. But `bench_log.csv` is a one-shot load-test log, not live telemetry — to confirm this mechanism is actually happening in a running production deployment (not just in this offline test), the metric to pull is the serving stack's own preemption counter: in a vLLM-style serving stack this is `num_preemptions_total` (a running Prometheus counter incremented every time the scheduler evicts a sequence to free KV-cache blocks), alongside `gpu_cache_usage_perc` (the live analogue of this log's `kv_cache_util`). Expected value: `num_preemptions_total` should stay flat at 0 while concurrent long-context (~4096-token) requests stay at or below ~24-28, then start climbing once concurrency exceeds that — mirroring the exact pattern already seen in `preempted_seqs` here (0 → 7 → 23), and any sustained climb in that counter alongside `gpu_cache_usage_perc` pinned near 1.0 would confirm the same KV-cache-exhaustion mechanism is recurring live, not just an artifact of this one test run.
