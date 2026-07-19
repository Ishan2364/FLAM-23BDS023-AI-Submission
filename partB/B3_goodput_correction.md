# B3 — The Goodput Correction

REPORT_v0 Section 2 claims (a) longer prompts give better throughput, and (b) batch 48 will deliver ~3200 tok/s. Both trace to the same misread column: `reported_tok_s`. Computed by `partB/goodput_calc.py`.

## The misread column

Hypothesis check, batch=24, prompt_len=3584 row:

```
(prompt_len + gen_len) * num_requests / wall_clock_s = (3584+512) * 24 / 61.16 = 1607.3
reported_tok_s from log                                                       = 1607.4
=> MATCHES
```

`reported_tok_s` is literally `(prompt tokens + generated tokens) / wall_clock_s` — it counts the ~3584 prompt tokens (read in one cheap parallel prefill pass) as if they were generated one-by-one at the same rate as the 512 actually-generated tokens. Long prompts get to "count" thousands of nearly-free tokens toward the throughput number, which is exactly why longer prompts *looked* faster.

## Honest goodput, two independent derivations (same row)

**Method 1 — generated tokens only, over wall clock:**
```
gen_len * num_requests / wall_clock_s = 512 * 24 / 61.16 = 200.9 tok/s
```

**Method 2 — from decode-phase per-token latency (`itl_ms_p50`):**
```
per-request rate = 1000 / 96.07 = 10.409 tok/s/request
goodput = 10.409 * 24 = 249.8 tok/s
```

Both land in the same ~200-250 tok/s range despite being derived completely differently (one from total wall-clock time, one from steady-state per-token decode latency) — cross-validating each other. Compared to the reported 1607.4 tok/s, the log's number **overstates real generation throughput by ~613%**.

## The batch-48 "~3200 tok/s" claim

Traces to the exact same bug, compounded with a naive linear-scaling assumption: `1607.4 (batch 24's reported/blended tok/s) x 2 (batch doubling: 48/24=2) = 3214.8` — matching the report's "~3200" almost exactly. The report took the already-blended, misleading batch-24 number and naively doubled it for batch 48, ignoring that (per B1/B2) the GPU runs out of KV-cache room well before batch 48 and throughput *drops*, not doubles.

## What the report should have said

Honest generation throughput at batch 24 is ~200-250 tok/s, not 1607 — the earlier number counted prompt-reading as if it were generation. Longer prompts don't give "better throughput"; they make the blended metric look better because more prefill tokens get folded into the same denominator. And batch 48 does not deliver ~3200 tok/s — per B2, real throughput at batch 48 is *lower* than at batch 24 (1298.5 vs 1607.4 reported, and honest goodput would be lower still), because the GPU is past its KV-cache capacity and thrashing on preemption, not scaling linearly.
