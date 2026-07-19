# Audit Submission — Tokenizer & Serving Findings

Audit of `starter_kit/REPORT_v0.md` (tokenizer fertility + serving throughput claims), per the assignment. Full reasoning/dead-ends are in `NOTEBOOK.md`; this file is just structure + how to reproduce.

## Structure

**Start here if you only read one thing:** `NOTEBOOK.md` (the full chronological reasoning) or the numbered `A0`-`A4` / `B1`-`B4` files below (the polished, per-question writeups). Everything else is supporting code/data.

### Repo root

| file | what it is |
|---|---|
| `NOTEBOOK.md` | Chronological lab notebook (graded as-is) — every hypothesis, experiment, result, and dead end, in the order it happened. |
| `AI_USAGE.md` | Honest summary of where AI helped and where it misled, per part. |
| `requirements.txt` | All Python deps needed for Parts A and B. |
| `.env` | `HF_KEY=...` for gated FLORES-200 access. Gitignored — not in the pushed repo. |

### `partA/` — tokenizer audit

**Writeups (read these):**
| file | answers |
|---|---|
| `A0_baseline_reproduction.md` | Does our setup reproduce the intern's original numbers before we touch anything? |
| `A1_corpus.md` | What eval corpus did we build — languages, size, domain, caveats? |
| `A2_audit.md` | What's actually wrong with `fertility.py` — the real bug, the false alarm, the conceptual flaw? |
| `A3_corrected_analysis.md` | Redone properly: 3 tokenizers x 4 denominators — which number should drive the routing decision? |
| `A4_recommendation_memo.md` | The ≤1-page recommendation memo. |

**Code and data (what the writeups above are derived from):**
| path | what it is |
|---|---|
| `reproducing_result/` | Untouched `fertility.py` + the original 10-line sample corpus — the A0 baseline. |
| `audit_experiments/` | One variant script per A2 candidate (each isolates exactly one change), plus a local FLORES-101 copy for scale tests. |
| `corrected_analysis.py` | The A3 script: bug-fixed, reports all 4 denominators, works with any `--tokenizer`. |
| `corpus_prep_flores200.py` | Downloads FLORES-200 from the gated `facebook/flores` (needs `HF_KEY` in `.env`). |
| `data/flores101_eval/` | FLORES-101 (public, ungated) — committed, the primary reproducible corpus copy. |
| `data/flores200_eval/` | FLORES-200 (gated) — gitignored, regenerate locally with `corpus_prep_flores200.py`. |

### `partB/` — capacity reconciliation

**Writeups (read these):**
| file | answers |
|---|---|
| `B1_kv_cache_capacity.md` | How much KV-cache memory per token, and how many concurrent sequences can the GPU hold? |
| `B2_throughput_anomaly.md` | Where does throughput stop scaling with batch size, and why? |
| `B3_goodput_correction.md` | What's wrong with the report's `reported_tok_s`-based throughput claims? |
| `B4_confirming_metric.md` | What live production metric would confirm the B2 mechanism? |

**Code and data:**
| path | what it is |
|---|---|
| `kv_cache_calc.py` | Script behind B1. |
| `throughput_anomaly.py` | Script behind B2. |
| `goodput_calc.py` | Script behind B3. |
| `data/` | `bench_log.csv` + `model_spec.md`, copied from `starter_kit/bench/`. |

### `partC/` — decision memo

| file | what it is |
|---|---|
| `memo.md` | ≤1-page decision memo: casual-tone rollout across 6 languages, under real constraints. |

## Setup

```
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

FLORES-200 requires a HuggingFace token with access to the gated `facebook/flores` repo — put it in a `.env` file in this directory as `HF_KEY="hf_..."`. Not required to reproduce anything below: FLORES-101 (already committed under `partA/data/flores101_eval/`) is numerically identical to FLORES-200 for all 4 languages used here (see `A1_corpus.md`).

## Reproduce A0 — baseline

```
cd partA/reproducing_result
..\..\venv\Scripts\python.exe fertility.py --corpus eng=corpus_sample\eng_sample.txt --corpus hin=corpus_sample\hin_sample.txt --tokenizer gpt2
```
Expected: eng 1.27, hin 7.45, 5.89x — matches `REPORT_v0.md`.

## Reproduce A2 — the one confirmed bug

Of the 5 code-level candidates tested (see `A2_audit.md` for the full set, including the 4 that turned out to have no meaningful effect), only one actually changes the numbers: `words = line.split(" ")` (`partA/reproducing_result/fertility.py`, line 62). A plain single-space split turns a double space into an empty-string "word," inflating the word count and understating fertility.

**Exact fix** (`partA/audit_experiments/fertility_split_ws.py` vs. the original):
```diff
- words = line.split(" ")
+ words = line.split()
```

Reproduce the before/after:
```
cd partA\audit_experiments
..\..\venv\Scripts\python.exe fertility.py           --corpus eng=corpus_sample\eng_sample.txt --corpus hin=corpus_sample\hin_sample.txt --tokenizer gpt2
..\..\venv\Scripts\python.exe fertility_split_ws.py   --corpus eng=corpus_sample\eng_sample.txt --corpus hin=corpus_sample\hin_sample.txt --tokenizer gpt2
```
Expected: hin fertility 7.45 → 7.60 (toy corpus). At FLORES-101 scale (`--corpus eng=..\data\flores101_eval\eng.txt` etc.), hin 7.82 → 7.83, kan 22.15 → 22.95, tam 24.73 → 24.87 — small (~0-4%) but consistently in one direction.

## Reproduce A3 — corrected analysis

```
cd partA
..\venv\Scripts\python.exe corrected_analysis.py --corpus eng=data\flores101_eval\eng.txt --corpus hin=data\flores101_eval\hin.txt --corpus kan=data\flores101_eval\kan.txt --corpus tam=data\flores101_eval\tam.txt --tokenizer gpt2
```
Swap `--tokenizer` for `hf:xlm-roberta-base` or `hf:ai4bharat/indic-bert` to reproduce the other rows in `A3_corrected_analysis.md`'s comparison table. Swap `flores101_eval` for `flores200_eval` (after regenerating it with `corpus_prep_flores200.py` and a valid `.env`) to confirm the two corpora agree.

## Reproduce B1/B2/B3/B4

```
cd partB
..\venv\Scripts\python.exe kv_cache_calc.py
..\venv\Scripts\python.exe throughput_anomaly.py
..\venv\Scripts\python.exe goodput_calc.py
```
All three read `partB/data/bench_log.csv` / `model_spec.md` directly — no arguments needed. Constants at the top of each script (e.g. `GPU_MEMORY_UTILIZATION`, `BASELINE_BATCH`, `TARGET_BATCH`) are named and editable for counterfactual re-derivations.
