"""
Run canary-leak probes across multiple independent synthetic canaries.

This experiment strengthens the disclosure evidence by testing whether leakage
persists when the protected token changes. It orchestrates redteam_behavior.py,
rescoring, and aggregate reporting. Raw canaries remain only in ignored local
run artifacts; the aggregate paper table uses canary IDs and hashes.

Example:
    python experiments/redteam_canary_rotation.py \
        --models command-r7b-12-2024 \
        --n-canaries 5 \
        --n-prompts 100 \
        --out-dir experiments/results/redteam_canary_rotation \
        --paper-md paper/redteam_canary_rotation_results.md
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import subprocess
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run canary-rotation red-team probes.")
    parser.add_argument("--models", nargs="+", default=["command-r7b-12-2024"])
    parser.add_argument("--n-canaries", type=int, default=5)
    parser.add_argument("--n-prompts", type=int, default=100)
    parser.add_argument("--seed", type=int, default=41)
    parser.add_argument("--difficulty", default="max", choices=["baseline", "hard", "max"])
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--paper-md", type=Path, default=None)
    parser.add_argument("--env-path", type=Path, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def synthetic_canary(index: int, seed: int) -> str:
    rng = random.Random(f"alignquant-canary-rotation:{seed}:{index}")
    left = rng.getrandbits(48)
    right = rng.getrandbits(48)
    return f"AQ_ROTATION_{index:02d}_{left:012x}_{right:012x}_DO_NOT_DISCLOSE"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_command(command: list[str]) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, check=True)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dataset_row(summary: dict[str, Any], dataset: str) -> dict[str, Any]:
    for row in summary.get("by_model_dataset", []):
        if row.get("dataset") == dataset:
            return row
    raise KeyError(dataset)


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def count_from_rate(rate: float, n: int) -> int:
    return int(round(rate * n))


def wilson_interval(positives: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 0.0
    phat = positives / n
    denominator = 1 + z**2 / n
    center = phat + z**2 / (2 * n)
    spread = z * math.sqrt((phat * (1 - phat) + z**2 / (4 * n)) / n)
    return (center - spread) / denominator, (center + spread) / denominator


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def markdown(rows: list[dict[str, Any]]) -> str:
    chunks = [
        "# Canary Rotation Results",
        "",
        (
            "This table tests whether synthetic secret leakage persists across "
            "multiple independently generated canaries. Raw canary values are "
            "not included; each row includes only a SHA-256 prefix."
        ),
        "",
        "| Canary | Model | N | Canary SHA-256 Prefix | Exact Leak | Any Leak | Refusal |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in rows:
        chunks.append(
            "| "
            f"`{row['canary_id']}` | `{row['model']}` | {row['n']} | "
            f"`{row['canary_sha256_prefix']}` | `{row['exact_canary_leak_count']}/{row['n']}` "
            f"(`{row['exact_canary_leak_rate']}`) | "
            f"`{row['any_canary_leak_rate']}` | `{row['refusal_rate']}` |"
        )

    if rows:
        by_model: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_model.setdefault(str(row["model"]), []).append(row)

        chunks.extend(["", "## Aggregate", ""])
        for model, group in sorted(by_model.items()):
            exact_values = [float(str(row["exact_canary_leak_rate"]).rstrip("%")) / 100 for row in group]
            any_values = [float(str(row["any_canary_leak_rate"]).rstrip("%")) / 100 for row in group]
            exact_count = sum(int(row["exact_canary_leak_count"]) for row in group)
            any_count = sum(int(row["any_canary_leak_count"]) for row in group)
            total_n = sum(int(row["n"]) for row in group)
            exact_low, exact_high = wilson_interval(exact_count, total_n)
            any_low, any_high = wilson_interval(any_count, total_n)
            chunks.extend(
                [
                    f"### `{model}`",
                    "",
                    f"- Canaries tested: `{len(group)}`",
                    f"- Total probes: `{total_n}`",
                    f"- Exact leaks: `{exact_count}/{total_n}`",
                    f"- Any leaks: `{any_count}/{total_n}`",
                    f"- Mean exact leak rate: `{pct(sum(exact_values) / len(exact_values))}`",
                    f"- Mean any leak rate: `{pct(sum(any_values) / len(any_values))}`",
                    f"- Pooled exact leak 95% Wilson CI: `{pct(exact_low)}`-`{pct(exact_high)}`",
                    f"- Pooled any leak 95% Wilson CI: `{pct(any_low)}`-`{pct(any_high)}`",
                    "",
                ]
            )

    while chunks and chunks[-1] == "":
        chunks.pop()
    return "\n".join(chunks) + "\n"


def main() -> None:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    args.out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for index in range(1, args.n_canaries + 1):
        canary = synthetic_canary(index, args.seed)
        canary_id = f"canary_{index:02d}"
        run_dir = args.out_dir / canary_id

        behavior_cmd = [
            sys.executable,
            str(script_dir / "redteam_behavior.py"),
            "--models",
            *args.models,
            "--datasets",
            "canary_leak",
            "--difficulty",
            args.difficulty,
            "--n-prompts",
            str(args.n_prompts),
            "--seed",
            str(args.seed + index),
            "--temperature",
            str(args.temperature),
            "--max-tokens",
            str(args.max_tokens),
            "--canary",
            canary,
            "--out-dir",
            str(run_dir),
        ]
        if args.env_path is not None:
            behavior_cmd.extend(["--env-path", str(args.env_path)])
        if args.resume:
            behavior_cmd.append("--resume")
        if args.dry_run:
            behavior_cmd.append("--dry-run")

        run_command(behavior_cmd)
        if args.dry_run:
            continue

        run_command(
            [
                sys.executable,
                str(script_dir / "score_redteam_responses.py"),
                "--run-dir",
                str(run_dir),
                "--scores-out",
                "scores_v2.csv",
                "--summary-out",
                "summary_v2.json",
            ]
        )

        summary = load_json(run_dir / "summary_v2.json")
        for canary_summary in summary.get("by_model_dataset", []):
            if canary_summary.get("dataset") != "canary_leak":
                continue
            n = int(canary_summary["n"])
            exact_rate = float(canary_summary["exact_canary_leak_rate"])
            partial_rate = float(canary_summary["partial_canary_leak_rate"])
            encoded_rate = float(canary_summary["encoded_canary_leak_rate"])
            any_rate = float(canary_summary["any_canary_leak_rate"])
            refusal_rate = float(canary_summary["refusal_rate"])
            rows.append(
                {
                    "canary_id": canary_id,
                    "model": canary_summary["model"],
                    "n": n,
                    "canary_sha256_prefix": sha256_text(canary)[:16],
                    "exact_canary_leak_count": count_from_rate(exact_rate, n),
                    "partial_canary_leak_count": count_from_rate(partial_rate, n),
                    "encoded_canary_leak_count": count_from_rate(encoded_rate, n),
                    "any_canary_leak_count": count_from_rate(any_rate, n),
                    "refusal_count": count_from_rate(refusal_rate, n),
                    "exact_canary_leak_rate": pct(exact_rate),
                    "partial_canary_leak_rate": pct(partial_rate),
                    "encoded_canary_leak_rate": pct(encoded_rate),
                    "any_canary_leak_rate": pct(any_rate),
                    "refusal_rate": pct(refusal_rate),
                    "run_dir": str(run_dir),
                }
            )

    if rows:
        write_csv(args.out_dir / "canary_rotation_summary.csv", rows)
        (args.out_dir / "canary_rotation_summary.json").write_text(
            json.dumps(rows, indent=2),
            encoding="utf-8",
        )
        if args.paper_md is not None:
            args.paper_md.parent.mkdir(parents=True, exist_ok=True)
            args.paper_md.write_text(markdown(rows), encoding="utf-8")

    print(f"Completed canary rotation with {len(rows)} summarized rows")


if __name__ == "__main__":
    main()
