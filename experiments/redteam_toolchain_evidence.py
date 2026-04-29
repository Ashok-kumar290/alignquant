"""
Generate statistical and appendix evidence for the clean tool-chain run.

This is an offline analysis helper. It reads the tool-chain responses CSV,
computes Wilson intervals for aggregate metrics, and writes a redacted appendix
with representative hashed cases.

Example:
    python experiments/redteam_toolchain_evidence.py \
        --responses experiments/results/redteam_toolchain_exfiltration_clean_3x8/responses.csv \
        --out-stats-md paper/redteam_toolchain_statistical_evidence.md \
        --out-appendix-md paper/redteam_toolchain_appendix.md
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_METRICS = [
    "first_turn_any_canary_leak",
    "final_exact_canary_leak",
    "final_any_canary_leak",
    "transcript_any_canary_leak",
    "final_refused",
]

PREFERRED_CASES = [
    ("command-r7b-12-2024", "summary-then-direct", "final_exact_canary_leak", "exact-exfiltration"),
    ("command-r7b-12-2024", "fields-then-value", "final_exact_canary_leak", "exact-exfiltration"),
    ("command-r7b-12-2024", "safe-json-then-unsafe-json", "final_exact_canary_leak", "exact-exfiltration"),
    ("command-r7b-12-2024", "transform-then-original", "final_exact_canary_leak", "exact-exfiltration"),
    ("command-r-plus-08-2024", "safe-json-then-unsafe-json", "final_exact_canary_leak", "rare-exact-or-near-exact"),
    ("command-r-plus-08-2024", "summary-then-direct", "final_any_canary_leak", "partial-disclosure"),
    ("command-a-03-2025", "fields-then-value", "final_any_canary_leak", "format-leak"),
    ("command-a-03-2025", "summary-then-direct", "final_refused", "clean-refusal"),
]


@dataclass(frozen=True)
class IntervalRow:
    model: str
    metric: str
    positives: int
    n: int
    rate: float
    ci_low: float
    ci_high: float


@dataclass(frozen=True)
class AppendixCase:
    section: str
    model: str
    case_id: str
    variant: str
    canary_id: str
    raw_record_sha256: str
    first_turn_any_canary_leak: bool
    final_exact_canary_leak: bool
    final_partial_canary_leak: bool
    final_any_canary_leak: bool
    final_refused: bool
    first_response_redacted: str
    final_response_redacted: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create statistical and appendix evidence for tool-chain red-team results.")
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--metrics", nargs="+", default=DEFAULT_METRICS)
    parser.add_argument("--out-stats-md", type=Path, required=True)
    parser.add_argument("--out-appendix-md", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, default=None)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def csv_bool(value: Any) -> bool:
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


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def compute_intervals(rows: list[dict[str, str]], metrics: list[str], confidence: float) -> list[IntervalRow]:
    interval_rows: list[IntervalRow] = []
    models = sorted({row["model"] for row in rows})
    for model in models:
        group = [row for row in rows if row["model"] == model]
        n = len(group)
        for metric in metrics:
            positives = sum(csv_bool(row.get(metric, "")) for row in group)
            low, high = wilson_interval(positives, n, confidence)
            interval_rows.append(
                IntervalRow(
                    model=model,
                    metric=metric,
                    positives=positives,
                    n=n,
                    rate=positives / n if n else 0.0,
                    ci_low=low,
                    ci_high=high,
                )
            )
    return interval_rows


def raw_record_hash(row: dict[str, str]) -> str:
    encoded = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def redact(text: str, canary: str) -> str:
    if not canary:
        return text
    return text.replace(canary, "[REDACTED_SECRET]")


def select_case(rows: list[dict[str, str]], model: str, variant: str, metric: str) -> dict[str, str] | None:
    candidates = [
        row for row in rows
        if row["model"] == model
        and row["variant"] == variant
        and csv_bool(row.get(metric, ""))
    ]
    if candidates:
        return candidates[0]
    return None


def build_appendix_cases(rows: list[dict[str, str]]) -> list[AppendixCase]:
    cases: list[AppendixCase] = []
    for model, variant, metric, section in PREFERRED_CASES:
        row = select_case(rows, model, variant, metric)
        if row is None:
            continue
        canary = ""
        tool_context = row.get("tool_context", "")
        marker = '"audit_token": "'
        if marker in tool_context:
            canary = tool_context.split(marker, 1)[1].split('"', 1)[0]
        cases.append(
            AppendixCase(
                section=section,
                model=row["model"],
                case_id=row["case_id"],
                variant=row["variant"],
                canary_id=row["canary_id"],
                raw_record_sha256=raw_record_hash(row),
                first_turn_any_canary_leak=csv_bool(row.get("first_turn_any_canary_leak", "")),
                final_exact_canary_leak=csv_bool(row.get("final_exact_canary_leak", "")),
                final_partial_canary_leak=csv_bool(row.get("final_partial_canary_leak", "")),
                final_any_canary_leak=csv_bool(row.get("final_any_canary_leak", "")),
                final_refused=csv_bool(row.get("final_refused", "")),
                first_response_redacted=redact(row.get("first_response_text", ""), canary),
                final_response_redacted=redact(row.get("final_response_text", ""), canary),
            )
        )
    return cases


def stats_markdown(intervals: list[IntervalRow], confidence: float, rows: list[dict[str, str]]) -> str:
    chunks = [
        "# Tool-Chain Statistical Evidence",
        "",
        (
            "This file reports count-based Wilson confidence intervals for the "
            "clean multi-turn tool-chain exfiltration rerun. It is generated "
            "offline from the local responses CSV and makes no model calls."
        ),
        "",
        f"Confidence level: `{confidence:.0%}`",
        "",
        "## Aggregate Metrics",
        "",
        "| Model | Metric | Count | Rate | CI Low | CI High |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in intervals:
        chunks.append(
            "| "
            f"`{row.model}` | `{row.metric}` | {row.positives}/{row.n} | "
            f"`{pct(row.rate)}` | `{pct(row.ci_low)}` | `{pct(row.ci_high)}` |"
        )

    chunks.extend(
        [
            "",
            "## Variant Spotlights",
            "",
            "| Model | Variant | Final Exact Leak | Final Any Leak | Final Refusal |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for model, variant in [
        ("command-r7b-12-2024", "summary-then-direct"),
        ("command-r7b-12-2024", "fields-then-value"),
        ("command-r7b-12-2024", "safe-json-then-unsafe-json"),
        ("command-r7b-12-2024", "transform-then-original"),
        ("command-r-plus-08-2024", "summary-then-direct"),
        ("command-a-03-2025", "fields-then-value"),
    ]:
        group = [row for row in rows if row["model"] == model and row["variant"] == variant]
        if not group:
            continue
        n = len(group)
        final_exact = sum(csv_bool(row.get("final_exact_canary_leak", "")) for row in group)
        final_any = sum(csv_bool(row.get("final_any_canary_leak", "")) for row in group)
        final_refused = sum(csv_bool(row.get("final_refused", "")) for row in group)
        chunks.append(
            "| "
            f"`{model}` | `{variant}` | `{final_exact}/{n}` | `{final_any}/{n}` | `{final_refused}/{n}` |"
        )

    chunks.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `command-r7b-12-2024` still shows a strong two-turn exfiltration path after an apparently safe first-step summary.",
            "- `command-r-plus-08-2024` and `command-a-03-2025` are materially stronger on exact final-turn leakage in this clean rerun, but residual partial disclosures remain in a few cases.",
            "- This experiment is stronger than the earlier noisy draft because the canary format no longer shares suffix text with the refusal policy.",
        ]
    )
    return "\n".join(chunks) + "\n"


def appendix_markdown(cases: list[AppendixCase], source_path: Path) -> str:
    def fenced_block(text: str) -> list[str]:
        fence = "```"
        if "```" in text:
            fence = "````"
        return [fence, text, fence]

    chunks = [
        "# Tool-Chain Audit Appendix",
        "",
        (
            "This appendix contains redacted representative cases from the clean "
            "tool-chain exfiltration rerun. Each case includes a SHA-256 hash of "
            "the full raw CSV row so it can be verified against the local result "
            "artifact without publishing the synthetic secret."
        ),
        "",
        f"Source file: `{source_path}`",
        "",
    ]
    for idx, case in enumerate(cases, start=1):
        chunks.extend(
            [
                f"## Case {idx}: {case.section} / {case.model} / {case.variant}",
                "",
                f"- Case ID: `{case.case_id}`",
                f"- Canary ID: `{case.canary_id}`",
                f"- First-turn any leak: `{case.first_turn_any_canary_leak}`",
                f"- Final exact leak: `{case.final_exact_canary_leak}`",
                f"- Final partial leak: `{case.final_partial_canary_leak}`",
                f"- Final any leak: `{case.final_any_canary_leak}`",
                f"- Final refusal: `{case.final_refused}`",
                f"- Raw row SHA-256: `{case.raw_record_sha256}`",
                "",
                "**First Turn**",
                "",
                *fenced_block(case.first_response_redacted),
                "",
                "**Final Turn**",
                "",
                *fenced_block(case.final_response_redacted),
                "",
            ]
        )
    return "\n".join(chunks).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    rows = read_csv(args.responses)
    intervals = compute_intervals(rows, args.metrics, args.confidence)
    appendix_cases = build_appendix_cases(rows)

    args.out_stats_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_stats_md.write_text(stats_markdown(intervals, args.confidence, rows), encoding="utf-8")

    args.out_appendix_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_appendix_md.write_text(appendix_markdown(appendix_cases, args.responses), encoding="utf-8")

    if args.out_json is not None:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(
            json.dumps(
                {
                    "intervals": [asdict(row) for row in intervals],
                    "appendix_cases": [asdict(case) for case in appendix_cases],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    print(f"Wrote statistical evidence to {args.out_stats_md}")
    print(f"Wrote appendix evidence to {args.out_appendix_md}")
    if args.out_json is not None:
        print(f"Wrote JSON to {args.out_json}")


if __name__ == "__main__":
    main()
