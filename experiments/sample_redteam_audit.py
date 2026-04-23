"""
Sample red-team cases for human audit.

This joins responses.csv with scores_v2.csv from a completed run and writes a
small redacted review set. It does not make model calls.

Example:
    python sample_redteam_audit.py \
        --run-dir results/redteam_deep_max_100 \
        --out-prefix audit_sample
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path
from typing import Any


DEFAULT_LABELS = [
    "canary_leak",
    "hierarchy_violation",
    "over_refusal",
    "refusal",
    "answered",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sample scored red-team responses for audit.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--responses", default="responses.csv")
    parser.add_argument("--scores", default="scores_v2.csv")
    parser.add_argument("--out-prefix", default="audit_sample")
    parser.add_argument("--per-label", type=int, default=8)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--labels", nargs="+", default=DEFAULT_LABELS)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def redact(text: str, canary: str) -> str:
    if not canary:
        return text
    return text.replace(canary, "[REDACTED_CANARY]")


def join_rows(responses: list[dict[str, str]], scores: list[dict[str, str]]) -> list[dict[str, str]]:
    by_id = {row["response_id"]: row for row in responses}
    joined = []
    for score in scores:
        response = by_id.get(score["response_id"])
        if response is None:
            continue
        joined.append({**response, **{f"score_{k}": v for k, v in score.items()}})
    return joined


def sample_rows(rows: list[dict[str, str]], labels: list[str], per_label: int, seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    sampled = []
    seen_ids = set()
    for label in labels:
        candidates = [row for row in rows if row.get("score_label") == label]
        rng.shuffle(candidates)
        for row in candidates[:per_label]:
            if row["response_id"] in seen_ids:
                continue
            sampled.append(row)
            seen_ids.add(row["response_id"])
    return sampled


def compact_row(row: dict[str, str]) -> dict[str, str]:
    canary = row.get("canary", "")
    return {
        "response_id": row.get("response_id", ""),
        "model": row.get("model", ""),
        "dataset": row.get("dataset", ""),
        "variant": row.get("variant", ""),
        "risk_type": row.get("risk_type", ""),
        "score_label": row.get("score_label", ""),
        "score_refused": row.get("score_refused", ""),
        "score_exact_canary_leak": row.get("score_exact_canary_leak", ""),
        "score_partial_canary_leak": row.get("score_partial_canary_leak", ""),
        "score_any_canary_leak": row.get("score_any_canary_leak", ""),
        "score_hierarchy_violation": row.get("score_hierarchy_violation", ""),
        "score_over_refusal": row.get("score_over_refusal", ""),
        "human_label": "",
        "human_notes": "",
        "prompt": redact(row.get("prompt", ""), canary),
        "response_text": redact(row.get("response_text", ""), canary),
    }


def markdown_report(rows: list[dict[str, str]]) -> str:
    chunks = ["# Red-Team Human Audit Sample", ""]
    for idx, row in enumerate(rows, start=1):
        chunks.extend(
            [
                f"## Case {idx}: {row['score_label']} / {row['dataset']} / {row['variant']}",
                "",
                f"- Response ID: `{row['response_id']}`",
                f"- Model: `{row['model']}`",
                f"- Risk type: `{row['risk_type']}`",
                f"- Exact canary leak: `{row['score_exact_canary_leak']}`",
                f"- Partial canary leak: `{row['score_partial_canary_leak']}`",
                f"- Hierarchy violation: `{row['score_hierarchy_violation']}`",
                f"- Over-refusal: `{row['score_over_refusal']}`",
                "",
                "**Prompt**",
                "",
                "```text",
                row["prompt"],
                "```",
                "",
                "**Response**",
                "",
                "```text",
                row["response_text"],
                "```",
                "",
            ]
        )
    return "\n".join(chunks)


def main() -> None:
    args = parse_args()
    responses = read_csv(args.run_dir / args.responses)
    scores = read_csv(args.run_dir / args.scores)
    joined = join_rows(responses, scores)
    sampled = sample_rows(joined, args.labels, args.per_label, args.seed)
    compact = [compact_row(row) for row in sampled]

    csv_path = args.run_dir / f"{args.out_prefix}.csv"
    md_path = args.run_dir / f"{args.out_prefix}.md"
    write_csv(csv_path, compact)
    md_path.write_text(markdown_report(compact), encoding="utf-8")

    print(f"Sampled {len(compact)} cases")
    print(f"Saved CSV to {csv_path}")
    print(f"Saved Markdown to {md_path}")


if __name__ == "__main__":
    main()
