# Lab Notebook — Tokenizer & Serving Audit

Chronological log: hypothesis → experiment → result → revision. Dead ends included on purpose.

## 2026-07-19 — Setup

- Created `your-submission/` scaffold, kept `starter_kit/` untouched as reference.
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
