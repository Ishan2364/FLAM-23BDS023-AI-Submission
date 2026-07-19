# Part B — Capacity Reconciliation: Calculations & Written Answers

Full arithmetic, cross-checks, and raw script output are in `results.md` and `NOTEBOOK.md`. This is the condensed written-answer version.

## B1 — KV-cache bytes/token and max concurrent sequences

**KV-cache bytes/token** = 2 (K and V) × 28 layers × 8 KV_heads × 128 head_dim × 2 bytes (fp16) = **114,688 bytes/token** (112 KiB/token).

**Max concurrent 4096-token sequences:** model weights = 4.2e9 × 2 bytes = 7.83 GiB. Usable GPU memory for KV cache = 24 GiB × 0.92 − 7.83 GiB − 1.6 GiB overhead = 12.66 GiB. Bytes per 4096-token sequence = 114,688 × 4096 = 448 MiB. **Max sequences ≈ 12.66 GiB ÷ 448 MiB ≈ 28.**

Checked against `bench_log.csv`: zero preemptions through batch 24 (93% KV util), preemption begins at batch 32 (97% KV util, 7 preempted) — the predicted ceiling of ~28 sits exactly in that transition zone. Prediction confirmed.

## B2 — the long-context throughput anomaly

`reported_tok_s` rises through batch 24 (1607.4 tok/s) then **falls** at batch 32 (1384.0) and batch 48 (1298.5) — a 19.2% cumulative drop, despite more requests being added. Naive linear projection from batch 24's per-request rate predicts 2143.2 tok/s at batch 32 and 3214.8 at batch 48; actual results fall short by 35.4% and 59.6% respectively.

**Mechanism:** `kv_cache_util` hits 0.97 (full) exactly at batch 32, and `preempted_seqs` jumps from 0 to 7 to 23 across batch 24→32→48. Once KV cache is full, the scheduler must preempt (evict) sequences mid-generation to free room, then resume them later — that eviction/resume cycle burns time without producing output tokens, so throughput drops as request count rises past the GPU's real capacity.

**Proposed fix:** cap admission at batch ≤24 for ~4096-token requests (KV-cache-aware admission control, not just queue depth). **Predicted effect:** sustains 1607.4 tok/s instead of degrading to 1298.5 tok/s — a ~19.2% throughput improvement, computed directly from already-measured before/after values in the log.

## B3 — the goodput correction

Both of REPORT_v0's Section 2 conclusions ("longer prompts give better throughput," "batch 48 will deliver ~3200 tok/s") come from `reported_tok_s` blending prefill (prompt) tokens with decode (generated) tokens. Confirmed: `(prompt_len + gen_len) × num_requests / wall_clock_s = 1607.3` matches the logged `reported_tok_s = 1607.4` for the batch-24/prompt-3584 row.

**Honest goodput for that row, two independent methods:**
- Generated tokens only ÷ wall clock: `512 × 24 / 61.16 = 200.9 tok/s`
- From decode-phase latency: `(1000 / 96.07) × 24 = 249.8 tok/s`

Both land in the same ~200-250 tok/s range — cross-validating each other — vs. the reported 1607.4 tok/s, an overstatement of ~613%.

The batch-48 "~3200 tok/s" claim is `1607.4 × 2` (naive doubling for double the batch size) — it inherits the same blended-metric error and additionally ignores that the GPU runs out of KV-cache room well before batch 48 (B1/B2), where real throughput is *lower* than batch 24's, not double.

**What the report should have said:** honest generation throughput at batch 24 is ~200-250 tok/s, not 1607. Longer prompts don't improve throughput — they just add more "free" prefill tokens to an already-misleading blended metric. Batch 48 does not deliver ~3200 tok/s; measured throughput there is lower than at batch 24, because the system is past its KV-cache capacity and thrashing on preemption.

## B4 — confirming metric

`preempted_seqs` in this log already confirms the B2 mechanism offline. To confirm it's happening live in production, pull the serving stack's own running counters: `num_preemptions_total` (Prometheus-style counter, incremented per scheduler eviction) and `gpu_cache_usage_perc` (live analogue of `kv_cache_util`). Expect `num_preemptions_total` to stay flat at 0 while concurrent ~4096-token requests stay ≤~24-28, then climb once concurrency exceeds that ceiling — mirroring the 0→7→23 pattern already observed here — with `gpu_cache_usage_perc` pinned near 1.0 whenever it climbs.
