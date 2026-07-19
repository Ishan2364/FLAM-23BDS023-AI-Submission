# A0 — Baseline Reproduction

Before auditing `fertility.py`, we reproduced the intern's exact reported numbers on an unmodified copy of the script and the original sample corpora — this establishes a known-good reference point for every audit finding that follows.

## Setup

- `partA/reproducing_result/` holds an untouched copy of `fertility.py` plus the original `corpus_sample/eng_sample.txt` and `hin_sample.txt`.
- Environment: local venv, `tiktoken>=0.7.0` only (no fixes, no modifications).

## Command

```
python fertility.py --corpus eng=corpus_sample/eng_sample.txt --corpus hin=corpus_sample/hin_sample.txt --tokenizer gpt2
```

## Output

```
tokenizer: gpt2
lang      fertility (tok/word)    tok/char
------------------------------------------
eng                       1.27       0.226
hin                       7.45       1.579

hin is 5.89x the fertility of eng (worse tokenization)
```

## Conclusion

Matches `REPORT_v0.md` exactly (1.27 / 0.226 eng, 7.45 / 1.579 hin, 5.89x ratio). Baseline confirmed — every subsequent audit finding (A2) and corrected analysis (A3) is measured as a delta against this reference, not against a re-derived or assumed number.
