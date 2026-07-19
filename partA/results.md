# Results — Tokenizer Fertility Audit

All runs: FLORES-200 (primary corpus) unless noted; FLORES-101 used only as a cross-check (numbers identical in every case tested).

## Baseline reproduction (toy sample corpus, unmodified `fertility.py`)

| lang | fertility (tok/word) | tok/char |
|---|---|---|
| eng | 1.27 | 0.226 |
| hin | 7.45 | 1.579 |

hin is 5.89x the fertility of eng — matches `REPORT_v0.md`.

## A2 — candidate bug tests

### #1 — `.lower()` (line 60)

| corpus | eng fert (with/without) | hin fert (with/without) | ratio (with/without) |
|---|---|---|---|
| toy sample (10 lines) | 1.27 / 1.23 | 7.45 / 7.45 | 5.89x / 6.06x |
| FLORES (997 lines) | 1.28 / 1.24 | 7.82 / 7.82 | 6.10x / 6.33x |

### #2 — `line.split(" ")` → `line.split()` (line 62)

| corpus | eng fert (before/after) | hin fert (before/after) | kan (before/after) | tam (before/after) |
|---|---|---|---|---|
| toy sample (10 lines) | 1.27 / 1.28 | 7.45 / 7.60 | — | — |
| FLORES (997 lines) | 1.28 / 1.28 | 7.82 / 7.83 | 22.15 / 22.95 | 24.73 / 24.87 |

### #3 — `len(line)` → grapheme-cluster count (line 63, tok/char only)

| corpus | eng tok/char | hin tok/char | kan tok/char | tam tok/char |
|---|---|---|---|---|
| toy sample, `len()` | 0.226 | 1.579 | — | — |
| toy sample, grapheme | 0.226 | 1.638 | — | — |
| FLORES, `len()` | 0.215 | 1.528 | 2.655 | 2.717 |
| FLORES, grapheme | 0.215 | 1.598 | 2.911 | 3.175 |

### #4 — NFC normalization (line 49)

Removed entirely (`fertility_no_nfc.py`): output byte-for-byte identical to original on both toy sample and FLORES, every language, every column. **No-op on this data — confirmed harmless.**

### #5 — macro-avg vs micro-avg

| corpus | eng fert (macro/micro) | hin fert (macro/micro) | kan (macro/micro) | tam (macro/micro) |
|---|---|---|---|---|
| toy sample (10 lines) | 1.27 / 1.25 | 7.45 / 7.40 | — | — |
| FLORES (997 lines) | 1.28 / 1.27 | 7.82 / 7.79 | 22.15 / 21.70 | 24.73 / 24.46 |

### #6 — base-language ordering (`base = langs[0]`)

| `--corpus` order | printed result |
|---|---|
| eng, hin | "hin is 5.89x the fertility of eng" |
| hin, eng | "eng is 0.17x the fertility of hin (better tokenization)" |

Per-language numbers unchanged (7.45 / 1.27 either way) — only the framing flips.

### #7 — `random.seed(1337)`

`random` imported and seeded, never called elsewhere in the file. Confirmed dead code.

## A2 — conceptual bug: tokenizer swap (fertility / tok-per-word, unmodified script, FLORES corpus)

| tokenizer | eng | hin (ratio) | kan (ratio) | tam (ratio) |
|---|---|---|---|---|
| gpt2 | 1.28 | 7.82 (6.10x) | 22.15 (17.27x) | 24.73 (19.28x) |
| xlm-roberta-base | 1.42 | 1.50 (1.06x) | 2.51 (1.77x) | 2.44 (1.72x) |
| muril-base-cased | 1.29 | 1.25 (0.97x) | 1.77 (1.37x) | 1.74 (1.34x) |
| ai4bharat/indic-bert | 1.38 | 1.70 (1.23x) | 3.10 (2.24x) | 3.34 (2.42x) |

## A3 — corrected analysis: 3 tokenizers x 4 denominators (FLORES-200, primary)

### gpt2

| lang | tok/word | tok/byte | tok/grapheme | tok/sentence |
|---|---|---|---|---|
| eng | 1.283 | 0.2150 | 0.2152 | 26.78 |
| hin | 7.826 | 0.5943 | 1.5977 | 192.42 |
| kan | 22.946 | 0.9785 | 2.9112 | 350.85 |
| tam | 24.867 | 0.9957 | 3.1748 | 398.38 |

### xlm-roberta-base

| lang | tok/word | tok/byte | tok/grapheme | tok/sentence |
|---|---|---|---|---|
| eng | 1.419 | 0.2372 | 0.2374 | 29.58 |
| hin | 1.500 | 0.1144 | 0.3069 | 36.75 |
| kan | 2.601 | 0.1116 | 0.3314 | 39.74 |
| tam | 2.453 | 0.0987 | 0.3140 | 39.23 |

### ai4bharat/indic-bert

| lang | tok/word | tok/byte | tok/grapheme | tok/sentence |
|---|---|---|---|---|
| eng | 1.383 | 0.2316 | 0.2318 | 28.86 |
| hin | 1.702 | 0.1296 | 0.3479 | 41.82 |
| kan | 3.214 | 0.1373 | 0.4082 | 49.11 |
| tam | 3.359 | 0.1348 | 0.4292 | 53.79 |

### Ratio to eng, by denominator and tokenizer

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

## FLORES-101 cross-check

Identical run against `partA/data/flores101_eval/` (all 3 tokenizers, all 4 denominators): every value matched the FLORES-200 table above to 2 decimal places.
