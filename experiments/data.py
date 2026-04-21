"""
alignquant.data
Prompt loaders for refusal / truthfulness / sycophancy axes.

Primary sources (downloaded lazily on first call):
  - AdvBench (Zou et al. 2023): harmful instruction behaviors.
  - Alpaca-cleaned: harmless instruction-following prompts.

Licensing note: AdvBench is released under MIT. Alpaca-cleaned is CC-BY-NC 4.0.
Both are used here for evaluation only; not redistributed in this repo.
"""

from __future__ import annotations

import csv
import io
import os
import random
import urllib.request
from pathlib import Path
from typing import List, Tuple

CACHE = Path(os.environ.get("ALIGNQUANT_CACHE", "~/.cache/alignquant")).expanduser()
CACHE.mkdir(parents=True, exist_ok=True)

ADVBENCH_URL = (
    "https://raw.githubusercontent.com/llm-attacks/llm-attacks/main/"
    "data/advbench/harmful_behaviors.csv"
)
ALPACA_URL = (
    "https://raw.githubusercontent.com/gururise/AlpacaDataCleaned/main/"
    "alpaca_data_cleaned.json"
)


def _download(url: str, dst: Path) -> Path:
    if dst.exists():
        return dst
    print(f"[data] downloading {url} -> {dst}")
    with urllib.request.urlopen(url) as r:
        dst.write_bytes(r.read())
    return dst


def load_advbench(n: int = 128, seed: int = 0) -> List[str]:
    """Return `n` harmful instruction prompts from AdvBench."""
    path = _download(ADVBENCH_URL, CACHE / "advbench_harmful_behaviors.csv")
    rows = list(csv.DictReader(io.StringIO(path.read_text())))
    prompts = [r["goal"].strip() for r in rows if r.get("goal")]
    random.Random(seed).shuffle(prompts)
    return prompts[:n]


def load_alpaca_harmless(n: int = 128, seed: int = 0) -> List[str]:
    """Return `n` harmless instruction prompts from Alpaca-cleaned."""
    import json as _json

    path = _download(ALPACA_URL, CACHE / "alpaca_cleaned.json")
    items = _json.loads(path.read_text())
    prompts = []
    for it in items:
        instr = (it.get("instruction") or "").strip()
        inp = (it.get("input") or "").strip()
        if not instr:
            continue
        p = f"{instr}\n{inp}".strip() if inp else instr
        if 10 < len(p) < 400:
            prompts.append(p)
    random.Random(seed).shuffle(prompts)
    return prompts[:n]


def refusal_pairs(n: int = 128) -> Tuple[List[str], List[str]]:
    return load_advbench(n), load_alpaca_harmless(n)


if __name__ == "__main__":
    h, s = refusal_pairs(8)
    print("HARMFUL sample:", h[0])
    print("HARMLESS sample:", s[0])
