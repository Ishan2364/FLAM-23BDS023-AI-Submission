# AI Usage

Used Claude throughout — for setup, scripting, running/interpreting experiments, and drafting. I directed which experiments to run and what to test next; every number in this submission was actually executed and pasted back by me before being accepted, not taken on Claude's word.

## Part A — tokenizer audit

**Helped:** scaffolding the repo (`your-submission`/`partA`/`partB`/`partC` structure matching the deliverable spec), writing every isolated variant script for the candidate bug tests (`fertility_no_lower.py`, `fertility_split_ws.py`, `fertility_grapheme.py`, `fertility_no_nfc.py`, `fertility_micro_avg.py`), the FLORES-101/FLORES-200 download and corpus-prep scripts (including handling the gated HF token safely, `.gitignore` hygiene), and `corrected_analysis.py` for the A3 multi-tokenizer/multi-denominator comparison. Also caught a real risk I'd have missed — a `.gitignore` mistake that would have let the gated FLORES-200 data get committed to a public repo, and a stray scratch file that shouldn't have been tracked.

**Misled:** I went in with a pre-drafted list of 7-8 candidate "bugs" in `fertility.py` (`.lower()`, `split(" ")`, grapheme counting, macro vs micro averaging, base-language ordering, dead `random.seed`), framed fairly confidently as likely real problems. After testing each one in isolation, most turned out to have negligible or no effect — `.lower()` moved things ~3% in the *opposite* direction I expected, NFC normalization did literally nothing, several others were sub-5% noise even at FLORES scale. Only 1 of the 7-8 was a real (minor) bug, 1 was a confirmed non-issue, and the actual conceptual flaw (tokenizer/script-coverage confound) wasn't on the original list at all — it came from a separate hypothesis I pushed to test afterward, which turned out to be the one that actually mattered.

## Part B — capacity reconciliation

**Helped:** walked me through the KV-cache-bytes-per-token formula and why GQA's KV-head count (not the query-head count) is what matters, the max-concurrent-sequences arithmetic, and how to read `bench_log.csv`'s columns against those predictions (`kv_cache_util`, `preempted_seqs`) to confirm or refute them. Also explained, in plain terms, why "throughput per se" and "goodput" are different things, which led directly to spotting that `reported_tok_s` blends prefill and decode tokens — and then connected that same bug to the report's batch-48 extrapolation (`1607.4 x 2 ≈ "~3200"`), which I hadn't noticed myself until it was pointed out. Built the three calculation scripts (`kv_cache_calc.py`, `throughput_anomaly.py`, `goodput_calc.py`) so every number could be re-derived live rather than hardcoded.

**Misled:** nothing significant went wrong here — the formulas are standard (KV-cache sizing, goodput vs. throughput) and every prediction lined up cleanly against the log on the first pass. The one moment of hesitation was a brief, self-corrected aside about whether MuRIL covers Kannada/Tamil (it does) — caught and fixed within the same message, not something that propagated into a wrong result.

## Part C — decision memo

**Helped:** laid out the tradeoffs between the three options (SFT, small rewriter model, prompt-only) specifically against the given constraints — one GPU for 2 weeks, a reviewer who only covers 2 of 6 languages, a 3-week deadline — and recommended the rewriter option with reasoning I could evaluate rather than blindly accept (mainly: SFT risks unverifiable regressions in the 4 languages the reviewer can't check). Helped structure the back-of-envelope arithmetic (data volume, GPU-hours, reviewer throughput) into concrete numbers.

**Misled / caveat:** unlike Parts A and B, nothing here is empirically tested — it's a judgment call under constraints, and Claude's confidence in recommending option (b) is not backed by an experiment the way the tokenizer/capacity findings are. I'm treating this section as reasoned opinion, not evidence, and said so explicitly in the memo's kill criterion.
