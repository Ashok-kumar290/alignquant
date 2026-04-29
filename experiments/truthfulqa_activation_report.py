"""
Build a paper-ready markdown summary from a TruthfulQA activation pilot run.

This is an offline report generator for outputs created by
`truthfulqa_quant_cosine.py`.

Example:
    python truthfulqa_activation_report.py \
        --run-dir results/truthfulqa_r7b_nf4 \
        --out-md ../paper/truthfulqa_r7b_nf4_report.md
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a markdown report for a TruthfulQA activation run.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--summary", default="summary.json")
    parser.add_argument("--layer-summary", default="layer_summary.csv")
    parser.add_argument("--category-summary", default="category_layer_summary.csv")
    parser.add_argument("--metadata", default="run_metadata.json")
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument("--top-categories", type=int, default=8)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def markdown(metadata: dict, aggregate: dict, layer_rows: list[dict[str, str]], category_rows: list[dict[str, str]], top_categories: int) -> str:
    most_shifted_layer = aggregate.get("most_shifted_layer", {})
    best_preserved_layer = aggregate.get("best_preserved_layer", {})
    most_shifted_category = aggregate.get("most_shifted_category", {})
    best_preserved_category = aggregate.get("best_preserved_category", {})

    chunks = [
        "# TruthfulQA Activation Geometry Report",
        "",
        "This file summarizes a completed FP16-vs-quantized activation pilot on TruthfulQA prompts.",
        "",
        "## Run Metadata",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Model | `{metadata.get('model_id', '')}` |",
        f"| Baseline | `{metadata.get('baseline_scheme', '')}` |",
        f"| Quant scheme | `{metadata.get('quant_scheme', '')}` |",
        f"| Layers | `{metadata.get('layers', [])}` |",
        f"| Prompt count | `{metadata.get('n_prompts', '')}` |",
        f"| Max length | `{metadata.get('max_length', '')}` |",
        f"| Chat template | `{metadata.get('use_chat_template', '')}` |",
        "",
        "## Headline Readout",
        "",
        f"- Overall mean prompt cosine: `{aggregate.get('overall_mean_prompt_cosine', 0.0):.4f}`",
        f"- Overall mean-vector cosine: `{aggregate.get('overall_mean_vector_cosine', 0.0):.4f}`",
    ]

    if most_shifted_layer:
        chunks.append(
            f"- Most shifted layer: `{int(float(most_shifted_layer['layer']))}` with mean prompt cosine `{float(most_shifted_layer['mean_prompt_cosine']):.4f}`"
        )
    if best_preserved_layer:
        chunks.append(
            f"- Best preserved layer: `{int(float(best_preserved_layer['layer']))}` with mean prompt cosine `{float(best_preserved_layer['mean_prompt_cosine']):.4f}`"
        )
    if most_shifted_category:
        chunks.append(
            f"- Most shifted category-layer pair: `{most_shifted_category['category']}` @ layer `{int(float(most_shifted_category['layer']))}` with mean prompt cosine `{float(most_shifted_category['mean_prompt_cosine']):.4f}`"
        )
    if best_preserved_category:
        chunks.append(
            f"- Best preserved category-layer pair: `{best_preserved_category['category']}` @ layer `{int(float(best_preserved_category['layer']))}` with mean prompt cosine `{float(best_preserved_category['mean_prompt_cosine']):.4f}`"
        )

    chunks.extend(
        [
            "",
            "## Layer Summary",
            "",
            "| Layer | Mean Prompt Cosine | Std | Mean-Vector Cosine | FP16 Norm | Quant Norm |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in layer_rows:
        chunks.append(
            "| "
            f"{row['layer']} | `{float(row['mean_prompt_cosine']):.4f}` | `{float(row['std_prompt_cosine']):.4f}` | "
            f"`{float(row['aggregate_mean_vector_cosine']):.4f}` | `{float(row['fp16_mean_norm']):.4f}` | `{float(row['quant_mean_norm']):.4f}` |"
        )

    chunks.extend(
        [
            "",
            "## Most Shifted Categories",
            "",
            "| Layer | Category | N | Mean Prompt Cosine | Std |",
            "| ---: | --- | ---: | ---: | ---: |",
        ]
    )
    for row in category_rows[:top_categories]:
        chunks.append(
            "| "
            f"{row['layer']} | `{row['category']}` | {row['n_prompts']} | "
            f"`{float(row['mean_prompt_cosine']):.4f}` | `{float(row['std_prompt_cosine']):.4f}` |"
        )

    chunks.extend(
        [
            "",
            "## Interpretation Template",
            "",
            "- Lower cosine indicates a larger activation-space shift between FP16 and the quantized model.",
            "- If low-cosine layers cluster around the same residual-stream region across models, that supports a localized alignment-tax story.",
            "- If category-sensitive shifts are concentrated in truthfulness-heavy categories, that strengthens the case for axis-specific degradation rather than uniform numerical noise.",
        ]
    )
    return "\n".join(chunks) + "\n"


def main() -> None:
    args = parse_args()
    metadata = json.loads((args.run_dir / args.metadata).read_text(encoding="utf-8"))
    aggregate = json.loads((args.run_dir / args.summary).read_text(encoding="utf-8"))
    layer_rows = read_csv(args.run_dir / args.layer_summary)
    category_rows = read_csv(args.run_dir / args.category_summary)
    category_rows.sort(key=lambda row: float(row["mean_prompt_cosine"]))

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(
        markdown(metadata, aggregate, layer_rows, category_rows, args.top_categories),
        encoding="utf-8",
    )
    print(f"Wrote report to {args.out_md}")


if __name__ == "__main__":
    main()
