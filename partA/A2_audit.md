# A2 — Script & Metric Audit

Seven candidate issues in `fertility.py` were tested, each isolated and measured against both the 10-line sample corpus and the 997-line FLORES corpus (script variants in `partA/audit_experiments/`). Three are taken forward as the final claims — one code bug, one confirmed-harmless ("looks suspicious but fine"), one conceptual flaw. The other four are logged as tested-but-rejected, not silently dropped.

## Final claims

### 1. Clean code bug — `words = line.split(" ")` (line 62)

A plain single-space split turns any double space in the source text into an empty-string "word," inflating the word count and understating fertility. Both sample corpora and FLORES-101 contain lines with double spaces. Isolated via `fertility_split_ws.py` (`split(" ")` → `split()`):

| corpus | eng (before→after) | hin (before→after) | kan | tam |
|---|---|---|---|---|
| toy sample (10 lines) | 1.27→1.28 | 7.45→7.60 | — | — |
| FLORES (997 lines) | 1.28→1.28 | 7.82→7.83 | 22.15→22.95 | 24.73→24.87 |

Small (~0-4%) but real and consistently in one direction (original always slightly *understates* fertility). **Verdict: genuine, minor bug.**

### 2. Suspicious but fine — NFC normalization (line 49)

Looks exactly like the kind of silent text-mangling that could bias a cross-language comparison. Tested by removing it entirely (`fertility_no_nfc.py`) on both corpora: output was byte-for-byte identical to the original in every column, every language. The corpora used here are already NFC-normalized, so this line is currently a no-op. **Verdict: confirmed harmless, not a bug** — though it could matter on messier, non-normalized real-world/scraped text; this evidence only rules it out on this data.

### 3. Conceptual problem — tokens/word via an English-trained tokenizer conflates language cost with tokenizer coverage

The script computes tokens/word exactly as specified — the bug is that this isn't the right question when the tokenizer itself is a confound. gpt2's BPE vocab has effectively no Kannada/Tamil coverage, so it degrades toward byte-level encoding for those scripts, making "fertility" mostly measure *tokenizer-training mismatch*, not intrinsic language cost.

Evidence: swapping only the tokenizer, same unmodified script, same FLORES corpus:

| tokenizer | eng | hin (ratio) | kan (ratio) | tam (ratio) |
|---|---|---|---|---|
| gpt2 | 1.28 | 7.82 (6.10x) | 22.15 (17.27x) | 24.73 (19.28x) |
| xlm-roberta-base | 1.42 | 1.50 (1.06x) | 2.51 (1.77x) | 2.44 (1.72x) |
| muril-base-cased | 1.29 | 1.25 (0.97x) | 1.77 (1.37x) | 1.74 (1.34x) |
| ai4bharat/indic-bert | 1.38 | 1.70 (1.23x) | 3.10 (2.24x) | 3.34 (2.42x) |

English stays roughly flat across all four tokenizers; Hindi's "6x worse" collapses to near-parity (0.97x-1.23x); Kannada/Tamil's "17-19x worse" collapses to 1.3x-2.4x — replicated across three independent Indic-aware tokenizers, not a one-model fluke. **Verdict: this is the report's real conceptual bug.** The report's "budget 6x serving cost for Hindi, route Indic traffic separately" is largely an artifact of benchmarking with gpt2 specifically. A real, smaller residual gap (~1.2-2.4x) does survive — the honest claim is "the gap is far smaller than reported and mostly a tokenizer-choice artifact," not "there is no gap."

## Tested and rejected (not claimed as bugs)

| # | candidate | finding |
|---|---|---|
| 1 | `.lower()` (line 60) | Real, asymmetric effect (Hindi unchanged, English shifts ~3%) but small, and direction *narrows* not widens the reported gap — not the report's problem. |
| 2 | macro-avg vs micro-avg | ~0-5% shift at both corpus sizes, doesn't flip the headline gap. |
| 3 | `chars = len(line)` (grapheme vs. codepoint count) | Real effect on `tok/char` only (e.g. hin 1.528→1.598), doesn't touch fertility/tok-word, and doesn't change the headline conclusion. |
| 4 | `base = langs[0]` (ratio direction) | Confirmed to be an artifact of `--corpus` argument order (per-language numbers unchanged), not a computational bug. |
| 5 | `random.seed(1337)` | Confirmed dead code — imported and seeded, never used elsewhere in the file. Harmless. |

Full before/after tables for each, including the FLORES-scale reruns, are in `NOTEBOOK.md` and `results.md`.
