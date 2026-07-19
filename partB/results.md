# Results — Capacity Reconciliation

Source: `bench/model_spec.md` (FLM-4B-Instruct, 1x L4 24GB) and `bench_log.csv`, copied to `partB/data/`.

## B1 — KV-cache bytes/token and max concurrent sequences

**KV-cache bytes/token:**

```
2 (K and V) x 28 layers x 8 KV_heads x 128 head_dim x 2 bytes (fp16) = 114,688 bytes/token (112 KiB/token)
```

**Max concurrent 4096-token sequences:**

| quantity | value |
|---|---|
| model weights (4.2e9 params x 2 bytes fp16) | 7.83 GiB |
| usable GPU memory for KV cache (24 GiB x 0.92 − weights − 1.6 GiB overhead) | 12.66 GiB |
| bytes per 4096-token sequence (114,688 x 4096) | 448 MiB |
| **predicted max concurrent 4096-token sequences** | **~28** |

**Cross-check against `bench_log.csv`** (rows with `prompt_len=3584, gen_len=512`, i.e. 4096 tokens total):

| batch | kv_cache_util | preempted_seqs |
|---|---|---|
| 4 | 0.16 | 0 |
| 8 | 0.31 | 0 |
| 16 | 0.62 | 0 |
| 24 | 0.93 | 0 |
| 32 | 0.97 | 7 |
| 48 | 0.97 | 23 |

**Verdict:** predicted ceiling (~28) sits exactly between batch 24 (no preemption, 93% KV util) and batch 32 (preemption begins, 97% KV util) — the formula-derived prediction and the measured load test agree on where the system runs out of KV-cache room.

## B2 — the long-context throughput anomaly

Baseline (last no-preemption batch): batch=24, reported_tok_s=1607.4, per-request rate=66.98 tok/s/request.

| batch | tok/s | %chg vs prev | naive-projected | shortfall % | preempted |
|---|---|---|---|---|---|
| 4 | 565.4 | — | 267.9 | -111.0% | 0 |
| 8 | 902.6 | +59.6% | 535.8 | -68.5% | 0 |
| 16 | 1311.4 | +45.3% | 1071.6 | -22.4% | 0 |
| 24 | 1607.4 | +22.6% | 1607.4 | 0.0% | 0 |
| 32 | 1384.0 | -13.9% | 2143.2 | 35.4% | 7 |
| 48 | 1298.5 | -6.2% | 3214.8 | 59.6% | 23 |

**Anomaly:** throughput rises through batch 24, then *falls* at batch 32 and 48 despite more requests being added — a 19.2% cumulative drop from batch 24's peak, and a 35.4%-59.6% shortfall vs. naive linear projection.

**Mechanism:** `kv_cache_util` hits 0.97 (full) at batch 32, forcing the scheduler to preempt (evict mid-generation) 7 sequences at batch 32 and 23 at batch 48 (see B1 table) — eviction/resume cycles burn time without producing output tokens, so throughput drops even as request count rises.

**Fix:** cap admission at batch ≤24 for ~4096-token requests (KV-cache-aware admission control) instead of overcommitting. **Predicted effect:** sustaining 1607.4 tok/s instead of degrading to 1298.5 tok/s — a **~19.2% throughput improvement**, using already-measured before/after numbers from this log.

## B3 — the goodput correction

Hypothesis check (batch=24, prompt_len=3584 row):

```
(prompt_len + gen_len) * num_requests / wall_clock_s = (3584+512) * 24 / 61.16 = 1607.3
reported_tok_s from log                                                       = 1607.4   -> MATCHES
```

`reported_tok_s` blends prefill (prompt) tokens with decode (generated) tokens — confirmed.

**Honest goodput, same row, two independent methods:**

| method | calculation | result |
|---|---|---|
| 1 — generated tokens / wall clock | 512 * 24 / 61.16 | 200.9 tok/s |
| 2 — from decode-phase latency (`itl_ms_p50`) | (1000/96.07) * 24 | 249.8 tok/s |

Both land in the same ~200-250 tok/s range despite independent derivations. Reported 1607.4 tok/s overstates real generation throughput by **~613%**.

**Batch-48 "~3200 tok/s" claim:** `1607.4 x 2 (batch doubling) = 3214.8` — matches the report's claim almost exactly. The report took the already-blended batch-24 number and naively doubled it for batch 48, ignoring that the GPU runs out of KV-cache room before batch 48 (B1/B2) and throughput actually *drops*.

**What the report should have said:** honest generation throughput at batch 24 is ~200-250 tok/s, not 1607. Longer prompts don't give better throughput — more free prefill tokens just inflate the blended metric. Batch 48 does not deliver ~3200 tok/s — real throughput there is lower than batch 24's, not double, because of KV-cache exhaustion and preemption.

## B4 — confirming metric

`preempted_seqs` in `bench_log.csv` already confirms the mechanism offline (0 through batch 24, 7 at batch 32, 23 at batch 48 — exactly at the batch sizes past B1's ~28-sequence predicted ceiling). To confirm this is happening in a live production deployment (not just this one test run), pull the serving stack's own running counters: `num_preemptions_total` (a vLLM-style Prometheus counter incremented per scheduler eviction) and `gpu_cache_usage_perc` (live analogue of `kv_cache_util`). Expected: `num_preemptions_total` flat at 0 while concurrent ~4096-token requests stay ≤~24-28, then climbing once concurrency exceeds that — mirroring the 0→7→23 pattern already seen here — with `gpu_cache_usage_perc` pinned near 1.0 whenever it climbs.
