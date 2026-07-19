# A1 — Eval Corpus

## Languages (4, as required)

English (eng), Hindi (hin), Kannada (kan), Tamil (tam). Hindi is Indo-Aryan; Kannada and Tamil are both Dravidian, satisfying the "two Dravidian languages" requirement and giving a script-family contrast (Latin vs. Devanagari vs. Kannada script vs. Tamil script).

## Corpus and why

**FLORES-200** (`facebook/flores` on HuggingFace) is the primary/declared corpus — the current, actively-maintained release, and the one the assignment brief itself points to. Pulling it required a personal HF token since the repo is gated (`partA/corpus_prep_flores200.py`, token read from `.env`, never committed).

To cross-check and to keep a reproducible, redistributable copy in the repo, we also pulled the same 4 languages from **FLORES-101**, Meta's earlier public/ungated tarball (`https://dl.fbaipublicfiles.com/flores101/dataset/flores101_dataset.tar.gz`, CC-BY-SA).

The two are **numerically identical** for eng/hin/kan/tam — confirmed by running the identical analysis script against both and matching every value to 2 decimal places (see A3). So while FLORES-200 is the corpus of record, FLORES-101 serves as an independent, reproducible confirmation — `flores200_eval/` stays local-only (gitignored, gated-access data shouldn't be redistributed), `flores101_eval/` is committed for grader reproducibility.

## Size

997 parallel sentences per language (3,988 total across 4 languages), sentence-aligned by line number — line N in `eng.txt` is a direct translation of line N in `hin.txt`/`kan.txt`/`tam.txt`.

## Domain

Professionally translated, drawn from a mix of Wikinews, Wikijunior, and Wikivoyage articles — encyclopedic/journalistic prose, not conversational or transactional text (no chat messages, no code-mixing, no slang).

## Preprocessing

None beyond what `fertility.py`/`corrected_analysis.py` themselves do (NFC normalization, lowercasing). Files saved as plain UTF-8 `.txt`, one sentence per line, no filtering or resampling on our end.

## What this corpus cannot tell us

997 sentences is a reasonable smoke-test size but still small relative to real production traffic, and formal, professionally-translated encyclopedic prose is not representative of actual user queries — no code-switching, no informal register, no domain-specific jargon (support tickets, casual chat, voice-to-text artifacts) that a production system would actually see. Because FLORES-101 and FLORES-200 collapsed to the same sentences for these 4 languages, we effectively only sampled one translation of each source sentence, not independent corpora — this doesn't triangulate across corpus sources, only across tokenizers and metrics. Any fertility numbers in A2/A3 should be read as "how this specific benchmark text tokenizes," not as a guaranteed predictor of live traffic cost.
