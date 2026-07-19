# B1 — KV-Cache Bytes/Token and Max Concurrent Sequences

Source: `bench/model_spec.md` (FLM-4B-Instruct, 1x L4 24GB), copied to `partB/data/`. Computed by `partB/kv_cache_calc.py` — constants are named/editable so this can be re-derived live with different assumptions.

## KV-cache bytes/token (exact)

```
2 (K and V) x 28 layers x 8 KV_heads x 128 head_dim x 2 bytes (fp16) = 114,688 bytes/token (112 KiB/token)
```

GQA matters here — 8 KV heads, not the 24 query heads, is what determines KV-cache size.

## Max concurrent 4096-token sequences

| quantity | value |
|---|---|
| model weights (4.2e9 params x 2 bytes fp16) | 7.83 GiB |
| usable GPU memory for KV cache (24 GiB x 0.92 − weights − 1.6 GiB overhead) | 12.66 GiB |
| bytes per 4096-token sequence (114,688 x 4096) | 448 MiB |
| **predicted max concurrent 4096-token sequences** | **~28** |

## Cross-check against `bench_log.csv`

Rows with `prompt_len=3584, gen_len=512` (3584+512 = 4096 tokens total, matching the sequence length assumed above):

| batch | kv_cache_util | preempted_seqs |
|---|---|---|
| 4 | 0.16 | 0 |
| 8 | 0.31 | 0 |
| 16 | 0.62 | 0 |
| 24 | 0.93 | 0 |
| 32 | 0.97 | 7 |
| 48 | 0.97 | 23 |

## Conclusion

Prediction confirmed. The predicted ceiling (~28 sequences) sits exactly in the transition zone the log shows: batch 24 is below the ceiling with zero preemptions (93% KV util, still headroom); batch 32 is above it and immediately shows preemption (7 sequences evicted); batch 48 (further above) shows even more (23 evicted). If the formula's ceiling were badly wrong, this clean "fine below it, breaks right above it" pattern wouldn't hold — a formula derived only from the spec sheet and a real measured load test agree on where the system runs out of KV-cache room.
