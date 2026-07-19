# B2 — The Long-Context Throughput Anomaly

Naive expectation: throughput (`reported_tok_s`) should keep rising as batch size rises. Computed by `partB/throughput_anomaly.py`, using batch 24 (the last batch with zero preemptions) as a "no-contention" baseline.

## Data

Baseline: batch=24, reported_tok_s=1607.4, per-request rate=66.98 tok/s/request.

| batch | tok/s | %chg vs prev | naive-projected | shortfall % | preempted |
|---|---|---|---|---|---|
| 4 | 565.4 | — | 267.9 | -111.0% | 0 |
| 8 | 902.6 | +59.6% | 535.8 | -68.5% | 0 |
| 16 | 1311.4 | +45.3% | 1071.6 | -22.4% | 0 |
| 24 | 1607.4 | +22.6% | 1607.4 | 0.0% | 0 |
| 32 | 1384.0 | -13.9% | 2143.2 | 35.4% | 7 |
| 48 | 1298.5 | -6.2% | 3214.8 | 59.6% | 23 |

## The anomaly

Throughput rises through batch 24, then **falls** at batch 32 and 48 despite more requests being added — a 19.2% cumulative drop from batch 24's peak, and a 35.4%-59.6% shortfall vs. naive linear projection from the batch-24 per-request rate.

## Mechanism

`kv_cache_util` hits 0.97 (essentially full) exactly at batch 32, and `preempted_seqs` goes from 0 (batch 24) to 7 (batch 32) to 23 (batch 48) — see B1. Once the KV cache is full, the scheduler can't just hold more sequences: it has to preempt (evict) some mid-generation to free room, then resume them later. That eviction/resume cycle burns time without producing new output tokens, so wall-clock time grows faster than useful work does — which is exactly why throughput falls even as `num_requests` rises. Same root cause as B1 (GPU out of KV-cache room), now shown to directly cause a measurable throughput regression, not just a capacity ceiling.

## Proposed fix

Cap admission at batch size ≤24 for ~4096-token-long requests (admission control keyed off predicted KV-cache usage, not just queue depth) — reject/queue excess requests instead of overcommitting and thrashing.

**Predicted quantitative effect:** sustaining batch 24's 1607.4 tok/s instead of degrading to batch 48's 1298.5 tok/s — a **~19.2% throughput improvement**, computed directly from already-measured before/after values in this log.
