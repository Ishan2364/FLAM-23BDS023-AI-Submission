# A3 — Corrected Analysis

`partA/corrected_analysis.py`: bug-fixed (`split()` not `split(" ")`, per A2), keeps NFC normalization (confirmed harmless), reports **4 denominators** per language — tok/word, tok/byte (UTF-8), tok/grapheme, and tok/sentence — across **3 tokenizers** (gpt2, xlm-roberta-base, ai4bharat/indic-bert), on FLORES-200 (primary corpus; FLORES-101 run confirmed numerically identical, see A1).

## Results

### gpt2

| lang | tok/word | tok/byte | tok/grapheme | tok/sentence |
|---|---|---|---|---|
| eng | 1.283 | 0.2150 | 0.2152 | 26.78 |
| hin | 7.826 | 0.5943 | 1.5977 | 192.42 |
| kan | 22.946 | 0.9785 | 2.9112 | 350.85 |
| tam | 24.867 | 0.9957 | 3.1748 | 398.38 |

### xlm-roberta-base

| lang | tok/word | tok/byte | tok/grapheme | tok/sentence |
|---|---|---|---|---|
| eng | 1.419 | 0.2372 | 0.2374 | 29.58 |
| hin | 1.500 | 0.1144 | 0.3069 | 36.75 |
| kan | 2.601 | 0.1116 | 0.3314 | 39.74 |
| tam | 2.453 | 0.0987 | 0.3140 | 39.23 |

### ai4bharat/indic-bert

| lang | tok/word | tok/byte | tok/grapheme | tok/sentence |
|---|---|---|---|---|
| eng | 1.383 | 0.2316 | 0.2318 | 28.86 |
| hin | 1.702 | 0.1296 | 0.3479 | 41.82 |
| kan | 3.214 | 0.1373 | 0.4082 | 49.11 |
| tam | 3.359 | 0.1348 | 0.4292 | 53.79 |

### Ratio to eng, by denominator and tokenizer

| tokenizer | denom | hin | kan | tam |
|---|---|---|---|---|
| gpt2 | tok/word | 6.10x | 17.89x | 19.38x |
| gpt2 | tok/byte | 2.76x | 4.55x | 4.63x |
| gpt2 | tok/sentence | 7.18x | 13.10x | 14.88x |
| xlm-roberta-base | tok/word | 1.06x | 1.83x | 1.73x |
| xlm-roberta-base | tok/byte | 0.48x | 0.47x | 0.42x |
| xlm-roberta-base | tok/sentence | 1.24x | 1.34x | 1.33x |
| indic-bert | tok/word | 1.23x | 2.32x | 2.43x |
| indic-bert | tok/byte | 0.56x | 0.59x | 0.58x |
| indic-bert | tok/sentence | 1.45x | 1.70x | 1.86x |

## Key observation — tok/byte is its own confound

Under xlm-roberta-base and indic-bert, Hindi/Kannada/Tamil come out *cheaper per byte* than English (ratios < 1.0x). Not because Indic text is cheaper to serve — Devanagari/Kannada/Tamil are ~3 bytes/codepoint in UTF-8 vs. English's 1 byte/char, so tok/byte is inflated for English and deflated for Indic scripts independent of real cost. tok/byte fails the same test tok/word failed: it doesn't hold a fair unit constant across scripts.

## Which single number should drive the routing decision

**tok/sentence.** FLORES sentences are translations of each other — same meaning, same content — so tokens-to-encode-one-sentence directly answers "how much context/compute does this language cost for the same request," which is exactly what a routing/capacity decision needs. It isn't distorted by whitespace-word morphology differences (A2's bug) or UTF-8 byte-density differences (above). Under gpt2 it still shows the same misleading 7-15x gap as tok/word did; under an Indic-aware tokenizer it shows a real, modest residual: Hindi ~1.2-1.5x, Kannada/Tamil ~1.3-1.9x — consistent with tok/word's residual finding, cross-validating it.

**Conclusion:** the number to drive the routing-and-cost decision is tokens per request (tok/sentence on parallel data), measured with an Indic-aware tokenizer — not tok/word (conflates morphology with tokenizer coverage) and not tok/byte (conflates UTF-8 script density with cost). xlm-roberta-base showed the smallest, most consistent residual gap (1.24x-1.34x) of the tokenizers tested — see A4 for the routing recommendation.

## Cross-check

Identical run against FLORES-101 (public, ungated copy kept in the repo): every value matched the FLORES-200 table above to 2 decimal places — confirms the result isn't an artifact of one particular data pull or HF access path.
