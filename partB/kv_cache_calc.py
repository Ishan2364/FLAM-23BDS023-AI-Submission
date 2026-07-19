#!/usr/bin/env python3
"""
kv_cache_calc.py -- B1: KV-cache bytes/token and max concurrent
4096-token sequences, from bench/model_spec.md, cross-checked against
bench_log.csv (kv_cache_util, preempted_seqs).

All constants below are named and editable so this can be re-derived
live with different assumptions (e.g. a counterfactual GPU, a
different gpu_memory_utilization) without touching the formulas.
"""

import csv
import os

# ---- model_spec.md: FLM-4B-Instruct -----------------------------------
NUM_LAYERS = 28
KV_HEADS = 8          # GQA -- fewer than the 24 query heads
HEAD_DIM = 128
KV_CACHE_BYTES_PER_ELEM = 2   # fp16
MODEL_PARAMS = 4.2e9
WEIGHTS_BYTES_PER_PARAM = 2   # fp16

# ---- model_spec.md: hardware & serving config -------------------------
GPU_MEMORY_GIB = 24
GPU_MEMORY_UTILIZATION = 0.92
NON_KV_OVERHEAD_GIB = 1.6
MAX_MODEL_LEN = 4096

GIB = 1024 ** 3

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def kv_bytes_per_token():
    # 2 (K and V) x layers x kv_heads x head_dim x bytes/element
    return 2 * NUM_LAYERS * KV_HEADS * HEAD_DIM * KV_CACHE_BYTES_PER_ELEM


def max_concurrent_sequences(seq_len=MAX_MODEL_LEN):
    weights_bytes = MODEL_PARAMS * WEIGHTS_BYTES_PER_PARAM
    usable_bytes = GPU_MEMORY_GIB * GIB * GPU_MEMORY_UTILIZATION
    usable_for_kv = usable_bytes - weights_bytes - NON_KV_OVERHEAD_GIB * GIB
    bytes_per_seq = kv_bytes_per_token() * seq_len
    return usable_for_kv, bytes_per_seq, usable_for_kv // bytes_per_seq


def main():
    kvbpt = kv_bytes_per_token()
    print(f"KV-cache bytes/token = 2 x {NUM_LAYERS} x {KV_HEADS} x {HEAD_DIM} x {KV_CACHE_BYTES_PER_ELEM}"
          f" = {kvbpt:,} bytes ({kvbpt / 1024:.1f} KiB/token)")

    usable_for_kv, bytes_per_seq, max_seqs = max_concurrent_sequences()
    weights_gib = MODEL_PARAMS * WEIGHTS_BYTES_PER_PARAM / GIB
    print()
    print(f"Model weights: {MODEL_PARAMS:.1e} params x {WEIGHTS_BYTES_PER_PARAM} bytes = {weights_gib:.2f} GiB")
    print(f"Usable GPU memory for KV cache = {GPU_MEMORY_GIB} GiB x {GPU_MEMORY_UTILIZATION}"
          f" - {weights_gib:.2f} GiB (weights) - {NON_KV_OVERHEAD_GIB} GiB (overhead)"
          f" = {usable_for_kv / GIB:.2f} GiB")
    print(f"Bytes per {MAX_MODEL_LEN}-token sequence = {bytes_per_seq:,} bytes ({bytes_per_seq / GIB:.3f} GiB)")
    print(f"=> max concurrent {MAX_MODEL_LEN}-token sequences = {int(max_seqs)}")

    print()
    print("Cross-check against bench_log.csv (rows with prompt_len=3584, closest to max_model_len):")
    print(f"{'batch':>6}{'prompt_len':>12}{'kv_cache_util':>15}{'preempted_seqs':>16}")
    with open(os.path.join(DATA_DIR, "bench_log.csv")) as f:
        for row in csv.DictReader(f):
            if row["prompt_len"] == "3584":
                print(f"{row['batch_size']:>6}{row['prompt_len']:>12}{row['kv_cache_util']:>15}{row['preempted_seqs']:>16}")


if __name__ == "__main__":
    main()
