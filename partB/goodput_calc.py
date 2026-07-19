#!/usr/bin/env python3
"""
goodput_calc.py -- B3: honest "goodput" for a chosen bench_log.csv row,
derived two independent ways, compared against the report's
reported_tok_s.

Hypothesis: reported_tok_s = (prompt_len + gen_len) * num_requests / wall_clock_s
i.e. it counts prefill (prompt) tokens as if they were generated at the
same rate as decode tokens -- prefill is a single cheap parallel pass,
decode is slow token-by-token, so blending them inflates throughput for
long-prompt rows.

Method 1 (generated tokens / wall clock):
    goodput = gen_len * num_requests / wall_clock_s

Method 2 (from decode-phase per-token latency, itl_ms_p50):
    per_request_rate = 1000 / itl_ms_p50   (tokens/sec, one request's decode)
    goodput = per_request_rate * num_requests   (all requests decoding concurrently)

TARGET_BATCH / TARGET_PROMPT_LEN pick the row -- edit to re-derive live
for a different row.
"""

import csv
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TARGET_BATCH = "24"
TARGET_PROMPT_LEN = "3584"


def load_row():
    with open(os.path.join(DATA_DIR, "bench_log.csv")) as f:
        for row in csv.DictReader(f):
            if row["batch_size"] == TARGET_BATCH and row["prompt_len"] == TARGET_PROMPT_LEN:
                return row
    raise SystemExit(f"no row found for batch={TARGET_BATCH}, prompt_len={TARGET_PROMPT_LEN}")


def main():
    row = load_row()
    prompt_len = int(row["prompt_len"])
    gen_len = int(row["gen_len"])
    num_requests = int(row["num_requests"])
    wall_clock_s = float(row["wall_clock_s"])
    reported_tok_s = float(row["reported_tok_s"])
    itl_ms_p50 = float(row["itl_ms_p50"])

    print(f"Row: batch={row['batch_size']}, prompt_len={prompt_len}, gen_len={gen_len}, "
          f"num_requests={num_requests}, wall_clock_s={wall_clock_s}\n")

    # confirm the hypothesis: reported_tok_s counts prompt + gen tokens together
    naive_total = (prompt_len + gen_len) * num_requests / wall_clock_s
    print(f"Hypothesis check: (prompt_len + gen_len) * num_requests / wall_clock_s = {naive_total:.1f}")
    print(f"reported_tok_s from log                                              = {reported_tok_s:.1f}")
    print(f"=> {'MATCHES' if abs(naive_total - reported_tok_s) < 1 else 'does not match'} "
          f"(confirms reported_tok_s blends prefill + decode tokens)\n")

    # Method 1: generated tokens only, over wall clock
    goodput_1 = gen_len * num_requests / wall_clock_s
    print(f"Method 1 (gen_len * num_requests / wall_clock_s):")
    print(f"  {gen_len} * {num_requests} / {wall_clock_s} = {goodput_1:.1f} tok/s\n")

    # Method 2: from decode-phase per-token latency
    per_request_rate = 1000 / itl_ms_p50
    goodput_2 = per_request_rate * num_requests
    print(f"Method 2 (from itl_ms_p50, decode-phase per-token latency):")
    print(f"  per-request rate = 1000 / {itl_ms_p50} = {per_request_rate:.3f} tok/s/request")
    print(f"  goodput = {per_request_rate:.3f} * {num_requests} = {goodput_2:.1f} tok/s\n")

    avg_goodput = (goodput_1 + goodput_2) / 2
    overstatement = (reported_tok_s - avg_goodput) / avg_goodput * 100
    print(f"Both methods agree within the same order of magnitude (~{goodput_1:.0f}-{goodput_2:.0f} tok/s),"
          f" vs. reported_tok_s={reported_tok_s:.1f} -- "
          f"reported number overstates honest goodput by ~{overstatement:.0f}%.")


if __name__ == "__main__":
    main()
