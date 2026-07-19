# Lab Notebook — Tokenizer & Serving Audit

Chronological log: hypothesis → experiment → result → revision. Dead ends included on purpose.

## 2026-07-19 — Setup

- Created `23BDS023-submission/` scaffold, kept `starter_kit/` untouched as reference.
- Copied `fertility.py` → `partA/fertility_audit.py` as our working copy (baseline behavior unchanged so far).
- Plan: (1) reproduce the intern's reported numbers on the sample corpus before changing anything, (2) audit the script/metric on that same small corpus, (3) build a real multilingual eval corpus, (4) rerun corrected analysis, (5) write memo.

## 2026-07-19 — Baseline reproduction

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

## 2026-07-19 — A2, candidate #1: `.lower()` (line 60)

Hypothesis: lowercasing is a no-op for Hindi (no case in Devanagari) but shifts English token counts (BPE is case-sensitive) — asymmetric effect on a cross-language metric.

Test: `audit_experiments/fertility_no_lower.py` (identical script, `.lower()` removed), same corpus/tokenizer.

| | eng fertility | hin fertility | ratio |
|---|---|---|---|
| with `.lower()` (original) | 1.27 | 7.45 | 5.89x |
| without `.lower()` | 1.23 | 7.45 | 6.06x |

**Confirmed:** effect is real and asymmetric exactly as predicted — Hindi unchanged (0.00), English shifts (-0.04, ~3%). But direction matters: removing `.lower()` *increases* the eng-hin gap, not decreases it, so `.lower()` was making the reported disparity slightly smaller than the true one, not inflating it. Small magnitude (~3% on eng, ratio moves 5.89→6.06) — doesn't flip the headline conclusion. Verdict: real but minor effect, not the flaw driving the report's biggest problems. Moving to next candidate.

## 2026-07-19 — A2, candidate #2: `line.split(" ")` (line 62)

Test: `audit_experiments/fertility_split_ws.py`, `line.split(" ")` → `line.split()`.

| | eng fertility | hin fertility | ratio |
|---|---|---|---|
| `split(" ")` (original) | 1.27 | 7.45 | 5.89x |
| `split()` | 1.28 | 7.60 | 5.92x |

Observation only, no verdict yet.

## 2026-07-19 — A2, candidate #3: `chars = len(line)` (line 63)

Test: `audit_experiments/fertility_grapheme.py` — replaced `len(line)` with a grapheme-cluster approximation (`grapheme_len`: counts codepoints but skips Unicode combining marks, so Devanagari matras attached to a base consonant aren't counted as extra "characters").

| | eng tok/char | hin tok/char |
|---|---|---|
| `len(line)` (original) | 0.226 | 1.579 |
| grapheme-aware count | 0.226 | 1.638 |

Fertility (tok/word) unchanged in both, as expected — this only touches the tok/char column. Observation only, no verdict yet.

## 2026-07-19 — A2, candidate #4: NFC normalization (line 49)

Test: `audit_experiments/fertility_no_nfc.py` — removed `unicodedata.normalize("NFC", line)`.

Result: output identical to original in every column (eng and hin). Sample corpus files are already NFC-normalized, so this line is currently a no-op on this data — flag as red-herring candidate, though could matter on messier real-world/scraped text later.

## 2026-07-19 — A2, candidate #5: macro-avg vs micro-avg (lines 56-67)

Test: `audit_experiments/fertility_micro_avg.py` — sum tokens/words/chars across corpus, divide once, instead of averaging per-line ratios.

| | eng fertility | eng tok/char | hin fertility | hin tok/char | ratio |
|---|---|---|---|---|---|
| macro-avg (original) | 1.27 | 0.226 | 7.45 | 1.579 | 5.89x |
| micro-avg | 1.25 | 0.221 | 7.40 | 1.583 | 5.91x |

Observation only, no verdict yet. At this corpus size (~10 lines) the shift is small; open question for A3 whether it grows at FLORES-200 scale.

## 2026-07-19 — A2, candidate #6: `base = langs[0]` (line 97)

Test: reran with `--corpus` order swapped (hin first, eng second).

| order | printed ratio |
|---|---|
| eng, hin (original) | "hin is 5.89x the fertility of eng" |
| hin, eng (swapped) | "eng is 0.17x the fertility of hin (better tokenization)" |

Per-language fertility numbers unchanged (7.45 / 1.27 either way) — only the printed framing/direction flips with argument order. Confirms base language is an arbitrary artifact of CLI arg order, not a principled reference point.

## 2026-07-19 — A2, candidate #7: `random.seed(1337)` (line 25)

Checked: `random` is imported and seeded but never called anywhere else in the file (`grep -n random fertility.py` → only the import and seed lines). Dead code as it stands in this script.

## 2026-07-19 — A1: real eval corpus (FLORES-101)

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

## 2026-07-19 — A1: FLORES-200 (gated) via HF token

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

## 2026-07-19 — A2, candidates #1/#2/#3/#5 rerun at scale (FLORES-101, 997 lines)

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

**Verdict:** at 997-line scale, candidates #1, #2, #3, #5 each move numbers by only ~0-5%, and none flip or meaningfully narrow the headline gap (eng vs hin/kan/tam still off by 6x/18x/20x either way). No `.lower()` (#1) only shifts eng (1.28→1.24, ~3%) — hin/kan/tam completely unchanged (0 combining case in these scripts), confirming the asymmetric-but-minor pattern already seen on the toy corpus, just larger sample this time. Same conclusion as the toy-corpus tests, just confirmed at scale: these are real, measurable, but minor effects — not the conceptual bug the report is missing. The real conceptual problem is elsewhere (see A2 writeup): comparing "tokens per whitespace-word" as a cost proxy across languages with different morphology/script density, without holding information-content constant — that's the denominator question A3 exists to fix, not any of these code-level nitpicks.

## 2026-07-19 — A2, conceptual bug test: swap tokenizer (gpt2 → xlm-roberta-base)

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

## 2026-07-19 — more Indic-aware tokenizers: MuRIL, indic-bert

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
