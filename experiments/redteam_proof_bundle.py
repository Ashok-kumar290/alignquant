"""
Build a redacted vendor proof bundle from red-team response and score files.

The bundle is designed for responsible disclosure. It includes redacted prompts
and responses for representative findings, plus SHA-256 hashes over canonical
unredacted records. The hashes make the examples auditable against local raw
CSV outputs without publishing the canary or API material.

Example:
    python experiments/redteam_proof_bundle.py \
        --run-dir experiments/results/redteam_deep_max_100 \
        --out-md paper/redteam_vendor_proof_bundle.md \
        --out-json experiments/results/redteam_deep_max_100/proof_bundle.json
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_LABELS = ["canary_leak", "hierarchy_violation", "over_refusal"]
HASH_FIELDS = [
    "response_id",
    "timestamp_utc",
    "provider",
    "model",
    "prompt_id",
    "dataset",
    "risk_type",
    "difficulty",
    "variant",
    "prompt",
    "system_prompt",
    "canary",
    "temperature",
    "max_tokens",
    "response_text",
    "error",
]


@dataclass(frozen=True)
class ProofCase:
    response_id: str
    model: str
    dataset: str
    variant: str
    label: str
    risk_type: str
    exact_canary_leak: bool
    partial_canary_leak: bool
    encoded_canary_leak: bool
    any_canary_leak: bool
    hierarchy_violation: bool
    over_refusal: bool
    raw_record_sha256: str
    prompt_redacted: str
    response_redacted: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a redacted red-team proof bundle.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--responses", default="responses.csv")
    parser.add_argument("--scores", default="scores_v2.csv")
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--labels", nargs="+", default=DEFAULT_LABELS)
    parser.add_argument("--per-label", type=int, default=6)
    parser.add_argument("--seed", type=int, default=29)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def csv_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def redact(text: str, canary: str) -> str:
    if not canary:
        return text

    redacted = text.replace(canary, "[REDACTED_SECRET]")
    for chunk in re.split(r"[^A-Za-z0-9]+", canary):
        if len(chunk) >= 4:
            redacted = re.sub(
                re.escape(chunk),
                "[REDACTED_SECRET_FRAGMENT]",
                redacted,
                flags=re.IGNORECASE,
            )
    return redacted


def canonical_hash(row: dict[str, str]) -> str:
    canonical = {
        field: row.get(field, "")
        for field in HASH_FIELDS
    }
    encoded = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def join_rows(responses: list[dict[str, str]], scores: list[dict[str, str]]) -> list[dict[str, str]]:
    responses_by_id = {row["response_id"]: row for row in responses}
    joined = []
    for score in scores:
        response = responses_by_id.get(score["response_id"])
        if response is None:
            continue
        joined.append({**response, **{f"score_{key}": value for key, value in score.items()}})
    return joined


def sample_rows(rows: list[dict[str, str]], labels: list[str], per_label: int, seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    sampled = []
    seen_ids = set()
    for label in labels:
        candidates = [
            row for row in rows
            if row.get("score_label") == label and row.get("response_id") not in seen_ids
        ]
        rng.shuffle(candidates)
        selected = candidates[:per_label]
        sampled.extend(selected)
        seen_ids.update(row["response_id"] for row in selected)
    return sampled


def to_proof_case(row: dict[str, str]) -> ProofCase:
    canary = row.get("canary", "")
    return ProofCase(
        response_id=row.get("response_id", ""),
        model=row.get("model", ""),
        dataset=row.get("dataset", ""),
        variant=row.get("variant", ""),
        label=row.get("score_label", ""),
        risk_type=row.get("risk_type", ""),
        exact_canary_leak=csv_bool(row.get("score_exact_canary_leak", "")),
        partial_canary_leak=csv_bool(row.get("score_partial_canary_leak", "")),
        encoded_canary_leak=csv_bool(row.get("score_encoded_canary_leak", "")),
        any_canary_leak=csv_bool(row.get("score_any_canary_leak", "")),
        hierarchy_violation=csv_bool(row.get("score_hierarchy_violation", "")),
        over_refusal=csv_bool(row.get("score_over_refusal", "")),
        raw_record_sha256=canonical_hash(row),
        prompt_redacted=redact(row.get("prompt", ""), canary),
        response_redacted=redact(row.get("response_text", ""), canary),
    )


def summarize(cases: list[ProofCase]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        counts[case.label] = counts.get(case.label, 0) + 1
    return counts


def clean_block(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines())


def markdown(cases: list[ProofCase], run_dir: Path) -> str:
    counts = summarize(cases)
    chunks = [
        "# Red-Team Vendor Proof Bundle",
        "",
        (
            "This bundle contains redacted representative cases from the local "
            "red-team run. Each case includes a SHA-256 hash over a canonical "
            "unredacted raw record so the example can be verified against the "
            "local CSV artifacts without publishing the synthetic canary."
        ),
        "",
        f"Source run directory: `{run_dir}`",
        "",
        "## Included Cases",
        "",
        "| Label | Count |",
        "| --- | ---: |",
    ]
    for label, count in sorted(counts.items()):
        chunks.append(f"| `{label}` | {count} |")

    chunks.extend(
        [
            "",
            "## Verification Method",
            "",
            "For each case, hash the canonical JSON object containing these raw CSV fields:",
            "",
            "```text",
            ", ".join(HASH_FIELDS),
            "```",
            "",
            "JSON must be serialized with sorted keys and compact separators before SHA-256 hashing.",
            "",
            "## Cases",
            "",
        ]
    )

    for index, case in enumerate(cases, start=1):
        chunks.extend(
            [
                f"### Case {index}: {case.label} / {case.dataset} / {case.variant}",
                "",
                f"- Response ID: `{case.response_id}`",
                f"- Model: `{case.model}`",
                f"- Risk type: `{case.risk_type}`",
                f"- Exact canary leak: `{case.exact_canary_leak}`",
                f"- Partial canary leak: `{case.partial_canary_leak}`",
                f"- Encoded canary leak: `{case.encoded_canary_leak}`",
                f"- Any canary leak: `{case.any_canary_leak}`",
                f"- Hierarchy violation: `{case.hierarchy_violation}`",
                f"- Over-refusal: `{case.over_refusal}`",
                f"- Raw record SHA-256: `{case.raw_record_sha256}`",
                "",
                "**Prompt**",
                "",
                "```text",
                clean_block(case.prompt_redacted),
                "```",
                "",
                "**Response**",
                "",
                "```text",
                clean_block(case.response_redacted),
                "```",
                "",
            ]
        )
    while chunks and chunks[-1] == "":
        chunks.pop()
    return "\n".join(line.rstrip() for line in chunks) + "\n"


def main() -> None:
    args = parse_args()
    responses = read_csv(args.run_dir / args.responses)
    scores = read_csv(args.run_dir / args.scores)
    joined = join_rows(responses, scores)
    sampled = sample_rows(joined, args.labels, args.per_label, args.seed)
    cases = [to_proof_case(row) for row in sampled]

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(markdown(cases, args.run_dir), encoding="utf-8")

    if args.out_json is not None:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(
            json.dumps([asdict(case) for case in cases], indent=2),
            encoding="utf-8",
        )

    print(f"Wrote {len(cases)} proof cases to {args.out_md}")
    if args.out_json is not None:
        print(f"Wrote JSON to {args.out_json}")


if __name__ == "__main__":
    main()
