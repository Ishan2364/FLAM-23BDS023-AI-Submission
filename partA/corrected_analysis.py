#!/usr/bin/env python3
"""
corrected_analysis.py -- A3 corrected tokenizer comparison.

Same job as fertility.py, but:
  - fixes the confirmed split(" ") bug (uses split() instead)
  - reports three denominators per language: tokens/word,
    tokens/byte (utf-8), tokens/grapheme-cluster
  - keeps NFC normalization (confirmed harmless on this corpus)

Usage:
    python corrected_analysis.py --corpus eng=data/flores101_eval/eng.txt \
                                  --corpus hin=data/flores101_eval/hin.txt \
                                  --corpus kan=data/flores101_eval/kan.txt \
                                  --corpus tam=data/flores101_eval/tam.txt \
                                  --tokenizer gpt2
"""

import argparse
import unicodedata


def load_tokenizer(spec: str):
    if spec.startswith("hf:"):
        from transformers import AutoTokenizer

        tok = AutoTokenizer.from_pretrained(spec[3:])
        return lambda s: tok.encode(s, add_special_tokens=False)
    else:
        import tiktoken

        enc = tiktoken.get_encoding(spec)
        return enc.encode


def read_lines(path: str):
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            line = unicodedata.normalize("NFC", line)
            lines.append(line)
    return lines


def grapheme_len(s):
    """Approximate grapheme-cluster count: don't count combining marks separately."""
    return sum(1 for ch in s if not unicodedata.combining(ch))


def analyze(lines, encode):
    """Return macro-averaged (tok/word, tok/byte, tok/grapheme) and mean tok/sentence."""
    per_word, per_byte, per_grapheme, per_sentence = [], [], [], []
    for line in lines:
        line = line.lower()
        tokens = encode(line)
        n_tokens = len(tokens)
        words = line.split()  # bug fix: was split(" ")
        n_bytes = len(line.encode("utf-8"))
        n_graphemes = grapheme_len(line)
        per_word.append(n_tokens / len(words))
        per_byte.append(n_tokens / n_bytes)
        per_grapheme.append(n_tokens / n_graphemes)
        per_sentence.append(n_tokens)
    n = len(per_word)
    return (
        sum(per_word) / n,
        sum(per_byte) / n,
        sum(per_grapheme) / n,
        sum(per_sentence) / n,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", action="append", required=True, metavar="LANG=PATH")
    ap.add_argument("--tokenizer", default="gpt2")
    args = ap.parse_args()

    encode = load_tokenizer(args.tokenizer)

    print(f"tokenizer: {args.tokenizer}")
    print(f"{'lang':<8}{'tok/word':>12}{'tok/byte':>12}{'tok/grapheme':>16}{'tok/sentence':>16}")
    print("-" * 64)
    for spec in args.corpus:
        lang, path = spec.split("=", 1)
        lines = read_lines(path)
        tw, tb, tg, ts = analyze(lines, encode)
        print(f"{lang:<8}{tw:>12.3f}{tb:>12.4f}{tg:>16.4f}{ts:>16.2f}")


if __name__ == "__main__":
    main()
