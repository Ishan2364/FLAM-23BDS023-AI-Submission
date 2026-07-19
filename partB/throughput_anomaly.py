#!/usr/bin/env python3
"""
throughput_anomaly.py -- B2: quantify the long-prompt (3584) throughput
anomaly in bench_log.csv.

Two numbers:
  1. % change in reported_tok_s batch-over-batch (does throughput ever
     go down as batch size goes up?)
  2. shortfall vs. a naive linear projection: take the last
     no-preemption batch as the "per-request rate" baseline, project
     what throughput *should* be at larger batch sizes if that rate
     held with no contention, and compare to what was actually measured.

BASELINE_BATCH is the reference row -- edit it to re-derive live with
a different baseline (e.g. the smallest batch instead of the largest
un-preempted one).
"""

import csv
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PROMPT_LEN = "3584"
BASELINE_BATCH = "24"  # last batch size with preempted_seqs == 0


def load_rows():
    with open(os.path.join(DATA_DIR, "bench_log.csv")) as f:
        return [row for row in csv.DictReader(f) if row["prompt_len"] == PROMPT_LEN]


def main():
    rows = load_rows()
    rows.sort(key=lambda r: int(r["batch_size"]))

    baseline = next(r for r in rows if r["batch_size"] == BASELINE_BATCH)
    baseline_tok_s = float(baseline["reported_tok_s"])
    baseline_batch = int(baseline["batch_size"])
    per_request_rate = baseline_tok_s / baseline_batch

    print(f"Baseline: batch={baseline_batch}, reported_tok_s={baseline_tok_s}, "
          f"per-request rate={per_request_rate:.2f} tok/s/request\n")

    print(f"{'batch':>6}{'tok/s':>10}{'%chg vs prev':>14}{'naive-projected':>17}{'shortfall %':>13}{'preempted':>11}")
    prev_tok_s = None
    for row in rows:
        batch = int(row["batch_size"])
        tok_s = float(row["reported_tok_s"])
        pct_chg = "" if prev_tok_s is None else f"{(tok_s - prev_tok_s) / prev_tok_s * 100:+.1f}%"
        naive = per_request_rate * batch
        shortfall = (naive - tok_s) / naive * 100
        print(f"{batch:>6}{tok_s:>10.1f}{pct_chg:>14}{naive:>17.1f}{shortfall:>12.1f}%{row['preempted_seqs']:>11}")
        prev_tok_s = tok_s


if __name__ == "__main__":
    main()
