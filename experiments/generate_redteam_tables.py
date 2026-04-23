"""
Generate compact red-team result tables from completed run summaries.

This script does not make model calls. It reads the baseline and deep-probe
summary JSON files and writes publication-friendly CSV and Markdown tables.

Example:
    python generate_redteam_tables.py \
        --baseline-run results/redteam_behavior_max_100 \
        --deep-run results/redteam_deep_max_100 \
        --out-dir results/redteam_tables
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate red-team result tables.")
    parser.add_argument("--baseline-run", type=Path, required=True)
    parser.add_argument("--deep-run", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("results/redteam_tables"))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dataset_row(summary: dict[str, Any], dataset: str) -> dict[str, Any]:
    for row in summary["by_model_dataset"]:
        if row["dataset"] == dataset:
            return row
    raise KeyError(dataset)


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    baseline = load_json(args.baseline_run / "summary.json")
    deep = load_json(args.deep_run / "summary_v2.json")

    advbench = dataset_row(baseline, "advbench")
    benign = dataset_row(baseline, "benign_refusal")
    truthfulqa = dataset_row(baseline, "truthfulqa")
    canary = dataset_row(deep, "canary_leak")
    hierarchy = dataset_row(deep, "hierarchy_attack")
    boundary = dataset_row(deep, "boundary_probe")

    rows = [
        {
            "test": "Max AdvBench",
            "model": advbench["model"],
            "n": advbench["n"],
            "metric": "unsafe_compliance_rate",
            "value": pct(advbench["unsafe_compliance_rate"]),
            "interpretation": "harmful-request compliance was not observed",
        },
        {
            "test": "Max AdvBench",
            "model": advbench["model"],
            "n": advbench["n"],
            "metric": "refusal_rate",
            "value": pct(advbench["refusal_rate"]),
            "interpretation": "all sampled harmful requests were refused",
        },
        {
            "test": "Benign refusal controls",
            "model": benign["model"],
            "n": benign["n"],
            "metric": "over_refusal_rate",
            "value": pct(benign["over_refusal_rate"]),
            "interpretation": "safe requests sometimes triggered refusal",
        },
        {
            "test": "TruthfulQA",
            "model": truthfulqa["model"],
            "n": truthfulqa["n"],
            "metric": "refusal_rate",
            "value": pct(truthfulqa["refusal_rate"]),
            "interpretation": "some factual prompts were refused",
        },
        {
            "test": "Canary leakage",
            "model": canary["model"],
            "n": canary["n"],
            "metric": "exact_canary_leak_rate",
            "value": pct(canary["exact_canary_leak_rate"]),
            "interpretation": "exact synthetic secret was exposed",
        },
        {
            "test": "Canary leakage",
            "model": canary["model"],
            "n": canary["n"],
            "metric": "any_canary_leak_rate",
            "value": pct(canary["any_canary_leak_rate"]),
            "interpretation": "exact or distinctive partial secret leakage",
        },
        {
            "test": "Instruction hierarchy",
            "model": hierarchy["model"],
            "n": hierarchy["n"],
            "metric": "hierarchy_violation_rate",
            "value": pct(hierarchy["hierarchy_violation_rate"]),
            "interpretation": "some responses accepted false authority framing",
        },
        {
            "test": "Boundary probes",
            "model": boundary["model"],
            "n": boundary["n"],
            "metric": "over_refusal_rate",
            "value": pct(boundary["over_refusal_rate"]),
            "interpretation": "safe dual-use prompts sometimes over-refused",
        },
    ]

    csv_path = args.out_dir / "headline_results.csv"
    md_path = args.out_dir / "headline_results.md"
    write_csv(csv_path, rows)

    table_rows = [
        [row["test"], row["model"], str(row["n"]), row["metric"], row["value"], row["interpretation"]]
        for row in rows
    ]
    md = "\n".join(
        [
            "# Red-Team Headline Results",
            "",
            markdown_table(
                ["Test", "Model", "N", "Metric", "Value", "Interpretation"],
                table_rows,
            ),
            "",
            "Generated from:",
            "",
            f"- `{args.baseline_run / 'summary.json'}`",
            f"- `{args.deep_run / 'summary_v2.json'}`",
            "",
        ]
    )
    md_path.write_text(md, encoding="utf-8")

    print(f"Saved CSV to {csv_path}")
    print(f"Saved Markdown to {md_path}")


if __name__ == "__main__":
    main()
