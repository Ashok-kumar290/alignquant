"""
Generate Wilson confidence intervals for red-team score CSVs.

This is an offline analysis helper. It reads one or more scored result files and
writes Markdown/JSON tables with count-based 95% intervals. It makes no model
calls and does not require provider credentials.

Example:
    python experiments/redteam_confidence_intervals.py \
        --score-files \
          experiments/results/redteam_behavior_max_100/scores.csv \
          experiments/results/redteam_deep_max_100/scores_v2.csv \
        --out-md paper/redteam_statistical_evidence.md \
        --out-json experiments/results/redteam_confidence_intervals.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_METRICS = [
    "refused",
    "unsafe_compliance",
    "over_refusal",
    "canary_leaked",
    "exact_canary_leak",
    "partial_canary_leak",
    "encoded_canary_leak",
    "any_canary_leak",
    "hierarchy_violation",
]


@dataclass(frozen=True)
class IntervalRow:
    model: str
    dataset: str
    metric: str
    positives: int
    n: int
    rate: float
    ci_low: float
    ci_high: float
    source_file: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute red-team Wilson intervals.")
    parser.add_argument("--score-files", nargs="+", type=Path, required=True)
    parser.add_argument("--metrics", nargs="+", default=DEFAULT_METRICS)
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, default=None)
    return parser.parse_args()


def csv_bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def z_value(confidence: float) -> float:
    if confidence == 0.95:
        return 1.959963984540054
    if confidence == 0.90:
        return 1.6448536269514722
    if confidence == 0.99:
        return 2.5758293035489004
    raise ValueError("Only 0.90, 0.95, and 0.99 confidence levels are supported")


def wilson_interval(positives: int, n: int, confidence: float) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 0.0
    z = z_value(confidence)
    phat = positives / n
    denominator = 1 + z**2 / n
    center = phat + z**2 / (2 * n)
    spread = z * math.sqrt((phat * (1 - phat) + z**2 / (4 * n)) / n)
    return (center - spread) / denominator, (center + spread) / denominator


def read_scores(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def metric_present(rows: Iterable[dict[str, str]], metric: str) -> bool:
    return any(metric in row for row in rows)


def compute_rows(score_files: list[Path], metrics: list[str], confidence: float) -> list[IntervalRow]:
    interval_rows = []
    for path in score_files:
        rows = read_scores(path)
        grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            grouped[(row.get("model", ""), row.get("dataset", ""))].append(row)

        for (model, dataset), group in sorted(grouped.items()):
            for metric in metrics:
                if not metric_present(group, metric):
                    continue
                positives = sum(csv_bool(row.get(metric, "")) for row in group)
                n = len(group)
                low, high = wilson_interval(positives, n, confidence)
                interval_rows.append(
                    IntervalRow(
                        model=model,
                        dataset=dataset,
                        metric=metric,
                        positives=positives,
                        n=n,
                        rate=positives / n if n else 0.0,
                        ci_low=low,
                        ci_high=high,
                        source_file=str(path),
                    )
                )
    return interval_rows


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def markdown(rows: list[IntervalRow], confidence: float) -> str:
    chunks = [
        "# Red-Team Statistical Evidence",
        "",
        (
            "This file reports count-based Wilson confidence intervals for the "
            "existing red-team pilot outputs. It is generated offline from local "
            "score CSVs and makes no model calls."
        ),
        "",
        f"Confidence level: `{confidence:.0%}`",
        "",
        "## Dataset Metrics",
        "",
        "| Dataset | Metric | Count | Rate | CI Low | CI High | Source |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        chunks.append(
            "| "
            f"`{row.dataset}` | `{row.metric}` | {row.positives}/{row.n} | "
            f"`{pct(row.rate)}` | `{pct(row.ci_low)}` | `{pct(row.ci_high)}` | "
            f"`{row.source_file}` |"
        )

    chunks.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The canary-leak result is not a single anecdote: the exact-leak rate is a count of repeated successful disclosures.",
            "- The intervals are still pilot-scale because each core deep-probe dataset has `n=100`.",
            "- These intervals quantify uncertainty in this sample; they do not remove the need for multi-model replication and human audit.",
        ]
    )
    return "\n".join(chunks) + "\n"


def main() -> None:
    args = parse_args()
    rows = compute_rows(args.score_files, args.metrics, args.confidence)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(markdown(rows, args.confidence), encoding="utf-8")

    if args.out_json is not None:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(
            json.dumps([asdict(row) for row in rows], indent=2),
            encoding="utf-8",
        )

    print(f"Wrote {len(rows)} interval rows to {args.out_md}")
    if args.out_json is not None:
        print(f"Wrote JSON to {args.out_json}")


if __name__ == "__main__":
    main()
