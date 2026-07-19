#!/usr/bin/env python3
"""
corpus_prep_flores200.py -- pull eng/hin/kan/tam dev sets from the
gated `facebook/flores` (FLORES-200) dataset on HuggingFace and write
them out as plain parallel .txt files (one sentence per line, aligned
by row order) for use with fertility.py.

Requires a HuggingFace token with access to facebook/flores, read from
the HF_KEY variable in a .env file in the current directory (see
python-dotenv). Never commit .env -- it's already in .gitignore.

Usage:
    python partA/corpus_prep_flores200.py
"""

import os
import sys

from dotenv import load_dotenv
from huggingface_hub import hf_hub_download

LANGS = {
    "eng": "eng_Latn",
    "hin": "hin_Deva",
    "kan": "kan_Knda",
    "tam": "tam_Taml",
}
OUT_DIR = os.path.join(os.path.dirname(__file__), "data", "flores200_eval")
TEXT_COL_CANDIDATES = ["text", "sentence", "sentence_text"]


def main():
    load_dotenv()
    token = os.environ.get("HF_KEY")
    if not token:
        sys.exit("HF_KEY not found -- check your .env file")

    import pandas as pd

    os.makedirs(OUT_DIR, exist_ok=True)

    frames = {}
    for lang, code in LANGS.items():
        path = hf_hub_download(
            repo_id="facebook/flores",
            repo_type="dataset",
            filename=f"data/language/{code}/dev-00000-of-00001.parquet",
            token=token,
        )
        df = pd.read_parquet(path)
        print(f"{lang} ({code}): columns = {list(df.columns)}, rows = {len(df)}")
        frames[lang] = df

    text_col = None
    for cand in TEXT_COL_CANDIDATES:
        if cand in frames["eng"].columns:
            text_col = cand
            break
    if text_col is None:
        sys.exit(
            f"Couldn't find a text column among {TEXT_COL_CANDIDATES} -- "
            f"check the printed columns above and edit TEXT_COL_CANDIDATES."
        )

    # align by 'id' if present, else assume row order already matches
    for lang, df in frames.items():
        if "id" in df.columns:
            df.sort_values("id", inplace=True)
        out_path = os.path.join(OUT_DIR, f"{lang}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            for line in df[text_col]:
                f.write(line.strip().replace("\n", " ") + "\n")
        print(f"wrote {out_path} ({len(df)} lines)")


if __name__ == "__main__":
    main()
